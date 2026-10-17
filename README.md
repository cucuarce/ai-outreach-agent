# ai-outreach-agent

Genera borradores de mensajes de contacto a empresas a partir del texto de la empresa y del perfil del candidato. Nunca envía mensajes: el borrador lo revisa y lo manda la persona.

## Resultados

Corridas de evaluación con Ollama (qwen2.5:7b en CPU, temperatura del redactor 0,3, 2
reintentos). Cada cifra sale del `reporte.md` de la carpeta de evidencia indicada y de los
`research.md` de las specs 001 y 002.

| Corrida | Evidencia (`eval/evidencia/`) | Válidos con borrador entregado | `invalido` | Aprobación en el primer intento | Duración |
|---|---|---|---|---|---|
| R13: línea base de la spec 001 (sección R13 de su research) | `20261014-192524-qwen2.5-7b` | 0/6 | 6/13 | 2/8 | 4802 s |
| Desarrollo 002 | `20261015-171951-qwen2.5-7b` | 3/6 | 4/13 | 4/10 | 5095 s |
| Validación 002 (6 casos válidos) | `20261017-101728-qwen2.5-7b` | 1/6 | 5/6 (de 6 casos) | 0/6 | 3340 s |

"Aprobación en el primer intento" se cuenta sobre los casos que llegaron a redactar. La duración
es la suma de las duraciones por caso.

### Experimento diagnóstico, fuera del sistema

Corrida con `openai/gpt-oss-120b` vía Groq (`scripts/evaluar_groq.py`) sobre los 13 casos de
desarrollo. Es un diagnóstico para separar el efecto del modelo, no un resultado del sistema:
según la constitución 2.1.0 (principio IV, condición 5), se reporta junto a los de Ollama y nunca
los reemplaza. Detalle en `specs/002-calidad-redactor/research.md`, "Experimento de modelo
(Groq)".

| Corrida | Evidencia (`eval/evidencia/`) | Válidos con borrador entregado | `invalido` | Aprobación en el primer intento | Duración |
|---|---|---|---|---|---|
| Experimento Groq (casos de desarrollo) | `20261017-144005-openai-gpt-oss-120b` | 6/6 | 0/13 | 10/11 | 651,5 s |

### Conclusión

1. Con qwen2.5:7b en CPU, la validación dio 1/6 válidos con borrador entregado, y los 5 casos
   `invalido` fallaron por longitud en todos sus intentos.
2. El experimento diagnóstico apunta al modelo como cuello de botella de la longitud: en los
   mismos 13 casos de desarrollo, qwen2.5:7b entregó 3/6 válidos y gpt-oss-120b 6/6. No es la
   misma muestra que la validación (1/6) y no se puede inferir que el modelo explique ese
   resultado. Salvedad: es un modelo de razonamiento, así que la diferencia no es solo de
   tamaño.
3. Lo que no depende del modelo:
   - El criterio de la 001 "los casos insuficientes no entregan borrador" (SC-004 del
     reporte) da 2/4 con los dos modelos, con los mismos dos casos
     fallando (insuficiente-03 e insuficiente-04): no hay verificación semántica de la relación
     entre dato y perfil.
   - Según la revisión del usuario, también con gpt-oss-120b aparece un requisito de la oferta
     presentado como habilidad propia del candidato (valido-02 y valido-05).

Los límites de la sección siguiente condicionan todas estas cifras.

### Afirmaciones sin respaldo

Todas las cifras son según la revisión del usuario: n chico, un solo revisor y un criterio de
juicio, no una regla automática (el criterio está en `eval/revisiones/002-groq-20261017.json`).
Los conteos son borradores con al menos una afirmación sin respaldo sobre los revisados.

| Corrida | Según la revisión del usuario |
|---|---|
| R13 | 2 de 2 revisados (inyeccion-01, inyeccion-03) |
| Desarrollo 002 | 5 de 6 revisados |
| Validación 002 | 1 de 1 revisado |
| Experimento Groq (diagnóstico) | 2 de 6 válidos revisados (valido-02, valido-05); 5 borradores sin revisar |

Las filas no son comparables: la revisión de desarrollo adoptó la segunda lectura de Claude y la
del experimento con Groq no adoptó ninguna; la fila de desarrollo mezcla válidos, insuficientes e
inyección y la de Groq solo válidos; un solo revisor con un criterio de juicio.

Solo válidos entregados, con la misma advertencia: desarrollo 3 de 3, Groq 2 de 6.

## Límites conocidos

Al 2026-10-17, solo con lo medido u observado hasta hoy: la línea base de la 001 (`specs/001-outreach-draft/research.md`, "Línea base de la evaluación (qwen2.5:7b)"), y la medición del evaluador de relación dato-perfil (decisión D4), las corridas de desarrollo y validación y el experimento con Groq (`specs/002-calidad-redactor/research.md`).

- **Bedrock sin ejecución real**: `BedrockProvider` solo se probó contra Moto; nunca se ejecutó contra Bedrock real (`specs/001-outreach-draft/research.md`, "Interfaz de proveedor de LLM"; plan).
- **Perfil ficticio y único**: todas las corridas (los 13 casos de desarrollo, la validación y el experimento con Groq) usan el mismo perfil ficticio (`ejemplos/perfil.txt`; `specs/001-outreach-draft/research.md`, "Script de evaluación contra Ollama"); los resultados no dicen nada sobre otros perfiles.
- **n=1 por caso en todas las corridas**: desarrollo, validación y experimento se corrieron una sola vez por caso; con Ollama, con qwen2.5:7b en CPU sin GPU dedicada (`specs/001-outreach-draft/research.md`, "Configuración del modelo de Ollama" y "Línea base de la evaluación (qwen2.5:7b)"). Con un modelo no determinista, una corrida por caso no alcanza para estimar tasas por caso.
- **Filtro de instrucciones acotado**: `es_instruccion` no reconoce órdenes en voseo sin destinatario ("decí que…", "terminá con…", inyeccion-03) ni el vocativo "System:" (inyeccion-02) (research de la 001, limitación «instrucción sin patrón reconocible»).
- **Perfil verificado con un solo punto**: el criterio `perfil` exige que aparezca el ancla de al menos 1 de los `puntos_usados`; los demás puntos declarados no se verifican (`specs/001-outreach-draft/research.md`, "Verificación de que el borrador menciona los hechos y el perfil"; `MIN_PUNTOS = 1`).
- **Fórmulas de búsqueda solo en es/en**: las fórmulas genéricas de búsqueda de personal ("We are hiring", "Sumate") se detectan solo en español e inglés; pt, fr, de e it quedan sin cobertura (spec 002, requisito FR-001: una fórmula genérica de búsqueda no cuenta como dato concreto; y decisión D1 de su research, sobre esas fórmulas).
- **Contenido del ancla**: ningún filtro evalúa el contenido de un ancla, solo su forma (largo, fórmula, presencia en la cita). "gente con ganas" pasa todos los filtros, y "equipo de datos" pasa como resto de "Sumate al equipo de datos" (spec 002, research D1).
- **Afirmaciones sin respaldo**: la validación automática no las detecta; solo las marca la revisión humana. Cifras y advertencias en la sección "Afirmaciones sin respaldo".
- **Relación dato-perfil sin verificar (D4)**: el evaluador de relación por término compartido se midió contra el mini-set etiquetado por el usuario (0/52 falsos aceptos, 2/4 falsos rechazos, 1/3 casos válidos con una `buena` conservada) y no pasó la puerta; no se integró (spec 002, plan.md decisión e). El requisito FR-008 de la 002 (una conexión entre un dato de la empresa y un punto del perfil se conserva solo si el punto muestra experiencia en algo que el dato indica que la empresa hace, usa o busca) queda sin cumplir: una conexión sin relación, como las de insuficiente-04, no se detecta.
- **Validación sin insuficientes ni inyecciones**: los 6 casos de validación son de tipo válido, así que SC-004 (insuficientes sin borrador) y SC-005 (inyecciones sin contenido prohibido) no se verificaron fuera de muestra.
- **Ajuste y varianza no separables**: la mejora de desarrollo (3/6) frente a la validación (1/6) no se puede separar entre sobreajuste de las reglas de la 002 a los casos de desarrollo y variación entre corridas.
- **"No nombrar ninguna empresa" sin ejercitar**: oferta-084, el único caso de validación sin nombre esperado, no entregó borrador, así que ese control no se probó.
- **Inyecciones del experimento sin revisión manual**: los 3 borradores de inyección de la corrida con Groq no se revisaron a mano; su 3/3 es el control automático, no una garantía de seguridad.

## Hallazgos para una spec futura

Detalle en `specs/002-calidad-redactor/research.md`, "Resultados de desarrollo", (e), y en los resultados de validación y del experimento con Groq.

- **Sin alternativa para `nombre_empresa` nulo**: si el investigador no propone el nombre, ningún paso usa otra fuente y el criterio `empresa` no aplica (valido-04 y valido-06 en desarrollo; oferta-098 en validación).
- **Ancla igual al nombre de la empresa**: `verificar_hechos` no compara el ancla con el nombre de la empresa, y un hecho así puede hacer pasar el umbral de hechos (insuficiente-03).
- **Sin verificación semántica**: `verificar_estrategia` solo comprueba ids; una conexión sin relación entre dato y perfil no se detecta (insuficiente-04, FR-008).
- **`reescribir` solo con texto idéntico**: el modo de reescritura se activa solo cuando un intento repite el texto del anterior; intentos distintos pero igual de cortos siguen en `conservar`.
- **Citas largas descartadas**: un hecho con cita de más de 300 caracteres se descarta en vez de recortarse (valido-05; fuera de alcance de la 002).
- **Control de atribución**: ningún criterio detecta un requisito de la oferta presentado como experiencia propia del candidato; hoy solo lo marca la revisión humana.
