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
    python -m src.recommender <user_id> --n 5 --diversity 0.5
    python -m src.recommender --new-user advanced --activity 1
    python -m src.recommender <user_id> --include-completed
"""

import argparse
import csv
import math

from src.config import (
    ACTIVITY_TYPE_IDS,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    EXPERIENCE_NUMERIC_MAP,
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

# Cold start: map experience level to avg_difficulty_num (already /4 normalized)
# Values represent a user's expected avg difficulty based on declared experience.
_EXPERIENCE_TO_DIFF_NUM = {
    "beginner":     1.25 / 4,   # 0.3125 — mostly easy routes
    "intermediate": 2.00 / 4,   # 0.5000 — moderate routes
    "advanced":     3.00 / 4,   # 0.7500 — hard routes
    "expert":       3.75 / 4,   # 0.9375 — hard/expert routes
}


# =============================================================================
# Public API
# =============================================================================

def recommend(user_id, n=10, exclude_completed=True, diversity_lambda=0.0):
    """Return the top N route recommendations for a user.

    Args:
        user_id: int, target user.
        n: int, number of recommendations to return.
        exclude_completed: bool, skip routes the user has already completed.
        diversity_lambda: float in [0, 1]. 0 = pure relevance (default),
            0.5 = balanced, 1 = pure diversity. Uses MMR reranking when > 0.

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

    return _score_and_rank(
        profile, route_feats, route_names, route_raw, excluded, n, diversity_lambda
    )


def recommend_new_user(experience_level, preferred_activity_type_id=None,
                       n=10, diversity_lambda=0.0):
    """Recommend routes for a user not yet in the system (cold start).

    Builds a synthetic profile from declared preferences. Physical features
    (distance, elevation) default to neutral since there is no history.

    Args:
        experience_level: str, one of beginner / intermediate / advanced / expert.
        preferred_activity_type_id: int or None (1=hiking, 2=trail_running, 3=cycling).
        n: int, number of recommendations.
        diversity_lambda: float, MMR diversity parameter (same as recommend()).

    Returns:
        list[dict], same format as recommend().
    """
    valid = set(EXPERIENCE_NUMERIC_MAP.keys())
    if experience_level not in valid:
        raise ValueError(f"experience_level must be one of: {sorted(valid)}")

    _, route_feats, route_names, route_raw, _ = _load_data()
    profile = _build_cold_start_profile(experience_level, preferred_activity_type_id)

    return _score_and_rank(profile, route_feats, route_names, route_raw, set(), n, diversity_lambda)


# =============================================================================
# Internal helpers shared by recommend() and recommend_new_user()
# =============================================================================

def _score_and_rank(profile, route_feats, route_names, route_raw, excluded, n, diversity_lambda):
    """Score all eligible routes and return top-n, optionally MMR-reranked."""
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

    if diversity_lambda > 0.0:
        return _mmr_rerank(scored, route_feats, diversity_lambda, n)
    return scored[:n]


def _mmr_rerank(candidates, route_feats, lambda_, n):
    """Maximal Marginal Relevance reranking.

    At each step, selects the candidate that maximises:
        lambda_ * relevance_score - (1 - lambda_) * max_sim_to_selected

    lambda_=1.0 → pure relevance (identical to original ranking).
    lambda_=0.0 → pure diversity.
    lambda_=0.5 → balanced trade-off (recommended default).

    Args:
        candidates: list of scored dicts, pre-sorted by score desc.
        route_feats: dict route_id -> feature dict (for similarity).
        lambda_: float in [0, 1].
        n: int, number of items to select.

    Returns:
        list[dict], reranked.
    """
    selected = []
    remaining = list(candidates)

    while len(selected) < n and remaining:
        if not selected:
            best = remaining[0]
        else:
            best = max(
                remaining,
                key=lambda x: (
                    lambda_ * x["score"]
                    - (1 - lambda_) * max(
                        _route_sim(x["route_id"], s["route_id"], route_feats)
                        for s in selected
                    )
                ),
            )
        selected.append(best)
        remaining.remove(best)

    return selected


def _route_sim(rid_a, rid_b, route_feats):
    """Similarity between two routes: 1 - fraction of key attributes that differ."""
    a = route_feats.get(rid_a, {})
    b = route_feats.get(rid_b, {})
    diffs = [
        a.get("difficulty")       != b.get("difficulty"),
        a.get("zone_id")          != b.get("zone_id"),
        a.get("activity_type_id") != b.get("activity_type_id"),
    ]
    return 1.0 - sum(diffs) / len(diffs)


def _build_cold_start_profile(experience_level, preferred_activity_type_id):
    """Synthetic user profile from declared experience and activity preference.

    Physical features (distance, elevation) are set to None so the Gaussian
    similarity returns 0.5 (neutral) — no penalisation for unknown fitness level.
    All terrain types get uniform weight (1/5) since no history is available.
    Zone affinity defaults to _ZONE_SCORE_OTHER for all zones.
    """
    avg_difficulty_num = _EXPERIENCE_TO_DIFF_NUM.get(experience_level, 0.5)

    pref = preferred_activity_type_id
    if pref == ACTIVITY_TYPE_IDS["hiking"]:
        pct_hiking, pct_trail_running, pct_cycling = 1.0, 0.0, 0.0
    elif pref == ACTIVITY_TYPE_IDS["trail_running"]:
        pct_hiking, pct_trail_running, pct_cycling = 0.0, 1.0, 0.0
    elif pref == ACTIVITY_TYPE_IDS["cycling"]:
        pct_hiking, pct_trail_running, pct_cycling = 0.0, 0.0, 1.0
    else:
        pct_hiking = pct_trail_running = pct_cycling = 1.0 / 3.0

    uniform_terrain = 1.0 / 5.0

    return {
        "avg_difficulty_num":   avg_difficulty_num,
        "pct_hiking":           pct_hiking,
        "pct_trail_running":    pct_trail_running,
        "pct_cycling":          pct_cycling,
        "pct_mountain":         uniform_terrain,
        "pct_coastal":          uniform_terrain,
        "pct_forest":           uniform_terrain,
        "pct_urban_park":       uniform_terrain,
        "pct_desert":           uniform_terrain,
        "avg_distance_km":      None,   # neutral physical score
        "avg_elevation_gain_m": None,   # neutral physical score
        "top_zone_1_id":        None,   # all zones get exploration bonus
        "top_zone_2_id":        None,
        "top_zone_3_id":        None,
    }


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
        description="Content-based route recommender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.recommender 42\n"
            "  python -m src.recommender 42 --n 5 --diversity 0.5\n"
            "  python -m src.recommender --new-user advanced --activity 1\n"
        ),
    )
    parser.add_argument(
        "user_id", type=int, nargs="?", default=None,
        help="Existing user ID (omit when using --new-user)",
    )
    parser.add_argument(
        "--n", type=int, default=10,
        help="Number of recommendations (default: 10)",
    )
    parser.add_argument(
        "--include-completed", action="store_true",
        help="Include routes already completed by the user",
    )
    parser.add_argument(
        "--diversity", type=float, default=0.0, metavar="LAMBDA",
        help="MMR diversity parameter 0-1 (0=relevance only, 0.5=balanced)",
    )
    parser.add_argument(
        "--new-user", metavar="EXPERIENCE",
        choices=["beginner", "intermediate", "advanced", "expert"],
        help="Cold start: experience level for a user not in the system",
    )
    parser.add_argument(
        "--activity", type=int, choices=[1, 2, 3], default=None,
        help="Preferred activity type ID for cold start (1=hiking, 2=trail, 3=cycling)",
    )
    args = parser.parse_args()

    if args.new_user:
        label = f"new {args.new_user} user"
        recs = recommend_new_user(
            args.new_user,
            preferred_activity_type_id=args.activity,
            n=args.n,
            diversity_lambda=args.diversity,
        )
    elif args.user_id is not None:
        label = f"user {args.user_id}"
        recs = recommend(
            args.user_id,
            n=args.n,
            exclude_completed=not args.include_completed,
            diversity_lambda=args.diversity,
        )
    else:
        parser.error("Provide a user_id or use --new-user EXPERIENCE")
        return

    diversity_tag = f" [diversity lambda={args.diversity}]" if args.diversity > 0 else ""
    print(f"\nTop {len(recs)} recommendations for {label}{diversity_tag}")
    print("=" * 70)

    for i, r in enumerate(recs, 1):
        zone_name = _ZONE_NAMES.get(r["zone_id"], f"zone_{r['zone_id']}")
        bd = r["breakdown"]
        ranked = sorted(bd.items(), key=lambda x: WEIGHTS[x[0]] * x[1], reverse=True)
        top3 = [f"{k}={v:.2f}" for k, v in ranked[:3]]

        print(f"\n{i:2d}. [{r['score']:.4f}] {r['route_name']}")
        print(f"     {r['difficulty']}, {r['distance_km']:.1f} km, {zone_name}")
        print(f"     Top factors: {', '.join(top3)}")

    print()


if __name__ == "__main__":
    main()
