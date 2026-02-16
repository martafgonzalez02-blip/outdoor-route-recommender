"""
Construccion de perfiles de usuario a partir de fact_activities + dim_routes.

Solo actividades completadas cuentan para preferencias (abandonos = mismatch).
Usuarios con < FEATURE_MIN_ACTIVITIES completadas usan fallback a datos declarados.
"""

import math
from collections import Counter

from src.config import (
    ACTIVITY_TYPE_IDS,
    DIFFICULTY_NUMERIC_MAP,
    EXPERIENCE_NUMERIC_MAP,
    FEATURE_MIN_ACTIVITIES,
    TERRAIN_TYPE_IDS,
)


# Mapas inversos para labels
_ACT_ID_TO_NAME = {v: k for k, v in ACTIVITY_TYPE_IDS.items()}
_TERRAIN_ID_TO_NAME = {v: k for k, v in TERRAIN_TYPE_IDS.items()}


def build_user_profiles(users, routes, activities):
    """Construye perfil de features para cada usuario.

    Args:
        users: lista de dicts (de users.csv).
        routes: lista de dicts (de routes.csv).
        activities: lista de dicts (de activities.csv).

    Returns:
        list[dict]: un dict por usuario con ~35 features.
    """
    # Indexar rutas por id
    routes_by_id = {}
    for r in routes:
        rid = int(r["route_id"])
        routes_by_id[rid] = r

    # Agrupar actividades por usuario
    user_activities = {}
    for a in activities:
        uid = int(a["user_id"])
        user_activities.setdefault(uid, []).append(a)

    # Construir perfiles
    profiles = []
    for u in users:
        uid = int(u["user_id"])
        acts = user_activities.get(uid, [])
        profile = _build_one_profile(u, acts, routes_by_id)
        profiles.append(profile)

    return profiles


def _build_one_profile(user, activities, routes_by_id):
    """Construye el perfil de un usuario."""
    uid = int(user["user_id"])

    # Separar completadas y todas
    all_acts = activities
    completed = [a for a in all_acts if _is_completed(a)]
    n_total = len(all_acts)
    n_completed = len(completed)
    has_sufficient = n_completed >= FEATURE_MIN_ACTIVITIES

    # --- Volumen y engagement ---
    completion_rate = n_completed / n_total if n_total > 0 else 0.0

    rated = [a for a in all_acts if a.get("rating", "") != ""]
    n_rated = len(rated)
    avg_rating_given = (
        sum(int(a["rating"]) for a in rated) / n_rated if n_rated > 0 else None
    )

    # Temporales
    if n_total > 0:
        dates = sorted(_parse_date_str(a["activity_date"]) for a in all_acts)
        first_date = dates[0]
        last_date = dates[-1]
        activity_span_days = (last_date - first_date).days
        # Dias desde ultima actividad hasta fin del dataset (2024-12-31)
        from datetime import date
        ref_date = date(2024, 12, 31)
        days_since_last = (ref_date - last_date).days
        months = max(1, activity_span_days / 30.0)
        activities_per_month = n_total / months
    else:
        activity_span_days = 0
        days_since_last = None
        activities_per_month = 0.0

    # --- Features sobre completadas ---
    if has_sufficient:
        profile_acts = completed
    else:
        profile_acts = completed  # usamos las que hay, fallback en categoricas

    # Enriquecer con datos de ruta
    enriched = []
    for a in profile_acts:
        rid = int(a["route_id"])
        r = routes_by_id.get(rid, {})
        enriched.append((a, r))

    # --- Preferencia de dificultad ---
    if enriched:
        diffs = [r.get("difficulty", "") for _, r in enriched]
        diff_counter = Counter(diffs)
        n_diff = len(diffs)
        pct_easy = diff_counter.get("easy", 0) / n_diff
        pct_moderate = diff_counter.get("moderate", 0) / n_diff
        pct_hard = diff_counter.get("hard", 0) / n_diff
        pct_expert = diff_counter.get("expert", 0) / n_diff
        avg_difficulty_num = sum(
            DIFFICULTY_NUMERIC_MAP.get(d, 2) for d in diffs
        ) / n_diff
    else:
        # Fallback a experience_level declarado
        exp = user.get("experience_level", "intermediate")
        exp_num = EXPERIENCE_NUMERIC_MAP.get(exp, 2)
        pct_easy = 1.0 if exp_num == 1 else 0.0
        pct_moderate = 1.0 if exp_num == 2 else 0.0
        pct_hard = 1.0 if exp_num == 3 else 0.0
        pct_expert = 1.0 if exp_num == 4 else 0.0
        avg_difficulty_num = float(exp_num)

    # --- Preferencia de actividad ---
    if enriched:
        act_types = [int(r.get("activity_type_id", 0)) for _, r in enriched]
        act_counter = Counter(act_types)
        n_acts_typed = len(act_types)
        pct_hiking = act_counter.get(ACTIVITY_TYPE_IDS["hiking"], 0) / n_acts_typed
        pct_trail_running = act_counter.get(ACTIVITY_TYPE_IDS["trail_running"], 0) / n_acts_typed
        pct_cycling = act_counter.get(ACTIVITY_TYPE_IDS["cycling"], 0) / n_acts_typed
    else:
        # Fallback a preferred_activity_type_id declarado
        pref = user.get("preferred_activity_type_id", "")
        pref_id = int(pref) if pref != "" else None
        pct_hiking = 1.0 if pref_id == ACTIVITY_TYPE_IDS["hiking"] else 0.0
        pct_trail_running = 1.0 if pref_id == ACTIVITY_TYPE_IDS["trail_running"] else 0.0
        pct_cycling = 1.0 if pref_id == ACTIVITY_TYPE_IDS["cycling"] else 0.0
        # Si no tiene preferencia, distribucion uniforme
        if pref_id is None:
            pct_hiking = 1.0 / 3.0
            pct_trail_running = 1.0 / 3.0
            pct_cycling = 1.0 / 3.0

    # --- Perfil fisico ---
    if enriched:
        distances = [float(r.get("distance_km", 0)) for _, r in enriched]
        elevations = [int(r.get("elevation_gain_m", 0)) for _, r in enriched]
        durations = [float(a.get("actual_duration_h", 0)) for a, _ in enriched]
        estimated = [float(r.get("estimated_duration_h", 1)) for _, r in enriched]

        avg_distance_km = _mean(distances)
        std_distance_km = _std(distances)
        avg_elevation_gain_m = _mean(elevations)
        std_elevation_gain_m = _std(elevations)
        avg_duration_h = _mean(durations)

        # Pace factor: actual / estimated (< 1 = mas rapido que estimado)
        pace_factors = [
            float(a.get("actual_duration_h", 0)) / float(r.get("estimated_duration_h", 1))
            for a, r in enriched
            if float(r.get("estimated_duration_h", 1)) > 0
        ]
        avg_pace_factor = _mean(pace_factors) if pace_factors else None
    else:
        avg_distance_km = None
        std_distance_km = None
        avg_elevation_gain_m = None
        std_elevation_gain_m = None
        avg_duration_h = None
        avg_pace_factor = None

    # --- Preferencia geografica ---
    if enriched:
        zones = [int(r.get("zone_id", 0)) for _, r in enriched]
        zone_counter = Counter(zones)
        n_zones_total = len(zones)
        num_distinct_zones = len(zone_counter)

        # Top 3 zonas
        top_zones = zone_counter.most_common(3)
        top_zone_1_id = top_zones[0][0] if len(top_zones) >= 1 else None
        top_zone_1_pct = top_zones[0][1] / n_zones_total if len(top_zones) >= 1 else 0.0
        top_zone_2_id = top_zones[1][0] if len(top_zones) >= 2 else None
        top_zone_2_pct = top_zones[1][1] / n_zones_total if len(top_zones) >= 2 else 0.0
        top_zone_3_id = top_zones[2][0] if len(top_zones) >= 3 else None
    else:
        num_distinct_zones = 0
        top_zone_1_id = None
        top_zone_1_pct = 0.0
        top_zone_2_id = None
        top_zone_2_pct = 0.0
        top_zone_3_id = None

    # --- Preferencia de terreno ---
    if enriched:
        terrains = [int(r.get("terrain_type_id", 0)) for _, r in enriched]
        terrain_counter = Counter(terrains)
        n_terrain = len(terrains)
        pct_mountain = terrain_counter.get(TERRAIN_TYPE_IDS["mountain"], 0) / n_terrain
        pct_coastal = terrain_counter.get(TERRAIN_TYPE_IDS["coastal"], 0) / n_terrain
        pct_forest = terrain_counter.get(TERRAIN_TYPE_IDS["forest"], 0) / n_terrain
        pct_urban_park = terrain_counter.get(TERRAIN_TYPE_IDS["urban_park"], 0) / n_terrain
        pct_desert = terrain_counter.get(TERRAIN_TYPE_IDS["desert"], 0) / n_terrain
    else:
        pct_mountain = 0.0
        pct_coastal = 0.0
        pct_forest = 0.0
        pct_urban_park = 0.0
        pct_desert = 0.0

    # --- Formato de ruta ---
    if enriched:
        circulars = sum(1 for _, r in enriched if int(r.get("is_circular", 0)) == 1)
        pct_circular = circulars / len(enriched)
    else:
        pct_circular = 0.0

    return {
        "user_id": uid,
        # Volumen
        "total_activities": n_total,
        "completed_activities": n_completed,
        "completion_rate": _round(completion_rate, 4),
        "rated_activities": n_rated,
        "avg_rating_given": _round(avg_rating_given, 2),
        "days_since_last_activity": days_since_last,
        "activity_span_days": activity_span_days,
        "activities_per_month": _round(activities_per_month, 2),
        # Dificultad
        "pct_easy": _round(pct_easy, 4),
        "pct_moderate": _round(pct_moderate, 4),
        "pct_hard": _round(pct_hard, 4),
        "pct_expert": _round(pct_expert, 4),
        "avg_difficulty_num": _round(avg_difficulty_num, 2),
        # Actividad
        "pct_hiking": _round(pct_hiking, 4),
        "pct_trail_running": _round(pct_trail_running, 4),
        "pct_cycling": _round(pct_cycling, 4),
        # Fisico
        "avg_distance_km": _round(avg_distance_km, 2),
        "std_distance_km": _round(std_distance_km, 2),
        "avg_elevation_gain_m": _round(avg_elevation_gain_m, 1),
        "std_elevation_gain_m": _round(std_elevation_gain_m, 1),
        "avg_duration_h": _round(avg_duration_h, 2),
        "avg_pace_factor": _round(avg_pace_factor, 3),
        # Geografica
        "top_zone_1_id": top_zone_1_id,
        "top_zone_1_pct": _round(top_zone_1_pct, 4),
        "top_zone_2_id": top_zone_2_id,
        "top_zone_2_pct": _round(top_zone_2_pct, 4),
        "top_zone_3_id": top_zone_3_id,
        "num_distinct_zones": num_distinct_zones,
        # Terreno
        "pct_mountain": _round(pct_mountain, 4),
        "pct_coastal": _round(pct_coastal, 4),
        "pct_forest": _round(pct_forest, 4),
        "pct_urban_park": _round(pct_urban_park, 4),
        "pct_desert": _round(pct_desert, 4),
        # Formato
        "pct_circular": _round(pct_circular, 4),
        # Meta
        "has_sufficient_data": 1 if has_sufficient else 0,
    }


# =============================================================================
# Helpers
# =============================================================================

def _is_completed(activity):
    """Determina si una actividad fue completada."""
    val = activity.get("completed", "1")
    return str(val) in ("1", "True", "true")


def _parse_date_str(date_str):
    """Parsea una fecha ISO (YYYY-MM-DD) sin dependencias."""
    from datetime import date
    parts = date_str.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def _mean(values):
    """Media de una lista de numeros. None si vacia."""
    if not values:
        return None
    return sum(values) / len(values)


def _std(values):
    """Desviacion estandar poblacional. None si < 2 valores."""
    if len(values) < 2:
        return 0.0 if values else None
    avg = sum(values) / len(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def _round(value, decimals):
    """Round que maneja None."""
    if value is None:
        return None
    return round(value, decimals)
