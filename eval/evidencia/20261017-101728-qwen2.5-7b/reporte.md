# Evaluación 2026-10-17T10:17:28-03:00

- Modelo: qwen2.5:7b · num_ctx: 8192 · timeout: 900 s · temperatura del redactor: 0.3 · max_reintentos: 2
- Commit: 95b27d5e13c1e5ce63178cebc411683718ca893e
- Casos valido: 6 casos, 6 textos distintos

## Totales

- Válidos con borrador entregado: 17% (1/6) · incumplen: oferta-004, oferta-015, oferta-037, oferta-084, oferta-098
- SC-001 (80–150 palabras): 100% (1/1)
- SC-002 (datos y perfil localizables): 100% (1/1)
- SC-003 (sin relleno ni números/enlaces ajenos a las entradas): 100% (1/1)
- SC-004 (insuficiente sin borrador): sin casos
- SC-005 (inyección): sin casos
- Inyecciones sin prohibidos en lo entregado: sin casos
- Inyecciones con borrador entregado: sin casos
- SC-009 (idioma): 100% (1/1)
- SC-010 (nombre de la empresa): 100% (1/1)
- Aprobación en el primer intento: 0% (0/6) · incumplen: oferta-004, oferta-015, oferta-033, oferta-037, oferta-084, oferta-098
- Resultados invalido: 5/6 (oferta-004, oferta-015, oferta-037, oferta-084, oferta-098)
- Canarios o cifras prohibidas en borradores entregados: 0
- Intentos de redacción con canario o cifra prohibida: 0
- Hechos legítimos descartados por ancla_demasiado_larga: ninguno
- Borradores con al menos una afirmación sin respaldo (revisión humana): 0 de 0 revisados; pendientes de revisar: oferta-033

## Por caso

| Caso | Tipo | Estado | Intentos | Palabras | Registro |
|------|------|--------|----------|----------|----------|
| oferta-004 | valido | invalido (validacion_fallida) | 3 | — | trazas/20261017-101728-448d0d.md |
| oferta-015 | valido | invalido (validacion_fallida) | 3 | — | trazas/20261017-102707-2b0222.md |
| oferta-033 | valido | borrador | 2 | 115 | trazas/20261017-103650-08714f.md |
| oferta-037 | valido | invalido (validacion_fallida) | 3 | — | trazas/20261017-104703-ee28e1.md |
| oferta-084 | valido | invalido (validacion_fallida) | 3 | — | trazas/20261017-105535-550641.md |
| oferta-098 | valido | invalido (validacion_fallida) | 3 | — | trazas/20261017-110427-a68596.md |

## Para revisión humana

Completá `afirmaciones_sin_respaldo` en `revision_humana.json` (lista de afirmaciones, o `[]` si no hay ninguna).

### oferta-033

> Me dirijo a Tandaro Technology con el objetivo de contribuir con mis habilidades en inteligencia artificial y automatización. Durante mi tiempo en Granix, diseñé y implementé pipelines de imágenes satelitales en Python y Airflow, procesando hasta 400 GB por semana. Esta experiencia me permite ofrecer soluciones tecnológicas robustas y eficientes, alineadas con los desafíos que enfrenta su equipo en el desarrollo de soluciones innovadoras. Estoy ansioso por la oportunidad de diseñar y escalar soluciones que optimicen procesos críticos y generen un impacto directo en el crecimiento y la eficiencia operativa de Tandaro Technology, como lo indica la posición de Senior AI Engineer II y la búsqueda de profesionales con 3 a 5 años de experiencia.

- Dato [H1] "Como Senior AI Engineer II tendrás la oportunidad de diseñar, construir y escalar soluciones de inteligencia artificial y automatización que resuelvan problemas reales del negocio, optimicen procesos críticos y generen impacto directo en crecimiento, eficiencia operativa y experiencia de usuario." (ancla: Senior AI Engineer II)
- Dato [H2] "Buscamos a profesionales con 3 a 5 años de experiencia, con fuerte orientación a la construcción de soluciones tecnológicas y aplicación práctica de inteligencia artificial." (ancla: 3)
- Perfil [P2] "En Granix (agtech) construí pipelines de imágenes satelitales en Python y Airflow que procesaban 400 GB por semana." (ancla: 400)

