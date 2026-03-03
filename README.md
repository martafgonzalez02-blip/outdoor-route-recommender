# Outdoor Route Recommender

Content-based route recommendation engine for outdoor activities (hiking, trail running, cycling). Built as a complete data platform project: from schema design and data simulation through feature engineering, scoring, and offline evaluation.

**Stack**: Python · MySQL 8.0 · Docker
**Approach**: Content-based, explainable, no ML frameworks
**Data**: 500 users · 200 routes · ~20,000 activities (simulated, seed=42)

---

## Problem

Outdoor route platforms (Wikiloc, Komoot, AllTrails) accumulate thousands of routes but discovery remains poor: basic distance/area filters, popularity-sorted lists, and little personalization.

A user who consistently hikes 15 km mountain routes with 800 m elevation gain receives the same suggestions as someone who walks 5 km along the coast. The system does not learn from behavior.

This project builds a recommendation engine that derives each user's real profile from their activity history and surfaces routes that match their pattern.

## Solution

A 6-dimension scoring model that compares normalized user profiles against route features:

| Dimension | Weight | Signal |
|-----------|--------|--------|
| Activity type | 0.30 | % of hikes / trail runs / rides in user history |
| Difficulty | 0.25 | Gaussian similarity on avg difficulty (σ = 0.25) |
| Terrain | 0.15 | % of mountain / coastal / forest / ... in history |
| Physical fit | 0.15 | Gaussian similarity on distance + elevation (σ = 0.30) |
| Zone affinity | 0.10 | Top 3 preferred geographic zones |
| Route quality | 0.05 | Normalized average rating |

All features normalized to [0, 1] with shared min-max stats, enabling direct comparison between user profiles and route attributes.

## Quick start

```bash
# 1. Start MySQL
docker compose up -d

# 2. Generate simulated data
python -m src.generate_all

# 3. Build user and route features
python -m src.build_features

# 4. Get recommendations
python -m src.recommender 42
python -m src.recommender 42 --n 5 --diversity 0.5
python -m src.recommender --new-user advanced --activity 1

# 5. Run offline evaluation
python -m src.evaluation
```

Requirements: Python 3.8+, [Docker Desktop](https://www.docker.com/products/docker-desktop/).
The CSV pipeline (steps 2–5) runs without Docker.

## Architecture

```
data/raw/                     data/processed/
  users.csv      ─┐
  routes.csv     ─┼─► build_features ─► user_profiles.csv  ─┐
  activities.csv ─┘                     route_features.csv  ─┼─► recommender → ranked list
                                        feature_stats.csv   ─┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full design details, scoring model internals, and migration notes.

## Evaluation results

Methodology: behavioral consistency — completed activities treated as positive implicit feedback.

| Metric | Value | Interpretation |
|--------|-------|----------------|
| hit@10 | 0.99 | 99% of users have ≥1 completed route in top-10 |
| recall@10 | 0.20 | 20% of each user's completed routes recovered |
| ndcg@10 | 0.50 | Good ranking quality — hits appear early in the list |
| coverage@10 | 0.92 | 92% of catalog recommended to at least 1 user |
| diversity@10 | 0.26 | Low — typical content-based trade-off, improved with MMR |
| personalization@10 | 0.92 | Different users get very different recommendation lists |

Diversity is improved with MMR reranking (`--diversity 0.5`): zone variety in a top-10 goes from 1 to 7 distinct zones for a typical user.

## Data model

Star schema in MySQL 8.0. Three lookup dimensions, two main dimensions, one fact table:

```
dim_activity_types   (3 rows) ─┐
dim_terrain_types    (5 rows) ─┤
dim_geographic_zones (10 rows)─┤─► dim_routes (200 rows) ─┐
                                    dim_users  (500 rows) ─┼─► fact_activities (~20K rows)
```

See [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for table definitions, column descriptions, and design rationale.

## Key design decisions

**No ML framework** — features and scoring are pure Python + SQL. Every step is explicit, inspectable, and debuggable without understanding a black box.

**Simulated data** — avoids legal and scraping issues. Distributions are realistic: lognormal activities per user, beta-distributed registration dates, zone-conditional route properties. Reproducible with seed=42.

**Content-based over collaborative filtering** — with a simulated dataset there are no real co-consumption patterns to exploit. Content-based is honest about what the data can support, and every recommendation is explainable.

**Shared normalization stats** — user features (avg_distance_km, avg_elevation_gain_m) are normalized using the same min/max as the corresponding route features. This makes Gaussian similarity between user and route valid on the same scale.

**Cold start at two levels** — users with < 5 completions fall back to declared preferences during feature engineering. Users not yet in the system use `recommend_new_user()` which builds a synthetic profile from experience level and preferred activity.

## Project structure

```
outdoor-route-recommender/
├── data/
│   ├── raw/                     # Generated CSVs (gitignored, reproducible)
│   └── processed/               # Normalized feature CSVs (gitignored)
├── docs/
│   ├── ARCHITECTURE.md          # System design, data flow, scoring model
│   ├── DATA_MODEL.md            # Schema documentation
│   ├── DATA_GENERATION.md       # Simulation methodology and distributions
│   ├── DATA_QUALITY.md          # 28 DQ checks across 5 tiers
│   └── FEATURES.md              # 56 features: user profiles + route features
├── sql/
│   ├── schema.sql               # DDL: star schema with seed data
│   └── quality_checks.sql       # 24 SQL validation queries (post-load)
├── src/
│   ├── config.py                # Centralized parameters and distributions
│   ├── generate_all.py          # Data generation orchestrator
│   ├── db_loader.py             # CSV → MySQL loader (batch, FK order)
│   ├── data_quality.py          # 28 DQ checks on CSVs, 5 tiers
│   ├── build_features.py        # Feature engineering orchestrator
│   ├── recommender.py           # Scoring engine + CLI
│   ├── evaluation.py            # Offline evaluation: 6 metrics
│   └── features/
│       ├── user_profiles.py     # 35 features per user
│       ├── route_features.py    # 21 features per route
│       └── normalization.py     # Min-max scaling utilities
├── docker-compose.yml           # MySQL 8.0 container
└── .env.example                 # Environment variables template
```

## All commands

```bash
# Infrastructure
docker compose up -d                        # Start MySQL
docker compose down                         # Stop MySQL
docker compose down -v                      # Stop and delete data (full reset)
docker exec -it outdoor-routes-db \
  mysql -u routes_user -proutes_pass outdoor_routes   # Connect to DB

# Data pipeline
python -m src.generate_all                  # Generate CSVs in data/raw/
python -m src.generate_all --load-db        # Generate CSVs + load into MySQL
python -m src.generate_all --check          # Generate CSVs + run DQ checks
python -m src.data_quality                  # Run 28 DQ checks on existing CSVs
python -m src.build_features                # Feature engineering: raw/ -> processed/

# Recommender
python -m src.recommender 42                # Top 10 for user 42
python -m src.recommender 42 --n 5         # Top 5
python -m src.recommender 42 --diversity 0.5          # MMR reranking (balanced)
python -m src.recommender 42 --include-completed      # Include already-done routes
python -m src.recommender --new-user advanced         # Cold start, no activity type
python -m src.recommender --new-user beginner --activity 1   # Cold start, hiking

# Evaluation
python -m src.evaluation                    # Print evaluation report
python -m src.evaluation --output docs/EVALUATION_REPORT.txt
```

## Phases

| Phase | Name | Key deliverables |
|-------|------|-----------------|
| 0 | Foundations | README, problem definition |
| 1 | Data model | schema.sql, DATA_MODEL.md |
| 2 | Data generation | generators, db_loader, DATA_GENERATION.md |
| 3 | Data quality | 28 checks, quality_checks.sql, DATA_QUALITY.md |
| 4 | Feature engineering | 56 features, normalization, FEATURES.md |
| 5 | Recommender v1 | recommender.py, 6-dimension scoring |
| 6 | Offline evaluation | evaluation.py, 6 metrics |
| 7 | Edge cases | Cold start, MMR diversification |
| 8 | Final documentation | README, ARCHITECTURE.md |
