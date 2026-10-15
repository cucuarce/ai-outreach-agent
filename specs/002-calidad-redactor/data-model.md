# Data Model: Calidad del borrador tras la línea base R13

Este documento solo describe los cambios respecto de `specs/001-outreach-draft/data-model.md`.
Lo que no figura acá sigue igual.

## Hecho: causa de descarte nueva (D1)

`verificar_hechos` evalúa las causas en este orden:

1. `cita_demasiado_larga`
2. `cita_no_localizable`
3. `patron_de_instruccion`
4. `ancla_demasiado_larga`
5. **`ancla_formula_busqueda`** (nueva)
6. `ancla_fuera_de_cita`
7. `duplicado`

| Causa | Condición |
|---|---|
| `ancla_formula_busqueda` | El ancla normalizada (minúsculas, sin tildes, espacios colapsados) coincide con algún patrón de `data/formulas_busqueda.json`. |

**Regla**: la cita puede contener una fórmula; lo que se descarta es el hecho cuya **ancla** la
contiene. Un hecho descartado no cuenta para el mínimo de 2 (FR-003).

**Reducción antes de descartar** (research D1): si el ancla tiene 6 palabras o menos y contiene
una fórmula, se le quita la fórmula, los conectores que la siguen ("a", "un", "una", "an",
"the") y las stopwords iniciales que queden. El resto pasa a ser el ancla si tiene al menos una
palabra que no es stopword ni está en `restos_vacios` (equipo, empresa, proyecto, compañía, team,
company, project) y aparece en la cita. Si no, se aplica `ancla_formula_busqueda`.

| Campo de `Hecho` | Tipo | Descripción |
|---|---|---|
| `ancla_original` | `str \| None` | El ancla que devolvió el investigador, solo si se le quitó una fórmula. `None` en los demás casos. |

La traza de `verificar_hechos` agrega `anclas_sin_formula`: `[{id, ancla, ancla_original}]`, solo
si hubo alguna reducción.

## Conexión: evaluación de relación (D4, D6)

| Campo (traza) | Tipo | Descripción |
|---|---|---|
| `hecho_id`, `punto_id` | str | Igual que en la 001. |
| `causa` | `sin_relacion` \| `id_no_valido` | Solo en las conexiones descartadas. |
| `terminos_compartidos` | list[str] | Solo en las conservadas: los términos normalizados que comparten las dos citas. |

**Reglas**:
- Una conexión se conserva si sus dos ids son válidos y las citas comparten al menos un término
  (research D4).
- Si no queda ninguna conexión, la ejecución corta con `sin_conexion_perfil`, motivo que ya
  existe en la 001.
- La `razon` sigue sin participar en ninguna decisión.

## EstadoGrafo: textos de los intentos (D3)

| Campo | Antes (001) | Ahora |
|---|---|---|
| `texto_borrador_anterior` | `str \| None`, el texto del intento anterior | **Se elimina.** |
| `textos_borradores` | — | `list[str]`: los textos normalizados de todos los intentos, en orden. |
| `modo_correccion` | — | `"conservar" \| "reescribir"`: el modo del próximo intento del redactor. |

### Transiciones de `validar_borrador`

| Resultado de la validación | ¿Repite un intento anterior? | ¿Quedan intentos? | Siguiente |
|---|---|---|---|
| ok | — | — | `finalizar` (borrador) |
| falla | no | sí | redactor en modo `conservar` |
| falla | sí | sí | redactor en modo `reescribir` |
| falla | — | no | `finalizar` (`invalido`, `validacion_fallida`) |

La repetición ya no produce un `resultado` en `validar_borrador` (se elimina el corte de research
R2 de la 001).

## Intento de redacción (traza)

| Nodo | Campo nuevo | Valor |
|---|---|---|
| `redactor` | `modo_correccion` | `"inicial"` en el primer intento; `"conservar"` o `"reescribir"` en los reintentos. |
| `validar_borrador` | `repite_intento` | Número del intento cuyo texto repite, o `null`. |

## Configuración de corrida (D7)

`config.json` agrega dos campos:

| Campo | Tipo | Descripción |
|---|---|---|
| `git_commit` | str \| null | Salida de `git rev-parse HEAD` al iniciar la corrida. |
| `git_cambios_sin_commit` | bool \| null | `true` si `git status --porcelain` no está vacío. |

## Mini-set de conexiones (D5)

**Ítem para etiquetar**: `id` (opaco), `cita_dato`, `cita_punto`, `etiqueta`
(`""` | `"buena"` | `"mala"` | `"dudosa"`) y `nota` (opcional).

**Origen**, en un archivo aparte, indexado por `id`:
- `casos`: lista de `{caso, hecho_id}`, porque la misma cita de dato puede venir de varios casos;
- `punto_perfil`: índice de la oración del perfil, o `null` si la cita del punto no está en
  ninguna;
- `propuesta_por_estratega`: bool.

## Caso de validación (D7)

Mismo esquema que los casos de `eval/casos/` (contrato `eval.md` de la 001). Vive en
`eval/validacion/casos/`, y en `notas` registra el id de la oferta de origen.
