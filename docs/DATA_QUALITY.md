# Data Quality — Fase 3

Sistema de validacion de calidad de datos para el proyecto outdoor-route-recommender.

## Enfoque

La calidad de datos se valida en **5 tiers progresivos**, de lo mas basico (esquema) a lo mas sofisticado (distribuciones). Cada tier solo tiene sentido si los anteriores pasan.

| Tier | Nombre | Que valida | Checks |
|------|--------|------------|--------|
| 1 | Schema integrity | Conteos, columnas, PKs | 8 |
| 2 | Referential integrity | FKs entre tablas | 5 |
| 3 | Domain ranges | Valores dentro de limites | 8 |
| 4 | Coherencia temporal/logica | Fechas y relaciones fisicas | 3 |
| 5 | Distribuciones | Proporciones estadisticas | 4 |
| | **Total** | | **28** |

## Severidad

Cada check tiene un nivel de severidad que determina su impacto en el score global:

- **FAIL**: Error critico. Los datos son incorrectos y no se puede avanzar. Genera exit code 1.
- **WARN**: Desviacion estadistica tolerable. Los datos son correctos pero una distribucion esta fuera de tolerancia. No bloquea.
- **PASS**: Check superado sin problemas.

**Score**: `(PASS + WARN) / total * 100`. Un WARN cuenta como "aceptable" porque en datos simulados con seed fijo, las distribuciones pueden desviarse ligeramente sin invalidar los datos.

## Catalogo de checks

### Tier 1 — Schema integrity

| # | Check | Tipo | Descripcion |
|---|-------|------|-------------|
| 1 | `users_row_count` | FAIL | Exactamente 500 usuarios |
| 2 | `routes_row_count` | FAIL | Exactamente 200 rutas |
| 3 | `activities_row_count` | FAIL | ~20,000 actividades (+/-10%) |
| 4 | `users_columns` | FAIL | Columnas esperadas presentes en CSV |
| 5 | `routes_columns` | FAIL | Columnas esperadas presentes en CSV |
| 6 | `activities_columns` | FAIL | Columnas esperadas presentes en CSV |
| 7 | `users_pk_unique` | FAIL | user_id 1..500 sin gaps |
| 8 | `routes_pk_unique` | FAIL | route_id 1..200 sin gaps |

### Tier 2 — Referential integrity

| # | Check | Tipo | Descripcion |
|---|-------|------|-------------|
| 9 | `activities_user_fk` | FAIL | Todos los user_id en activities existen en users |
| 10 | `activities_route_fk` | FAIL | Todos los route_id en activities existen en routes |
| 11 | `routes_activity_type_fk` | FAIL | activity_type_id en {1,2,3} |
| 12 | `routes_terrain_type_fk` | FAIL | terrain_type_id en {1,2,3,4,5} |
| 13 | `routes_zone_fk` | FAIL | zone_id en {1..10} |

### Tier 3 — Domain ranges

| # | Check | Tipo | Descripcion |
|---|-------|------|-------------|
| 14 | `routes_distance_min` | FAIL | distance_km >= 0.5 |
| 15 | `routes_elevation_min` | FAIL | elevation_gain_m >= 10 |
| 16 | `routes_duration_min` | FAIL | estimated_duration_h >= 0.5 |
| 17 | `activities_duration_min` | FAIL | actual_duration_h >= 0.2 |
| 18 | `activities_rating_range` | FAIL | rating en {1,2,3,4,5} (o vacio) |
| 19 | `activities_completed_values` | FAIL | completed en {0,1} |
| 20 | `routes_difficulty_values` | FAIL | difficulty en {easy,moderate,hard,expert} |
| 21 | `users_experience_values` | FAIL | experience_level en {beginner,intermediate,advanced,expert} |

### Tier 4 — Coherencia temporal/logica

| # | Check | Tipo | Descripcion |
|---|-------|------|-------------|
| 22 | `activity_after_registration` | FAIL | activity_date >= registration_date |
| 23 | `circular_elevation_match` | WARN | En circulares: elevation_gain == elevation_loss |
| 24 | `linear_elevation_bound` | WARN | En lineales: elevation_loss <= elevation_gain |

### Tier 5 — Distribuciones

| # | Check | Tipo | Descripcion |
|---|-------|------|-------------|
| 25 | `experience_distribution` | WARN | Desviacion max por nivel <= 5pp |
| 26 | `weekend_rate` | WARN | Desviacion de weekend rate (55%) <= 3pp |
| 27 | `rating_mean_completed` | WARN | Media de rating completadas ~3.8 (+/-0.3) |
| 28 | `rating_mean_abandoned` | WARN | Media de rating abandonadas ~2.2 (+/-0.3) |

## Thresholds

Todos los thresholds estan centralizados en `src/config.py`:

| Parametro | Valor | Justificacion |
|-----------|-------|---------------|
| `DQ_DISTRIBUTION_TOLERANCE` | 5% | Tolerancia por categoria en distribuciones discretas (experience). Con N=500, la varianza binomial permite ~4pp de desviacion al 95% de confianza. |
| `DQ_RATE_TOLERANCE` | 3% | Tolerancia para rates (weekend_probability). Con ~20K actividades, la desviacion esperada es ~0.7pp, asi que 3pp es conservador. |
| `DQ_MEAN_TOLERANCE` | 0.3 | Tolerancia en medias de rating (escala 1-5). Con miles de ratings, la desviacion del sampling es ~0.02, asi que 0.3 cubre incluso skew en la distribucion truncada. |
| `DQ_ACTIVITIES_TOLERANCE` | 10% | Tolerancia en total de actividades. El generador usa lognormal por usuario, asi que el total exacto varia con la seed. |

## Uso

### Validacion sobre CSVs (Python)

```bash
# Ejecutar checks independientemente
python -m src.data_quality

# Guardar report en archivo
python -m src.data_quality --output data/quality_report.txt

# Generar datos + validar
python -m src.generate_all --check

# Pipeline completo: generar + cargar + validar
python -m src.generate_all --load-db --check
```

### Validacion post-carga en MySQL (SQL)

```bash
# Conectar a MySQL y ejecutar quality_checks.sql
docker exec -it outdoor-routes-db mysql -u routes_user -proutes_pass outdoor_routes < sql/quality_checks.sql
```

Las queries SQL replican los checks de Python pero operan sobre las tablas MySQL directamente. Son utiles para validar despues de cargar datos con `--load-db`, y para verificar que la carga no introdujo problemas (truncamientos, conversiones de tipo, etc.).

## Arquitectura

```
src/data_quality.py          # 28 checks sobre CSVs en data/raw/
  ├── check_schema()         # Tier 1 (8 checks)
  ├── check_referential()    # Tier 2 (5 checks)
  ├── check_domain_ranges()  # Tier 3 (8 checks)
  ├── check_temporal()       # Tier 4 (3 checks)
  └── check_distributions()  # Tier 5 (4 checks)

sql/quality_checks.sql       # 24 queries equivalentes para MySQL post-carga

src/generate_all.py --check  # Integracion: genera CSVs + valida
```

**Nota**: El SQL tiene 24 queries vs 28 checks en Python. Los 4 checks de columnas (4-6 en Python) no aplican en SQL porque el schema de MySQL ya los garantiza con las definiciones de tabla.

## Decisiones tecnicas

1. **Checks sobre CSVs, no sobre DB**: El modulo Python valida los CSVs generados antes de cargarlos. Esto permite detectar errores de generacion sin necesitar Docker/MySQL corriendo.

2. **WARN vs FAIL**: Los checks de distribucion usan WARN porque con datos simulados por sampling, desviaciones pequenas son esperables y no invalidan los datos. Solo errores estructurales (FKs, rangos, conteos) son FAIL.

3. **Exit codes**: `data_quality.py` y `generate_all.py --check` devuelven exit code 1 solo si hay FAILs. WARNs producen exit code 0. Esto permite integrar en CI sin falsos positivos por varianza estadistica.

4. **SQL paralelo**: Las queries SQL estan disenadas para ejecutarse independientemente, sin transacciones ni tablas temporales. Cada query produce una fila con `check_name`, `status` y `detail`.

5. **Thresholds centralizados**: Todos los umbrales viven en `config.py` junto con las distribuciones que generan los datos. Esto garantiza que si se cambian las distribuciones, los thresholds se actualizan en el mismo lugar.
