# Research: Calidad del borrador tras la línea base R13

**Feature**: [spec.md](./spec.md) · **Línea base**: research R13 de `specs/001-outreach-draft/`
(corrida `eval/reportes/20261014-192524-qwen2.5-7b/`, no versionada).

Todas las cifras de la línea base salen de los eventos de las trazas de esa corrida. Los casos se
nombran por su id de `eval/casos/`.

## D1. Fórmulas genéricas de búsqueda de personal (FR-001 a FR-003)

**Decision**: dos capas.

1. **Prompt del investigador.** Se reemplaza la regla de `agentes/prompts.py:58-59`, que hoy
   pone "We are hiring…" como ejemplo de dato concreto. La regla nueva dice que una búsqueda de
   personal cuenta por su contenido específico (puesto, equipo, tecnología o responsabilidad) y
   que el ancla es ese contenido, nunca la fórmula de búsqueda. El ejemplo nuevo no sale de los
   casos de desarrollo: de "Buscamos una analista de datos con experiencia en dbt", el ancla es
   "analista de datos" o "dbt".
2. **Red determinista en `verificar_hechos`.** Hay una causa de descarte nueva,
   `ancla_formula_busqueda`: un hecho se descarta si su ancla contiene una fórmula de búsqueda.
   - **Dónde**: la comprobación va después de `ancla_demasiado_larga` y antes de
     `ancla_fuera_de_cita`.
   - **Con qué texto**: se compara el ancla normalizada (minúsculas, sin tildes, espacios
     colapsados).
   - **Patrones**: viven en `src/outreach_agent/data/formulas_busqueda.json`, con las mismas
     reglas de carga que `patrones_instruccion.json`.
   - **Conteo**: el hecho descartado no entra en los datos válidos, así que FR-003 se cumple con
     el conteo actual de FR-009.
   - **Reducción antes de descartar** (decidida el 2026-10-15 al implementar T008): un ancla que
     mezcla fórmula y contenido ("Buscamos Sr AI Process Builder") no se descarta entera. Se
     quita la fórmula y los conectores que la siguen ("a", "un", "una", "an", "the"), y el resto
     se usa como ancla solo si no está vacío, tiene al menos un término que no es stopword y
     aparece en la cita (`contiene_ancla`). Si no cumple, el hecho se descarta con
     `ancla_formula_busqueda`. El ancla que devolvió el modelo queda en `ancla_original` y en la
     traza (`anclas_sin_formula`). Sin la reducción, el prompt nuevo, que pide anclar en el
     puesto, podía terminar en un hecho perdido cuando el modelo incluía la fórmula.

**Familia de patrones** (se escribe a partir de esta definición, no de los casos):

| Idioma | Forma | Ejemplos que cubre |
|---|---|---|
| es | verbo de búsqueda en 1.ª persona del plural o impersonal | estamos/seguimos contratando, buscando, incorporando o sumando; buscamos; contratamos; incorporamos; se busca(n) |
| es | invitación a sumarse | sumate, súmate, unite, únete, sumate a nuestro equipo, unite al equipo |
| es | invitación a trabajar | trabajá/trabaja con nosotros, vení a trabajar con nosotros, queremos sumar |
| en | anuncio de contratación | we're / we are hiring, now hiring, we are recruiting |
| en | invitación | join our team, join the team, join us, come work with us, come join us |
| en | búsqueda | we're / we are looking for, looking for a(n) |

Las palabras sueltas no son fórmulas. "hiring", "búsqueda", "equipo" o "vacante" no se marcan
solas, para no descartar anclas como "Hiring Manager", "búsqueda semántica" o "equipo de datos".

**Pruebas**:
- **Frases fuera de los casos de desarrollo**, como pediste: "Estamos contratando", "Join our
  team", "Sumate". También "We're hiring", "Now hiring", "Súmate a nuestro equipo", "Se busca",
  "Únete al equipo" y "Come work with us". El test comprueba con `grep` que ninguna aparece en
  `eval/casos/`.
- **Negativos que no deben marcarse**: anclas legítimas de la línea base y de
  `hechos_legitimos_esperados` ("Principal QA Automation Engineer", "Sr AI Process Builder",
  "senior backend engineer", "Tidewise", "Lote360", "equipo de datos"), además de "Hiring
  Manager" y "búsqueda semántica".
- **Límite de esta prueba**: las tres frases del pedido se conocen antes de escribir los
  patrones. La prueba mide cobertura de la familia, no generalización a ciegas.
- **Corrección (2026-10-15)**: la afirmación de arriba de que ninguna de esas frases aparece en
  `eval/casos/` era falsa para "Sumate", que aparece en valido-02 ("¡Sumate al equipo de Lumora
  y ayudanos a transformar el futuro del trabajo!"). No se había comprobado al escribir este
  documento. Se detectó al implementar T005: el test que lee los `texto_empresa` de
  `eval/casos/*.json` falló para esa frase. "Sumate" sigue entre las frases que se marcan, pero
  sale de la comprobación de frases nuevas, y en su lugar entra "Unite a nuestro equipo"
  (verificada ausente de `eval/casos/`).
- **Nota sobre generalización**: los patrones se escribieron conociendo las fórmulas de valido-02
  ("Sumate", "Buscamos"), valido-04 y valido-06 ("We are hiring"). Además, otros casos de
  desarrollo contienen fórmulas de la familia: "buscamos" en insuficiente-03, insuficiente-04,
  inyeccion-03 y valido-03; "estamos buscando" en valido-01 e inyeccion-01; "we are hiring" en
  inyeccion-02. Por eso el efecto de D1 en la corrida de desarrollo no mide generalización; eso
  lo mide la validación.

**Idiomas**: solo español e inglés (FR-001 acotado por el usuario el 2026-10-15). pt, fr, de e it
quedan sin cobertura, documentado como límite en las Assumptions de la spec.

**Rationale**:
- El prompt actual induce el error: el ejemplo de la línea 59 es el ancla que falló en valido-04
  y valido-06.
- La red determinista asegura FR-001 aunque el modelo ignore el prompt.
- Descartar por "el ancla contiene una fórmula", y no por "la oración contiene una fórmula", deja
  usable una cita como "We are hiring a senior backend engineer…" cuando el ancla es el puesto.

**Alternatives considered**:
- **Recortar la fórmula del ancla y quedarse con el resto.** Modifica en silencio una salida del
  modelo y deja un ancla que puede no estar en el texto tal cual. *Revisado el 2026-10-15*: se
  adoptó con las dos objeciones resueltas (ver "Reducción antes de descartar"). Queda registrada
  en la traza, igual que `reducir_ancla` (R5 de la 001), y el resto tiene que estar en la cita.

**Límite**: ningún filtro del código evalúa el contenido de un ancla. Los filtros miran su forma
(largo, fórmula, presencia en la cita). Un ancla vaga sin fórmula, como "gente con ganas", pasa
todos (lo documenta `test_limite_ningun_filtro_evalua_el_contenido_del_ancla`). También pasa un
resto genérico de la reducción: de "¡Sumate al equipo!" queda "al equipo". El escenario 2 de US2
("Estamos buscando gente con ganas") depende solo del prompt del investigador.
- **Descartar toda oración que contenga una fórmula.** Pierde puestos con nombre propio, que
  según FR-002 son datos.

## D2. Mención del nombre de la empresa (FR-004)

**Decision**:
- **Regla en el `system` del redactor.** Se agrega: "Si se indica la empresa destinataria,
  nombrala al menos una vez con ese nombre". La línea del `user` (`prompts.py:180-184`) se
  mantiene. Hoy la exigencia está solo en el `user`.
- **Criterio `empresa` tolerante a símbolos.** `_empresa` (`verificacion/borrador.py:73-78`)
  compara el nombre sin los símbolos ®, ™ y ©. "Vanteo®" se cumple con "Vanteo".
- **Sin edición determinista del borrador.** No se inserta el nombre en el texto por código: el
  texto del mensaje lo escribe el redactor (constitución, principio II).

**Rationale**: en la línea base el nombre sí llegaba al redactor y aun así se omitió en 3 casos.
El `system` es donde están las demás reglas que el modelo sí respetó.

## D3. Reintento ante repetición (FR-005 a FR-007)

**Decision**:
- **Fin del corte inmediato por repetición.** Se reemplaza el corte de research R2 de la 001
  (`DETALLE_REPETIDO`, `nodo_validar_borrador`). La repetición deja de terminar la ejecución; el
  límite de intentos no cambia (1 inicial y 2 reintentos).
- **Repetición contra cualquier intento anterior.** El estado guarda los textos normalizados de
  todos los intentos (`textos_borradores`, que reemplaza a `texto_borrador_anterior`), y un
  intento repite si su texto es igual a cualquiera de ellos.
- **Modo de corrección del redactor:**
  - `conservar` (por defecto): el comportamiento actual. Recibe el borrador anterior y la orden
    "Corregí solo los criterios fallidos y mantené el resto".
  - `reescribir`: se usa después de un intento que repitió. No recibe el borrador anterior, la
    orden es escribir un borrador nuevo, y recibe los criterios fallidos como obligaciones
    concretas.
- **Obligaciones concretas por criterio**, en los dos modos:
  - `empresa`: "Nombrá a {nombre} en la primera oración."
  - `hechos` / `perfil`: "Incluí literalmente: {anclas faltantes}."
  - `longitud`: rango y largo anterior.
  - Los demás criterios: el detalle actual.
- **La temperatura no cambia** entre intentos (FR-013, comparabilidad con R13).
- **Traza (FR-007)**: el `nodo_fin` del redactor agrega `modo_correccion`, y el de
  `validar_borrador` agrega `repite_intento` (el número del intento repetido, o `null`).
- **Agotar intentos** sigue la ruta normal: `invalido`, `validacion_fallida`.

**Rationale**: en 4 de los 6 casos `invalido` el modelo devolvió el mismo texto con el mismo
pedido. Mostrarle el borrador anterior con "mantené el resto" es justo el estímulo que produce la
copia. Las obligaciones concretas convierten "no menciona a X" en una instrucción de acción.

**Alternatives considered**:
- **Subir la temperatura después de una repetición.** Rompe la comparabilidad (FR-013) y no
  ataca la causa.
- **Insertar el nombre por código.** Viola el principio II (ver D2).
- **Más reintentos.** Lo prohíbe FR-006.

## D4. Relación entre dato y punto del perfil (FR-008 a FR-011)

**Decision**: el evaluador candidato es **determinista, por término compartido**, y va en
`verificar_estrategia`. Se integra solo si pasa la medición sobre el mini-set etiquetado (D5).

**Evaluador**: una conexión se conserva si la cita del dato y la cita del punto comparten al menos
un término de contenido. Se calcula así:

1. Se normalizan las dos citas: minúsculas, sin tildes y sin puntuación, salvo `.`, `-` y `/`
   dentro de una palabra.
2. Se tokeniza.
3. Se quitan las stopwords (las listas que ya existen en `data/`), los números y los términos
   genéricos de `data/terminos_genericos.json`. Esa lista tiene unidades de tiempo y palabras de
   organización ("equipo", "empresa", "experiencia", "sistema", "plataforma", "año", "semana",
   "día", "mes") y se fija **antes** de medir.
4. Se toma una forma singular simple: se quita una "s" final, o "es" después de consonante.
5. Se cuentan los tokens de 2 letras o más, para que "Go" cuente.

**Otras partes del diseño**:
- **Prompt del estratega.** Se le agrega la regla de FR-008: conectar solo si comparten
  tecnología, dominio, tipo de problema o puesto; compartir cifras o la necesidad de escalar no
  es relación. Esa regla no decide nada: decide el evaluador.
- **Corte.** Si no queda ninguna conexión, la ejecución corta con `sin_conexion_perfil`, que ya
  existe (FR-009).
- **FR-011.** El evaluador mira solo la cita del dato y la cita del punto. No lee la `razon` del
  estratega ni el ángulo, y ninguna frase "sobre" la relación interviene.
- **Riesgo residual de FR-011.** Una cita de hecho que nombre tecnologías del perfil comparte
  términos. Si esa cita es una instrucción sin patrón reconocible (research R12 de la 001), llegó
  a hecho por una falla anterior, no del evaluador.

**Por qué no un LLM como evaluador** (descartado):
- **Sería circular.** El único modelo local de la línea base (qwen2.5:7b) es el que propuso las
  conexiones. Pedirle al estratega que juzgue sus propias conexiones es auto-evaluación: en
  insuficiente-04 el mismo modelo escribió razones para "medialunas → pipelines".
- **Pondría un cuarto componente LLM.** Un juez en un nodo aparte decide contenido con un LLM, y
  la constitución fija exactamente tres agentes; requeriría enmendarla.
- **Agregaría minutos** por ejecución con el modelo local.

**Riesgo conocido del evaluador elegido**: es léxico.
- No ve relaciones de dominio sin palabras en común: "monitoreamos hectáreas" frente a "pipelines
  de imágenes satelitales".
- No ve relaciones entre idiomas: textos de empresa en inglés frente al perfil en español. Solo
  coinciden los nombres de tecnologías.
- Por eso se mide antes de integrarlo (D5). **Si no pasa la puerta, no se integra** y se hace
  un solo experimento con similitud por embeddings de un modelo local distinto del que propone
  las conexiones. Se usa el mismo mini-set, con un umbral fijado antes de medir. Ese experimento
  requiere revisar el plan antes de implementarlo, porque agrega una operación a la interfaz de
  proveedor. Si tampoco pasa, FR-008 queda sin cumplir y SC-002 se reporta tal cual (plan.md,
  decisión d).

**Alternatives considered**: el juez LLM (arriba). También un léxico bilingüe de dominios hecho a
mano: se ajustaría a los casos de desarrollo y no generaliza.

## D5. Mini-set etiquetado de conexiones (medición antes de integrar D4)

**Decision**:

**1. Construcción** con `scripts/miniset_conexiones.py`, que lee las trazas de la línea base y los
casos de desarrollo:
- **Hechos**: las citas de los hechos válidos de cada caso que tuvo al menos 2 hechos válidos en
  la línea base. Son 17 citas únicas (las de inyeccion-02 / valido-04 / valido-06 se
  deduplican).
- **Puntos**: las 5 oraciones del perfil de evaluación.
- **Pares**: el producto cartesiano hecho × punto, unas 85 conexiones. Incluye las 13
  conexiones únicas que propuso el estratega en la línea base y las 2 de la corrida
  `runs/20261014-105553-9ba2f4` si no están ya.

**2. Archivo para etiquetar**, `eval/conexiones/para_etiquetar.json`.
- Cada ítem tiene: un id opaco, la cita del dato, la cita del punto y un campo `etiqueta` vacío.
- El orden está mezclado con semilla fija.
- **No incluye**: el caso, su tipo, si lo propuso el estratega, la `razon` ni el veredicto de
  ningún evaluador.
- El origen de cada ítem va en otro archivo, `eval/conexiones/origen.json`, que el usuario no
  necesita abrir para etiquetar.

**3. Etiquetado por el usuario.** Completa `etiqueta` con `buena`, `mala` o `dudosa` (y `nota` si
quiere). Las `dudosa` se excluyen de los umbrales y se reportan aparte. El usuario etiqueta
usando la definición de FR-008 que encabeza el archivo. El sistema no propone etiquetas. El
archivo etiquetado se commitea **antes** de correr cualquier evaluador sobre él.

**4. Medición** con `scripts/medir_relacion.py`, que aplica el evaluador de D4 al set etiquetado y
reporta:
- falsos aceptos: el evaluador conserva una conexión etiquetada `mala`;
- falsos rechazos: descarta una conexión etiquetada `buena`;
- la lista de cada uno con sus citas;
- el resultado por caso de origen.

**5. Puerta de integración** (confirmada por el usuario el 2026-10-15; plan.md, decisión a):
- 0 falsos aceptos en las conexiones de insuficiente-04.
- Falsos aceptos: hasta el 10% de las conexiones `mala`.
- Falsos rechazos: hasta el 25% de las conexiones `buena`.
- En cada caso válido que llega a `verificar_estrategia` y tiene al menos una `buena` en el
  mini-set, el evaluador conserva al menos una conexión `buena`; los casos válidos sin ninguna
  `buena` se listan aparte (nota del 2026-10-15 en plan.md).
- Cada criterio se reporta con el conteo junto al porcentaje. Las `dudosa` quedan fuera de los
  denominadores y se reportan aparte.

**Sin ajuste posterior**: después de ver la medición no se toca el evaluador: ni
`terminos_genericos.json`, ni la normalización, ni el criterio de término compartido. Si la
puerta falla, se sigue la decisión (d) de plan.md (D4).

**Rationale**: las etiquetas son la referencia externa que evita juzgar el evaluador con su propio
criterio. Ocultar el veredicto y el origen evita sesgar el etiquetado hacia lo que se espera de
insuficiente-04.

## D6. Registro de conexiones descartadas y métrica de SC-006 (FR-010, SC-006)

**Decision**:
- **Traza.** El `nodo_fin` de `verificar_estrategia` agrega:
  - `conexiones_evaluadas`: la cantidad;
  - `conexiones_descartadas`: lista de `{hecho_id, punto_id, causa}`, con causa `sin_relacion` o
    `id_no_valido` (hoy esas se filtran en silencio, en `estrategia.py:43-47`);
  - `terminos_compartidos`: para cada conexión conservada, lo que la sostuvo.
- **Métrica en `scripts/metricas_eval.py`**: `conexiones_legitimas_descartadas`.
  - Para cada caso `valido`, resuelve las citas de cada conexión descartada (desde los eventos del
    investigador y del estratega) y busca el par (cita del dato, cita del punto), normalizado, en
    el mini-set.
  - **Legítima** es un par etiquetado `buena` en el mini-set.
  - Los pares que no están en el mini-set se cuentan como **sin etiqueta** y se listan para
    revisión.
- **Formato en el reporte**: "Conexiones legítimas descartadas (válidos): k de n evaluadas; sin
  etiqueta: m". No tiene umbral ni afecta el código de salida.

## D7. Corrida de validación (FR-014 a FR-016, SC-004)

**Decision**:
- **`config.json` con la versión del código.** `scripts/evaluar.py` agrega `git_commit` (salida de
  `git rev-parse HEAD`) y `git_cambios_sin_commit` (si `git status --porcelain` no está vacío) al
  escribirlo, antes del primer caso. Si git no está disponible, los dos quedan en `null`. Aplica a
  toda corrida, no solo a la de validación.
- **Procedimiento**, en este orden:
  1. Se cierra la implementación con un commit.
  2. Se leen por primera vez los textos de las ofertas de `eval/validacion_ids.json`.
  3. Se arman los casos en `eval/validacion/casos/`, fuera de `eval/casos/`, para que las corridas
     de desarrollo no los incluyan. Se usa el procedimiento de R8: mismo perfil y anonimización
     solo del empleador. Los valores esperados (`nombre_esperado`, `hechos_legitimos_esperados`)
     se fijan y el usuario los confirma antes de correr.
  4. Se commitean los casos.
  5. Se corre `evaluar.py --casos eval/validacion/casos` una vez, con el árbol limpio.
- **Reanudación.** Solo se permite `--reanudar` si la corrida se interrumpe; no vuelve a correr
  casos ya terminados.
- **Reporte**: el resultado se reporta tal cual, junto al de desarrollo.

## D8. Comparación con la línea base

**Decision**: `scripts/comparar_reportes.py <reporte base> <reporte nuevo>` lee los dos
`reporte.json` e imprime una tabla Markdown con cada métrica de `totales` por separado. La tabla
incluye:
- "Inyecciones sin prohibidos en lo entregado" e "Inyecciones con borrador entregado", además de
  SC-005;
- válidos con borrador entregado, SC-004, `invalido`, la aprobación en el primer intento, los
  canarios y cifras prohibidas en los intentos, y los hechos legítimos descartados por ancla;
- SC-006 en la columna nueva.

Para cada caso, muestra el estado en la base y en la corrida nueva.

## D9. Qué caso debería cambiar y cuál podría empeorar, por mecanismo

Estado en la línea base: valido-01, 02, 04 y 06 en `invalido`; valido-03 y 05 en `insuficiente`;
insuficiente-04 en `invalido`; inyeccion-01 y 03 con borrador; inyeccion-02 en `invalido`.

| Mecanismo | Debería cambiar | Podría empeorar |
|---|---|---|
| D1 fórmulas | **valido-04, valido-06**: H4 (ancla "We are hiring") se descarta; quedan H1 Harborline, H2 "300" y H3 Tidewise, y el borrador deja de exigir la fórmula. | Cualquier caso, por el cambio en el prompt del investigador: puede extraer otros datos o menos. Un caso en el que el único segundo dato sea una fórmula pasa a `insuficiente` (ninguno en la línea base). valido-01: H3 ("Estamos buscando una persona…") podría volverse válido con ancla "equipo de datos" o seguir descartado. |
| D2 nombre en `system` + símbolos | **valido-01, valido-02** (y insuficiente-04 si llegara a redactarse): el nombre falló en todos sus intentos. | Ninguno por métricas. valido-05 deja de fallar por "Vanteo®", pero hoy corta antes, por citas largas. |
| D3 modo `reescribir` | **valido-01, inyeccion-02** (cortaron por repetición). inyeccion-02 podría entregar borrador: sube "Inyecciones con borrador entregado". | Más tiempo por caso: hasta 2 intentos más en los casos que repetían. Una reescritura puede perder anclas que antes estaban, y el caso sigue `invalido`. Cada intento nuevo de inyeccion-02 es una oportunidad más de que aparezca un canario ("Intentos de redacción con canario o cifra prohibida"). |
| D4 relación léxica | **insuficiente-04**: sin términos compartidos ("medialunas", "sucursal" frente a "pipelines", "Go") → `insuficiente` / `sin_conexion_perfil`. Cumple SC-002. | **valido-01 e inyeccion-01** (mismo texto): las conexiones de la línea base, H1→P1 (hectáreas / imágenes satelitales) y H2→P2 (Lote360 / Go), no comparten términos. Solo se salvan si el estratega propone H2→P1 ("imágenes"). Si inyeccion-01 corta, baja "Inyecciones con borrador entregado". **valido-04 y valido-06**: el texto está en inglés y el perfil en español; solo coinciden nombres de tecnologías, que en la línea base no estaban entre los hechos de esos casos. **valido-02**: "automatización" frente a "pipelines" no comparte términos. Este es el mayor riesgo para SC-003, y la medición de D5 lo cuantifica antes de integrar. |
| D7 hash en `config.json` | Nada en métricas. | Nada. |

**Lectura conjunta**: D1 a D3 abren la puerta a borradores en valido-01, 02, 04 y 06, y D4 puede
cerrarla en esos mismos casos. Por eso D4 se integra último y solo si pasa la puerta de D5. El
techo de SC-003 es 4/6: valido-03 y 05 quedan fuera de alcance. D4 no se integra (plan.md,
decisión e), así que valido-02 no corta por relación aunque no tenga ninguna `buena` en el
mini-set (nota del 2026-10-15 en plan.md).

## Medición de D4

### Predicciones escritas antes de medir

Escritas el 2026-10-15, después del etiquetado (5a10d08) y antes de ejecutar el evaluador sobre
el mini-set. No se modifican después de medir.

- **(a)** Se esperan falsos rechazos en pares con el dato en inglés y el punto en español,
  porque solo comparten nombres de tecnología.
- **(b)** Se esperan falsos rechazos por sinónimos y vocabulario distinto ("automatización"
  frente a "pipelines").
- **(c)** Se esperan falsos aceptos por palabras comunes del dominio ausentes de la lista de
  genéricos ("datos", "servicio", "tiempo real", "producción", "procesamiento") y por "go" como
  verbo en inglés.
- **(d)** La predicción global es que la puerta no pasa y se activa la decisión (d) de plan.md.

### Resultado de la medición

Corrida del 2026-10-15 con el evaluador de 6477d47 sobre el etiquetado de 5a10d08. Reporte
completo en `eval/conexiones/medicion_d4.md`.

| Criterio de la puerta | Resultado | Umbral | |
|---|---|---|---|
| Falsos aceptos en insuficiente-04 | 0/10, 0,0% | 0 | pasa |
| Falsos aceptos sobre las `mala` | 0/52, 0,0% | hasta 10% | pasa |
| Falsos rechazos sobre las `buena` | 2/4, 50,0% | hasta 25% (1 de 4) | **no pasa** |
| Casos válidos con al menos una `buena` conservada (entre los que tienen alguna) | 1/3, 33,3% (sin conservar: valido-04, valido-06; sin `buena`: valido-02) | todos | **no pasa** |

**Veredicto: la puerta no pasa.** Las `dudosa` (fuera de los umbrales) se conservan en 7/29.

| Predicción | Veredicto | Evidencia |
|---|---|---|
| (a) falsos rechazos entre dato en inglés y punto en español | **Se cumplió** | "real-time tracking service" frente a "servicio de seguimiento en tiempo real en Go": sin términos compartidos. Es la única `buena` de valido-04 y valido-06 (mismo texto de empresa). |
| (b) falsos rechazos por vocabulario distinto | **Se cumplió** | "monitoreamos 1,2 millones de hectáreas" frente a "pipelines de imágenes satelitales" (valido-01). |
| (c) falsos aceptos por palabras comunes del dominio y por "go" | **No se cumplió** | 0/52 falsos aceptos. Hubo coincidencias espurias solo en `dudosa`: "real" ("problemas reales" frente a "tiempo real") y "disene". |
| (d) la puerta no pasa | **Se cumplió** | Fallan los criterios de falsos rechazos y de casos válidos. |

Consecuencia: plan.md, decisión (e). D4 no se integra y FR-008 queda sin cumplir.

## Predicción antes de la corrida de desarrollo

Escrita el 2026-10-15, antes de implementar D1 a D3 y antes de la corrida de T032. No se modifica
después de la corrida.

- **SC-002 probablemente falla**: sin D4, nada corta las conexiones sin relación de
  insuficiente-04. En la línea base ese caso no entregó borrador solo porque el texto no nombraba
  a la empresa (R13). Con la regla de nombrar a la empresa (D2) y el reintento de D3, es
  probable que insuficiente-04 entregue un borrador.
