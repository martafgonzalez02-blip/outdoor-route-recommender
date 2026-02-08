# DATA_MODEL.md — Modelo de datos analítico

## Visión general

Esquema estrella diseñado para soportar un motor de recomendación content-based de rutas outdoor. El modelo prioriza:

- **Queries analíticas**: perfilado de usuarios, matching de rutas, evaluación de recomendaciones
- **Explicabilidad**: cada recomendación se puede trazar a atributos concretos (distancia, desnivel, terreno, zona)
- **Simplicidad**: mínima complejidad necesaria, extensible en fases posteriores

**Base de datos**: MySQL 8.0
**Grano de la fact table**: 1 fila = 1 usuario completó (o intentó) 1 ruta en 1 día

## Diagrama

```
dim_activity_types          dim_terrain_types          dim_geographic_zones
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│ activity_type_id │       │ terrain_type_id   │       │ zone_id              │
│ name             │       │ name              │       │ name                 │
└────────┬─────────┘       └────────┬──────────┘       │ region               │
         │                          │                   │ country              │
         │                          │                   │ latitude_center      │
         │                          │                   │ longitude_center     │
         │                          │                   └──────────┬───────────┘
         │                          │                              │
         ▼                          ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              dim_routes                                 │
│  route_id | name | distance_km | elevation_gain_m | elevation_loss_m   │
│  estimated_duration_h | difficulty | is_circular | created_date         │
│  activity_type_id (FK) | terrain_type_id (FK) | zone_id (FK)           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                   fact_activities                     │
│  activity_id | user_id (FK) | route_id (FK)          │
│  activity_date | completed | actual_duration_h       │
│  rating | created_at                                 │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                     dim_users                        │
│  user_id | username | registration_date              │
│  experience_level | preferred_activity_type_id (FK)  │
└──────────────────────────────────────────────────────┘
         │
         ▼
dim_activity_types (FK)
```

**Relaciones:**
- `fact_activities` → `dim_users` (N:1)
- `fact_activities` → `dim_routes` (N:1)
- `dim_routes` → `dim_activity_types` (N:1)
- `dim_routes` → `dim_terrain_types` (N:1)
- `dim_routes` → `dim_geographic_zones` (N:1)
- `dim_users` → `dim_activity_types` (N:1, nullable)

## Tablas

### Dimensiones lookup

| Tabla | Propósito | Filas esperadas |
|-------|-----------|-----------------|
| `dim_activity_types` | Catálogo de actividades: hiking, trail_running, cycling | 3 |
| `dim_terrain_types` | Catálogo de terrenos: mountain, coastal, forest, urban_park, desert | 5 |
| `dim_geographic_zones` | Zonas geográficas con coordenadas centrales | 10-20 |

### Dimensiones principales

**`dim_users`** — Perfil estático del usuario al registrarse.
- `experience_level`: declarado por el usuario, no calculado. El perfil real se deriva de `fact_activities`.
- `preferred_activity_type_id`: opcional. Si es NULL, se infiere del historial.

**`dim_routes`** — Catálogo de rutas con atributos de contenido.
- Atributos clave para recomendación: `distance_km`, `elevation_gain_m`, `difficulty`, `activity_type_id`, `terrain_type_id`, `zone_id`.
- `is_circular`: indica si la ruta empieza y termina en el mismo punto.
- Cada ruta tiene exactamente 1 tipo de actividad, 1 tipo de terreno y 1 zona geográfica.

### Tabla de hechos

**`fact_activities`** — Registro de actividades reales de usuarios en rutas.
- `completed`: FALSE si el usuario abandonó la ruta antes de terminar.
- `actual_duration_h`: duración real (puede diferir de `estimated_duration_h` en la ruta).
- `rating`: 1-5, nullable. No todos los usuarios puntúan cada actividad.
- Constraint CHECK: `rating` entre 1 y 5 (o NULL).

## Preguntas de producto que el modelo responde

### 1. Perfil implícito de un usuario
¿Qué tipo de rutas hace realmente un usuario? (vs. lo que declaró al registrarse)

```sql
SELECT
    u.user_id,
    u.experience_level AS declared_level,
    at.name AS activity_type,
    AVG(r.distance_km) AS avg_distance,
    AVG(r.elevation_gain_m) AS avg_elevation,
    COUNT(*) AS total_activities,
    AVG(fa.rating) AS avg_rating
FROM fact_activities fa
JOIN dim_users u ON fa.user_id = u.user_id
JOIN dim_routes r ON fa.route_id = r.route_id
JOIN dim_activity_types at ON r.activity_type_id = at.activity_type_id
WHERE fa.completed = TRUE
GROUP BY u.user_id, u.experience_level, at.name;
```

### 2. Rutas similares a una ruta dada
Encuentra rutas con atributos parecidos (mismo tipo, terreno similar, rango de distancia/desnivel).

```sql
SELECT
    r2.route_id,
    r2.name,
    r2.distance_km,
    r2.elevation_gain_m,
    r2.difficulty
FROM dim_routes r1
JOIN dim_routes r2
    ON r1.activity_type_id = r2.activity_type_id
    AND r1.route_id != r2.route_id
WHERE r1.route_id = 1  -- ruta de referencia
    AND ABS(r2.distance_km - r1.distance_km) < 5
    AND ABS(r2.elevation_gain_m - r1.elevation_gain_m) < 300
ORDER BY ABS(r2.distance_km - r1.distance_km) + ABS(r2.elevation_gain_m - r1.elevation_gain_m);
```

### 3. Rutas no descubiertas por un usuario
Rutas que encajan con el perfil del usuario pero que aún no ha hecho.

```sql
SELECT r.route_id, r.name, r.distance_km, r.difficulty
FROM dim_routes r
WHERE r.activity_type_id IN (
    SELECT r2.activity_type_id
    FROM fact_activities fa2
    JOIN dim_routes r2 ON fa2.route_id = r2.route_id
    WHERE fa2.user_id = 1
    GROUP BY r2.activity_type_id
    ORDER BY COUNT(*) DESC
    LIMIT 1
)
AND r.route_id NOT IN (
    SELECT fa3.route_id
    FROM fact_activities fa3
    WHERE fa3.user_id = 1
)
ORDER BY r.route_id;
```

### 4. Calidad percibida de rutas
Ranking de rutas por rating medio, filtrado por mínimo de actividades.

```sql
SELECT
    r.route_id,
    r.name,
    r.difficulty,
    COUNT(*) AS total_activities,
    AVG(fa.rating) AS avg_rating,
    SUM(CASE WHEN fa.completed = FALSE THEN 1 ELSE 0 END) AS abandonments
FROM fact_activities fa
JOIN dim_routes r ON fa.route_id = r.route_id
WHERE fa.rating IS NOT NULL
GROUP BY r.route_id, r.name, r.difficulty
HAVING total_activities >= 5
ORDER BY avg_rating DESC;
```

### 5. Ratio de abandono por dificultad y nivel de experiencia
¿Los principiantes abandonan más rutas difíciles?

```sql
SELECT
    u.experience_level,
    r.difficulty,
    COUNT(*) AS total,
    SUM(CASE WHEN fa.completed = FALSE THEN 1 ELSE 0 END) AS abandonments,
    ROUND(SUM(CASE WHEN fa.completed = FALSE THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS abandonment_pct
FROM fact_activities fa
JOIN dim_users u ON fa.user_id = u.user_id
JOIN dim_routes r ON fa.route_id = r.route_id
GROUP BY u.experience_level, r.difficulty
ORDER BY u.experience_level, r.difficulty;
```

### 6. Zonas geográficas más populares por tipo de actividad

```sql
SELECT
    gz.name AS zone_name,
    at.name AS activity_type,
    COUNT(*) AS total_activities,
    COUNT(DISTINCT fa.user_id) AS unique_users
FROM fact_activities fa
JOIN dim_routes r ON fa.route_id = r.route_id
JOIN dim_geographic_zones gz ON r.zone_id = gz.zone_id
JOIN dim_activity_types at ON r.activity_type_id = at.activity_type_id
GROUP BY gz.name, at.name
ORDER BY total_activities DESC;
```

## Decisiones de diseño y trade-offs

| Decisión | Justificación |
|----------|---------------|
| **1 terrain_type por ruta** (sin tabla bridge M:N) | Mínima complejidad. Una ruta de montaña que pasa por bosque se clasifica por su terreno dominante. Se puede añadir M:N en el futuro si los datos lo requieren. |
| **experience_level como ENUM estático** | Viene del registro del usuario, no se recalcula. El perfil real se deriva de queries sobre fact_activities. Evita complejidad de triggers o campos calculados. |
| **Sin tabla de bookmarks/wishlist** | La fact table registra actividades reales. Interacciones tipo "guardar para después" se pueden añadir en Fase 7 (edge cases) si son necesarias. |
| **Sin soft deletes** | No hay columna `deleted_at`. Para datos simulados no necesitamos rastrear borrados. |
| **Coordenadas en zona, no en ruta** | Las rutas se geolocalizan por zona (resolución suficiente para recomendación por proximidad). No necesitamos coordenadas de inicio/fin por ruta con datos simulados. |
| **CHECK constraint en rating** | MySQL 8.0 soporta CHECK constraints. Garantiza integridad a nivel de BD, no solo en la capa de aplicación. |
| **Índices en FKs de fact_activities** | Los JOINs por user_id y route_id son el patrón más frecuente en queries de recomendación. El índice en activity_date permite filtrar por ventana temporal. |
| **Datos semilla en el DDL** | Las dimensiones lookup (activity_types, terrain_types, geographic_zones) se insertan con el schema para que estén disponibles inmediatamente. |

## Evolución futura

| Fase | Posible extensión |
|------|-------------------|
| Fase 2 | Ingesta masiva de datos simulados en las tablas existentes |
| Fase 4 | Vistas materializadas o tablas derivadas para features precalculadas (perfil de usuario, scores de ruta) |
| Fase 7 | Tabla `user_interactions` para bookmarks, búsquedas, vistas — señales implícitas para cold start |
| Fase 7 | Tabla bridge `route_terrain_types` si una ruta necesita múltiples terrenos |
| Fase 7 | Campos `latitude`/`longitude` en `dim_routes` si se necesita matching geográfico fino |
| Fase 8 | Particionado de `fact_activities` por fecha si el volumen crece |
