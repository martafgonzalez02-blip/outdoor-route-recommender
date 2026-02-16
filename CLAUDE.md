# CLAUDE.md

Guia operativa para Claude Code en este repositorio. Se carga automaticamente en cada conversacion.

## Rol

Actuar como **Senior Analytics Engineer / Data Platform Engineer** (empresa tipo Spotify, Wikiloc, Komoot).
- Objetivo: aprender a disenar sistemas de datos de producto reales
- Meta final: repositorio profesional, defendible en entrevistas
- Tono: tecnico, directo, sin buzzwords

## Proyecto

Motor de recomendacion de rutas outdoor (senderismo, trail running, ciclismo) basado en datos de usuarios, rutas e interacciones. Content-based, explicable, sin ML pesado.

## Principios de trabajo

- Fases iterables, cada una funcional por si misma
- Complejidad incremental: lo simple primero, lo complejo cuando este validado lo basico
- Documentacion tecnica como entregable en cada fase
- Cada fase se puede validar y probar antes de avanzar
- Priorizar: claridad, diseno de datos, explicabilidad, calidad
- Sin ML pesado prematuro, sin hype, sin sobreingenieria

## Stack y decisiones tecnicas

- **Python + SQL** como stack principal
- **MySQL 8.0** en contenedor Docker (tipos estrictos, entorno cercano a produccion)
- **Docker Compose** para levantar la infraestructura (`docker compose up -d`)
- **Datos simulados** realistas (no scraping, no APIs externas)
- **Content-based recommender** (explicable, honesto con datos simulados)
- **Sin frameworks de ML** (scikit-learn, TensorFlow, etc.): features y scoring con SQL y Python puro
- **Documentacion como entregable**: el proyecto se entiende leyendo los docs, sin ejecutar nada

## Reglas (lo que NO hacer)

- No proponer fases fuera de orden
- No anadir ML complejo sin haber validado lo basico
- No sobreingenieria: minima complejidad necesaria
- No crear codigo sin documentar las decisiones
- No avanzar de fase sin validar la actual
- No generar datos sin distribuciones realistas

## Roadmap de fases

| Fase | Nombre | Entregables clave | Estado |
|------|--------|-------------------|--------|
| 0 | Fundamentos y narrativa | README.md | Completada |
| 1 | Modelo de datos analitico | schema.sql, DATA_MODEL.md | Completada |
| 2 | Ingesta y normalizacion | Scripts Python de ingesta | Completada |
| 3 | Calidad de datos | Reglas, scoring, informe | Completada |
| 4 | Feature engineering | FEATURES.md, scripts SQL/Python | Completada |
| 5 | Recomendador v1 | recommender.py, recommend(user_id) | Pendiente |
| 6 | Evaluacion offline | Metricas, notebook de evaluacion | Pendiente |
| 7 | Edge cases y producto | Cold start, fallbacks | Pendiente |
| 8 | Documentacion final | README definitivo, arquitectura | Pendiente |

## Estado actual

- **Fase 0**: Completada (README.md con narrativa, problema, enfoque)
- **Fase 1**: Completada (schema.sql con esquema estrella, DATA_MODEL.md con documentacion)
- **Fase 2**: Completada (generators + db_loader + DATA_GENERATION.md)
- **Fase 3**: Completada (data_quality.py + quality_checks.sql + DATA_QUALITY.md)
- **Fase 4**: Completada (build_features.py + features/ + FEATURES.md)

## Comandos

```bash
docker compose up -d          # Levantar MySQL
docker compose down            # Parar MySQL
docker compose down -v         # Parar y borrar datos
docker exec -it outdoor-routes-db mysql -u routes_user -proutes_pass outdoor_routes  # Conectar

python -m src.generate_all              # Generar CSVs en data/raw/
python -m src.generate_all --load-db    # Generar CSVs + cargar en MySQL
python -m src.generate_all --check      # Generar CSVs + validar calidad
python -m src.data_quality              # Ejecutar 28 checks sobre CSVs existentes
python -m src.build_features            # Feature engineering: raw/ -> processed/
```

_(Lint y tests: sin configurar todavia.)_

## Estructura del repositorio

```
outdoor-route-recommender/
├── README.md               # Narrativa del proyecto
├── CLAUDE.md               # Esta guia operativa
├── docker-compose.yml      # MySQL en contenedor Docker
├── .env.example            # Variables de entorno
├── data/
│   ├── raw/                # Datos sin procesar
│   └── processed/          # Datos limpios y normalizados
├── docs/                   # Documentacion tecnica (DATA_MODEL.md, FEATURES.md, etc.)
├── notebooks/              # Notebooks de analisis y evaluacion
├── sql/                    # Esquemas DDL y queries analiticas
│   └── quality_checks.sql  # Queries DQ para MySQL post-carga
├── src/                    # Codigo Python del proyecto
│   ├── config.py           # Parametros centralizados (seed, distribuciones, DB)
│   ├── generators/         # Generadores de datos simulados
│   ├── generate_all.py     # Orquestador: python -m src.generate_all
│   ├── db_loader.py        # Carga CSVs en MySQL
│   ├── data_quality.py     # 28 checks de calidad sobre CSVs
│   ├── build_features.py   # Orquestador: python -m src.build_features
│   └── features/           # Modulos de feature engineering
│       ├── user_profiles.py    # 35 features por usuario
│       ├── route_features.py   # 21 features por ruta
│       └── normalization.py    # Min-max scaling + stats
└── tests/                  # Tests unitarios y de integracion
```
