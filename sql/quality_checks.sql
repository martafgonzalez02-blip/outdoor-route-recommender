-- =============================================================================
-- Outdoor Route Recommender — Data Quality Checks (post-carga MySQL)
-- Fase 3: Validacion de datos en base de datos
-- MySQL 8.0
-- =============================================================================
-- Ejecutar despues de cargar datos con: python -m src.generate_all --load-db
-- Cada query devuelve check_name, status (PASS/FAIL/WARN), detail.

-- =============================================================================
-- Tier 1: Schema integrity
-- =============================================================================

-- 1. users_row_count
SELECT 'users_row_count' AS check_name,
       CASE WHEN cnt = 500 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('Esperado 500, encontrado ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_users) t;

-- 2. routes_row_count
SELECT 'routes_row_count' AS check_name,
       CASE WHEN cnt = 200 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('Esperado 200, encontrado ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_routes) t;

-- 3. activities_row_count (~20000 +/-10%)
SELECT 'activities_row_count' AS check_name,
       CASE WHEN cnt BETWEEN 18000 AND 22000 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('Esperado 18000-22000, encontrado ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM fact_activities) t;

-- 4. users_pk_continuous (sin gaps)
SELECT 'users_pk_continuous' AS check_name,
       CASE WHEN mn = 1 AND mx = cnt THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('min=', mn, ' max=', mx, ' count=', cnt) AS detail
FROM (SELECT MIN(user_id) AS mn, MAX(user_id) AS mx, COUNT(*) AS cnt
      FROM dim_users) t;

-- 5. routes_pk_continuous (sin gaps)
SELECT 'routes_pk_continuous' AS check_name,
       CASE WHEN mn = 1 AND mx = cnt THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('min=', mn, ' max=', mx, ' count=', cnt) AS detail
FROM (SELECT MIN(route_id) AS mn, MAX(route_id) AS mx, COUNT(*) AS cnt
      FROM dim_routes) t;

-- =============================================================================
-- Tier 2: Referential integrity
-- =============================================================================

-- 6. activities_user_fk (no huerfanos)
SELECT 'activities_user_fk' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('user_ids huerfanos: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM fact_activities fa
      LEFT JOIN dim_users u ON fa.user_id = u.user_id
      WHERE u.user_id IS NULL) t;

-- 7. activities_route_fk (no huerfanos)
SELECT 'activities_route_fk' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('route_ids huerfanos: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM fact_activities fa
      LEFT JOIN dim_routes r ON fa.route_id = r.route_id
      WHERE r.route_id IS NULL) t;

-- 8. routes_activity_type_fk
SELECT 'routes_activity_type_fk' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('activity_type_ids invalidos: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_routes r
      LEFT JOIN dim_activity_types at2 ON r.activity_type_id = at2.activity_type_id
      WHERE at2.activity_type_id IS NULL) t;

-- 9. routes_terrain_type_fk
SELECT 'routes_terrain_type_fk' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('terrain_type_ids invalidos: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_routes r
      LEFT JOIN dim_terrain_types tt ON r.terrain_type_id = tt.terrain_type_id
      WHERE tt.terrain_type_id IS NULL) t;

-- 10. routes_zone_fk
SELECT 'routes_zone_fk' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('zone_ids invalidos: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_routes r
      LEFT JOIN dim_geographic_zones gz ON r.zone_id = gz.zone_id
      WHERE gz.zone_id IS NULL) t;

-- =============================================================================
-- Tier 3: Domain ranges
-- =============================================================================

-- 11. routes_distance_range
SELECT 'routes_distance_range' AS check_name,
       CASE WHEN min_d >= 0.5 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('distance_km min=', ROUND(min_d, 2), ' max=', ROUND(max_d, 2)) AS detail
FROM (SELECT MIN(distance_km) AS min_d, MAX(distance_km) AS max_d
      FROM dim_routes) t;

-- 12. routes_elevation_range
SELECT 'routes_elevation_range' AS check_name,
       CASE WHEN min_e >= 10 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('elevation_gain_m min=', min_e, ' max=', max_e) AS detail
FROM (SELECT MIN(elevation_gain_m) AS min_e, MAX(elevation_gain_m) AS max_e
      FROM dim_routes) t;

-- 13. routes_duration_range
SELECT 'routes_duration_range' AS check_name,
       CASE WHEN min_d >= 0.5 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('estimated_duration_h min=', min_d, ' max=', max_d) AS detail
FROM (SELECT MIN(estimated_duration_h) AS min_d, MAX(estimated_duration_h) AS max_d
      FROM dim_routes) t;

-- 14. activities_duration_range
SELECT 'activities_duration_range' AS check_name,
       CASE WHEN min_d >= 0.2 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('actual_duration_h min=', min_d, ' max=', max_d) AS detail
FROM (SELECT MIN(actual_duration_h) AS min_d, MAX(actual_duration_h) AS max_d
      FROM fact_activities) t;

-- 15. activities_rating_range
SELECT 'activities_rating_range' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('ratings fuera de 1-5: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM fact_activities
      WHERE rating IS NOT NULL AND (rating < 1 OR rating > 5)) t;

-- 16. routes_difficulty_values
SELECT 'routes_difficulty_values' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('dificultades fuera de ENUM: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_routes
      WHERE difficulty NOT IN ('easy', 'moderate', 'hard', 'expert')) t;

-- 17. users_experience_values
SELECT 'users_experience_values' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('experience fuera de ENUM: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM dim_users
      WHERE experience_level NOT IN ('beginner', 'intermediate', 'advanced', 'expert')) t;

-- =============================================================================
-- Tier 4: Coherencia temporal/logica
-- =============================================================================

-- 18. activity_after_registration
SELECT 'activity_after_registration' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
       CONCAT('actividades antes de registro: ', cnt) AS detail
FROM (SELECT COUNT(*) AS cnt FROM fact_activities fa
      JOIN dim_users u ON fa.user_id = u.user_id
      WHERE fa.activity_date < u.registration_date) t;

-- 19. circular_elevation_match (gain == loss en circulares)
SELECT 'circular_elevation_match' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('circulares con gain != loss: ', cnt, '/', total) AS detail
FROM (SELECT SUM(CASE WHEN elevation_gain_m != elevation_loss_m THEN 1 ELSE 0 END) AS cnt,
             COUNT(*) AS total
      FROM dim_routes WHERE is_circular = 1) t;

-- 20. linear_elevation_bound (loss <= gain en lineales)
SELECT 'linear_elevation_bound' AS check_name,
       CASE WHEN cnt = 0 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('lineales con loss > gain: ', cnt, '/', total) AS detail
FROM (SELECT SUM(CASE WHEN elevation_loss_m > elevation_gain_m THEN 1 ELSE 0 END) AS cnt,
             COUNT(*) AS total
      FROM dim_routes WHERE is_circular = 0) t;

-- =============================================================================
-- Tier 5: Distribuciones
-- =============================================================================

-- 21. experience_distribution (desviacion max <= 5pp)
SELECT 'experience_distribution' AS check_name,
       CASE WHEN max_dev <= 0.05 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('max desviacion: ', ROUND(max_dev * 100, 1), '% — ',
              'beginner: ', ROUND(beg_pct * 100, 1), '% (35%), ',
              'intermediate: ', ROUND(int_pct * 100, 1), '% (40%), ',
              'advanced: ', ROUND(adv_pct * 100, 1), '% (18%), ',
              'expert: ', ROUND(exp_pct * 100, 1), '% (7%)') AS detail
FROM (
    SELECT
        beg_pct, int_pct, adv_pct, exp_pct,
        GREATEST(
            ABS(beg_pct - 0.35),
            ABS(int_pct - 0.40),
            ABS(adv_pct - 0.18),
            ABS(exp_pct - 0.07)
        ) AS max_dev
    FROM (
        SELECT
            SUM(experience_level = 'beginner') / COUNT(*) AS beg_pct,
            SUM(experience_level = 'intermediate') / COUNT(*) AS int_pct,
            SUM(experience_level = 'advanced') / COUNT(*) AS adv_pct,
            SUM(experience_level = 'expert') / COUNT(*) AS exp_pct
        FROM dim_users
    ) sub
) t;

-- 22. weekend_rate (desviacion <= 3pp del 55% esperado)
SELECT 'weekend_rate' AS check_name,
       CASE WHEN ABS(wknd_rate - 0.55) <= 0.03 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('weekend rate: ', ROUND(wknd_rate * 100, 1), '% (esperado 55%, ',
              'desviacion: ', ROUND(ABS(wknd_rate - 0.55) * 100, 1), '%)') AS detail
FROM (
    SELECT SUM(DAYOFWEEK(activity_date) IN (1, 7)) / COUNT(*) AS wknd_rate
    FROM fact_activities
) t;

-- 23. rating_mean_completed (desviacion <= 0.3 de 3.8)
SELECT 'rating_mean_completed' AS check_name,
       CASE WHEN ABS(avg_r - 3.8) <= 0.3 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('media completadas: ', ROUND(avg_r, 2),
              ' (esperado 3.8, desviacion: ', ROUND(ABS(avg_r - 3.8), 2), ')') AS detail
FROM (SELECT AVG(rating) AS avg_r FROM fact_activities
      WHERE completed = 1 AND rating IS NOT NULL) t;

-- 24. rating_mean_abandoned (desviacion <= 0.3 de 2.2)
SELECT 'rating_mean_abandoned' AS check_name,
       CASE WHEN ABS(avg_r - 2.2) <= 0.3 THEN 'PASS' ELSE 'WARN' END AS status,
       CONCAT('media abandonadas: ', ROUND(avg_r, 2),
              ' (esperado 2.2, desviacion: ', ROUND(ABS(avg_r - 2.2), 2), ')') AS detail
FROM (SELECT AVG(rating) AS avg_r FROM fact_activities
      WHERE completed = 0 AND rating IS NOT NULL) t;
