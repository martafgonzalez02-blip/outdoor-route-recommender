"""
Modulo de calidad de datos para el proyecto outdoor-route-recommender.

Ejecuta 28 checks organizados en 5 tiers:
  1. Schema integrity (8 checks)
  2. Referential integrity (5 checks)
  3. Domain ranges (8 checks)
  4. Coherencia temporal/logica (3 checks)
  5. Distribuciones (4 checks)

Uso:
  python -m src.data_quality                   # Report por stdout
  python -m src.data_quality --output FILE     # Tambien escribe a archivo
"""

import argparse
import csv
import sys
from datetime import date as date_cls

from src.config import (
    DATA_RAW_DIR,
    DQ_ACTIVITIES_TOLERANCE,
    DQ_DISTRIBUTION_TOLERANCE,
    DQ_MEAN_TOLERANCE,
    DQ_RATE_TOLERANCE,
    NUM_ROUTES,
    NUM_USERS,
    RATING_MEAN_ABANDONED,
    RATING_MEAN_COMPLETED,
    TARGET_ACTIVITIES,
    USER_EXPERIENCE_DIST,
    WEEKEND_PROBABILITY,
)

# =============================================================================
# Helpers
# =============================================================================

def _load_csvs():
    """Lee los 3 CSVs de data/raw/ y devuelve (users, routes, activities)."""
    def _read(filename):
        path = DATA_RAW_DIR / filename
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    return _read("users.csv"), _read("routes.csv"), _read("activities.csv")


def _parse_date(date_str):
    """Convierte 'YYYY-MM-DD' a date."""
    parts = date_str.split("-")
    return date_cls(int(parts[0]), int(parts[1]), int(parts[2]))


def _check(name, passed, message, level="FAIL"):
    """Crea un resultado de check.

    Args:
        name: nombre unico del check
        passed: True si pasa, False si falla
        message: descripcion del resultado
        level: 'FAIL' o 'WARN' (usado cuando passed=False)

    Returns:
        dict con keys: name, status, message
    """
    if passed:
        status = "PASS"
    else:
        status = level
    return {"name": name, "status": status, "message": message}


# =============================================================================
# Tier 1: Schema integrity (8 checks)
# =============================================================================

def check_schema(users, routes, activities):
    """Checks de integridad del esquema: counts, columnas, PKs."""
    results = []

    # 1. users_row_count
    n_users = len(users)
    results.append(_check(
        "users_row_count",
        n_users == NUM_USERS,
        f"Esperado {NUM_USERS}, encontrado {n_users}",
    ))

    # 2. routes_row_count
    n_routes = len(routes)
    results.append(_check(
        "routes_row_count",
        n_routes == NUM_ROUTES,
        f"Esperado {NUM_ROUTES}, encontrado {n_routes}",
    ))

    # 3. activities_row_count (~TARGET_ACTIVITIES +/-10%)
    n_acts = len(activities)
    low = int(TARGET_ACTIVITIES * (1 - DQ_ACTIVITIES_TOLERANCE))
    high = int(TARGET_ACTIVITIES * (1 + DQ_ACTIVITIES_TOLERANCE))
    results.append(_check(
        "activities_row_count",
        low <= n_acts <= high,
        f"Esperado {TARGET_ACTIVITIES} +/-10% [{low}-{high}], encontrado {n_acts}",
    ))

    # 4. users_columns
    expected_user_cols = {"user_id", "username", "registration_date",
                          "experience_level", "preferred_activity_type_id"}
    actual_user_cols = set(users[0].keys()) if users else set()
    results.append(_check(
        "users_columns",
        expected_user_cols.issubset(actual_user_cols),
        f"Esperadas {sorted(expected_user_cols)}, encontradas {sorted(actual_user_cols)}",
    ))

    # 5. routes_columns
    expected_route_cols = {"route_id", "name", "distance_km", "elevation_gain_m",
                           "elevation_loss_m", "estimated_duration_h", "difficulty",
                           "is_circular", "activity_type_id", "terrain_type_id",
                           "zone_id", "created_date"}
    actual_route_cols = set(routes[0].keys()) if routes else set()
    results.append(_check(
        "routes_columns",
        expected_route_cols.issubset(actual_route_cols),
        f"Esperadas {sorted(expected_route_cols)}, encontradas {sorted(actual_route_cols)}",
    ))

    # 6. activities_columns
    expected_act_cols = {"activity_id", "user_id", "route_id", "activity_date",
                         "completed", "actual_duration_h", "rating"}
    actual_act_cols = set(activities[0].keys()) if activities else set()
    results.append(_check(
        "activities_columns",
        expected_act_cols.issubset(actual_act_cols),
        f"Esperadas {sorted(expected_act_cols)}, encontradas {sorted(actual_act_cols)}",
    ))

    # 7. users_pk_unique
    user_ids = [int(u["user_id"]) for u in users]
    expected_ids = list(range(1, NUM_USERS + 1))
    results.append(_check(
        "users_pk_unique",
        sorted(user_ids) == expected_ids,
        f"user_id 1..{NUM_USERS} unicos sin gaps: {len(user_ids)} ids, "
        f"min={min(user_ids) if user_ids else 'N/A'}, max={max(user_ids) if user_ids else 'N/A'}",
    ))

    # 8. routes_pk_unique
    route_ids = [int(r["route_id"]) for r in routes]
    expected_rids = list(range(1, NUM_ROUTES + 1))
    results.append(_check(
        "routes_pk_unique",
        sorted(route_ids) == expected_rids,
        f"route_id 1..{NUM_ROUTES} unicos sin gaps: {len(route_ids)} ids, "
        f"min={min(route_ids) if route_ids else 'N/A'}, max={max(route_ids) if route_ids else 'N/A'}",
    ))

    return results


# =============================================================================
# Tier 2: Referential integrity (5 checks)
# =============================================================================

def check_referential_integrity(users, routes, activities):
    """Checks de integridad referencial: FKs entre tablas."""
    results = []

    valid_user_ids = {int(u["user_id"]) for u in users}
    valid_route_ids = {int(r["route_id"]) for r in routes}

    # 9. activities_user_fk
    act_user_ids = {int(a["user_id"]) for a in activities}
    orphan_users = act_user_ids - valid_user_ids
    results.append(_check(
        "activities_user_fk",
        len(orphan_users) == 0,
        f"user_ids huerfanos en activities: {len(orphan_users)}"
        + (f" (ej: {sorted(orphan_users)[:5]})" if orphan_users else ""),
    ))

    # 10. activities_route_fk
    act_route_ids = {int(a["route_id"]) for a in activities}
    orphan_routes = act_route_ids - valid_route_ids
    results.append(_check(
        "activities_route_fk",
        len(orphan_routes) == 0,
        f"route_ids huerfanos en activities: {len(orphan_routes)}"
        + (f" (ej: {sorted(orphan_routes)[:5]})" if orphan_routes else ""),
    ))

    # 11. routes_activity_type_fk
    valid_act_types = {1, 2, 3}
    route_act_types = {int(r["activity_type_id"]) for r in routes}
    invalid_act = route_act_types - valid_act_types
    results.append(_check(
        "routes_activity_type_fk",
        len(invalid_act) == 0,
        f"activity_type_ids invalidos en routes: {invalid_act if invalid_act else 'ninguno'}",
    ))

    # 12. routes_terrain_type_fk
    valid_terrains = {1, 2, 3, 4, 5}
    route_terrains = {int(r["terrain_type_id"]) for r in routes}
    invalid_ter = route_terrains - valid_terrains
    results.append(_check(
        "routes_terrain_type_fk",
        len(invalid_ter) == 0,
        f"terrain_type_ids invalidos en routes: {invalid_ter if invalid_ter else 'ninguno'}",
    ))

    # 13. routes_zone_fk
    valid_zones = set(range(1, 11))
    route_zones = {int(r["zone_id"]) for r in routes}
    invalid_zones = route_zones - valid_zones
    results.append(_check(
        "routes_zone_fk",
        len(invalid_zones) == 0,
        f"zone_ids invalidos en routes: {invalid_zones if invalid_zones else 'ninguno'}",
    ))

    return results


# =============================================================================
# Tier 3: Domain ranges (8 checks)
# =============================================================================

def check_domain_ranges(users, routes, activities):
    """Checks de rangos de dominio: valores dentro de limites esperados."""
    results = []

    # 14. routes_distance_min
    distances = [float(r["distance_km"]) for r in routes]
    min_dist = min(distances)
    results.append(_check(
        "routes_distance_min",
        min_dist >= 0.5,
        f"distance_km min={min_dist:.2f} (esperado >= 0.5)",
    ))

    # 15. routes_elevation_min
    elevations = [int(r["elevation_gain_m"]) for r in routes]
    min_elev = min(elevations)
    results.append(_check(
        "routes_elevation_min",
        min_elev >= 10,
        f"elevation_gain_m min={min_elev} (esperado >= 10)",
    ))

    # 16. routes_duration_min
    durations = [float(r["estimated_duration_h"]) for r in routes]
    min_dur = min(durations)
    results.append(_check(
        "routes_duration_min",
        min_dur >= 0.5,
        f"estimated_duration_h min={min_dur:.1f} (esperado >= 0.5)",
    ))

    # 17. activities_duration_min
    act_durations = [float(a["actual_duration_h"]) for a in activities]
    min_act_dur = min(act_durations)
    results.append(_check(
        "activities_duration_min",
        min_act_dur >= 0.2,
        f"actual_duration_h min={min_act_dur:.1f} (esperado >= 0.2)",
    ))

    # 18. activities_rating_range
    ratings_raw = [a["rating"] for a in activities if a["rating"] != ""]
    ratings = [int(r) for r in ratings_raw]
    invalid_ratings = [r for r in ratings if r not in {1, 2, 3, 4, 5}]
    results.append(_check(
        "activities_rating_range",
        len(invalid_ratings) == 0,
        f"ratings fuera de 1-5: {len(invalid_ratings)}"
        + (f" (ej: {invalid_ratings[:5]})" if invalid_ratings else ""),
    ))

    # 19. activities_completed_values
    completed_vals = {a["completed"] for a in activities}
    valid_completed = {"0", "1"}
    invalid_completed = completed_vals - valid_completed
    results.append(_check(
        "activities_completed_values",
        len(invalid_completed) == 0,
        f"completed fuera de {{0,1}}: {invalid_completed if invalid_completed else 'ninguno'}",
    ))

    # 20. routes_difficulty_values
    difficulties = {r["difficulty"] for r in routes}
    valid_difficulties = {"easy", "moderate", "hard", "expert"}
    invalid_diff = difficulties - valid_difficulties
    results.append(_check(
        "routes_difficulty_values",
        len(invalid_diff) == 0,
        f"difficulty invalidos: {invalid_diff if invalid_diff else 'ninguno'}",
    ))

    # 21. users_experience_values
    experiences = {u["experience_level"] for u in users}
    valid_experiences = {"beginner", "intermediate", "advanced", "expert"}
    invalid_exp = experiences - valid_experiences
    results.append(_check(
        "users_experience_values",
        len(invalid_exp) == 0,
        f"experience_level invalidos: {invalid_exp if invalid_exp else 'ninguno'}",
    ))

    return results


# =============================================================================
# Tier 4: Coherencia temporal/logica (3 checks)
# =============================================================================

def check_temporal_coherence(users, routes, activities):
    """Checks de coherencia temporal y logica entre entidades."""
    results = []

    # Index users by id for lookups
    user_reg = {int(u["user_id"]): _parse_date(u["registration_date"]) for u in users}

    # 22. activity_after_registration
    violations = 0
    for a in activities:
        uid = int(a["user_id"])
        act_date = _parse_date(a["activity_date"])
        reg_date = user_reg.get(uid)
        if reg_date and act_date < reg_date:
            violations += 1
    results.append(_check(
        "activity_after_registration",
        violations == 0,
        f"Actividades antes de registro: {violations}",
    ))

    # Index routes by id
    routes_by_id = {int(r["route_id"]): r for r in routes}

    # 23. circular_elevation_match
    circular_mismatches = 0
    circular_total = 0
    for r in routes:
        if int(r["is_circular"]) == 1:
            circular_total += 1
            if int(r["elevation_gain_m"]) != int(r["elevation_loss_m"]):
                circular_mismatches += 1
    results.append(_check(
        "circular_elevation_match",
        circular_mismatches == 0,
        f"Circulares con gain != loss: {circular_mismatches}/{circular_total}",
        level="WARN",
    ))

    # 24. linear_elevation_bound
    linear_violations = 0
    linear_total = 0
    for r in routes:
        if int(r["is_circular"]) == 0:
            linear_total += 1
            if int(r["elevation_loss_m"]) > int(r["elevation_gain_m"]):
                linear_violations += 1
    results.append(_check(
        "linear_elevation_bound",
        linear_violations == 0,
        f"Lineales con loss > gain: {linear_violations}/{linear_total}",
        level="WARN",
    ))

    return results


# =============================================================================
# Tier 5: Distribuciones (4 checks)
# =============================================================================

def check_distributions(users, routes, activities):
    """Checks de distribuciones: tolerancias sobre proporciones esperadas."""
    results = []
    n_users = len(users)
    n_acts = len(activities)

    # 25. experience_distribution
    exp_counts = {}
    for u in users:
        lvl = u["experience_level"]
        exp_counts[lvl] = exp_counts.get(lvl, 0) + 1

    max_deviation = 0.0
    deviations = []
    for level, expected_pct in USER_EXPERIENCE_DIST.items():
        actual_pct = exp_counts.get(level, 0) / n_users
        deviation = abs(actual_pct - expected_pct)
        max_deviation = max(max_deviation, deviation)
        deviations.append(f"{level}: {actual_pct:.1%} vs {expected_pct:.0%}")

    results.append(_check(
        "experience_distribution",
        max_deviation <= DQ_DISTRIBUTION_TOLERANCE,
        f"Max desviacion: {max_deviation:.1%} (tol: {DQ_DISTRIBUTION_TOLERANCE:.0%}). "
        + ", ".join(deviations),
        level="WARN",
    ))

    # 26. weekend_rate
    weekend_count = 0
    for a in activities:
        d = _parse_date(a["activity_date"])
        if d.weekday() >= 5:
            weekend_count += 1
    weekend_rate = weekend_count / n_acts
    deviation = abs(weekend_rate - WEEKEND_PROBABILITY)
    results.append(_check(
        "weekend_rate",
        deviation <= DQ_RATE_TOLERANCE,
        f"Weekend rate: {weekend_rate:.1%} (esperado: {WEEKEND_PROBABILITY:.0%}, "
        f"desviacion: {deviation:.1%}, tol: {DQ_RATE_TOLERANCE:.0%})",
        level="WARN",
    ))

    # 27. rating_mean_completed
    completed_ratings = [
        int(a["rating"]) for a in activities
        if a["completed"] == "1" and a["rating"] != ""
    ]
    if completed_ratings:
        mean_completed = sum(completed_ratings) / len(completed_ratings)
        dev = abs(mean_completed - RATING_MEAN_COMPLETED)
        results.append(_check(
            "rating_mean_completed",
            dev <= DQ_MEAN_TOLERANCE,
            f"Media completadas: {mean_completed:.2f} (esperado: {RATING_MEAN_COMPLETED}, "
            f"desviacion: {dev:.2f}, tol: {DQ_MEAN_TOLERANCE})",
            level="WARN",
        ))
    else:
        results.append(_check(
            "rating_mean_completed",
            False,
            "No hay ratings de actividades completadas",
            level="WARN",
        ))

    # 28. rating_mean_abandoned
    abandoned_ratings = [
        int(a["rating"]) for a in activities
        if a["completed"] == "0" and a["rating"] != ""
    ]
    if abandoned_ratings:
        mean_abandoned = sum(abandoned_ratings) / len(abandoned_ratings)
        dev = abs(mean_abandoned - RATING_MEAN_ABANDONED)
        results.append(_check(
            "rating_mean_abandoned",
            dev <= DQ_MEAN_TOLERANCE,
            f"Media abandonadas: {mean_abandoned:.2f} (esperado: {RATING_MEAN_ABANDONED}, "
            f"desviacion: {dev:.2f}, tol: {DQ_MEAN_TOLERANCE})",
            level="WARN",
        ))
    else:
        results.append(_check(
            "rating_mean_abandoned",
            False,
            "No hay ratings de actividades abandonadas",
            level="WARN",
        ))

    return results


# =============================================================================
# Orquestacion y report
# =============================================================================

def run_all_checks():
    """Ejecuta los 28 checks y devuelve (results, score, status).

    Returns:
        (list[dict], float, str): resultados, score 0-100, status global
    """
    users, routes, activities = _load_csvs()

    results = []
    results.extend(check_schema(users, routes, activities))
    results.extend(check_referential_integrity(users, routes, activities))
    results.extend(check_domain_ranges(users, routes, activities))
    results.extend(check_temporal_coherence(users, routes, activities))
    results.extend(check_distributions(users, routes, activities))

    # Score: WARN cuenta como pass
    passed = sum(1 for r in results if r["status"] in ("PASS", "WARN"))
    total = len(results)
    score = (passed / total * 100) if total > 0 else 0.0

    # Status global
    has_fail = any(r["status"] == "FAIL" for r in results)
    has_warn = any(r["status"] == "WARN" for r in results)
    if has_fail:
        status = "FAIL"
    elif has_warn:
        status = "WARN"
    else:
        status = "PASS"

    return results, score, status


def format_report(results, score, status):
    """Formatea el report como lista de lineas de texto.

    Returns:
        list[str]: lineas del report
    """
    lines = []
    lines.append("=" * 60)
    lines.append("DATA QUALITY REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Agrupar por tier
    tiers = [
        ("Tier 1 — Schema integrity", 0, 8),
        ("Tier 2 — Referential integrity", 8, 13),
        ("Tier 3 — Domain ranges", 13, 21),
        ("Tier 4 — Coherencia temporal/logica", 21, 24),
        ("Tier 5 — Distribuciones", 24, 28),
    ]

    for tier_name, start, end in tiers:
        lines.append(f"--- {tier_name} ---")
        for r in results[start:end]:
            icon = "PASS" if r["status"] == "PASS" else r["status"]
            lines.append(f"  [{icon:4s}] {r['name']}")
            lines.append(f"         {r['message']}")
        lines.append("")

    # Resumen
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_warn = sum(1 for r in results if r["status"] == "WARN")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")

    lines.append("=" * 60)
    lines.append(f"RESULTADO: {status}")
    lines.append(f"Score: {score:.0f}% ({n_pass} pass, {n_warn} warn, {n_fail} fail)")
    lines.append(f"Total checks: {len(results)}")
    lines.append("=" * 60)

    return lines


def main():
    """Entry point: ejecuta checks y muestra/escribe report."""
    parser = argparse.ArgumentParser(description="Data quality checks")
    parser.add_argument("--output", type=str, default=None,
                        help="Ruta de archivo para escribir el report")
    args = parser.parse_args()

    results, score, status = run_all_checks()
    lines = format_report(results, score, status)
    report = "\n".join(lines)

    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\nReport escrito en: {args.output}")

    # Exit code: 0 si no hay FAILs, 1 si hay FAILs
    sys.exit(1 if status == "FAIL" else 0)


if __name__ == "__main__":
    main()
