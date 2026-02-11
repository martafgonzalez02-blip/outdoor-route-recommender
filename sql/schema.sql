-- =============================================================================
-- Outdoor Route Recommender — Star Schema
-- Fase 1: Modelo de datos analítico
-- MySQL 8.0
-- =============================================================================

-- Ejecutar en orden: dimensiones lookup → dimensiones principales → hechos.
-- Este archivo se monta en /docker-entrypoint-initdb.d y se ejecuta
-- automáticamente al crear el contenedor por primera vez.

-- -----------------------------------------------------------------------------
-- Dimensiones lookup
-- -----------------------------------------------------------------------------

CREATE TABLE dim_activity_types (
    activity_type_id INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dim_terrain_types (
    terrain_type_id INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dim_geographic_zones (
    zone_id          INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    region           VARCHAR(100),
    country          VARCHAR(100) DEFAULT 'España',
    latitude_center  DECIMAL(9,6),
    longitude_center DECIMAL(9,6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- Dimensiones principales
-- -----------------------------------------------------------------------------

CREATE TABLE dim_users (
    user_id                    INT AUTO_INCREMENT PRIMARY KEY,
    username                   VARCHAR(100) NOT NULL UNIQUE,
    registration_date          DATE NOT NULL,
    experience_level           ENUM('beginner','intermediate','advanced','expert') NOT NULL,
    preferred_activity_type_id INT,

    CONSTRAINT fk_user_activity_type
        FOREIGN KEY (preferred_activity_type_id)
        REFERENCES dim_activity_types (activity_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dim_routes (
    route_id             INT AUTO_INCREMENT PRIMARY KEY,
    name                 VARCHAR(200) NOT NULL,
    description          TEXT,
    distance_km          DECIMAL(6,2) NOT NULL,
    elevation_gain_m     INT NOT NULL,
    elevation_loss_m     INT NOT NULL,
    estimated_duration_h DECIMAL(4,1) NOT NULL,
    difficulty           ENUM('easy','moderate','hard','expert') NOT NULL,
    is_circular          BOOLEAN DEFAULT FALSE,
    activity_type_id     INT NOT NULL,
    terrain_type_id      INT NOT NULL,
    zone_id              INT NOT NULL,
    created_date         DATE NOT NULL,

    CONSTRAINT fk_route_activity_type
        FOREIGN KEY (activity_type_id)
        REFERENCES dim_activity_types (activity_type_id),
    CONSTRAINT fk_route_terrain_type
        FOREIGN KEY (terrain_type_id)
        REFERENCES dim_terrain_types (terrain_type_id),
    CONSTRAINT fk_route_zone
        FOREIGN KEY (zone_id)
        REFERENCES dim_geographic_zones (zone_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- Tabla de hechos
-- -----------------------------------------------------------------------------

CREATE TABLE fact_activities (
    activity_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    route_id        INT NOT NULL,
    activity_date   DATE NOT NULL,
    completed       BOOLEAN DEFAULT TRUE,
    actual_duration_h DECIMAL(4,1),
    rating          TINYINT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_activity_user
        FOREIGN KEY (user_id)
        REFERENCES dim_users (user_id),
    CONSTRAINT fk_activity_route
        FOREIGN KEY (route_id)
        REFERENCES dim_routes (route_id),

    CONSTRAINT chk_rating
        CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índices para queries de recomendación (JOINs frecuentes por FK)
CREATE INDEX idx_fact_user  ON fact_activities (user_id);
CREATE INDEX idx_fact_route ON fact_activities (route_id);
CREATE INDEX idx_fact_date  ON fact_activities (activity_date);

-- Índices en dim_routes para filtrado por atributos de contenido
CREATE INDEX idx_route_activity ON dim_routes (activity_type_id);
CREATE INDEX idx_route_terrain  ON dim_routes (terrain_type_id);
CREATE INDEX idx_route_zone     ON dim_routes (zone_id);
CREATE INDEX idx_route_difficulty ON dim_routes (difficulty);

-- -----------------------------------------------------------------------------
-- Datos semilla para dimensiones lookup
-- -----------------------------------------------------------------------------

INSERT INTO dim_activity_types (name) VALUES
    ('hiking'),
    ('trail_running'),
    ('cycling');

INSERT INTO dim_terrain_types (name) VALUES
    ('mountain'),
    ('coastal'),
    ('forest'),
    ('urban_park'),
    ('desert');

INSERT INTO dim_geographic_zones (name, region, country, latitude_center, longitude_center) VALUES
    ('Pirineos',        'Cataluña',         'España', 42.6500,  1.0000),
    ('Costa Brava',     'Cataluña',         'España', 41.8500,  3.1000),
    ('Sierra de Guadarrama', 'Madrid',      'España', 40.7800, -3.9700),
    ('Picos de Europa', 'Asturias',         'España', 43.2000, -4.8500),
    ('Sierra Nevada',   'Andalucía',        'España', 37.0500, -3.3700),
    ('Montseny',        'Cataluña',         'España', 41.7700,  2.4000),
    ('Montserrat',      'Cataluña',         'España', 41.5933,  1.8370),
    ('Ordesa',          'Aragón',           'España', 42.6400,  0.0500),
    ('Garrotxa',        'Cataluña',         'España', 42.1500,  2.5000),
    ('Delta del Ebro',  'Cataluña',         'España', 40.7000,  0.8500);
