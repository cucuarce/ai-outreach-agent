---

description: "Task list for 002-calidad-redactor"
---

# Tasks: Calidad del borrador tras la línea base R13

**Input**: Design documents from `/specs/002-calidad-redactor/`

**Prerequisites**: plan.md, spec.md, research.md (D1–D9), data-model.md, contracts/, quickstart.md

**Tests**: incluidos. FR-017 exige al menos un test sin red por comportamiento nuevo, y que use la
respuesta grabada de la línea base cuando exista. Todos los tests usan pytest y `FakeProvider` y
se corren con `C:\venvs\outreach\Scripts\python.exe`. Dentro de cada fase, los tests se escriben
primero y deben fallar antes de implementar.

**Organization**: el orden es por riesgo, como se pidió, no por la prioridad de las historias:

1. D1 (US2, fórmulas).
2. D2 y D3 (US1, nombre y reintentos).
3. Registro de descartes, FR-010 (US3 parte A).
4. D4 (US3 parte B), solo después de medirse contra el mini-set con los umbrales de plan.md.
5. Evaluación de desarrollo, una sola corrida.
6. Validación, al final.

El mini-set se genera en el Setup para que el etiquetado manual corra en paralelo con D1 a D3.

**Restricciones que valen para todas las tareas**:
- Ninguna tarea antes de la Fase 8 lee `eval/validacion_ids.json` ni las ofertas de esos ids.
- Solo T032 ejecuta Ollama sobre los 13 casos, y una sola vez.
- `src/` y `tests/` cambian solo en las tareas que lo indican.
- Hacer commit al terminar cada tarea o grupo lógico, con el diff revisado por el usuario.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia de spec.md. US1 = nombre y reintentos (D2, D3); US2 = fórmulas (D1);
  US3 = relación entre dato y punto (D4, D5, D6).
- **MANUAL**: la hace el usuario, no Claude Code. Bloquea las tareas que dependen de ella.
- Rutas relativas a la raíz del repositorio.

## Referencias rápidas

- Decisiones D1–D9: research.md · Umbrales y decisiones (a)–(d): plan.md § Decisiones del usuario
- Estado, causas y transiciones: data-model.md
- Mini-set: contracts/miniset-conexiones.md · Traza: contracts/trace-delta.md
- Evaluación: contracts/eval-delta.md
- Línea base: `eval/reportes/20261014-192524-qwen2.5-7b/` (no versionada) y research R13 de la 001

---

## Phase 1: Setup (mini-set y etiquetado manual)

**Purpose**: generar el mini-set y dejar el etiquetado en manos del usuario lo antes posible.
Mientras se etiqueta se avanza con D1 a D3, que no dependen de él.

- [ ] T001 [P] Crear `scripts/miniset_conexiones.py` según contracts/miniset-conexiones.md.
  - **Flags**: `--corrida`, `--corrida-extra` y `--salida`.
  - **Entradas**: lee solo las trazas de la corrida de línea base y de `runs/20261014-105553-9ba2f4.jsonl`, más el `perfil` de `eval/casos/valido-01.json`. No lee `eval/validacion_ids.json` ni nada del proyecto ai-job-matcher.
  - **Pares**: arma el producto cartesiano entre las citas de los hechos válidos de cada caso con al menos 2 hechos válidos en la línea base y las 5 oraciones del perfil. Agrega los pares que propuso el estratega en las dos corridas y deduplica por (cita del dato, cita del punto) normalizadas.
  - **Salida**: escribe `para_etiquetar.json` (definición de etiquetas `buena`/`mala`/`dudosa`, `semilla_orden: 42`, ítems mezclados con id opaco = hash de las dos citas) y `origen.json` aparte.
  - **Protección**: se niega a sobrescribir un `para_etiquetar.json` que ya tenga etiquetas.

  Tests en `tests/unit/test_miniset_conexiones.py`, con trazas armadas a mano en `tmp_path`:
  - el archivo para etiquetar no contiene caso, tipo, `razon`, ángulo ni veredicto;
  - los ids son estables;
  - no hay pares duplicados;
  - el orden es el mismo con la misma semilla;
  - no sobrescribe un archivo con etiquetas.
- [ ] T002 Ejecutar `scripts/miniset_conexiones.py` sobre la línea base y escribir `eval/conexiones/para_etiquetar.json` y `eval/conexiones/origen.json`. Informar la cantidad de ítems (se esperan unos 85) sin mostrar sus orígenes, y commitear los dos archivos (depende de T001).
- [ ] T003 **MANUAL (usuario)** Etiquetar cada ítem de `eval/conexiones/para_etiquetar.json` con `buena`, `mala` o `dudosa`, según la definición de FR-008 del encabezado. Guardar el resultado como `eval/conexiones/etiquetado.json` y commitearlo. Claude Code no propone etiquetas, no muestra veredictos ni corre ningún evaluador sobre el mini-set antes de este commit. **Bloquea T025 y todo lo que depende de él: T026, T027, T030, T031, T032, T033 y la Fase 8** (depende de T002).

---

## Phase 2: Foundational (respuestas grabadas de la línea base)

**Purpose**: transcribir a `tests/` las respuestas del modelo de la línea base. Las trazas no
están versionadas, y los tests de US1, US2 y US3 las usan.

- [ ] T004 Crear `tests/escenarios_r13.py` con las respuestas del modelo copiadas de las trazas de `eval/reportes/20261014-192524-qwen2.5-7b/trazas/`, con el mismo formato que `INVESTIGADOR_VAGA` en `tests/escenarios.py`. Cada constante lleva un comentario con `run_id` y `seq` de origen. Constantes:
  - `INVESTIGADOR_VALIDO_04`: 4 hechos; H4 con ancla "We are hiring". Origen `20261014-202338-a90cbb`.
  - `INVESTIGADOR_INSUF_04` y `ESTRATEGA_INSUF_04`: Panificadora Del Sur; conexiones H1→P1 y H2→P2 con sus razones. Origen `20261014-193011-7f83e3`.
  - `INVESTIGADOR_VALIDO_01`, `ESTRATEGA_VALIDO_01`, `REDACTOR_VALIDO_01_INTENTO_1` y `REDACTOR_VALIDO_01_INTENTO_2`: el segundo, idéntico al primero y sin "Campo Claro". Origen `20261014-200024-e35420`.
  - `REDACTOR_INYECCION_02`: 52 palabras, con "I am excited about the opportunity". Origen `20261014-194532-972d57`.

  Incluir también los textos de empresa de esos casos, leídos de `eval/casos/<id>.json`. No hay que transcribirlos de las trazas.

**Checkpoint**: `tests/escenarios_r13.py` importa sin errores.

---

## Phase 3: User Story 2 - Una búsqueda de personal genérica no cuenta como dato concreto (Priority: P2, primera por riesgo)

**Goal**: FR-001 a FR-003 (research D1), en español e inglés.

**Independent Test**: con `INVESTIGADOR_VALIDO_04`, H4 se descarta con `ancla_formula_busqueda` y
H1 a H3 siguen válidos. Las frases fuera de los casos de desarrollo se marcan y las anclas
legítimas no.

- [x] T005 [P] [US2] (commit e9457d7) Escribir `tests/unit/test_formulas_busqueda.py`.
  - **Se marcan**: "Estamos contratando", "Join our team", "Sumate", "We're hiring", "Now hiring", "Súmate a nuestro equipo", "Se busca", "Únete al equipo", "Come work with us".
  - **Frases nuevas**: un test lee los `texto_empresa` de `eval/casos/*.json` y verifica que ninguna de esas frases aparece en ellos, comparando con texto normalizado.
  - **No se marcan**: "Principal QA Automation Engineer", "Sr AI Process Builder", "senior backend engineer", "Tidewise", "Lote360", "equipo de datos", "Hiring Manager", "búsqueda semántica".
  - Debe fallar antes de T006.
- [x] T006 [US2] (commit e9457d7) Crear `src/outreach_agent/data/formulas_busqueda.json` con la familia de la tabla de research D1, solo en español e inglés y agrupada por forma, sin palabras sueltas. Crear `src/outreach_agent/verificacion/formulas.py` con `es_formula_busqueda(texto) -> bool`, que carga igual que `verificacion/patrones.py` y compara contra el texto normalizado (minúsculas, sin tildes, espacios colapsados). Hacer pasar T005.
- [x] T007 [US2] (commit e9457d7) Agregar a `tests/unit/test_verificar_hechos.py`:
  - con `INVESTIGADOR_VALIDO_04` y el texto de `eval/casos/valido-04.json`, H4 queda en `descartados` con causa `ancla_formula_busqueda` y H1, H2 y H3 son válidos;
  - un ancla de más de 6 palabras que contiene una fórmula se descarta como `ancla_demasiado_larga` (orden de causas de data-model.md);
  - una cita con "We are hiring a senior backend engineer…" y ancla "senior backend engineer" es válida;
  - un texto con un solo dato concreto más una fórmula corta con `hechos_insuficientes` y el detalle "Se encontraron 1 de 2" (FR-003).

  Deben fallar antes de T008.
- [x] T008 [US2] (commit e9457d7) En `src/outreach_agent/verificacion/hechos.py`, agregar a `causa_de_descarte` la causa `ancla_formula_busqueda` después de `ancla_demasiado_larga` y antes de `ancla_fuera_de_cita` (orden de data-model.md), usando `es_formula_busqueda` sobre el ancla. Hacer pasar T007 (depende de T006).
- [x] T009 [US2] (commit 7e29871) En `src/outreach_agent/agentes/prompts.py`, reemplazar la regla de las líneas 58-59 por la de research D1:
  - una búsqueda de personal cuenta por su contenido específico, y el ancla es ese contenido, nunca la fórmula;
  - ejemplo: de "Buscamos una analista de datos con experiencia en dbt", el ancla es "analista de datos" o "dbt".

  Agregar a `tests/unit/test_prompts.py` que el `system` del investigador ya no contiene "We are hiring" y sí contiene la regla nueva.

**Checkpoint US2**: `pytest` en verde. Mostrar el diff al usuario antes del commit.

---

## Phase 4: User Story 1 - El borrador nombra a la empresa (Priority: P1)

**Goal**: FR-004 a FR-007 (research D2 y D3).

**Independent Test**: con las respuestas grabadas de valido-01 (intento 1 sin el nombre, intento
2 idéntico), la ejecución no termina en el intento 2. El intento 3 va en modo `reescribir`, sin el
borrador anterior, y si nombra a "Campo Claro" se entrega.

### Tests (primero, deben fallar)

- [x] T010 [P] [US1] (commit 59c58c8) Actualizar el test de la 001 en `tests/unit/test_validar_borrador.py:201`: `test_borrador_repetido_que_falla_corta_como_invalido` pasa a llamarse `test_borrador_repetido_que_falla_no_corta_y_marca_repeticion`. El test verifica que `nodo_validar_borrador`:
  - no agrega `resultado`;
  - deja `repite_intento` con el número del intento repetido;
  - deja el próximo modo en `reescribir`.

  Mantener `test_borrador_repetido_valido_no_corta` (línea 224). Adaptar el helper de la línea 195, que usa `texto_borrador_anterior`, a `textos_borradores`.
- [x] T011 [P] [US1] (commit 59c58c8) Actualizar el test de la 001 en `tests/integration/test_grafo_reintentos.py:80`: `test_borrador_repetido_corta_sin_gastar_los_reintentos_restantes` pasa a llamarse `test_borrador_repetido_no_corta_y_el_siguiente_intento_reescribe`.
  - Con la secuencia `[LARGO, repetido, válido]`, el resultado es `borrador` en el intento 3.
  - El `user` del tercer llamado al redactor no contiene "Borrador anterior:" y sí la instrucción de escribir un borrador nuevo.

  Agregar `test_tres_intentos_identicos_terminan_invalido_sin_superar_el_limite`: termina `invalido` con `validacion_fallida` después de exactamente 3 llamados al redactor (FR-006).
- [x] T012 [P] [US1] (commit 59c58c8) Agregar a `tests/integration/test_grafo_reintentos.py` un test con `INVESTIGADOR_VALIDO_01`, `ESTRATEGA_VALIDO_01`, `REDACTOR_VALIDO_01_INTENTO_1`, `REDACTOR_VALIDO_01_INTENTO_2` y un tercer borrador que nombra a "Campo Claro". Verifica:
  - el resultado es `borrador`;
  - la traza tiene `modo_correccion` = `inicial`, `conservar` y `reescribir`, y `repite_intento` = `null`, `1` y `null` (contracts/trace-delta.md);
  - el tercer prompt contiene "Nombrá a Campo Claro en la primera oración.".

  Otro test cubre la repetición no consecutiva: los intentos A, B y A dan `repite_intento` = `1` en el intento 3.
- [x] T013 [P] [US1] (commit 59c58c8) Agregar a `tests/unit/test_validar_borrador.py` que el criterio `empresa` con nombre "Vanteo®" se cumple con "Vanteo", y que se ignoran también ™ y ©. Agregar a `tests/unit/test_prompts.py`:
  - el `system` del redactor contiene la regla de nombrar a la empresa indicada;
  - las obligaciones por criterio: `empresa` → "Nombrá a {nombre} en la primera oración."; `hechos`/`perfil` → "Incluí literalmente: …" con las anclas faltantes; `longitud` → rango y largo anterior;
  - el modo `reescribir` no incluye el borrador anterior y el modo `conservar` sí.

### Implementación

- [x] T014 [US1] (commit 59c58c8) En `src/outreach_agent/estado.py`, eliminar `texto_borrador_anterior` y agregar `textos_borradores: list[str]` (los textos normalizados de todos los intentos, en orden) y `modo_correccion: str | None` (`"conservar" | "reescribir"`), como en data-model.md. Actualizar los usos en `src/outreach_agent/agentes/redactor.py` y `src/outreach_agent/verificacion/borrador.py`.
- [x] T015 [US1] (commit 59c58c8) En `src/outreach_agent/verificacion/borrador.py`:
  - `_empresa` compara el nombre sin ®, ™ ni ©;
  - reemplazar `es_repeticion` por `intento_repetido(estado) -> int | None`, que compara el texto normalizado contra todos los anteriores;
  - `nodo_validar_borrador` deja de llamar a `invalidar` por repetición, guarda `modo_correccion` (`reescribir` si repitió, `conservar` si no) y agrega `repite_intento` al detalle;
  - eliminar `DETALLE_REPETIDO`;
  - en el resumidor, `proximo_paso` toma solo `fin`, `reintento`, `reintento (reescribir)` o `inválido`.
  (depende de T014)
- [x] T016 [US1] (commit 59c58c8) En `src/outreach_agent/grafo.py`, revisar `ruta_despues_de_validar` y `finalizar`: sin el corte por repetición, la ruta depende solo de `validacion.ok` y del número de intento. Conservar `cortes.invalidar` si `finalizar` lo sigue usando (depende de T015).
- [x] T017 [US1] (commit 59c58c8) En `src/outreach_agent/agentes/prompts.py`:
  - agregar al `system` del redactor la regla de nombrar a la empresa indicada;
  - `_feedback_reintento` recibe el modo y el nombre y genera las obligaciones por criterio de research D3;
  - en modo `reescribir` omite "Borrador anterior:" y reemplaza `INSTRUCCION_REINTENTO` por la orden de escribir un borrador nuevo.

  En `src/outreach_agent/agentes/redactor.py`, pasar el modo, agregar el texto normalizado a `textos_borradores` y registrar `modo_correccion` en `resumir` (`inicial` en el primer intento). Hacer pasar T010 a T013 (depende de T014 a T016).
- [x] T018 [US1] (commit 6ff4b83) Documentar el cambio de comportamiento en la 001:
  - en `specs/001-outreach-draft/research.md` R2, una nota de que el corte inmediato por repetición fue reemplazado por el modo `reescribir` (spec 002, research D3);
  - en `specs/001-outreach-draft/data-model.md`, una nota de que `texto_borrador_anterior` fue reemplazado por `textos_borradores`.

**Checkpoint US1**: `pytest` en verde. Mostrar el diff antes del commit.

---

## Phase 5: User Story 3 (parte A) - Registro de conexiones descartadas (Priority: P3, FR-010)

**Goal**: la traza de `verificar_estrategia` registra cuántas conexiones se evaluaron y cuáles se
descartaron. La métrica de SC-006 queda lista antes de integrar D4.

**Independent Test**: una estrategia con una conexión que apunta a un id inexistente registra esa
conexión con causa `id_no_valido`.

- [ ] T019 [P] [US3] **Diferida (D4 no integrado; plan.md, decisión e).** Agregar a `tests/unit/test_verificar_estrategia.py`:
  - una conexión con `hecho_id` o `punto_id` no válido aparece en `conexiones_descartadas` con causa `id_no_valido`;
  - `conexiones_evaluadas` cuenta todas las propuestas;
  - con `ESTRATEGA_INSUF_04`, antes de D4: 2 evaluadas y 0 descartadas.

  Deben fallar antes de T020.
- [ ] T020 [US3] **Diferida (D4 no integrado; plan.md, decisión e).** En `src/outreach_agent/verificacion/estrategia.py`, registrar `conexiones_evaluadas` y `conexiones_descartadas` (`[{hecho_id, punto_id, causa}]`) en la actualización y en `resumir`, según contracts/trace-delta.md. Hoy esas conexiones se filtran sin registro (líneas 43-47). Hacer pasar T019.
- [ ] T021 [US3] **Diferida (D4 no integrado; plan.md, decisión e).** Agregar `conexiones_legitimas_descartadas` a `scripts/metricas_eval.py`, según contracts/eval-delta.md:
  - **Universo**: los casos `valido` que llegaron a `verificar_estrategia`.
  - **Citas**: se resuelven desde los eventos del investigador y del estratega.
  - **Legítima**: el par normalizado está etiquetado `buena` en el etiquetado.
  - **Sin etiqueta**: los pares que no están en el mini-set se cuentan aparte.
  - **Sin mini-set**: si no hay archivo, se reporta "sin mini-set".
  - **Forma**: `{"descartadas_legitimas": k, "evaluadas": n, "sin_etiqueta": m, "casos": [...]}`.

  En `scripts/evaluar.py`, agregar el flag `--etiquetado` (por defecto `eval/conexiones/etiquetado.json` si existe) y la línea del reporte "Conexiones legítimas descartadas (válidos): k de n evaluadas; sin etiqueta: m", sin efecto en el código de salida. Tests en `tests/unit/test_metricas_eval.py` y `tests/integration/test_evaluar.py`, con trazas y un etiquetado chico armados a mano; no usan el etiquetado real (depende de T020).

**Checkpoint**: `pytest` en verde. Commit.

---

## Phase 6: User Story 3 (parte B) - Evaluador de relación (D4), medido antes de integrar

**Goal**: FR-008, FR-009 y FR-011, solo si el evaluador pasa la puerta de plan.md (a).

**Independent Test**: con `ESTRATEGA_INSUF_04`, la ejecución termina en `insuficiente` /
`sin_conexion_perfil`, con 2 conexiones descartadas `sin_relacion`.

- [ ] T022 [P] [US3] Crear `src/outreach_agent/data/terminos_genericos.json` con la lista de research D4, paso 3: unidades de tiempo y palabras de organización ("equipo", "empresa", "experiencia", "sistema", "plataforma", "año", "semana", "día", "mes"). Commitearlo **antes** de T025. Después de T025 no se modifica (plan.md, decisión c).
- [ ] T023 [P] [US3] Crear `src/outreach_agent/verificacion/relacion.py` con `terminos_compartidos(cita_dato, cita_punto) -> list[str]`, siguiendo los pasos 1 a 5 de research D4: normalizar, tokenizar, quitar stopwords, números y términos genéricos, singular simple y tokens de 2 letras o más. Tests en `tests/unit/test_relacion.py` con ejemplos que no son pares del mini-set:
  - "Go" cuenta;
  - las cifras no cuentan;
  - "imágenes" coincide con "imagen";
  - los términos genéricos no cuentan;
  - una frase que afirma que "el perfil encaja" sin términos en común no produce relación (FR-011).

  Commitearlo **antes** de T025 (depende de T022).
- [ ] T024 [P] [US3] Crear `scripts/medir_relacion.py` según contracts/miniset-conexiones.md, con los umbrales de plan.md (a) fijos en el código:
  - 0 falsos aceptos en insuficiente-04;
  - falsos aceptos de hasta el 10% de las `mala`;
  - falsos rechazos de hasta el 25% de las `buena` (con 4 `buena`, como máximo 1 de 4; se reporta con ese tamaño);
  - al menos una `buena` conservada por cada caso válido que tenga al menos una `buena` en el mini-set; los casos válidos sin ninguna `buena` se listan aparte y no cuentan para este criterio (nota del 2026-10-15 en plan.md).

  Cada criterio se reporta con el conteo junto al porcentaje. Las `dudosa` van aparte, con el veredicto del evaluador y fuera de los denominadores (decisión b). Si hay ítems sin etiquetar, sale con código distinto de 0. No escribe el etiquetado. Tests en `tests/unit/test_medir_relacion.py` con un etiquetado chico armado a mano. Commitearlo **antes** de T025.
- [ ] T025 [US3] Ejecutar `scripts/medir_relacion.py --etiquetado eval/conexiones/etiquetado.json --origen eval/conexiones/origen.json`. Mostrarle al usuario:
  - falsos aceptos y falsos rechazos, con sus citas;
  - el resultado por caso;
  - cada criterio de la puerta.

  Registrar el resultado en una sección "Medición de D4" de `specs/002-calidad-redactor/research.md`, con el commit del etiquetado y el del evaluador. Después de ver los números no se modifica `relacion.py` ni `terminos_genericos.json` (decisión c) (depende de T003, T022, T023 y T024).
- [ ] T026 [US3] **No aplica (la puerta no pasó; research.md, "Resultado de la medición").** **Si T025 pasa la puerta**: integrar el evaluador en `src/outreach_agent/verificacion/estrategia.py`.
  - Descartar las conexiones sin términos compartidos con causa `sin_relacion` y registrar `terminos_compartidos` para las conservadas.
  - Si no queda ninguna conexión, cortar con `sin_conexion_perfil`.
  - Agregar al `system` del estratega (`src/outreach_agent/agentes/prompts.py`) la regla de FR-008.

  Tests:
  - `tests/unit/test_verificar_estrategia.py`: con `ESTRATEGA_INSUF_04`, 2 descartadas `sin_relacion`;
  - `tests/integration/test_grafo_insuficiente.py`: con `INVESTIGADOR_INSUF_04` y `ESTRATEGA_INSUF_04`, el grafo termina `insuficiente` / `sin_conexion_perfil` sin llamar al redactor.

  (depende de T020 y T025)
- [x] T027 [US3] **Cerrada por la decisión (e) de plan.md**: D4 no se integra y el experimento con embeddings no se corre en esta iteración; FR-008 queda sin cumplir y SC-002 se reporta tal cual. Texto original: **Si T025 no pasa la puerta**: no integrar nada en `src/` y detener el trabajo de D4. Presentar los números al usuario y revisar plan.md para el único experimento con embeddings (decisión d): modelo local distinto, mismo mini-set y umbral de similitud fijado antes de medir. Las tareas de ese experimento se agregan acá solo después de la revisión del plan. Si el experimento tampoco pasa, registrar en research.md que FR-008 queda sin cumplir y que SC-002 se reporta tal cual (depende de T025).

**Checkpoint US3**: `pytest` en verde. Commit. Está integrado solo lo que pasó la medición.

---

## Phase 7: Polish, evaluación de desarrollo y límites declarados

- [ ] T028 [P] En `scripts/evaluar.py`, agregar `git_commit` (`git rev-parse HEAD`) y `git_cambios_sin_commit` (si `git status --porcelain` no está vacío) a `config.json` antes del primer caso. Los dos valen `null` si git no está disponible. `--reanudar` conserva los valores originales. El encabezado de `reporte.md` muestra el commit y advierte si hay cambios sin commit. Inyectar la función que consulta git para testear sin depender del repositorio. Tests en `tests/integration/test_evaluar.py` (contracts/eval-delta.md).
- [ ] T029 [P] Crear `scripts/comparar_reportes.py <reporte base> <reporte nuevo>` según contracts/eval-delta.md:
  - una fila por clave de `totales`, con línea base, nueva y diferencia;
  - filas separadas para SC-005, "Inyecciones sin prohibidos en lo entregado" e "Inyecciones con borrador entregado";
  - una tabla por caso con estado y motivo;
  - advertencia si difieren modelo, `num_ctx`, temperatura o reintentos.

  Tests en `tests/unit/test_comparar_reportes.py` con dos `reporte.json` armados a mano.
- [x] T030 [P] (commits 5e42303 y e0e3ba7) Declarar los límites:
  - **R12** de `specs/001-outreach-draft/research.md`: (1) las fórmulas genéricas de búsqueda se detectan solo en español e inglés; pt, fr, de e it quedan sin cobertura; (2) "FR-008 sin cumplir en esta iteración: el evaluador de relación por término compartido no pasó la puerta (0/52 falsos aceptos, 2/4 falsos rechazos, 1/3 casos válidos con una `buena` conservada) y no se integró (decisión e de plan.md); SC-002 se reporta tal cual".
  - **README.md**: los mismos dos límites en una sección "Límites conocidos". README.md todavía no existe (T059 de la 001 está pendiente). Si sigue sin existir, crearlo solo con una línea de propósito ("genera borradores; nunca envía mensajes") y esa sección; T059 de la 001 lo completa después.

  (depende de T025 a T027)
- [x] T031 (en e0e3ba7: 467 tests pasan, `git status` limpio y `git diff --stat 19c3e0c -- eval/casos` vacío) Correr `pytest` completo con `C:\venvs\outreach\Scripts\python.exe` y commitear todo lo integrado. Antes de T032, `git status` debe estar limpio (depende de T001 a T030).
- [ ] T032 **Única corrida de desarrollo con Ollama**:

  ```text
  C:\venvs\outreach\Scripts\python.exe scripts/evaluar.py --casos eval/casos --modelo qwen2.5:7b --ollama-host http://localhost:11434 --timeout 900 --num-ctx 8192 --temp-redactor 0.3 --reintentos 2 --salida eval/reportes
  ```

  Reproduce exactamente `eval/reportes/20261014-192524-qwen2.5-7b/config.json` (R13, FR-013): modelo, host, timeout de 900 s, `num_ctx`, temperatura del redactor y reintentos. `--reanudar` se usa solo si la corrida se interrumpe; no se vuelven a correr casos terminados ni se repite la corrida. Después, correr `scripts/comparar_reportes.py` contra `eval/reportes/20261014-192524-qwen2.5-7b/reporte.json` y reportar:
  - los SC-001 a SC-006 de la spec;
  - por separado, "Inyecciones sin prohibidos en lo entregado", "Inyecciones con borrador entregado" y SC-005.

  Registrar los resultados en una sección "Resultados de desarrollo" de `specs/002-calidad-redactor/research.md` (depende de T031).
- [x] T033 **MANUAL (usuario)** Completar `afirmaciones_sin_respaldo` en `revision_humana.json` de la corrida de T032. Después, regenerar el reporte con `--reanudar <carpeta de la corrida de T032>`, que no ejecuta casos porque todos tienen resultado, y actualizar "Resultados de desarrollo" (depende de T032). (Revisión en `4e89b0a`: `eval/revisiones/002-desarrollo-20261015.json`. Evidencia en `388f118`: `eval/evidencia/`. El reporte se regeneró con `armar_reporte` directo y no con `--reanudar`, porque `--reanudar` consulta `/api/tags` de Ollama antes de armar el reporte. Resultado: 5 de 6 revisados con afirmaciones sin respaldo. Pendiente: actualizar "Resultados de desarrollo".)

**Checkpoint**: implementación cerrada. Commit final. `git status` limpio.

---

## Phase 8: Validación (última; una sola vez)

**Purpose**: FR-014 a FR-016 y SC-004. Esta fase no empieza hasta que T031 a T033 estén
commiteadas y `git status` esté limpio.

- [ ] T034 Verificar que `git status` está limpio y registrar el commit de cierre. Leer por primera vez las ofertas de `eval/validacion_ids.json` (4, 15, 33, 37, 84, 98) desde `ai-job-matcher/job-embeddings-search/data/raw/ofertas.json`. Armar `eval/validacion/casos/<id>.json` con el procedimiento de R8 de la 001:
  - **Esquema**: el de `eval/casos/`, con el mismo perfil.
  - **Anonimización**: solo del nombre del empleador.
  - **Notas**: `notas` registra el id de la oferta.
  - **Valores esperados**: proponer `tipo`, `nombre_esperado` y `hechos_legitimos_esperados` solo a partir del texto de cada oferta, sin abrir trazas ni resultados del sistema.

  Mostrarle al usuario los 6 casos sin ejecutar el sistema (depende de T033).
- [ ] T035 **MANUAL (usuario)** Confirmar o corregir los valores esperados de los 6 casos de validación. Commit de `eval/validacion/casos/` con `git status` limpio (depende de T034).
- [ ] T036 Correr una sola vez:

  ```text
  C:\venvs\outreach\Scripts\python.exe scripts/evaluar.py --casos eval/validacion/casos --modelo qwen2.5:7b --ollama-host http://localhost:11434 --timeout 900 --num-ctx 8192 --temp-redactor 0.3 --reintentos 2 --salida eval/reportes
  ```

  Usa la misma configuración que T032 y que la línea base. Verificar en `config.json` que `git_commit` es igual al commit de T035 y que `git_cambios_sin_commit` es `false`. Reportar el resultado tal cual en una sección "Resultado de validación" de `specs/002-calidad-redactor/research.md`, junto al de desarrollo. Después no se ajusta nada del sistema, de los casos ni de los criterios (FR-015) (depende de T035).
- [ ] T037 **MANUAL (usuario)** Completar `afirmaciones_sin_respaldo` en `revision_humana.json` de la corrida de validación de T036. Después, regenerar el reporte con `C:\venvs\outreach\Scripts\python.exe scripts/evaluar.py --reanudar <carpeta de la corrida de T036>`, que no ejecuta casos porque todos tienen resultado. Reportar el resultado completo, con la revisión humana, en "Resultado de validación" de `specs/002-calidad-redactor/research.md`, sin ajustar nada (FR-015) (depende de T036).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002 → T003 (MANUAL). T003 corre en paralelo con las Fases 2 a 5.
- **Foundational (Phase 2)**: bloquea los tests de las Fases 3 a 6.
- **US2 (Phase 3, D1)**: depende de la Fase 2.
- **US1 (Phase 4, D2 y D3)**: depende de la Fase 2. Va después de US2 por el orden de riesgo; no
  comparte archivos de implementación con US2, salvo `prompts.py` (T009 y T017 van en secuencia).
- **US3 parte A (Phase 5)**: depende de la Fase 2.
- **US3 parte B (Phase 6)**: T022, T023 y T024 pueden hacerse antes de T003. **T025 depende de T003
  (MANUAL)**. T026 o T027, según el resultado de T025.
- **Polish (Phase 7)**: T028 y T029 en cualquier momento. T030 depende de T025 a T027. T031 a T033
  dependen de todo lo anterior. T032 es la única corrida de desarrollo.
- **Validación (Phase 8)**: depende de T033 y de un `git status` limpio. Es la única fase que lee
  las ofertas de `eval/validacion_ids.json`. Orden: T034 → T035 (MANUAL) → T036 → T037 (MANUAL).

### Bloqueos por tareas MANUAL

- **T003** (etiquetado) bloquea T025, T026, T027, T030, T031, T032, T033 y la Fase 8 (T034–T037).
- **T033** (revisión humana) bloquea la Fase 8.
- **T035** (valores esperados de validación) bloquea T036 y T037.
- **T037** (revisión humana de validación) cierra la feature: el resultado de validación se reporta
  recién después de completarla.

### Within Each Phase

- Tests primero (deben fallar), después la implementación que los hace pasar.
- Los datos JSON van antes del módulo que los carga, y el módulo antes del nodo que lo usa.
- Antes de cada commit se muestra el diff al usuario.

### Parallel Opportunities

- Setup: T001 en paralelo con T004.
- US2: T005 en paralelo con los tests de US1 (T010 a T013) y con T019.
- US1: T010, T011, T012 y T013 en paralelo.
- US3: T022, T023 y T024 en paralelo con US1 y US2 (archivos distintos), siempre antes de T025.
- Polish: T028 y T029 en paralelo con cualquier fase anterior a T031.

---

## Parallel Example: tests de US1

```text
Task: "T010 Actualizar test de la 001 en tests/unit/test_validar_borrador.py:201"
Task: "T011 Actualizar test de la 001 en tests/integration/test_grafo_reintentos.py:80"
Task: "T012 Test con respuestas grabadas de valido-01 en tests/integration/test_grafo_reintentos.py"
Task: "T013 Tests de empresa sin símbolos y obligaciones en tests/unit/test_validar_borrador.py y tests/unit/test_prompts.py"
```

(T011 y T012 tocan el mismo archivo: si se hacen en paralelo, se integran en un solo commit.)

## Parallel Example: US3 parte B, antes de la medición

```text
Task: "T022 terminos_genericos.json en src/outreach_agent/data/"
Task: "T023 relacion.py y tests/unit/test_relacion.py"
Task: "T024 scripts/medir_relacion.py y tests/unit/test_medir_relacion.py"
```

---

## Implementation Strategy

### Primero lo de menor riesgo y mayor evidencia

1. Setup: generar el mini-set y pasarlo al usuario para etiquetar (T001 a T003).
2. Foundational: respuestas grabadas de la línea base (T004).
3. US2 (D1) → checkpoint.
4. US1 (D2 y D3) → checkpoint.
5. US3 parte A (registro y métrica) → checkpoint.

### D4, condicionado a la medición

6. Evaluador, script de medición y términos genéricos, commiteados antes de medir.
7. Medición contra el etiquetado del usuario (T025) → integrar (T026) o detenerse (T027).

### Una corrida, después una validación

8. Límites declarados, suite completa y commit de cierre.
9. Única corrida de desarrollo y comparación con la línea base (T032).
10. Validación: primera lectura de las ofertas, confirmación del usuario, una corrida y revisión
    humana (T034 a T037).

**MVP sugerido**: Fases 1 a 4 (US2 y US1). Ataca 4 de los 6 válidos sin borrador de la línea base
(valido-01, 02, 04 y 06) sin depender del etiquetado. Su efecto real recién se mide en T032, que
espera a que D4 esté resuelto.

---

## Notes

- Ninguna tarea antes de T034 lee `eval/validacion_ids.json` ni las ofertas de esos ids.
- Solo T032 ejecuta Ollama sobre los 13 casos de desarrollo, y T036 sobre los 6 de validación.
  Ninguna otra tarea usa Ollama: las regeneraciones con `--reanudar` de T033 y T037 no ejecutan
  casos.
- Los 13 casos de `eval/casos/` no se modifican (FR-012).
- No crear código capaz de enviar mensajes (principio III).
