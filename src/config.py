"""
Configuracion central para la generacion de datos simulados.

Todas las constantes, distribuciones y parametros de conexion viven aqui.
Seed = 42 para reproducibilidad total.
"""

import os
from datetime import date

# =============================================================================
# Reproducibilidad
# =============================================================================
SEED = 42

# =============================================================================
# Volumenes
# =============================================================================
NUM_USERS = 500
NUM_ROUTES = 200
TARGET_ACTIVITIES = 20_000

# =============================================================================
# Rango temporal
# =============================================================================
DATE_START = date(2022, 1, 1)
DATE_END = date(2024, 12, 31)

# =============================================================================
# IDs de lookup tables (deben coincidir con schema.sql seed data)
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
# Distribuciones de usuarios
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

# registration_date: beta(3,2) sobre DATE_START..DATE_END (sesgo reciente)
USER_REG_BETA_A = 3
USER_REG_BETA_B = 2

# =============================================================================
# Distribuciones de rutas
# =============================================================================

# Reparto de rutas por zona (no uniforme)
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

# Dificultad por tipo de zona (mountain vs non-mountain)
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

# Tipo de actividad por zona
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

# Terreno tipico por zona
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

# Parametros de ruta por dificultad (hiking base)
# (distance_km_mean, distance_km_std, elevation_gain_mean, elevation_gain_std)
ROUTE_PARAMS_BY_DIFFICULTY = {
    "easy": (6.0, 2.0, 200, 80),
    "moderate": (12.0, 3.5, 550, 150),
    "hard": (18.0, 4.0, 1000, 250),
    "expert": (25.0, 5.0, 1600, 350),
}

# Modificadores por tipo de actividad (respecto a hiking base)
ACTIVITY_MODIFIERS = {
    "hiking": {"distance_mult": 1.0, "duration_mult": 1.0},
    "trail_running": {"distance_mult": 1.0, "duration_mult": 0.65},
    "cycling": {"distance_mult": 3.0, "duration_mult": 0.40},
}

# Porcentaje de rutas circulares
CIRCULAR_RATE = 0.55

# =============================================================================
# Distribuciones de actividades
# =============================================================================

# Actividades por usuario: lognormal(mu, sigma) -> pocos power users
ACTIVITIES_LOGNORMAL_MU = 3.0
ACTIVITIES_LOGNORMAL_SIGMA = 0.8

# Pesos de afinidad para seleccion de ruta
AFFINITY_ACTIVITY_MATCH = 3.0       # ruta coincide con actividad preferida
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
AFFINITY_HOME_ZONE = 2.5           # ruta en zona "home" del usuario
AFFINITY_OTHER_ZONE = 1.0
NUM_HOME_ZONES = (1, 3)            # cada usuario tiene 1-3 zonas home

# Tasa de abandono por mismatch experiencia-dificultad
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

# Rating: 60% de completadas tienen rating
RATING_PROBABILITY = 0.60
RATING_MEAN_COMPLETED = 3.8
RATING_STD_COMPLETED = 0.9
RATING_MEAN_ABANDONED = 2.2
RATING_STD_ABANDONED = 0.8

# Factor de ajuste de duracion por experiencia
DURATION_EXPERIENCE_FACTOR = {
    "beginner": 1.25,
    "intermediate": 1.05,
    "advanced": 0.95,
    "expert": 0.85,
}

# Sesgo a fines de semana
WEEKEND_PROBABILITY = 0.55

# =============================================================================
# Vocabulario para nombres de rutas
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
DQ_DISTRIBUTION_TOLERANCE = 0.05   # 5pp max desviacion por categoria
DQ_RATE_TOLERANCE = 0.03           # 3pp para rates (weekend, etc.)
DQ_MEAN_TOLERANCE = 0.3            # max desviacion en medias (ratings)
DQ_ACTIVITIES_TOLERANCE = 0.10     # 10% tolerance en total actividades

# =============================================================================
# Conexion MySQL
# =============================================================================
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "routes_user"),
    "password": os.getenv("MYSQL_PASSWORD", "routes_pass"),
    "database": os.getenv("MYSQL_DATABASE", "outdoor_routes"),
}

# =============================================================================
# Rutas de archivos de salida
# =============================================================================
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
SQL_DIR = PROJECT_ROOT / "sql"
