# DATA_GENERATION.md — Generacion de datos simulados

## Resumen

Datos simulados realistas para las 3 tablas principales del esquema estrella:
- **500 usuarios** (`dim_users`)
- **200 rutas** (`dim_routes`)
- **~20,000 actividades** (`fact_activities`)

Seed fijo (42) para reproducibilidad total. Todas las distribuciones parametrizadas en `src/config.py`.

## Uso

```bash
# Generar CSVs (no requiere Docker)
python -m src.generate_all

# Generar CSVs + cargar en MySQL
python -m src.generate_all --load-db

# Seed personalizado
python -m src.generate_all --seed 123
```

**Archivos generados:**
```
data/raw/
  users.csv        (~500 filas)
  routes.csv       (~200 filas)
  activities.csv   (~20,000 filas)
```

## Distribuciones por entidad

### Usuarios (`src/generators/users.py`)

| Campo | Distribucion | Detalle |
|-------|-------------|---------|
| `registration_date` | Beta(3, 2) | Sesgo hacia fechas recientes (2022-2024) |
| `experience_level` | Categorica | beginner 35%, intermediate 40%, advanced 18%, expert 7% |
| `preferred_activity_type_id` | Categorica | hiking 51%, trail_running 21%, cycling 13%, NULL 15% |
| `username` | Faker es_ES | Base aleatoria + sufijo numerico para unicidad |

### Rutas (`src/generators/routes.py`)

Distribuciones condicionales: la zona determina la distribucion de actividad, terreno y dificultad.

| Campo | Distribucion | Detalle |
|-------|-------------|---------|
| `zone_id` | Categorica ponderada | Pirineos 15%, Guadarrama 12%, Picos/S.Nevada/Montseny/Ordesa/Garrotxa 10% cada |
| `activity_type_id` | Condicional a zona | Ej: Ordesa 65% hiking, Delta del Ebro 55% cycling |
| `terrain_type_id` | Condicional a zona | Ej: Montserrat 80% mountain, Montseny 55% forest |
| `difficulty` | Condicional a zona | Mountain: moderate/hard 35% cada. Flat: easy 40% |
| `distance_km` | Gauss truncado | Media/std por dificultad, multiplicador por actividad (cycling x3) |
| `elevation_gain_m` | Gauss truncado | Media/std por dificultad, min 10m |
| `elevation_loss_m` | Condicional | Circular: igual al gain. Lineal: gain * U(0.6, 1.0) |
| `estimated_duration_h` | Calculado | (dist/5 + elev/600) * activity_modifier |
| `is_circular` | Bernoulli(0.55) | 55% de rutas son circulares |
| `created_date` | Uniforme | Año previo a DATE_START (2021) |
| `name` | Vocabulario por zona | Combinacion de prefijo + lugar, sin duplicados |

**Parametros de ruta por dificultad (hiking base):**

| Dificultad | Distancia (media ± std) | Desnivel (media ± std) |
|------------|------------------------|------------------------|
| easy | 6.0 ± 2.0 km | 200 ± 80 m |
| moderate | 12.0 ± 3.5 km | 550 ± 150 m |
| hard | 18.0 ± 4.0 km | 1000 ± 250 m |
| expert | 25.0 ± 5.0 km | 1600 ± 350 m |

### Actividades (`src/generators/activities.py`)

El generador mas complejo: modela el comportamiento de cada usuario seleccionando rutas por afinidad.

| Campo | Distribucion | Detalle |
|-------|-------------|---------|
| Actividades/usuario | Lognormal(3.0, 0.8) | Escalado a ~20K total. Pocos power users, muchos casuales |
| Seleccion de ruta | Weighted sampling | Peso = activity_match * exp_diff_matrix * home_zone |
| `activity_date` | Post-registro + weekend bias | 55% fin de semana |
| `completed` | Bernoulli(1 - abandon_rate) | Tasa variable por (experiencia, dificultad) |
| `actual_duration_h` | estimated * exp_factor * N(1, 0.15) | Abandonados: 30-80% de estimada |
| `rating` | 60% probabilidad, Gauss | Completadas: media 3.8. Abandonadas: media 2.2. Clamp [1,5] |

**Modelo de afinidad para seleccion de ruta:**

```
weight(usuario, ruta) = W_activity * W_experience * W_zone

W_activity = 3.0  si ruta.activity == usuario.preferred_activity
             1.0  en otro caso

W_experience = matrix[usuario.experience, ruta.difficulty]
               (3.0 para match perfecto, 0.05 para mismatch extremo)

W_zone = 2.5  si ruta.zone in usuario.home_zones
         1.0  en otro caso
```

Cada usuario tiene 1-3 "home zones" asignadas aleatoriamente.

**Tasas de abandono:**

| Experiencia \ Dificultad | easy | moderate | hard | expert |
|--------------------------|------|----------|------|--------|
| beginner | 2% | 5% | 20% | 40% |
| intermediate | 1% | 3% | 8% | 20% |
| advanced | 1% | 1% | 3% | 8% |
| expert | 1% | 1% | 2% | 4% |

## Carga en base de datos (`src/db_loader.py`)

Requiere MySQL corriendo via Docker:

```bash
docker compose up -d
python -m src.generate_all --load-db
```

- Lee CSVs de `data/raw/`
- INSERT batch (100 filas) respetando orden de FKs: users → routes → activities
- Verifica conteos post-insercion
- Si la DB no esta disponible, muestra mensaje claro sin fallar

## Queries de validacion

Ejecutar despues de `--load-db` para verificar que los datos coinciden con las distribuciones esperadas.

### Volumen total
```sql
SELECT 'users' AS tabla, COUNT(*) AS filas FROM dim_users
UNION ALL
SELECT 'routes', COUNT(*) FROM dim_routes
UNION ALL
SELECT 'activities', COUNT(*) FROM fact_activities;
```

### Distribucion de experiencia (esperar: beginner ~35%, intermediate ~40%)
```sql
SELECT experience_level, COUNT(*) AS n,
       ROUND(COUNT(*) / (SELECT COUNT(*) FROM dim_users) * 100, 1) AS pct
FROM dim_users
GROUP BY experience_level
ORDER BY FIELD(experience_level, 'beginner', 'intermediate', 'advanced', 'expert');
```

### Rutas por zona
```sql
SELECT gz.name, COUNT(*) AS n,
       ROUND(COUNT(*) / (SELECT COUNT(*) FROM dim_routes) * 100, 1) AS pct
FROM dim_routes r
JOIN dim_geographic_zones gz ON r.zone_id = gz.zone_id
GROUP BY gz.name
ORDER BY n DESC;
```

### Tasa de abandono por experiencia y dificultad
```sql
SELECT u.experience_level, r.difficulty,
       COUNT(*) AS total,
       SUM(CASE WHEN fa.completed = 0 THEN 1 ELSE 0 END) AS abandoned,
       ROUND(SUM(CASE WHEN fa.completed = 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS abandon_pct
FROM fact_activities fa
JOIN dim_users u ON fa.user_id = u.user_id
JOIN dim_routes r ON fa.route_id = r.route_id
GROUP BY u.experience_level, r.difficulty
ORDER BY u.experience_level, r.difficulty;
```

### Rating medio por completado vs abandonado
```sql
SELECT
    CASE WHEN completed THEN 'completada' ELSE 'abandonada' END AS estado,
    COUNT(*) AS total,
    SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) AS con_rating,
    ROUND(AVG(rating), 2) AS rating_medio
FROM fact_activities
GROUP BY completed;
```

### Actividades por dia de la semana (esperar: sabado/domingo > 55%)
```sql
SELECT DAYNAME(activity_date) AS dia,
       COUNT(*) AS n,
       ROUND(COUNT(*) / (SELECT COUNT(*) FROM fact_activities) * 100, 1) AS pct
FROM fact_activities
GROUP BY DAYNAME(activity_date), DAYOFWEEK(activity_date)
ORDER BY DAYOFWEEK(activity_date);
```

## Arquitectura

```
src/config.py                 Parametros centralizados (seed, volumenes, distribuciones)
    |
    v
src/generators/
    users.py                  generate_users() → data/raw/users.csv
    routes.py                 generate_routes() → data/raw/routes.csv
    activities.py             generate_activities(users, routes) → data/raw/activities.csv
    |
    v
src/generate_all.py           Orquestador: python -m src.generate_all [--load-db]
    |
    v
src/db_loader.py              Lee CSVs → INSERT batch en MySQL
```

## Decisiones tecnicas

| Decision | Justificacion |
|----------|---------------|
| **Sin numpy** | `random.betavariate`, `random.gauss`, `random.lognormvariate` cubren las distribuciones necesarias. Evita dependencia pesada. |
| **CSV-first** | Genera CSVs siempre, DB opcional. Permite inspeccion sin Docker. |
| **Sin clases** | Funciones puras que reciben/devuelven listas de dicts. Minima complejidad. |
| **Todo en config.py** | Cero magic numbers en generators. Facilita ajustar distribuciones sin tocar logica. |
| **Lognormal para actividades/usuario** | Modela la distribucion tipica de plataformas: muchos usuarios casuales, pocos power users. |
| **Afinidad multiplicativa** | Tres factores (actividad, experiencia, zona) se multiplican. Un mismatch extremo reduce el peso sin eliminarlo. |
| **Faker es_ES** | Usernames con sabor local, coherente con zonas geograficas espanolas. |
