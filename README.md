# ai-outreach-agent

Genera borradores de mensajes de contacto a empresas a partir del texto de la empresa y del perfil del candidato. Nunca envía mensajes: el borrador lo revisa y lo manda la persona.

## Límites conocidos

Al 2026-10-15, solo con lo medido u observado hasta hoy: la línea base R13 (`specs/001-outreach-draft/research.md`) y la medición de D4 (`specs/002-calidad-redactor/research.md`).

- **Bedrock sin ejecución real**: `BedrockProvider` solo se probó contra Moto; nunca se ejecutó contra Bedrock real (R4, plan).
- **Perfil único**: los 13 casos de desarrollo usan el mismo perfil (`ejemplos/perfil.txt`, R8); los resultados no dicen nada sobre otros perfiles.
- **n=1 por caso**: cada caso se corrió una vez, con qwen2.5:7b en CPU sin GPU dedicada (R9, R13). Con un modelo no determinista, una corrida por caso no alcanza para estimar tasas por caso.
- **Filtro de instrucciones acotado**: `es_instruccion` no reconoce órdenes en voseo sin destinatario ("decí que…", "terminá con…", inyeccion-03) ni el vocativo "System:" (inyeccion-02) (R12, "instrucción sin patrón reconocible").
- **Perfil verificado con un solo punto**: el criterio `perfil` exige que aparezca el ancla de al menos 1 de los `puntos_usados`; los demás puntos declarados no se verifican (R5, `MIN_PUNTOS = 1`).
- **Fórmulas de búsqueda solo en es/en**: las fórmulas genéricas de búsqueda de personal ("We are hiring", "Sumate") se detectan solo en español e inglés; pt, fr, de e it quedan sin cobertura (spec 002, FR-001 y research D1).
- **Contenido del ancla**: ningún filtro evalúa el contenido de un ancla, solo su forma (largo, fórmula, presencia en la cita). "gente con ganas" pasa todos los filtros, y "equipo de datos" pasa como resto de "Sumate al equipo de datos" (spec 002, research D1).
- **Afirmaciones sin respaldo**: en R13, los 2 borradores entregados que se revisaron a mano (inyeccion-01 e inyeccion-03) tenían al menos una afirmación sin respaldo. Es n=2, no una tasa; la validación automática no lo detecta.
- **Relación dato-perfil sin verificar (D4)**: el evaluador de relación por término compartido se midió contra el mini-set etiquetado por el usuario (0/52 falsos aceptos, 2/4 falsos rechazos, 1/3 casos válidos con una `buena` conservada) y no pasó la puerta; no se integró (spec 002, plan.md decisión e). FR-008 de la 002 queda sin cumplir: una conexión sin relación, como las de insuficiente-04, no se detecta.
