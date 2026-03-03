"""
Content-based route recommender.

Scores routes against a user profile across 6 dimensions:
    activity (0.30) | difficulty (0.25) | terrain (0.15)
    physical (0.15) | zone (0.10)       | quality (0.05)

Requires processed feature files (run build_features first):
    data/processed/user_profiles.csv
    data/processed/route_features.csv

Usage:
    python -m src.recommender <user_id>
    python -m src.recommender <user_id> --n 5
    python -m src.recommender <user_id> --include-completed
"""

import argparse
import csv
import math

from src.config import (
    ACTIVITY_TYPE_IDS,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    TERRAIN_TYPE_IDS,
    ZONE_IDS,
)


# =============================================================================
# Scoring weights — must sum to 1.0
# =============================================================================

WEIGHTS = {
    "activity":   0.30,   # route activity matches user's preferred type
    "difficulty": 0.25,   # difficulty matches user's fitness level
    "terrain":    0.15,   # terrain type matches user's preference
    "physical":   0.15,   # distance/elevation match user's typical level
    "zone":       0.10,   # route is in user's preferred geographic zone
    "quality":    0.05,   # route quality signal (avg rating, normalized)
}

# Gaussian similarity bandwidth: lower = stricter match required
_SIGMA_DIFFICULTY = 0.25   # ~1 difficulty level of tolerance
_SIGMA_PHYSICAL   = 0.30   # ~30% of the normalized [0,1] range

# Zone affinity tiers
_ZONE_SCORE = {
    "top1":  1.0,
    "top2":  0.7,
    "top3":  0.5,
    "other": 0.1,   # small exploration bonus for unknown zones
}

# Inverse lookup: zone_id -> zone_name
_ZONE_NAMES = {v: k for k, v in ZONE_IDS.items()}


# =============================================================================
# Public API
# =============================================================================

def recommend(user_id, n=10, exclude_completed=True):
    """Return the top N route recommendations for a user.

    Args:
        user_id: int, target user.
        n: int, number of recommendations to return.
        exclude_completed: bool, skip routes the user has already completed.

    Returns:
        list[dict], sorted by score descending. Each dict contains:
            route_id, route_name, score, breakdown,
            difficulty, distance_km, zone_id
    """
    user_profiles, route_feats, route_names, route_raw, completed_per_user = _load_data()

    user_id = int(user_id)
    if user_id not in user_profiles:
        raise ValueError(f"user_id {user_id} not found in user_profiles.csv")

    profile  = user_profiles[user_id]
    excluded = completed_per_user.get(user_id, set()) if exclude_completed else set()

    scored = []
    for rid, route in route_feats.items():
        if rid in excluded:
            continue

        score, breakdown = _score_route(profile, route)
        raw = route_raw.get(rid, {})

        scored.append({
            "route_id":    rid,
            "route_name":  route_names.get(rid, f"Route {rid}"),
            "score":       round(score, 4),
            "breakdown":   breakdown,
            "difficulty":  raw.get("difficulty", ""),
            "distance_km": raw.get("distance_km", 0.0),
            "zone_id":     int(route.get("zone_id") or 0),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:n]


# =============================================================================
# Scoring
# =============================================================================

def _score_route(user, route):
    """Compute a [0,1] score and per-dimension breakdown for a user-route pair.

    Args:
        user: dict from user_profiles.csv (normalized features).
        route: dict from route_features.csv (normalized features).

    Returns:
        (float total_score, dict breakdown)
    """
    # 1. Activity type match
    act_id    = _safe_int(route.get("activity_type_id")) or 0
    act_score = _activity_score(user, act_id)

    # 2. Difficulty match (Gaussian similarity, both normalized by /4)
    user_diff = _safe_float(user.get("avg_difficulty_num"))
    route_diff = _safe_float(route.get("difficulty_num"))
    diff_score = _gaussian_sim(user_diff, route_diff, _SIGMA_DIFFICULTY)

    # 3. Terrain match
    terrain_id    = _safe_int(route.get("terrain_type_id")) or 0
    terrain_score = _terrain_score(user, terrain_id)

    # 4. Physical match — distance + elevation, same normalization scale
    dist_sim = _gaussian_sim(
        _safe_float(user.get("avg_distance_km")),
        _safe_float(route.get("distance_km")),
        _SIGMA_PHYSICAL,
    )
    elev_sim = _gaussian_sim(
        _safe_float(user.get("avg_elevation_gain_m")),
        _safe_float(route.get("elevation_gain_m")),
        _SIGMA_PHYSICAL,
    )
    physical_score = (dist_sim + elev_sim) / 2.0

    # 5. Zone affinity
    zone_id    = _safe_int(route.get("zone_id")) or 0
    zone_score = _zone_score(user, zone_id)

    # 6. Quality signal (avg_rating is min-max normalized to [0,1])
    avg_rating    = _safe_float(route.get("avg_rating"))
    quality_score = avg_rating if avg_rating is not None else 0.5

    breakdown = {
        "activity":   round(act_score,      4),
        "difficulty": round(diff_score,     4),
        "terrain":    round(terrain_score,  4),
        "physical":   round(physical_score, 4),
        "zone":       round(zone_score,     4),
        "quality":    round(quality_score,  4),
    }
    total = sum(WEIGHTS[k] * v for k, v in breakdown.items())

    return total, breakdown


def _activity_score(user, activity_type_id):
    """[0,1] score based on user's observed activity type distribution."""
    col = {
        ACTIVITY_TYPE_IDS["hiking"]:        "pct_hiking",
        ACTIVITY_TYPE_IDS["trail_running"]: "pct_trail_running",
        ACTIVITY_TYPE_IDS["cycling"]:       "pct_cycling",
    }.get(activity_type_id)

    if col is None:
        return 1.0 / 3.0  # unknown type: neutral
    val = _safe_float(user.get(col))
    return val if val is not None else 1.0 / 3.0


def _terrain_score(user, terrain_type_id):
    """[0,1] score based on user's observed terrain preference."""
    col = {
        TERRAIN_TYPE_IDS["mountain"]:   "pct_mountain",
        TERRAIN_TYPE_IDS["coastal"]:    "pct_coastal",
        TERRAIN_TYPE_IDS["forest"]:     "pct_forest",
        TERRAIN_TYPE_IDS["urban_park"]: "pct_urban_park",
        TERRAIN_TYPE_IDS["desert"]:     "pct_desert",
    }.get(terrain_type_id)

    if col is None:
        return 0.2  # unknown terrain: neutral (1/5 types)
    val = _safe_float(user.get(col))
    return val if val is not None else 0.2


def _zone_score(user, zone_id):
    """[0,1] score based on user's top preferred zones."""
    top1 = _safe_int(user.get("top_zone_1_id"))
    top2 = _safe_int(user.get("top_zone_2_id"))
    top3 = _safe_int(user.get("top_zone_3_id"))

    if zone_id == top1:
        return _ZONE_SCORE["top1"]
    if zone_id == top2:
        return _ZONE_SCORE["top2"]
    if zone_id == top3:
        return _ZONE_SCORE["top3"]
    return _ZONE_SCORE["other"]


def _gaussian_sim(a, b, sigma):
    """Gaussian similarity: 1.0 when a==b, decays with distance.

    Returns 0.5 (neutral) if either value is missing.
    """
    if a is None or b is None:
        return 0.5
    return math.exp(-((a - b) ** 2) / (2 * sigma ** 2))


# =============================================================================
# Data loading
# =============================================================================

def _load_data():
    """Load processed features and raw route metadata.

    Returns:
        user_profiles:      {user_id: dict of normalized features}
        route_feats:        {route_id: dict of normalized features}
        route_names:        {route_id: str name}
        route_raw:          {route_id: {difficulty, distance_km}}
        completed_per_user: {user_id: set of completed route_ids}
    """
    # Normalized user profiles
    user_profiles = {}
    with open(DATA_PROCESSED_DIR / "user_profiles.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            user_profiles[int(row["user_id"])] = row

    # Normalized route features
    route_feats = {}
    with open(DATA_PROCESSED_DIR / "route_features.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            route_feats[int(row["route_id"])] = row

    # Raw route names and display attributes (not normalized)
    route_names = {}
    route_raw = {}
    with open(DATA_RAW_DIR / "routes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rid = int(row["route_id"])
            route_names[rid] = row["name"]
            route_raw[rid] = {
                "difficulty":  row["difficulty"],
                "distance_km": float(row["distance_km"]),
            }

    # Completed routes per user (for exclusion)
    completed_per_user = {}
    with open(DATA_RAW_DIR / "activities.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["completed"] in ("1", "True", "true"):
                uid = int(row["user_id"])
                rid = int(row["route_id"])
                completed_per_user.setdefault(uid, set()).add(rid)

    return user_profiles, route_feats, route_names, route_raw, completed_per_user


# =============================================================================
# Helpers
# =============================================================================

def _safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Content-based route recommender"
    )
    parser.add_argument("user_id", type=int, help="User ID to recommend for")
    parser.add_argument(
        "--n", type=int, default=10,
        help="Number of recommendations (default: 10)",
    )
    parser.add_argument(
        "--include-completed", action="store_true",
        help="Include routes already completed by the user",
    )
    args = parser.parse_args()

    recs = recommend(
        args.user_id,
        n=args.n,
        exclude_completed=not args.include_completed,
    )

    print(f"\nTop {len(recs)} recommendations for user {args.user_id}")
    print("=" * 70)

    for i, r in enumerate(recs, 1):
        zone_name = _ZONE_NAMES.get(r["zone_id"], f"zone_{r['zone_id']}")
        bd = r["breakdown"]

        # Top 3 contributing factors (weight * score, descending)
        ranked = sorted(bd.items(), key=lambda x: WEIGHTS[x[0]] * x[1], reverse=True)
        top3 = [f"{k}={v:.2f}" for k, v in ranked[:3]]

        print(f"\n{i:2d}. [{r['score']:.4f}] {r['route_name']}")
        print(f"     {r['difficulty']}, {r['distance_km']:.1f} km, {zone_name}")
        print(f"     Top factors: {', '.join(top3)}")

    print()


if __name__ == "__main__":
    main()
