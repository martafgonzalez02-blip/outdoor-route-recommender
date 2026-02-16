"""
Orquestador de feature engineering.

Lee CSVs de data/raw/, computa features de usuario y ruta,
normaliza a [0,1] y escribe a data/processed/.

Uso:
    python -m src.build_features
"""

import csv
import sys
import time

from src.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    ROUTE_NORMALIZE_COLS,
    USER_NORMALIZE_COLS,
)
from src.features.normalization import (
    compute_stats,
    normalize_rows,
    save_stats,
)
from src.features.user_profiles import build_user_profiles
from src.features.route_features import build_route_features


# =============================================================================
# I/O helpers
# =============================================================================

def _load_csv(filename):
    """Lee un CSV de data/raw/ y devuelve lista de dicts."""
    path = DATA_RAW_DIR / filename
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(rows, filename, fieldnames):
    """Escribe lista de dicts a CSV en data/processed/."""
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_PROCESSED_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # Convertir None a cadena vacia para CSV
            clean = {k: ("" if v is None else v) for k, v in row.items()}
            writer.writerow(clean)
    return path


# =============================================================================
# Fieldnames para CSVs de salida
# =============================================================================

USER_PROFILE_FIELDS = [
    "user_id",
    # Volumen
    "total_activities", "completed_activities", "completion_rate",
    "rated_activities", "avg_rating_given",
    "days_since_last_activity", "activity_span_days", "activities_per_month",
    # Dificultad
    "pct_easy", "pct_moderate", "pct_hard", "pct_expert",
    "avg_difficulty_num",
    # Actividad
    "pct_hiking", "pct_trail_running", "pct_cycling",
    # Fisico
    "avg_distance_km", "std_distance_km",
    "avg_elevation_gain_m", "std_elevation_gain_m",
    "avg_duration_h", "avg_pace_factor",
    # Geografica
    "top_zone_1_id", "top_zone_1_pct",
    "top_zone_2_id", "top_zone_2_pct",
    "top_zone_3_id", "num_distinct_zones",
    # Terreno
    "pct_mountain", "pct_coastal", "pct_forest", "pct_urban_park", "pct_desert",
    # Formato
    "pct_circular",
    # Meta
    "has_sufficient_data",
]

ROUTE_FEATURE_FIELDS = [
    "route_id",
    # Estaticos
    "distance_km", "elevation_gain_m", "elevation_loss_m",
    "estimated_duration_h", "difficulty", "difficulty_num",
    "is_circular", "activity_type_id", "terrain_type_id", "zone_id",
    # Metricas de uso
    "total_activities", "unique_users",
    "completion_rate", "avg_rating", "num_ratings",
    "avg_actual_duration_h", "duration_accuracy",
    # Perfil demografico
    "pct_beginners", "pct_intermediate", "pct_advanced", "pct_expert_users",
]


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Outdoor Route Recommender — Feature Engineering")
    print("=" * 60)

    # 1. Cargar datos raw
    t0 = time.time()
    print("\n[1/5] Cargando CSVs de data/raw/ ...")
    users = _load_csv("users.csv")
    routes = _load_csv("routes.csv")
    activities = _load_csv("activities.csv")
    print(f"  Users: {len(users)}, Routes: {len(routes)}, Activities: {len(activities)}")
    print(f"  ({time.time() - t0:.2f}s)")

    # 2. Construir user profiles
    t0 = time.time()
    print("\n[2/5] Construyendo user profiles ...")
    user_profiles = build_user_profiles(users, routes, activities)
    n_sufficient = sum(1 for p in user_profiles if p["has_sufficient_data"])
    print(f"  {len(user_profiles)} perfiles ({n_sufficient} con datos suficientes)")
    print(f"  ({time.time() - t0:.2f}s)")

    # 3. Construir route features
    t0 = time.time()
    print("\n[3/5] Construyendo route features ...")
    route_features = build_route_features(routes, activities, users)
    n_with_acts = sum(1 for r in route_features if r["total_activities"] > 0)
    print(f"  {len(route_features)} rutas ({n_with_acts} con actividades)")
    print(f"  ({time.time() - t0:.2f}s)")

    # 4. Normalizar
    t0 = time.time()
    print("\n[4/5] Normalizando features (min-max a [0,1]) ...")

    # Compute stats sobre route features (referencia para ambos)
    all_stats = {}

    # Stats de rutas
    for col in ROUTE_NORMALIZE_COLS:
        values = [r[col] for r in route_features if r.get(col) is not None]
        all_stats[col] = compute_stats(values)

    # Stats de user profiles (sobre rango de datos de usuario)
    for col in USER_NORMALIZE_COLS:
        if col in all_stats:
            continue  # ya computado desde rutas (distancia, elevacion, etc.)
        values = [p[col] for p in user_profiles if p.get(col) is not None]
        all_stats[col] = compute_stats(values)

    # Normalizar user profiles (continuas)
    # Para features fisicas, usar rango de rutas como referencia
    route_ref_cols = ["avg_distance_km", "avg_elevation_gain_m", "avg_duration_h"]
    route_ref_map = {
        "avg_distance_km": "distance_km",
        "avg_elevation_gain_m": "elevation_gain_m",
        "avg_duration_h": "estimated_duration_h",
    }
    user_stats = {}
    for col in USER_NORMALIZE_COLS:
        if col in route_ref_map:
            # Usar rango de rutas como referencia
            ref_col = route_ref_map[col]
            user_stats[col] = all_stats[ref_col]
        elif col in all_stats:
            user_stats[col] = all_stats[col]
        else:
            values = [p[col] for p in user_profiles if p.get(col) is not None]
            user_stats[col] = compute_stats(values)

    normalize_rows(user_profiles, USER_NORMALIZE_COLS, user_stats)

    # Normalizar difficulty_num: /4
    for p in user_profiles:
        if p.get("avg_difficulty_num") is not None:
            p["avg_difficulty_num"] = round(p["avg_difficulty_num"] / 4.0, 4)

    # Normalizar route features (continuas)
    route_stats = {col: all_stats[col] for col in ROUTE_NORMALIZE_COLS if col in all_stats}
    normalize_rows(route_features, ROUTE_NORMALIZE_COLS, route_stats)

    # Normalizar difficulty_num en rutas: /4
    for r in route_features:
        r["difficulty_num"] = round(r["difficulty_num"] / 4.0, 4)

    # Guardar stats
    combined_stats = {}
    combined_stats.update({"user_" + k: v for k, v in user_stats.items()})
    combined_stats.update({"route_" + k: v for k, v in route_stats.items()})
    stats_path = DATA_PROCESSED_DIR / "feature_stats.csv"
    save_stats(combined_stats, stats_path)
    print(f"  Stats guardados en: {stats_path.relative_to(DATA_PROCESSED_DIR.parent.parent)}")
    print(f"  ({time.time() - t0:.2f}s)")

    # 5. Escribir CSVs normalizados
    t0 = time.time()
    print("\n[5/5] Escribiendo CSVs a data/processed/ ...")

    up_path = _write_csv(user_profiles, "user_profiles.csv", USER_PROFILE_FIELDS)
    rf_path = _write_csv(route_features, "route_features.csv", ROUTE_FEATURE_FIELDS)

    print(f"  {up_path.relative_to(DATA_PROCESSED_DIR.parent.parent)}: {len(user_profiles)} filas")
    print(f"  {rf_path.relative_to(DATA_PROCESSED_DIR.parent.parent)}: {len(route_features)} filas")
    print(f"  ({time.time() - t0:.2f}s)")

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  User profiles:  {len(user_profiles):>4d} ({len(USER_PROFILE_FIELDS) - 1} features)")
    print(f"  Route features: {len(route_features):>4d} ({len(ROUTE_FEATURE_FIELDS) - 1} features)")
    print(f"  Users con datos suficientes: {n_sufficient}/{len(user_profiles)}")
    print(f"  Archivos en: data/processed/")
    print("\nDone.")


if __name__ == "__main__":
    main()
