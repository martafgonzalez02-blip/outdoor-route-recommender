# Feature Engineering — Fase 4

Transformacion de datos raw a vectores de features normalizados, listos para el recomendador.

## Enfoque

El feature engineering transforma las 3 tablas raw (users, routes, activities) en 2 tablas de features:

- **User profiles**: vector de preferencias derivado del historial de actividades completadas.
- **Route features**: atributos estaticos de la ruta + metricas agregadas de uso real.

Ambas tablas se normalizan a `[0, 1]` con min-max scaling y se persisten en `data/processed/`.

```
data/raw/                          data/processed/
  users.csv      ─┐
  routes.csv     ─┼─> build_features ─> user_profiles.csv    (500 filas x 35 features)
  activities.csv ─┘                  ─> route_features.csv   (200 filas x 21 features)
                                     ─> feature_stats.csv    (stats de normalizacion)
```

## Decisiones de diseno

| Decision | Justificacion |
|----------|--------------|
| Solo completadas para preferencias | Actividades abandonadas indican mismatch, no preferencia |
| Minimo 5 completadas para perfil fiable | Con < 5, fallback a datos declarados (experience_level, preferred_activity) |
| Normalizacion min-max (no z-score) | Los features se usan para similaridad coseno; necesitamos rango acotado |
| Features fisicos normalizados contra rutas | avg_distance_km del usuario se escala con el rango de distance_km de rutas, para comparabilidad directa |
| difficulty_num / 4 (no min-max) | Escala ordinal conocida; min-max distorsionaria si el dataset no tiene rutas expert |
| Stats persistidos a CSV | Reproducibilidad: mismos min/max para normalizar nuevos datos |

## User profiles — 35 features

### Volumen y engagement (8)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `total_activities` | float [0,1] | Total actividades (normalizado) |
| `completed_activities` | float [0,1] | Actividades completadas (normalizado) |
| `completion_rate` | float [0,1] | completadas / total |
| `rated_activities` | int | Actividades con rating (absoluto) |
| `avg_rating_given` | float | Media de ratings otorgados (1-5) |
| `days_since_last_activity` | float [0,1] | Dias desde ultima actividad hasta 2024-12-31 (normalizado) |
| `activity_span_days` | float [0,1] | Dias entre primera y ultima actividad (normalizado) |
| `activities_per_month` | float [0,1] | Frecuencia mensual (normalizado) |

### Preferencia de dificultad (5)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `pct_easy` | float [0,1] | Proporcion de completadas en rutas easy |
| `pct_moderate` | float [0,1] | Proporcion en rutas moderate |
| `pct_hard` | float [0,1] | Proporcion en rutas hard |
| `pct_expert` | float [0,1] | Proporcion en rutas expert |
| `avg_difficulty_num` | float [0,1] | Media numerica de dificultad / 4 |

### Preferencia de actividad (3)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `pct_hiking` | float [0,1] | Proporcion de completadas en hiking |
| `pct_trail_running` | float [0,1] | Proporcion en trail running |
| `pct_cycling` | float [0,1] | Proporcion en cycling |

### Perfil fisico (6)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `avg_distance_km` | float [0,1] | Distancia media (normalizado vs rango de rutas) |
| `std_distance_km` | float [0,1] | Desviacion de distancia (normalizado) |
| `avg_elevation_gain_m` | float [0,1] | Desnivel medio (normalizado vs rango de rutas) |
| `std_elevation_gain_m` | float [0,1] | Desviacion de desnivel (normalizado) |
| `avg_duration_h` | float [0,1] | Duracion media (normalizado vs rango de rutas) |
| `avg_pace_factor` | float [0,1] | actual / estimado: < 1 = rapido, > 1 = lento (normalizado) |

### Preferencia geografica (6)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `top_zone_1_id` | int | ID de zona mas visitada |
| `top_zone_1_pct` | float [0,1] | Proporcion de actividades en zona top 1 |
| `top_zone_2_id` | int | ID de segunda zona |
| `top_zone_2_pct` | float [0,1] | Proporcion en zona top 2 |
| `top_zone_3_id` | int | ID de tercera zona |
| `num_distinct_zones` | float [0,1] | Zonas distintas visitadas (normalizado) |

### Preferencia de terreno (5)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `pct_mountain` | float [0,1] | Proporcion en terreno montania |
| `pct_coastal` | float [0,1] | Proporcion en terreno costero |
| `pct_forest` | float [0,1] | Proporcion en bosque |
| `pct_urban_park` | float [0,1] | Proporcion en parque urbano |
| `pct_desert` | float [0,1] | Proporcion en desierto |

### Formato y meta (2)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `pct_circular` | float [0,1] | Proporcion de rutas circulares completadas |
| `has_sufficient_data` | int {0,1} | 1 si >= 5 completadas (perfil basado en comportamiento real) |

## Route features — 21 features

### Atributos estaticos (9)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `distance_km` | float [0,1] | Distancia (normalizado) |
| `elevation_gain_m` | float [0,1] | Desnivel positivo (normalizado) |
| `elevation_loss_m` | float [0,1] | Desnivel negativo (normalizado) |
| `estimated_duration_h` | float [0,1] | Duracion estimada (normalizado) |
| `difficulty` | str | Etiqueta: easy, moderate, hard, expert |
| `difficulty_num` | float [0,1] | Dificultad numerica / 4 |
| `is_circular` | int {0,1} | 1 si la ruta es circular |
| `activity_type_id` | int | ID del tipo de actividad (1=hiking, 2=trail_running, 3=cycling) |
| `terrain_type_id` | int | ID del tipo de terreno |
| `zone_id` | int | ID de zona geografica |

### Metricas de uso (7)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `total_activities` | float [0,1] | Total de actividades en la ruta (normalizado) |
| `unique_users` | float [0,1] | Usuarios unicos (normalizado) |
| `completion_rate` | float [0,1] | Tasa de completado |
| `avg_rating` | float [0,1] | Rating medio (normalizado) |
| `num_ratings` | float [0,1] | Numero de ratings (normalizado) |
| `avg_actual_duration_h` | float [0,1] | Duracion real media (normalizado) |
| `duration_accuracy` | float | actual / estimado (precision de la estimacion) |

### Perfil demografico de usuarios (4)

| Feature | Tipo | Descripcion |
|---------|------|-------------|
| `pct_beginners` | float [0,1] | Proporcion de usuarios beginner en la ruta |
| `pct_intermediate` | float [0,1] | Proporcion intermediate |
| `pct_advanced` | float [0,1] | Proporcion advanced |
| `pct_expert_users` | float [0,1] | Proporcion expert |

## Normalizacion

### Min-max scaling

```
x_norm = (x - min) / (max - min)
```

Clamp a `[0, 1]` para evitar valores fuera de rango. Si `min == max`, devuelve `0.0`.

### Referencia cruzada para features fisicos

Los features fisicos del usuario se normalizan usando el rango de las rutas como referencia:

| User feature | Normalizado contra |
|-------------|-------------------|
| `avg_distance_km` | min/max de `distance_km` en rutas |
| `avg_elevation_gain_m` | min/max de `elevation_gain_m` en rutas |
| `avg_duration_h` | min/max de `estimated_duration_h` en rutas |

Esto permite comparacion directa usuario-ruta: si un usuario tiene `avg_distance_km = 0.6` y una ruta tiene `distance_km = 0.6`, estan en la misma escala.

### Stats persistidos

`data/processed/feature_stats.csv` contiene min, max y count de cada feature normalizado. Formato:

```csv
feature,min,max,count
user_total_activities,1.0,312.0,500
route_distance_km,2.1,45.3,200
...
```

## Cold start y fallback

| Situacion | Estrategia |
|-----------|-----------|
| Usuario con < 5 completadas | `has_sufficient_data = 0`. Features de actividad/dificultad/terreno usan fallback a datos declarados (experience_level -> dificultad, preferred_activity_type_id -> actividad). Features fisicos = None. |
| Usuario sin actividades | Proporciones uniformes para actividad (1/3 cada una), dificultad segun experience_level declarado. Todos los features fisicos = None. |
| Ruta sin actividades | Metricas de uso = None (total_activities = 0, ratings = None). Solo atributos estaticos disponibles. |

## Archivos generados

| Archivo | Contenido |
|---------|-----------|
| `data/processed/user_profiles.csv` | 500 filas x 35 features |
| `data/processed/route_features.csv` | 200 filas x 21 features |
| `data/processed/feature_stats.csv` | Min/max/count por feature normalizado |

## Ejecucion

```bash
python -m src.build_features
```

Requiere que `data/raw/` contenga los 3 CSVs generados en Fase 2 (`python -m src.generate_all`).

## Estructura de codigo

```
src/
├── build_features.py             # Orquestador: carga -> computa -> normaliza -> escribe
├── features/
│   ├── __init__.py               # Exports: build_user_profiles, build_route_features
│   ├── user_profiles.py          # 35 features por usuario
│   ├── route_features.py         # 21 features por ruta
│   └── normalization.py          # Min-max scaling + persistencia de stats
└── config.py                     # Constantes: mapas numericos, columnas a normalizar
```
