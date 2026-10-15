# Implementation Plan: Calidad del borrador tras la línea base R13

**Branch**: `002-calidad-redactor` (directorio de spec; no se creó rama git) | **Date**: 2026-10-15 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-calidad-redactor/spec.md`

## Summary

La línea base R13 no entregó borrador en ninguno de los 6 casos válidos. El plan ataca tres causas
con cambios dentro de los tres agentes existentes y de los nodos deterministas, sin agentes
nuevos:

- **Fórmulas genéricas** ("We are hiring"): se corrige el prompt del investigador y se agrega un
  descarte determinista del ancla que contiene la fórmula (D1).
- **Empresa omitida**: la regla de nombrar a la empresa pasa al `system` del redactor y el
  criterio `empresa` tolera los símbolos de marca (D2). La repetición deja de cortar y activa un
  modo de reescritura con obligaciones concretas (D3).
- **Conexiones sin relación**: un evaluador determinista por término compartido en
  `verificar_estrategia` (D4). Se integra solo si pasa la medición sobre un mini-set de conexiones
  que etiqueta el usuario sin ver veredictos (D5).

La evaluación agrega el registro de conexiones descartadas y la métrica de SC-006 (D6), el hash de
git en `config.json` (D7) y una tabla de comparación con la línea base (D8). Hay una única
corrida de validación sobre ofertas que no se leen hasta esa fase. El detalle está en
[research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.11+ (sin cambios respecto de la 001).

**Primary Dependencies**: las de la 001 (`langgraph`, `boto3`; `pytest`, `moto`). Sin
dependencias nuevas.

**Storage**: archivos locales.
- Datos nuevos: `src/outreach_agent/data/formulas_busqueda.json` y
  `src/outreach_agent/data/terminos_genericos.json`.
- Mini-set: `eval/conexiones/para_etiquetar.json`, `eval/conexiones/origen.json` y el archivo
  etiquetado.
- Casos de validación: `eval/validacion/casos/`.

**Testing**: pytest sin red. Se usan las respuestas del modelo grabadas en las trazas de la línea
base (insuficiente-04, valido-01, valido-04) como entradas de `FakeProvider`.

**Target Platform**: CLI local con Ollama (sin cambios).

**Project Type**: CLI de un solo proyecto.

**Performance Goals**: sin metas nuevas. D3 puede sumar hasta 2 intentos de redacción en los
casos que antes cortaban por repetición, dentro del mismo límite de 3 intentos.

**Constraints**:
- La configuración de evaluación es idéntica a R13: qwen2.5:7b, `num_ctx` 8192, temperatura del
  redactor 0.3 y `max_reintentos` 2.
- Los 13 casos de desarrollo no cambian.
- Las ofertas de validación no se leen hasta la fase de validación.
- El evaluador de relación no se ajusta después de medirlo.

**Scale/Scope**:
- 13 casos de desarrollo.
- Unas 85 conexiones en el mini-set.
- 6 ofertas de validación.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cómo lo cumple el diseño | Estado |
|-----------|--------------------------|--------|
| I. Alcance acotado | Sin fuentes nuevas de datos de la empresa. Las ofertas de validación son texto pegado, igual que en R8. | ✅ |
| II. Un agente, una responsabilidad | Siguen los tres agentes. Cambian prompts dentro de cada responsabilidad: qué es un dato (investigador), cuándo conectar (estratega) y cómo corregir (redactor). Los filtros nuevos (fórmula de búsqueda y relación) son deterministas y van en nodos de verificación que ya existen. No se agrega un juez LLM (D4) ni una edición del borrador por código (D2). | ✅ |
| III. El sistema nunca envía | Sin cambios. | ✅ |
| IV. Proveedor detrás de interfaz, sin costo de AWS | Sin cambios en la interfaz. La candidata alternativa de D4 (embeddings) la cambiaría; requiere una revisión del plan si se llega a usar. | ✅ |
| V. Tests sin red y trazas estructuradas | Tests nuevos con respuestas grabadas. La traza agrega campos (`contracts/trace-delta.md`). | ✅ |
| VI. Contenido externo como datos | El evaluador de relación usa solo las citas, nunca la `razon` ni el ángulo (FR-011). Las fórmulas se buscan en el ancla, no se interpretan. | ✅ |
| Stack | Sin componentes nuevos. | ✅ |

**Re-check post-diseño (Fase 1)**: sin violaciones. El modo `reescribir` del redactor no expone el
texto crudo de la empresa: recibe lo mismo que hoy, menos el borrador anterior.

## Diseño

### Cambios en el grafo

La forma del grafo no cambia. Cambian tres comportamientos:

```text
verificar_hechos      + causa ancla_formula_busqueda                       (D1)
verificar_estrategia  + descarte de conexiones sin término compartido       (D4, tras la puerta D5)
                      + registro de conexiones evaluadas / descartadas      (D6)
validar_borrador      - corte inmediato por repetición                      (D3)
                      + repite_intento en la traza
redactor              + modo_correccion: conservar | reescribir             (D3)
```

### Orden de trabajo

El orden importa: el mini-set se etiqueta antes de que exista un evaluador, y D4 se integra al
final.

1. **Mini-set (D5).**
   - Generar `para_etiquetar.json`.
   - **El usuario etiqueta sin ver veredictos.**
   - Commit de las etiquetas.
   - El usuario confirma la puerta de integración.
2. **D1 fórmulas.** Prompt del investigador, patrones, causa nueva y tests con frases fuera de los
   casos de desarrollo.
3. **D2 + D3 nombre y reintentos.** Prompt del redactor, criterio `empresa` sin símbolos, estado
   `textos_borradores`, modo `reescribir` y campos de traza. Se actualizan los tests de la 001
   que fijaban el corte por repetición:
   - `tests/unit/test_validar_borrador.py:201`;
   - `tests/integration/test_grafo_reintentos.py:80`.

   La nota de R2 en `specs/001-outreach-draft/research.md` pasa a remitir a D3.
4. **D6 registro.** Campos nuevos en la traza de `verificar_estrategia`, que también registran las
   conexiones con id no válido.
5. **D4 evaluador.** Se implementa y se mide con `scripts/medir_relacion.py` sobre el mini-set ya
   etiquetado, y se reportan los falsos rechazos y los falsos aceptos.
   - **Si pasa la puerta**: se integra en `verificar_estrategia` y se agrega la regla al prompt
     del estratega.
   - **Si no pasa**: se detiene acá y se le presentan los números al usuario.
6. **D6 métrica.** `conexiones_legitimas_descartadas` en `scripts/metricas_eval.py`, con la
   definición de legítima tomada del mini-set.
7. **D7 + D8.** `git_commit` y `git_cambios_sin_commit` en `config.json`, y
   `scripts/comparar_reportes.py`.
8. **Corrida de desarrollo.** Los 13 casos con la configuración de R13. Se compara con la línea
   base (D8) y se reportan por separado "Inyecciones sin prohibidos en lo entregado" e
   "Inyecciones con borrador entregado", además de SC-005.
9. **Validación (D7).** Commit de cierre → lectura de las 6 ofertas → casos con valores esperados
   confirmados por el usuario → commit → una corrida → reporte tal cual.

### Qué caso debería cambiar y cuál podría empeorar

Está en [research.md, D9](./research.md#d9-qué-caso-debería-cambiar-y-cuál-podría-empeorar-por-mecanismo).
Resumen:
- D1 apunta a valido-04 y valido-06; D2 y D3, a valido-01, valido-02 e inyeccion-02; D4, a
  insuficiente-04.
- D4 es el principal riesgo para valido-01, valido-02, valido-04, valido-06 e inyeccion-01: no ve
  relaciones de dominio ni entre idiomas.

## Project Structure

### Documentation (this feature)

```text
specs/002-calidad-redactor/
├── plan.md              # este archivo
├── research.md          # D1–D9
├── data-model.md        # cambios en estado, hechos, conexiones, intentos y config de corrida
├── quickstart.md        # cómo verificar cada fase
├── contracts/
│   ├── miniset-conexiones.md   # formato del mini-set, etiquetado y medición
│   ├── trace-delta.md          # campos nuevos de la traza
│   └── eval-delta.md           # config.json, métrica SC-006, comparación, casos de validación
└── tasks.md             # /speckit-tasks (no lo crea este comando)
```

### Source Code (repository root)

```text
src/outreach_agent/
├── agentes/prompts.py            # D1 investigador, D2/D3 redactor, D4 estratega
├── agentes/redactor.py           # D3 modo de corrección, textos_borradores
├── estado.py                     # D3 textos_borradores (reemplaza texto_borrador_anterior)
├── verificacion/hechos.py        # D1 causa ancla_formula_busqueda
├── verificacion/formulas.py      # D1 carga de patrones (nuevo; mismo esquema que patrones.py)
├── verificacion/relacion.py      # D4 término compartido (nuevo)
├── verificacion/estrategia.py    # D4 descarte, D6 registro
├── verificacion/borrador.py      # D2 empresa sin símbolos, D3 sin corte por repetición
├── grafo.py                      # D3 ruta después de validar sin el corte por repetición
└── data/
    ├── formulas_busqueda.json    # D1 (nuevo)
    └── terminos_genericos.json   # D4 (nuevo, fijo antes de medir)

scripts/
├── miniset_conexiones.py         # D5 (nuevo)
├── medir_relacion.py             # D5 (nuevo)
├── metricas_eval.py              # D6 métrica SC-006
├── evaluar.py                    # D7 git en config.json; SC-006 en el reporte
└── comparar_reportes.py          # D8 (nuevo)

eval/
├── conexiones/                   # D5 mini-set (para_etiquetar, origen, etiquetado)
└── validacion/casos/             # D7, se crea recién en la fase de validación

tests/
├── unit/test_formulas_busqueda.py        # D1, frases fuera de los casos de desarrollo
├── unit/test_verificar_hechos.py         # D1 causa nueva
├── unit/test_validar_borrador.py         # D2 símbolos; D3 actualiza el test de repetición de la 001
├── unit/test_relacion.py                 # D4
├── unit/test_verificar_estrategia.py     # D4/D6, con la estrategia grabada de insuficiente-04
├── unit/test_metricas_eval.py            # D6 métrica
├── unit/test_miniset_conexiones.py       # D5: el archivo para etiquetar no filtra origen ni veredicto
├── integration/test_grafo_reintentos.py  # D3 actualiza el test de repetición de la 001
├── integration/test_grafo_insuficiente.py # D4 insuficiente-04 → sin_conexion_perfil
└── integration/test_evaluar.py           # D7 git en config.json
```

**Structure Decision**: misma estructura de un solo paquete que la 001. Los módulos nuevos de
`verificacion/` siguen el patrón de `patrones.py`: datos en JSON y funciones puras.

## Complexity Tracking

Sin violaciones de la constitución que justificar.

## Decisiones del usuario (2026-10-15)

**Idiomas de FR-001**: la spec se acotó a español e inglés. pt, fr, de e it quedan sin cobertura
de fórmulas genéricas, documentado como límite en Assumptions. No se agregan patrones para esos
idiomas.

**(a) Umbrales de integración de D4**, fijados antes de medir:
- 0 falsos aceptos en las conexiones de insuficiente-04.
- Falsos aceptos: hasta el 10% de las conexiones etiquetadas `mala`.
- Falsos rechazos: hasta el 25% de las conexiones etiquetadas `buena`.
- Al menos una conexión `buena` conservada por cada caso válido que llega a
  `verificar_estrategia`.
- Cada umbral se reporta siempre con el conteo junto al porcentaje (por ejemplo, "2/21, 9,5%").

**(b) Etiqueta `dudosa`**: el mini-set admite `buena`, `mala` y `dudosa`. Las dudosas se excluyen
de los umbrales y de los denominadores, y se reportan aparte con el veredicto del evaluador.

**(c) Sin retoques**: el evaluador no se modifica después de ver los números de la medición. Eso
incluye la normalización, `terminos_genericos.json` y el criterio de término compartido.

**(d) Si D4 no pasa**: se hace un solo experimento con similitud por embeddings de un modelo local,
con el mismo mini-set y un umbral de similitud fijado antes de medir. Los criterios de (a) y (b)
no cambian. Si tampoco pasa, FR-008 queda sin cumplir en esta iteración, no se integra ningún
evaluador y SC-002 se reporta tal cual. El experimento de embeddings requiere revisar este plan
antes de implementarlo (interfaz de proveedor, principio IV).

**Nota (2026-10-15), posterior al etiquetado y anterior a cualquier medición**: el etiquetado
(commit 5a10d08) dio 52 `mala`, 4 `buena` y 29 `dudosa`. Ningún evaluador se ejecutó sobre el
mini-set antes de esta nota. Con eso se ajusta (a):
- El cuarto criterio pasa a ser: al menos una `buena` conservada por cada caso válido que tenga
  al menos una `buena` en el mini-set. Los casos válidos sin ninguna `buena` se listan aparte en
  el reporte y no cuentan para este criterio.
- Con 4 `buena`, el umbral de falsos rechazos (hasta el 25%) equivale a como máximo 1 de 4. El
  resultado se reporta con ese tamaño de muestra.
- Los otros tres umbrales no cambian.
- valido-02 no tiene ninguna `buena` entre sus 25 pares del mini-set. Con D4 integrado se espera
  que termine en `sin_conexion_perfil`.
- En consecuencia, el máximo alcanzable en desarrollo pasa de 4 a 3 de 6 válidos con borrador.
  Esto corrige la Assumption de spec.md ("El máximo alcanzable en desarrollo es 4 de 6
  válidos"), que no se reescribe.
