# Outdoor Route Recommender

Sistema de recomendación de rutas outdoor personalizadas (senderismo, trail running, ciclismo) basado en el historial de actividad y preferencias implícitas del usuario.

## Problema

Las plataformas de rutas outdoor (Wikiloc, Komoot, AllTrails) acumulan miles de rutas, pero la experiencia de descubrimiento sigue siendo pobre: filtros básicos por distancia o zona, listados ordenados por popularidad, y poca personalización real.

Un usuario que siempre hace rutas de montaña de 15 km con 800 m de desnivel recibe las mismas sugerencias que uno que pasea 5 km por la costa. El sistema no aprende del comportamiento.

**Este proyecto resuelve eso**: construir un motor de recomendación que entienda el perfil real de cada usuario a partir de sus interacciones y le sugiera rutas que encajen con su patrón de actividad.

## Usuario objetivo

Persona que usa una app de rutas outdoor de forma recurrente (al menos 1 actividad/semana). Tiene preferencias implícitas que no configura manualmente: tipo de terreno, rango de distancia, desnivel habitual, zona geográfica. Quiere descubrir rutas nuevas que se ajusten a su nivel y estilo sin tener que buscar manualmente.

## Qué es una "buena recomendación"

Una recomendación es buena cuando:

- **Encaja con el perfil del usuario**: distancia, desnivel y dificultad coherentes con su historial
- **Es descubrible**: el usuario no la habría encontrado fácilmente por su cuenta
- **Es explicable**: se puede justificar por qué se recomienda ("porque sueles hacer rutas de montaña entre 12-18 km con desnivel moderado")
- **No es obvia**: recomendar la ruta más popular de la zona no aporta valor

## Qué NO resuelve este sistema

- **No es una app**: no tiene frontend, API REST ni interfaz de usuario. Es un motor analítico
- **No usa ML complejo**: no hay redes neuronales, embeddings ni collaborative filtering avanzado. El enfoque es content-based con features interpretables
- **No trabaja con datos en tiempo real**: es un sistema batch, no streaming
- **No gestiona datos de GPS en bruto**: trabaja con atributos agregados de rutas (distancia, desnivel, duración), no con trazas GPX punto a punto
- **No resuelve el problema social**: no considera amigos, grupos ni componente social
- **No optimiza para engagement**: optimiza para relevancia y calidad de la recomendación, no para maximizar clics o tiempo en app

## Enfoque técnico

- **Python + SQL** como stack principal
- **SQLite** como base de datos (portable, sin infraestructura)
- **Datos simulados** realistas, no scraping ni APIs externas
- **Diseño analítico**: modelo de datos tipo estrella orientado a responder preguntas de producto
- **Iterativo**: cada fase es funcional por sí misma y añade complejidad incremental

## Estructura del repositorio

```
outdoor-route-recommender/
├── README.md               # Este archivo
├── CLAUDE.md               # Instrucciones para Claude Code
├── data/
│   ├── raw/                # Datos sin procesar
│   └── processed/          # Datos limpios y normalizados
├── docs/                   # Documentación técnica (DATA_MODEL.md, FEATURES.md, etc.)
├── notebooks/              # Notebooks de análisis y evaluación
├── sql/                    # Esquemas DDL y queries analíticas
├── src/                    # Código Python del proyecto
└── tests/                  # Tests unitarios y de integración
```

## Fases del proyecto

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Fundamentos y narrativa | Completada |
| 1 | Modelo de datos analítico | En curso |
| 2 | Ingesta de datos y normalización | Pendiente |
| 3 | Calidad de datos | Pendiente |
| 4 | Feature engineering | Pendiente |
| 5 | Recomendador v1 (content-based) | Pendiente |
| 6 | Evaluación offline | Pendiente |
| 7 | Edge cases y producto real | Pendiente |
| 8 | Documentación final | Pendiente |

## Decisiones de diseño

1. **SQLite sobre PostgreSQL**: para este proyecto no necesitamos concurrencia ni tipos avanzados. SQLite permite que cualquiera clone el repo y ejecute todo sin instalar nada.

2. **Datos simulados sobre datos reales**: evita problemas legales, de scraping y de privacidad. Permite controlar la distribución y los edge cases. Los datos se generan con distribuciones realistas basadas en rangos reales de actividades outdoor.

3. **Content-based sobre collaborative filtering**: con un dataset simulado no tiene sentido simular patrones de co-consumo. Content-based es más honesto, explicable y suficiente para demostrar diseño de datos.

4. **Sin framework de ML**: no usamos scikit-learn, TensorFlow ni similares. Las features y el scoring se calculan con SQL y Python puro. Esto fuerza a entender qué hace cada paso.

5. **Documentación como entregable**: cada fase produce documentación técnica, no solo código. El objetivo es que el proyecto se entienda leyendo los docs, sin ejecutar nada.
