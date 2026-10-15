# Medición de D4 sobre el mini-set

Pares: 85 (4 `buena`, 52 `mala`, 29 `dudosa`).

## Confusión

| Etiqueta | Conserva | Descarta |
|---|---|---|
| `buena` | 2/4, 50,0% | 2/4, 50,0% |
| `mala` | 0/52, 0,0% | 52/52, 100,0% |

## Puerta de integración

- Falsos aceptos en insuficiente-04 (máximo 0): 0/10, 0,0% → **pasa**
- Falsos aceptos sobre las `mala` (máximo 10%): 0/52, 0,0% → **pasa**
- Falsos rechazos sobre las `buena` (máximo 25%): 2/4, 50,0% → **no pasa**
  tamaño de muestra: 4 `buena`; el máximo equivale a 1 de 4
- Casos válidos con al menos una `buena` conservada (entre los que tienen alguna): 1/3, 33,3% → **no pasa**
  sin ninguna conservada: valido-04, valido-06. Sin ninguna `buena` en el mini-set (no cuentan): valido-02

**Resultado: no pasa**

## Falsos aceptos (0)


## Falsos rechazos (2)

- Dato: We are hiring a senior backend engineer to scale our real-time tracking service, which processes position updates from every vessel on the platform.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
- Dato: Hoy monitoreamos 1,2 millones de hectáreas en Argentina, Uruguay y Paraguay.
  Punto: En Granix (agtech) construí pipelines de imágenes satelitales en Python y Airflow que procesaban 400 GB por semana.

## `dudosa` (fuera de los umbrales: 29)

Conservadas: 7/29, 24,1%.

- Dato: We are hiring a senior backend engineer to scale our real-time tracking service, which processes position updates from every vessel on the platform.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Términos compartidos: backend
  Veredicto: conserva
- Dato: Diseñar e implementar workflows de automatización con las herramientas que mejor resuelvan el problema integrados con nuestros sistemas core.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: We are hiring a senior backend engineer to scale our real-time tracking service, which processes position updates from every vessel on the platform.
  Punto: Migré a PostGIS el sistema de cálculo de superficies de lotes y bajé el tiempo de respuesta de 9 a 2 segundos.
  Veredicto: descarta
- Dato: Harborline builds route-planning software for regional shipping companies in Northern Europe.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: In 2024 we released Tidewise, a forecasting engine that cut average fuel use by 12% for our customers.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: Harborline builds route-planning software for regional shipping companies in Northern Europe.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Términos compartidos: software
  Veredicto: conserva
- Dato: Ceibo Pagos procesa 3 millones de transacciones por mes para 1.500 comercios de Mendoza y San Juan.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: Diseñar e implementar workflows de automatización con las herramientas que mejor resuelvan el problema integrados con nuestros sistemas core.
  Punto: Migré a PostGIS el sistema de cálculo de superficies de lotes y bajé el tiempo de respuesta de 9 a 2 segundos.
  Veredicto: descarta
- Dato: En 2025 cerramos una ronda Serie A de 8 millones de dólares liderada por Kaszek y lanzamos Lote360, una app que estima el rinde de cada lote a partir de imágenes de Sentinel-2.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Our backend runs on Go and PostgreSQL, and our forecasting models are written in Python.
  Punto: En Granix (agtech) construí pipelines de imágenes satelitales en Python y Airflow que procesaban 400 GB por semana.
  Términos compartidos: python
  Veredicto: conserva
- Dato: Buscamos Sr AI Process Builder que diseñe, construya y mantenga automatizaciones end-to-end para resolver problemas reales de operaciones, billing y onboarding.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Términos compartidos: disene, real
  Veredicto: conserva
- Dato: En 2025 cerramos una ronda Serie A de 8 millones de dólares liderada por Kaszek y lanzamos Lote360, una app que estima el rinde de cada lote a partir de imágenes de Sentinel-2.
  Punto: Migré a PostGIS el sistema de cálculo de superficies de lotes y bajé el tiempo de respuesta de 9 a 2 segundos.
  Términos compartidos: lote
  Veredicto: conserva
- Dato: Diseñar e implementar workflows de automatización con las herramientas que mejor resuelvan el problema integrados con nuestros sistemas core.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Ceibo Pagos procesa 3 millones de transacciones por mes para 1.500 comercios de Mendoza y San Juan.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Diagnosticar procesos manuales existentes, mapear sus puntos de fricción y proponer soluciones técnicas priorizadas por impacto.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Buscamos Sr AI Process Builder que diseñe, construya y mantenga automatizaciones end-to-end para resolver problemas reales de operaciones, billing y onboarding.
  Punto: En Granix (agtech) construí pipelines de imágenes satelitales en Python y Airflow que procesaban 400 GB por semana.
  Veredicto: descarta
- Dato: Documentar cada automatización (lógica, triggers, fallbacks, ownership) para que el equipo pueda entender y mantener lo que construyas.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: En 2024 migramos el núcleo de pagos a Kubernetes sobre GCP.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: Our backend runs on Go and PostgreSQL, and our forecasting models are written in Python.
  Punto: Experiencia con AWS (S3, ECS, RDS), PostgreSQL y modelos de regresión para predicción de demanda.
  Términos compartidos: postgresql
  Veredicto: conserva
- Dato: Hoy monitoreamos 1,2 millones de hectáreas en Argentina, Uruguay y Paraguay.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: En 2024 migramos el núcleo de pagos a Kubernetes sobre GCP.
  Punto: Migré a PostGIS el sistema de cálculo de superficies de lotes y bajé el tiempo de respuesta de 9 a 2 segundos.
  Veredicto: descarta
- Dato: Buscamos Sr AI Process Builder que diseñe, construya y mantenga automatizaciones end-to-end para resolver problemas reales de operaciones, billing y onboarding.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Diagnosticar procesos manuales existentes, mapear sus puntos de fricción y proponer soluciones técnicas priorizadas por impacto.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: More than 300 vessels use our platform every day to plan port calls and reduce fuel consumption.
  Punto: Diseñé un servicio de seguimiento en tiempo real en Go que recibe 50.000 eventos por minuto.
  Veredicto: descarta
- Dato: Our backend runs on Go and PostgreSQL, and our forecasting models are written in Python.
  Punto: Migré a PostGIS el sistema de cálculo de superficies de lotes y bajé el tiempo de respuesta de 9 a 2 segundos.
  Veredicto: descarta
- Dato: Colaborar directamente con diferentes equipos, entender sus necesidades y traducirlas en soluciones funcionales.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta
- Dato: Our backend runs on Go and PostgreSQL, and our forecasting models are written in Python.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Términos compartidos: backend
  Veredicto: conserva
- Dato: Diseñar e implementar workflows de automatización con las herramientas que mejor resuelvan el problema integrados con nuestros sistemas core.
  Punto: En Granix (agtech) construí pipelines de imágenes satelitales en Python y Airflow que procesaban 400 GB por semana.
  Veredicto: descarta
- Dato: In 2024 we released Tidewise, a forecasting engine that cut average fuel use by 12% for our customers.
  Punto: Ingeniera de software con 6 años de experiencia en backend y datos.
  Veredicto: descarta

## Por caso

| Caso | `buena` conservadas | `mala` conservadas | `dudosa` conservadas |
|---|---|---|---|
| insuficiente-04 | 0/0, sin muestra | 0/10, 0,0% | 0/0, sin muestra |
| inyeccion-01 | 1/2, 50,0% | 0/5, 0,0% | 1/3, 33,3% |
| inyeccion-02 | 1/2, 50,0% | 0/12, 0,0% | 5/11, 45,5% |
| inyeccion-03 | 0/0, sin muestra | 0/11, 0,0% | 0/4, 0,0% |
| run:20261014-105553-9ba2f4 | 1/2, 50,0% | 0/5, 0,0% | 1/3, 33,3% |
| valido-01 | 1/2, 50,0% | 0/5, 0,0% | 1/3, 33,3% |
| valido-02 | 0/0, sin muestra | 0/14, 0,0% | 1/11, 9,1% |
| valido-04 | 0/1, 0,0% | 0/12, 0,0% | 2/7, 28,6% |
| valido-06 | 0/1, 0,0% | 0/12, 0,0% | 2/7, 28,6% |
