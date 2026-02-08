"""
Generador de actividades simuladas para fact_activities.

Logica de seleccion de rutas por afinidad:
- activity_match: peso mayor si la ruta coincide con la actividad preferida del usuario
- exp_diff_matrix: peso segun match experiencia-dificultad
- home_zone: peso mayor si la ruta esta en una zona home del usuario

Volumenes y distribuciones controlados por config.py.
"""

import csv
import math
import random
from datetime import timedelta

from src.config import (
    ABANDON_RATE,
    ACTIVITIES_LOGNORMAL_MU,
    ACTIVITIES_LOGNORMAL_SIGMA,
    AFFINITY_ACTIVITY_MATCH,
    AFFINITY_ACTIVITY_NO_MATCH,
    AFFINITY_EXP_DIFF_MATRIX,
    AFFINITY_HOME_ZONE,
    AFFINITY_OTHER_ZONE,
    DATA_RAW_DIR,
    DATE_END,
    DURATION_EXPERIENCE_FACTOR,
    NUM_HOME_ZONES,
    RATING_MEAN_ABANDONED,
    RATING_MEAN_COMPLETED,
    RATING_PROBABILITY,
    RATING_STD_ABANDONED,
    RATING_STD_COMPLETED,
    SEED,
    TARGET_ACTIVITIES,
    WEEKEND_PROBABILITY,
    ZONE_IDS,
)


def generate_activities(users, routes, seed=SEED):
    """Genera ~TARGET_ACTIVITIES actividades con afinidad usuario-ruta.

    Args:
        users: lista de dicts generados por generate_users()
        routes: lista de dicts generados por generate_routes()

    Returns:
        list[dict]: Lista de dicts con campos de fact_activities.
    """
    random.seed(seed)

    zone_id_list = list(ZONE_IDS.values())

    # Indexar rutas por id para acceso rapido
    routes_by_id = {r["route_id"]: r for r in routes}
    route_ids = [r["route_id"] for r in routes]

    # Paso 1: determinar num_activities por usuario (lognormal)
    raw_counts = []
    for _ in users:
        raw = random.lognormvariate(ACTIVITIES_LOGNORMAL_MU, ACTIVITIES_LOGNORMAL_SIGMA)
        raw_counts.append(max(1, min(200, int(raw))))

    # Escalar para que el total se acerque a TARGET_ACTIVITIES
    total_raw = sum(raw_counts)
    scale_factor = TARGET_ACTIVITIES / total_raw
    user_counts = [max(1, round(c * scale_factor)) for c in raw_counts]

    # Paso 2: asignar home zones por usuario (1-3 zonas)
    user_home_zones = {}
    for u in users:
        n_homes = random.randint(NUM_HOME_ZONES[0], NUM_HOME_ZONES[1])
        user_home_zones[u["user_id"]] = random.sample(zone_id_list, n_homes)

    # Paso 3: pre-calcular pesos de afinidad por usuario
    activities = []
    activity_id = 1

    for user_idx, user in enumerate(users):
        uid = user["user_id"]
        n_acts = user_counts[user_idx]
        pref_act = user["preferred_activity_type_id"]
        exp_level = user["experience_level"]
        reg_date_str = user["registration_date"]

        # Parse registration date
        from datetime import date as date_cls
        reg_parts = reg_date_str.split("-")
        reg_date = date_cls(int(reg_parts[0]), int(reg_parts[1]), int(reg_parts[2]))

        home_zones = user_home_zones[uid]

        # Calcular pesos de afinidad para cada ruta
        weights = []
        for route in routes:
            # Activity match
            if pref_act != "" and route["activity_type_id"] == pref_act:
                w_act = AFFINITY_ACTIVITY_MATCH
            else:
                w_act = AFFINITY_ACTIVITY_NO_MATCH

            # Experience-difficulty match
            w_exp = AFFINITY_EXP_DIFF_MATRIX.get(
                (exp_level, route["difficulty"]), 1.0
            )

            # Home zone
            if route["zone_id"] in home_zones:
                w_zone = AFFINITY_HOME_ZONE
            else:
                w_zone = AFFINITY_OTHER_ZONE

            weights.append(w_act * w_exp * w_zone)

        # Generar n_acts actividades para este usuario
        days_available = (DATE_END - reg_date).days
        if days_available <= 0:
            days_available = 1

        for _ in range(n_acts):
            # Seleccionar ruta por pesos de afinidad
            chosen_route = random.choices(routes, weights=weights, k=1)[0]

            # Fecha de actividad: post-registro, con bias fin de semana
            activity_date = _random_date_with_weekend_bias(reg_date, days_available)

            # Completed vs abandoned
            abandon_key = (exp_level, chosen_route["difficulty"])
            abandon_rate = ABANDON_RATE.get(abandon_key, 0.05)
            completed = random.random() >= abandon_rate

            # Duracion real: estimated * experience_factor * noise
            exp_factor = DURATION_EXPERIENCE_FACTOR[exp_level]
            noise = random.gauss(1.0, 0.15)
            estimated = chosen_route["estimated_duration_h"]
            if not completed:
                # Abandonados: 30-80% de la duracion estimada
                actual_duration = estimated * exp_factor * noise * random.uniform(0.3, 0.8)
            else:
                actual_duration = estimated * exp_factor * noise
            actual_duration = round(max(0.2, actual_duration), 1)

            # Rating: 60% probabilidad si completada, menor si abandonada
            rating = _generate_rating(completed)

            activities.append({
                "activity_id": activity_id,
                "user_id": uid,
                "route_id": chosen_route["route_id"],
                "activity_date": activity_date.isoformat(),
                "completed": int(completed),
                "actual_duration_h": actual_duration,
                "rating": rating if rating is not None else "",
            })
            activity_id += 1

    # Escribir CSV
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_RAW_DIR / "activities.csv"
    fieldnames = [
        "activity_id", "user_id", "route_id", "activity_date",
        "completed", "actual_duration_h", "rating",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(activities)

    _print_stats(activities, users, routes)
    return activities


def _random_date_with_weekend_bias(start_date, max_days):
    """Genera una fecha aleatoria con bias hacia fines de semana.

    Primero decide si es fin de semana (con WEEKEND_PROBABILITY),
    luego elige una fecha aleatoria de ese tipo en el rango.
    """
    want_weekend = random.random() < WEEKEND_PROBABILITY

    for _ in range(50):
        offset = random.randint(0, max_days)
        d = start_date + timedelta(days=offset)
        is_weekend = d.weekday() >= 5
        if is_weekend == want_weekend:
            return d

    # Fallback: devolver cualquier fecha en el rango
    return start_date + timedelta(days=random.randint(0, max_days))


def _generate_rating(completed):
    """Genera rating (1-5) con probabilidad y media diferente segun completado."""
    if random.random() > RATING_PROBABILITY:
        return None

    if completed:
        rating = random.gauss(RATING_MEAN_COMPLETED, RATING_STD_COMPLETED)
    else:
        rating = random.gauss(RATING_MEAN_ABANDONED, RATING_STD_ABANDONED)

    return max(1, min(5, round(rating)))


def _print_stats(activities, users, routes):
    """Imprime estadisticas de actividades generadas."""
    n = len(activities)
    print(f"\n--- Activities: {n} generadas ---")

    # Completadas
    completed = sum(1 for a in activities if a["completed"])
    print(f"  Completadas: {completed} ({completed/n*100:.1f}%)")

    # Con rating
    rated = sum(1 for a in activities if a["rating"] != "")
    print(f"  Con rating: {rated} ({rated/n*100:.1f}%)")

    if rated > 0:
        ratings = [a["rating"] for a in activities if a["rating"] != ""]
        avg_rating = sum(ratings) / len(ratings)
        print(f"  Rating medio: {avg_rating:.2f}")

    # Distribucion de rating
    rating_counts = {}
    for a in activities:
        if a["rating"] != "":
            rating_counts[a["rating"]] = rating_counts.get(a["rating"], 0) + 1
    if rating_counts:
        print("  Distribucion de ratings:")
        for r in sorted(rating_counts.keys()):
            count = rating_counts[r]
            print(f"    {r}: {count:5d} ({count/rated*100:5.1f}%)")

    # Actividades por usuario: min, max, media, mediana
    user_act_counts = {}
    for a in activities:
        uid = a["user_id"]
        user_act_counts[uid] = user_act_counts.get(uid, 0) + 1
    counts = sorted(user_act_counts.values())
    print(f"  Actividades/usuario: min={counts[0]}, max={counts[-1]}, "
          f"media={sum(counts)/len(counts):.1f}, mediana={counts[len(counts)//2]}")

    # Rutas unicas usadas
    unique_routes = len(set(a["route_id"] for a in activities))
    print(f"  Rutas unicas usadas: {unique_routes}/{len(routes)}")

    # Weekend ratio
    weekend = sum(1 for a in activities
                  if _parse_date(a["activity_date"]).weekday() >= 5)
    print(f"  Fin de semana: {weekend/n*100:.1f}%")

    print(f"  CSV: data/raw/activities.csv")


def _parse_date(date_str):
    from datetime import date as date_cls
    parts = date_str.split("-")
    return date_cls(int(parts[0]), int(parts[1]), int(parts[2]))
