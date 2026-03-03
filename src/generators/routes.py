"""
Simulated route generator for dim_routes.

Conditional distributions by zone:
- Zone -> activity, terrain, difficulty (weighted by zone)
- Difficulty -> distance, elevation (truncated gaussian)
- Estimated duration = f(distance, elevation, activity)
- Realistic names from ROUTE_NAME_PARTS
"""

import csv
import random
from datetime import timedelta

from src.config import (
    ACTIVITY_MODIFIERS,
    ACTIVITY_TYPE_IDS,
    CIRCULAR_RATE,
    DATA_RAW_DIR,
    DATE_START,
    DIFFICULTY_DIST_FLAT,
    DIFFICULTY_DIST_MOUNTAIN,
    NUM_ROUTES,
    ROUTE_NAME_PARTS,
    ROUTE_PARAMS_BY_DIFFICULTY,
    SEED,
    TERRAIN_TYPE_IDS,
    ZONE_ACTIVITY_DIST,
    ZONE_IDS,
    ZONE_IS_MOUNTAIN,
    ZONE_ROUTE_DIST,
    ZONE_TERRAIN_DIST,
)


def generate_routes(seed=SEED):
    """Generate NUM_ROUTES routes with conditional distributions by zone.

    Returns:
        list[dict]: List of dicts with dim_routes fields.
    """
    random.seed(seed)

    zone_names = list(ZONE_ROUTE_DIST.keys())
    zone_weights = list(ZONE_ROUTE_DIST.values())

    # Pre-generate zone assignments to respect proportions
    zone_assignments = random.choices(zone_names, weights=zone_weights, k=NUM_ROUTES)

    # Track used names to avoid duplicates
    used_names = set()

    routes = []
    for route_id, zone_name in enumerate(zone_assignments, start=1):
        zone_id = ZONE_IDS[zone_name]

        # Activity conditional on zone
        act_dist = ZONE_ACTIVITY_DIST[zone_name]
        activity_name = random.choices(
            list(act_dist.keys()), weights=list(act_dist.values()), k=1
        )[0]
        activity_type_id = ACTIVITY_TYPE_IDS[activity_name]

        # Terrain conditional on zone
        ter_dist = ZONE_TERRAIN_DIST[zone_name]
        terrain_name = random.choices(
            list(ter_dist.keys()), weights=list(ter_dist.values()), k=1
        )[0]
        terrain_type_id = TERRAIN_TYPE_IDS[terrain_name]

        # Difficulty conditional on zone (mountain vs flat)
        diff_dist = DIFFICULTY_DIST_MOUNTAIN if ZONE_IS_MOUNTAIN[zone_name] else DIFFICULTY_DIST_FLAT
        difficulty = random.choices(
            list(diff_dist.keys()), weights=list(diff_dist.values()), k=1
        )[0]

        # Distance and elevation: truncated gaussian (min 0.5 km, min 10 m)
        dist_mean, dist_std, elev_mean, elev_std = ROUTE_PARAMS_BY_DIFFICULTY[difficulty]

        # Distance modifier by activity
        dist_mult = ACTIVITY_MODIFIERS[activity_name]["distance_mult"]
        distance_km = max(0.5, random.gauss(dist_mean * dist_mult, dist_std * dist_mult))
        distance_km = round(distance_km, 2)

        elevation_gain = max(10, int(random.gauss(elev_mean, elev_std)))

        # Circular vs linear
        is_circular = random.random() < CIRCULAR_RATE
        if is_circular:
            elevation_loss = elevation_gain
        else:
            elevation_loss = int(elevation_gain * random.uniform(0.6, 1.0))

        # Estimated duration: (dist/5 + elev_gain/600) * activity_modifier
        duration_mult = ACTIVITY_MODIFIERS[activity_name]["duration_mult"]
        estimated_duration = (distance_km / 5.0 + elevation_gain / 600.0) * duration_mult
        estimated_duration = round(max(0.5, estimated_duration), 1)

        # Realistic name
        name = _generate_route_name(zone_name, used_names)
        used_names.add(name)

        # Creation date: uniform in the year prior to DATE_START
        days_before = random.randint(0, 365)
        created_date = DATE_START - timedelta(days=days_before)

        routes.append({
            "route_id": route_id,
            "name": name,
            "distance_km": distance_km,
            "elevation_gain_m": elevation_gain,
            "elevation_loss_m": elevation_loss,
            "estimated_duration_h": estimated_duration,
            "difficulty": difficulty,
            "is_circular": int(is_circular),
            "activity_type_id": activity_type_id,
            "terrain_type_id": terrain_type_id,
            "zone_id": zone_id,
            "created_date": created_date.isoformat(),
        })

    # Write CSV
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_RAW_DIR / "routes.csv"
    fieldnames = [
        "route_id", "name", "distance_km", "elevation_gain_m", "elevation_loss_m",
        "estimated_duration_h", "difficulty", "is_circular", "activity_type_id",
        "terrain_type_id", "zone_id", "created_date",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(routes)

    _print_stats(routes)
    return routes


def _generate_route_name(zone_name, used_names):
    """Generate a realistic route name for the given zone."""
    parts = ROUTE_NAME_PARTS[zone_name]
    for _ in range(50):
        prefix = random.choice(parts["prefixes"])
        place = random.choice(parts["places"])
        name = f"{prefix} {place}"
        if name not in used_names:
            return name
    # Fallback: add numeric suffix
    return f"{prefix} {place} {random.randint(1, 999)}"


def _print_stats(routes):
    """Print distribution of generated routes."""
    n = len(routes)
    print(f"\n--- Routes: {n} generated ---")

    # By zone
    zone_counts = {}
    zone_id_to_name = {v: k for k, v in ZONE_IDS.items()}
    for r in routes:
        zname = zone_id_to_name[r["zone_id"]]
        zone_counts[zname] = zone_counts.get(zname, 0) + 1
    print("  By zone:")
    for zname in sorted(zone_counts.keys()):
        count = zone_counts[zname]
        print(f"    {zname:25s}: {count:3d} ({count/n*100:5.1f}%)")

    # By difficulty
    diff_counts = {}
    for r in routes:
        d = r["difficulty"]
        diff_counts[d] = diff_counts.get(d, 0) + 1
    print("  By difficulty:")
    for d in ["easy", "moderate", "hard", "expert"]:
        count = diff_counts.get(d, 0)
        print(f"    {d:15s}: {count:3d} ({count/n*100:5.1f}%)")

    # Circular
    circ = sum(1 for r in routes if r["is_circular"])
    print(f"  Circular: {circ} ({circ/n*100:.1f}%)")

    # Average metrics
    avg_dist = sum(r["distance_km"] for r in routes) / n
    avg_elev = sum(r["elevation_gain_m"] for r in routes) / n
    avg_dur = sum(r["estimated_duration_h"] for r in routes) / n
    print(f"  Avg distance: {avg_dist:.1f} km")
    print(f"  Avg elevation: {avg_elev:.0f} m")
    print(f"  Avg duration: {avg_dur:.1f} h")
    print(f"  CSV: data/raw/routes.csv")
