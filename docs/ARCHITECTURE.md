# Architecture

## Overview

Batch content-based recommender. No real-time inference, no online learning. Data flows in one direction:

```
Simulation → Raw CSVs → Feature Engineering → Processed CSVs → Recommender → Rankings
```

Every stage is a standalone Python module that can be run and inspected independently.

---

## Data pipeline

```
src/generate_all.py
  ├── generators/users.py      → data/raw/users.csv        (500 users)
  ├── generators/routes.py     → data/raw/routes.csv       (200 routes)
  └── generators/activities.py → data/raw/activities.csv   (~20K activities)
         │
         ▼ (optional)
    src/db_loader.py           → MySQL 8.0 (FK order: users → routes → activities)
         │
         ▼
src/build_features.py
  ├── features/user_profiles.py  → 35 features per user
  ├── features/route_features.py → 21 features per route
  └── features/normalization.py  → min-max to [0, 1]
         │
         ▼
  data/processed/
    ├── user_profiles.csv
    ├── route_features.csv
    └── feature_stats.csv
         │
         ▼
src/recommender.py
  └── _score_route(user_profile, route_features) → score in [0, 1]
         │
         ▼
  Ranked list with score breakdown per dimension
```

The CSV path (generate → build_features → recommend) runs without Docker. MySQL is optional for post-load SQL validation.

---

## Database schema

Star schema in MySQL 8.0:

```
dim_activity_types   (id, name)              — 3 rows: hiking, trail_running, cycling
dim_terrain_types    (id, name)              — 5 rows: mountain, coastal, forest, urban_park, desert
dim_geographic_zones (id, name, region)      — 10 rows: Pirineos, Costa Brava, ...

dim_routes (200 rows)
  └── FK → dim_activity_types, dim_terrain_types, dim_geographic_zones

dim_users (500 rows)
  └── FK → dim_activity_types (preferred_activity_type_id, nullable)

fact_activities (~20K rows)
  └── FK → dim_users, dim_routes
```

Seed data for the three lookup tables is embedded in `sql/schema.sql` and loaded automatically when Docker initializes the container.

---

## Scoring model

For each (user, route) pair, 6 sub-scores are computed and combined:

```
score = 0.30 × activity_score
      + 0.25 × difficulty_score
      + 0.15 × terrain_score
      + 0.15 × physical_score
      + 0.10 × zone_score
      + 0.05 × quality_score
```

### Per-dimension detail

**activity_score** — direct lookup in user's activity distribution:
```
pct_hiking        if route.activity_type_id == 1
pct_trail_running if route.activity_type_id == 2
pct_cycling       if route.activity_type_id == 3
```

**difficulty_score** — Gaussian similarity between user's average difficulty and route's difficulty (both normalized by /4 to [0.25, 1.0]):
```
exp( -((user.avg_difficulty_num - route.difficulty_num)² / (2 × 0.25²)) )
```
±1 difficulty level gives similarity ≈ 0.61. ±2 levels gives ≈ 0.14.

**terrain_score** — direct lookup in user's terrain distribution:
```
pct_mountain / pct_coastal / pct_forest / pct_urban_park / pct_desert
```

**physical_score** — mean of two Gaussian similarities (σ = 0.30):
```
(Gaussian(user.avg_distance_km, route.distance_km)
 + Gaussian(user.avg_elevation_gain_m, route.elevation_gain_m)) / 2
```

**zone_score** — tiered lookup:
```
1.0  if route.zone_id == user.top_zone_1_id
0.7  if route.zone_id == user.top_zone_2_id
0.5  if route.zone_id == user.top_zone_3_id
0.1  otherwise (exploration bonus)
```

**quality_score** — `route.avg_rating` normalized to [0, 1] via min-max over the dataset. Defaults to 0.5 (neutral) when a route has no ratings.

### Missing value handling

All Gaussian similarities return 0.5 when either value is None. This handles:
- New routes with no activity history (avg_rating, completion_rate = None)
- Cold start users whose physical features (distance, elevation) are unknown

No special-casing needed in the scoring path.

---

## Normalization consistency

User features and route features must be on the same scale for Gaussian similarity to be valid. This is achieved by normalizing user physical features using the **route feature stats** as reference:

```python
# build_features.py
route_ref_map = {
    "avg_distance_km":      "distance_km",
    "avg_elevation_gain_m": "elevation_gain_m",
    "avg_duration_h":       "estimated_duration_h",
}
```

`feature_stats.csv` persists the min/max values used, enabling reproducible scoring without recomputing.

Difficulty normalization is separate: both `user.avg_difficulty_num` and `route.difficulty_num` are divided by 4 (the maximum value), putting them in [0.25, 1.0] on the same scale.

---

## Cold start

Two scenarios are handled:

**Scenario 1 — User with few activities** (`has_sufficient_data = 0`, threshold: 5 completions):
- Handled during feature engineering in `user_profiles.py`
- Categorical preferences (activity type, difficulty, terrain) fall back to declared fields in `dim_users`
- Physical features remain None → neutral Gaussian (0.5)
- No change in the recommender scoring path

**Scenario 2 — User not yet in the system** (no `user_id` at all):
- Handled by `recommend_new_user(experience_level, preferred_activity_type_id)`
- Builds a synthetic profile:

```
experience → avg_difficulty_num:  beginner=0.31, intermediate=0.50, advanced=0.75, expert=0.94
activity   → pct_*:               1.0 for preferred type, 0.0 for others (uniform if None)
terrain    → pct_*:               uniform 0.2 (no preference data)
physical   → avg_distance_km,     None → neutral Gaussian
             avg_elevation_gain_m
zone       → top_zone_*_id:       None → all zones get exploration bonus (0.1)
```

Same scoring path as any existing user.

---

## Diversification (MMR)

Pure content-based scoring tends to cluster recommendations in the same zone and difficulty — a known echo-chamber effect. Measured diversity@10 = 0.26.

Maximal Marginal Relevance reranking addresses this. At each step:

```
selected ← argmax over remaining candidates of:
    λ × relevance_score − (1−λ) × max_sim(candidate, already_selected)
```

Where similarity between routes is the fraction of shared attributes (difficulty, zone, activity type).

- λ = 1.0: pure relevance (identical to original ranking)
- λ = 0.5: balanced — zone variety goes from 1 to 7 distinct zones in a typical top-10
- λ = 0.0: pure diversity

Default is λ = 0 (backward compatible). Enabled with `--diversity LAMBDA`.

---

## Evaluation methodology

**Behavioral consistency**: for each user, score all routes including already-completed ones. Measure how many completed routes appear in top-K.

This is not leave-one-out (which would require recomputing features per user without the held-out item). It answers: *would the recommender have surfaced routes the user actually chose to do?*

Expected scores are high (hit@10 = 0.99) because the data simulator uses similar affinity signals to the recommender. This is a sanity check and baseline for comparing future changes, not a claim of generalization to unseen real-world data.

Diversity and personalization metrics are system-level and do not depend on implicit feedback.

---

## Migration to PostgreSQL

The project uses standard SQL throughout. Required changes:

| Component | MySQL 8.0 | PostgreSQL 16 |
|-----------|-----------|---------------|
| Auto-increment | `AUTO_INCREMENT` | `GENERATED ALWAYS AS IDENTITY` |
| Boolean column | `TINYINT(1)` | `BOOLEAN` |
| Date formatting | `DATE_FORMAT()` | `TO_CHAR()` |
| Python connector | `mysql-connector-python` | `psycopg2` / `psycopg3` |
| Docker image | `mysql:8.0` | `postgres:16` |
| Connection string | host/port/user/password/database | same keys, different driver |

JOINs, GROUP BY, WHERE, CTEs, and window functions work identically in both engines.

Estimated migration effort: < 1 day.
