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
| 1 | Modelo de datos analitico | schema.sql, DATA_MODEL.md | En curso |
| 2 | Ingesta y normalizacion | Scripts Python de ingesta | Pendiente |
| 3 | Calidad de datos | Reglas, scoring, informe | Pendiente |
| 4 | Feature engineering | FEATURES.md, scripts SQL/Python | Pendiente |
| 5 | Recomendador v1 | recommender.py, recommend(user_id) | Pendiente |
| 6 | Evaluacion offline | Metricas, notebook de evaluacion | Pendiente |
| 7 | Edge cases y producto | Cold start, fallbacks | Pendiente |
| 8 | Documentacion final | README definitivo, arquitectura | Pendiente |

## Estado actual

- **Fase 0**: Completada (README.md con narrativa, problema, enfoque)
- **Fase 1**: En curso (modelo de datos analitico)

## Comandos

```bash
docker compose up -d          # Levantar MySQL
docker compose down            # Parar MySQL
docker compose down -v         # Parar y borrar datos
docker exec -it outdoor-routes-db mysql -u routes_user -proutes_pass outdoor_routes  # Conectar
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
├── src/                    # Codigo Python del proyecto
└── tests/                  # Tests unitarios y de integracion
```
