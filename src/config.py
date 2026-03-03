"""
Central configuration for simulated data generation.

All constants, distributions and connection parameters live here.
Seed = 42 for full reproducibility.
"""

import os
from datetime import date

# =============================================================================
# Reproducibility
# =============================================================================
SEED = 42

# =============================================================================
# Volumes
# =============================================================================
NUM_USERS = 500
NUM_ROUTES = 200
TARGET_ACTIVITIES = 20_000

# =============================================================================
# Time range
# =============================================================================
DATE_START = date(2022, 1, 1)
DATE_END = date(2024, 12, 31)

# =============================================================================
# Lookup table IDs (must match schema.sql seed data)
# =============================================================================

# dim_activity_types
ACTIVITY_TYPE_IDS = {
    "hiking": 1,
    "trail_running": 2,
    "cycling": 3,
}

# dim_terrain_types
TERRAIN_TYPE_IDS = {
    "mountain": 1,
    "coastal": 2,
    "forest": 3,
    "urban_park": 4,
    "desert": 5,
}

# dim_geographic_zones
ZONE_IDS = {
    "Pirineos": 1,
    "Costa Brava": 2,
    "Sierra de Guadarrama": 3,
    "Picos de Europa": 4,
    "Sierra Nevada": 5,
    "Montseny": 6,
    "Montserrat": 7,
    "Ordesa": 8,
    "Garrotxa": 9,
    "Delta del Ebro": 10,
}

# =============================================================================
# User distributions
# =============================================================================

# experience_level: beginner 35%, intermediate 40%, advanced 18%, expert 7%
USER_EXPERIENCE_DIST = {
    "beginner": 0.35,
    "intermediate": 0.40,
    "advanced": 0.18,
    "expert": 0.07,
}

# preferred_activity_type_id: hiking 51%, trail_running 21%, cycling 13%, NULL 15%
USER_PREFERRED_ACTIVITY_DIST = {
    ACTIVITY_TYPE_IDS["hiking"]: 0.51,
    ACTIVITY_TYPE_IDS["trail_running"]: 0.21,
    ACTIVITY_TYPE_IDS["cycling"]: 0.13,
    None: 0.15,
}

# registration_date: beta(3,2) over DATE_START..DATE_END (recent bias)
USER_REG_BETA_A = 3
USER_REG_BETA_B = 2

# =============================================================================
# Route distributions
# =============================================================================

# Route distribution by zone (non-uniform)
ZONE_ROUTE_DIST = {
    "Pirineos": 0.15,
    "Costa Brava": 0.08,
    "Sierra de Guadarrama": 0.12,
    "Picos de Europa": 0.10,
    "Sierra Nevada": 0.10,
    "Montseny": 0.10,
    "Montserrat": 0.08,
    "Ordesa": 0.10,
    "Garrotxa": 0.10,
    "Delta del Ebro": 0.07,
}

# Difficulty by zone type (mountain vs non-mountain)
ZONE_IS_MOUNTAIN = {
    "Pirineos": True,
    "Costa Brava": False,
    "Sierra de Guadarrama": True,
    "Picos de Europa": True,
    "Sierra Nevada": True,
    "Montseny": True,
    "Montserrat": True,
    "Ordesa": True,
    "Garrotxa": False,
    "Delta del Ebro": False,
}

DIFFICULTY_DIST_MOUNTAIN = {
    "easy": 0.15,
    "moderate": 0.35,
    "hard": 0.35,
    "expert": 0.15,
}

DIFFICULTY_DIST_FLAT = {
    "easy": 0.40,
    "moderate": 0.35,
    "hard": 0.20,
    "expert": 0.05,
}

# Activity type by zone
ZONE_ACTIVITY_DIST = {
    "Pirineos": {"hiking": 0.55, "trail_running": 0.30, "cycling": 0.15},
    "Costa Brava": {"hiking": 0.45, "trail_running": 0.25, "cycling": 0.30},
    "Sierra de Guadarrama": {"hiking": 0.50, "trail_running": 0.30, "cycling": 0.20},
    "Picos de Europa": {"hiking": 0.60, "trail_running": 0.25, "cycling": 0.15},
    "Sierra Nevada": {"hiking": 0.50, "trail_running": 0.30, "cycling": 0.20},
    "Montseny": {"hiking": 0.45, "trail_running": 0.30, "cycling": 0.25},
    "Montserrat": {"hiking": 0.60, "trail_running": 0.30, "cycling": 0.10},
    "Ordesa": {"hiking": 0.65, "trail_running": 0.25, "cycling": 0.10},
    "Garrotxa": {"hiking": 0.45, "trail_running": 0.25, "cycling": 0.30},
    "Delta del Ebro": {"hiking": 0.25, "trail_running": 0.20, "cycling": 0.55},
}

# Typical terrain by zone
ZONE_TERRAIN_DIST = {
    "Pirineos": {"mountain": 0.70, "forest": 0.25, "desert": 0.05},
    "Costa Brava": {"coastal": 0.55, "forest": 0.30, "mountain": 0.15},
    "Sierra de Guadarrama": {"mountain": 0.55, "forest": 0.40, "urban_park": 0.05},
    "Picos de Europa": {"mountain": 0.75, "forest": 0.20, "coastal": 0.05},
    "Sierra Nevada": {"mountain": 0.65, "desert": 0.20, "forest": 0.15},
    "Montseny": {"forest": 0.55, "mountain": 0.40, "urban_park": 0.05},
    "Montserrat": {"mountain": 0.80, "forest": 0.15, "urban_park": 0.05},
    "Ordesa": {"mountain": 0.65, "forest": 0.30, "desert": 0.05},
    "Garrotxa": {"forest": 0.50, "mountain": 0.35, "urban_park": 0.15},
    "Delta del Ebro": {"coastal": 0.50, "urban_park": 0.25, "desert": 0.25},
}

# Route parameters by difficulty (hiking base)
# (distance_km_mean, distance_km_std, elevation_gain_mean, elevation_gain_std)
ROUTE_PARAMS_BY_DIFFICULTY = {
    "easy": (6.0, 2.0, 200, 80),
    "moderate": (12.0, 3.5, 550, 150),
    "hard": (18.0, 4.0, 1000, 250),
    "expert": (25.0, 5.0, 1600, 350),
}

# Modifiers by activity type (relative to hiking base)
ACTIVITY_MODIFIERS = {
    "hiking": {"distance_mult": 1.0, "duration_mult": 1.0},
    "trail_running": {"distance_mult": 1.0, "duration_mult": 0.65},
    "cycling": {"distance_mult": 3.0, "duration_mult": 0.40},
}

# Percentage of circular routes
CIRCULAR_RATE = 0.55

# =============================================================================
# Activity distributions
# =============================================================================

# Activities per user: lognormal(mu, sigma) -> few power users
ACTIVITIES_LOGNORMAL_MU = 3.0
ACTIVITIES_LOGNORMAL_SIGMA = 0.8

# Affinity weights for route selection
AFFINITY_ACTIVITY_MATCH = 3.0       # route matches preferred activity
AFFINITY_ACTIVITY_NO_MATCH = 1.0
AFFINITY_EXP_DIFF_MATRIX = {
    # (experience, difficulty) -> weight
    ("beginner", "easy"): 3.0,
    ("beginner", "moderate"): 1.5,
    ("beginner", "hard"): 0.2,
    ("beginner", "expert"): 0.05,
    ("intermediate", "easy"): 1.5,
    ("intermediate", "moderate"): 3.0,
    ("intermediate", "hard"): 1.5,
    ("intermediate", "expert"): 0.3,
    ("advanced", "easy"): 0.5,
    ("advanced", "moderate"): 1.5,
    ("advanced", "hard"): 3.0,
    ("advanced", "expert"): 1.5,
    ("expert", "easy"): 0.2,
    ("expert", "moderate"): 0.5,
    ("expert", "hard"): 1.5,
    ("expert", "expert"): 3.0,
}
AFFINITY_HOME_ZONE = 2.5           # route in user's "home" zone
AFFINITY_OTHER_ZONE = 1.0
NUM_HOME_ZONES = (1, 3)            # each user has 1-3 home zones

# Abandonment rate by experience-difficulty mismatch
ABANDON_RATE = {
    ("beginner", "easy"): 0.02,
    ("beginner", "moderate"): 0.05,
    ("beginner", "hard"): 0.20,
    ("beginner", "expert"): 0.40,
    ("intermediate", "easy"): 0.01,
    ("intermediate", "moderate"): 0.03,
    ("intermediate", "hard"): 0.08,
    ("intermediate", "expert"): 0.20,
    ("advanced", "easy"): 0.01,
    ("advanced", "moderate"): 0.01,
    ("advanced", "hard"): 0.03,
    ("advanced", "expert"): 0.08,
    ("expert", "easy"): 0.01,
    ("expert", "moderate"): 0.01,
    ("expert", "hard"): 0.02,
    ("expert", "expert"): 0.04,
}

# Rating: 60% of completed activities have a rating
RATING_PROBABILITY = 0.60
RATING_MEAN_COMPLETED = 3.8
RATING_STD_COMPLETED = 0.9
RATING_MEAN_ABANDONED = 2.2
RATING_STD_ABANDONED = 0.8

# Duration adjustment factor by experience
DURATION_EXPERIENCE_FACTOR = {
    "beginner": 1.25,
    "intermediate": 1.05,
    "advanced": 0.95,
    "expert": 0.85,
}

# Weekend bias
WEEKEND_PROBABILITY = 0.55

# =============================================================================
# Route name vocabulary
# =============================================================================

ROUTE_NAME_PARTS = {
    "Pirineos": {
        "prefixes": ["Circular de los Ibones de", "Ascension al", "Vuelta al",
                      "Travesia del", "Camino de", "Ruta de los Lagos de",
                      "Collado de", "Cresta de"],
        "places": ["Anayet", "Midi d'Ossau", "Posets", "Maladeta", "Perdiguero",
                   "Aneto", "Benasque", "Bielsa", "Panticosa", "Aiguestortes",
                   "Estany de Sant Maurici", "Colomers", "Balaitus"],
    },
    "Costa Brava": {
        "prefixes": ["Cami de Ronda por", "Senda litoral de", "Circular de",
                      "Ruta de las Calas de", "Paseo costero de"],
        "places": ["Tossa de Mar", "Calella de Palafrugell", "Cadaques",
                   "Cap de Creus", "Begur", "Llafranc", "Tamariu",
                   "Sant Feliu de Guixols", "Pals", "Sa Tuna"],
    },
    "Sierra de Guadarrama": {
        "prefixes": ["Circular de", "Ascension a", "Ruta por", "Travesia de",
                      "Senda de", "Camino al"],
        "places": ["Penalara", "La Bola del Mundo", "Siete Picos",
                   "La Pedriza", "Navacerrada", "Cercedilla", "Cuerda Larga",
                   "Los Cogorros", "La Maliciosa", "Cabezas de Hierro"],
    },
    "Picos de Europa": {
        "prefixes": ["Ruta del Cares por", "Ascension al", "Circular de",
                      "Travesia de", "Senda del", "Camino a"],
        "places": ["Naranjo de Bulnes", "Covadonga", "Lagos de Covadonga",
                   "Fuente De", "Tresviso", "Sotres", "Bulnes",
                   "Cabrales", "Poncebos", "Vega de Urriellu"],
    },
    "Sierra Nevada": {
        "prefixes": ["Ascension al", "Ruta de", "Circular de", "Vereda de",
                      "Travesia del", "Camino al"],
        "places": ["Mulhacen", "Veleta", "Trevelez", "Capileira",
                   "Lagunas de Sierra Nevada", "Alcazaba", "Cerro del Caballo",
                   "Pradollano", "Guejar Sierra", "Lanjaron"],
    },
    "Montseny": {
        "prefixes": ["Circular del", "Ruta de les Fonts de", "Senda del",
                      "Camino de", "Travesia de"],
        "places": ["Turo de l'Home", "Les Agudes", "Matagalls",
                   "Santa Fe", "Viladrau", "Montseny Poble",
                   "Font de Passavets", "Sot de l'Infern", "Aiguafreda"],
    },
    "Montserrat": {
        "prefixes": ["Circular de", "Via ferrata de", "Camino de",
                      "Ascension a", "Ruta de"],
        "places": ["Sant Joan", "Sant Jeroni", "La Miranda",
                   "Cavall Bernat", "El Bruc", "Collbato",
                   "Santa Cecilia", "Sant Benet", "La Moreneta"],
    },
    "Ordesa": {
        "prefixes": ["Circular de", "Senda de", "Ruta de las Cascadas de",
                      "Travesia del", "Faja de", "Camino a"],
        "places": ["Cola de Caballo", "Faja de Pelay", "Monte Perdido",
                   "Circo de Soaso", "Brecha de Rolando", "Torla",
                   "Anisclo", "Pineta", "Faja de las Flores"],
    },
    "Garrotxa": {
        "prefixes": ["Ruta de los Volcanes de", "Circular de", "Senda del",
                      "Camino por", "Travesia de"],
        "places": ["Santa Margarida", "Croscat", "Fageda d'en Jorda",
                   "Olot", "Castellfollit de la Roca", "Sant Pau",
                   "Batet", "Montsacopa", "Can Serra"],
    },
    "Delta del Ebro": {
        "prefixes": ["Ruta ciclista por", "Vuelta a", "Senda del",
                      "Paseo por", "Circular de"],
        "places": ["La Encanyissada", "El Fangar", "Punta de la Banya",
                   "Riumar", "Deltebre", "Sant Carles de la Rapita",
                   "L'Ampolla", "Illa de Buda", "Els Alfacs"],
    },
}

# =============================================================================
# Data quality thresholds (Phase 3)
# =============================================================================
DQ_DISTRIBUTION_TOLERANCE = 0.05   # 5pp max deviation per category
DQ_RATE_TOLERANCE = 0.03           # 3pp for rates (weekend, etc.)
DQ_MEAN_TOLERANCE = 0.3            # max deviation in means (ratings)
DQ_ACTIVITIES_TOLERANCE = 0.10     # 10% tolerance on total activities

# =============================================================================
# Feature engineering (Phase 4)
# =============================================================================
FEATURE_MIN_ACTIVITIES = 5  # minimum completed activities for reliable profile

DIFFICULTY_NUMERIC_MAP = {
    "easy": 1,
    "moderate": 2,
    "hard": 3,
    "expert": 4,
}

EXPERIENCE_NUMERIC_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}

# Continuous columns for min-max normalization (user profiles)
USER_NORMALIZE_COLS = [
    "total_activities", "completed_activities", "activities_per_month",
    "avg_rating_given", "days_since_last_activity", "activity_span_days",
    "avg_distance_km", "std_distance_km", "avg_elevation_gain_m",
    "std_elevation_gain_m", "avg_duration_h", "avg_pace_factor",
    "num_distinct_zones",
]

# Continuous columns for min-max normalization (route features)
ROUTE_NORMALIZE_COLS = [
    "distance_km", "elevation_gain_m", "elevation_loss_m",
    "estimated_duration_h", "total_activities", "unique_users",
    "avg_rating", "num_ratings", "avg_actual_duration_h",
]

# =============================================================================
# MySQL connection
# =============================================================================
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "routes_user"),
    "password": os.getenv("MYSQL_PASSWORD", "routes_pass"),
    "database": os.getenv("MYSQL_DATABASE", "outdoor_routes"),
}

# =============================================================================
# Output file paths
# =============================================================================
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
