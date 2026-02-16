"""
Construccion de features de ruta a partir de dim_routes + fact_activities.

Combina atributos estaticos de la ruta con metricas agregadas de uso.
"""

from collections import Counter

from src.config import (
    DIFFICULTY_NUMERIC_MAP,
    EXPERIENCE_NUMERIC_MAP,
)


def build_route_features(routes, activities, users):
    """Construye features para cada ruta.

    Args:
        routes: lista de dicts (de routes.csv).
        activities: lista de dicts (de activities.csv).
        users: lista de dicts (de users.csv).

    Returns:
        list[dict]: un dict por ruta con atributos + metricas.
    """
    # Indexar usuarios por id
    users_by_id = {}
    for u in users:
        users_by_id[int(u["user_id"])] = u

    # Agrupar actividades por ruta
    route_activities = {}
    for a in activities:
        rid = int(a["route_id"])
        route_activities.setdefault(rid, []).append(a)

    features = []
    for r in routes:
        rid = int(r["route_id"])
        acts = route_activities.get(rid, [])
        feat = _build_one_route(r, acts, users_by_id)
        features.append(feat)

    return features


def _build_one_route(route, activities, users_by_id):
    """Construye features de una ruta."""
    rid = int(route["route_id"])

    # --- Atributos estaticos ---
    distance_km = float(route["distance_km"])
    elevation_gain_m = int(route["elevation_gain_m"])
    elevation_loss_m = int(route["elevation_loss_m"])
    estimated_duration_h = float(route["estimated_duration_h"])
    difficulty = route["difficulty"]
    difficulty_num = DIFFICULTY_NUMERIC_MAP.get(difficulty, 2)
    is_circular = int(route.get("is_circular", 0))
    activity_type_id = int(route["activity_type_id"])
    terrain_type_id = int(route["terrain_type_id"])
    zone_id = int(route["zone_id"])

    # --- Metricas agregadas ---
    n_total = len(activities)
    unique_users = len(set(int(a["user_id"]) for a in activities)) if activities else 0

    completed = [a for a in activities if _is_completed(a)]
    n_completed = len(completed)
    completion_rate = n_completed / n_total if n_total > 0 else None

    # Ratings
    rated = [a for a in activities if a.get("rating", "") != ""]
    n_ratings = len(rated)
    avg_rating = (
        sum(int(a["rating"]) for a in rated) / n_ratings if n_ratings > 0 else None
    )

    # Duracion real
    durations = [float(a["actual_duration_h"]) for a in completed if a.get("actual_duration_h")]
    avg_actual_duration_h = (
        sum(durations) / len(durations) if durations else None
    )

    # Duration accuracy: actual / estimated
    duration_accuracy = (
        avg_actual_duration_h / estimated_duration_h
        if avg_actual_duration_h is not None and estimated_duration_h > 0
        else None
    )

    # --- Perfil demografico de usuarios ---
    if activities:
        user_ids = set(int(a["user_id"]) for a in activities)
        exp_counter = Counter()
        for uid in user_ids:
            u = users_by_id.get(uid)
            if u:
                exp = u.get("experience_level", "intermediate")
                exp_counter[exp] += 1
        n_users_profiled = sum(exp_counter.values())
        if n_users_profiled > 0:
            pct_beginners = exp_counter.get("beginner", 0) / n_users_profiled
            pct_intermediate = exp_counter.get("intermediate", 0) / n_users_profiled
            pct_advanced = exp_counter.get("advanced", 0) / n_users_profiled
            pct_expert_users = exp_counter.get("expert", 0) / n_users_profiled
        else:
            pct_beginners = None
            pct_intermediate = None
            pct_advanced = None
            pct_expert_users = None
    else:
        pct_beginners = None
        pct_intermediate = None
        pct_advanced = None
        pct_expert_users = None

    return {
        "route_id": rid,
        # Estaticos
        "distance_km": distance_km,
        "elevation_gain_m": elevation_gain_m,
        "elevation_loss_m": elevation_loss_m,
        "estimated_duration_h": estimated_duration_h,
        "difficulty": difficulty,
        "difficulty_num": difficulty_num,
        "is_circular": is_circular,
        "activity_type_id": activity_type_id,
        "terrain_type_id": terrain_type_id,
        "zone_id": zone_id,
        # Metricas de uso
        "total_activities": n_total,
        "unique_users": unique_users,
        "completion_rate": _round(completion_rate, 4),
        "avg_rating": _round(avg_rating, 2),
        "num_ratings": n_ratings,
        "avg_actual_duration_h": _round(avg_actual_duration_h, 2),
        "duration_accuracy": _round(duration_accuracy, 3),
        # Perfil demografico
        "pct_beginners": _round(pct_beginners, 4),
        "pct_intermediate": _round(pct_intermediate, 4),
        "pct_advanced": _round(pct_advanced, 4),
        "pct_expert_users": _round(pct_expert_users, 4),
    }


def _is_completed(activity):
    """Determina si una actividad fue completada."""
    val = activity.get("completed", "1")
    return str(val) in ("1", "True", "true")


def _round(value, decimals):
    """Round que maneja None."""
    if value is None:
        return None
    return round(value, decimals)
