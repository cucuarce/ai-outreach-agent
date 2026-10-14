# Data Model: Borrador de mensaje de outreach personalizado

**Feature**: `001-outreach-draft` | **Fecha**: 2026-10-08

Todo el modelo vive en memoria durante una ejecución; lo único que persiste son los registros de
traza (`contracts/trace.md`). Los tipos se implementan con `dataclasses` inmutables y el estado
del grafo con `TypedDict`.

## Entrada

Datos que el usuario provee al CLI.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `texto_empresa` | str | Obligatorio (FR-017). Contenido no confiable. Vacío tras `strip()` → `insuficiente` (FR-009). |
| `perfil` | str | Obligatorio (FR-017). Vacío tras `strip()` → `insuficiente` (FR-010). |
| `idioma_solicitado` | str \| None | Opcional. Código ISO 639-1 de los idiomas soportados (`es`, `en`, `pt`, `fr`, `de`, `it`). |
| `nombre_empresa_solicitado` | str \| None | Opcional (`--nombre-empresa`). Tiene prioridad sobre el nombre extraído del texto y no se verifica contra él (research R12). |

## Hecho (dato concreto de la empresa)

Producido por el investigador, filtrado por `verificar_hechos`.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `id` | str | `H1`, `H2`, … únicos en la ejecución. |
| `descripcion` | str | Paráfrasis breve del dato (≤ 200 caracteres). Solo para la traza y la salida al usuario; MUST NOT enviarse al estratega ni al redactor (research R3). |
| `cita` | str | Fragmento literal del texto de la empresa, ≤ 300 caracteres. MUST aparecer en el texto (espacios normalizados). |
| `ancla` | str | Elemento que no se traduce (nombre propio, cifra o término técnico) que MUST aparecer en `cita` y luego en el borrador (research R5). |

**Causas de descarte** (registradas en la traza): `cita_no_localizable`, `ancla_fuera_de_cita`,
`patron_de_instruccion`, `cita_demasiado_larga`, `ancla_demasiado_larga` (más de 6 palabras;
research R5), `duplicado`.

## PuntoPerfil

Elegido por el estratega, verificado por `verificar_estrategia`.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `id` | str | `P1`, `P2`, … |
| `descripcion` | str | Experiencia, habilidad, proyecto o logro. |
| `cita` | str | Fragmento literal del perfil. MUST aparecer en el perfil. |
| `ancla` | str | Elemento que no se traduce (nombre propio, cifra o término técnico) que MUST aparecer en `cita` y luego en el borrador (FR-004, research R5). |

**Causas de descarte**: `cita_no_localizable`, `ancla_fuera_de_cita`.

## Conexion

| Campo | Tipo | Reglas |
|-------|------|--------|
| `hecho_id` | str | MUST referir a un Hecho verificado. |
| `punto_id` | str | MUST referir a un PuntoPerfil verificado. |
| `razon` | str | Por qué el punto del perfil es relevante para el hecho. |

## Estrategia

| Campo | Tipo | Reglas |
|-------|------|--------|
| `angulo` | str | Enfoque del mensaje en una o dos oraciones. |
| `hechos_elegidos` | list[str] | ≥ 2 ids de Hecho verificados (FR-003). |
| `puntos_perfil` | list[PuntoPerfil] | ≥ 1 verificado (FR-004). |
| `conexiones` | list[Conexion] | ≥ 1 válida (FR-004). |

Tras `verificar_estrategia` (FR-010):
- Si no queda ningún PuntoPerfil válido → `insuficiente` con motivo `perfil_sin_puntos`.
- Si hay puntos válidos pero ninguna conexión válida → `insuficiente` con motivo
  `sin_conexion_perfil`.

## Borrador

Producido por el redactor.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `texto` | str | 80–150 palabras (FR-006). |
| `hechos_usados` | list[str] | ids de Hecho mencionados. |
| `puntos_usados` | list[str] | ids de PuntoPerfil mencionados. |

## ResultadoValidacion

| Campo | Tipo | Reglas |
|-------|------|--------|
| `ok` | bool | `true` si `fallos` está vacío. |
| `fallos` | list[Fallo] | `Fallo = {criterio, detalle}`; criterios: `longitud`, `relleno`, `idioma`, `hechos`, `perfil`, `numeros`, `enlaces`, `empresa` (research R2). |

## Resultado (salida de la ejecución)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `estado` | enum | `borrador` \| `insuficiente` \| `invalido` \| `error`. |
| `run_id` | str | Identificador de ejecución (FR-015). |
| `idioma` | str \| None | Idioma objetivo usado. |
| `nombre_empresa` | str \| None | Nombre de la empresa usado en el borrador, o `None` si no se conoce. |
| `origen_nombre_empresa` | str \| None | `"usuario"` (flag) o `"texto"` (extraído y verificado); `None` si no hay nombre. |
| `borrador` | Borrador \| None | Solo si `estado = borrador`. |
| `hechos_usados` | list[ElementoUsado] | Datos de empresa usados: `id`, `cita` literal verificada y `ancla` (FR-008). Sin `descripcion`. |
| `puntos_usados` | list[ElementoUsado] | Puntos de perfil usados: `id`, `cita` literal verificada y `ancla` (FR-008). Sin `descripcion`. |
| `motivo` | str \| None | Código de motivo si no hay borrador (ver tabla). |
| `detalle` | str \| None | Explicación legible (por ejemplo "se encontraron 1 de 2 datos concretos"). |
| `fallos` | list[Fallo] | Criterios incumplidos del último intento si `estado = invalido` (FR-011), también cuando se corta por borrador repetido (research R2). |
| `rutas_registro` | {jsonl, md} | Rutas de la traza. |

| `motivo` | Estado | Origen |
|----------|--------|--------|
| `empresa_vacia` | insuficiente | preparar_entrada |
| `perfil_vacio` | insuficiente | preparar_entrada |
| `idioma_indeterminado` | insuficiente | preparar_entrada |
| `hechos_insuficientes` | insuficiente | verificar_hechos |
| `perfil_sin_puntos` | insuficiente | verificar_estrategia |
| `sin_conexion_perfil` | insuficiente | verificar_estrategia |
| `validacion_fallida` | invalido | finalizar (reintentos agotados) o validar_borrador (borrador repetido; research R2) |
| `respuesta_invalida_llm` | error | cualquier agente (JSON inválido tras 1 reintento) |
| `proveedor_no_disponible` | error | proveedor |
| `contexto_excedido` | error | proveedor (Ollama recortó el prompt; research R4) |

## EstadoGrafo (TypedDict de LangGraph)

| Campo | Escribe | Lee |
|-------|---------|-----|
| `entrada` | CLI | preparar_entrada |
| `run_id`, `nonce`, `idioma_objetivo`, `idioma_empresa` | preparar_entrada | todos |
| `nombre_empresa`, `origen_nombre_empresa` | preparar_entrada (si hay flag) o verificar_hechos (si el nombre del texto se verifica) | redactor, validar_borrador, finalizar |
| `nombre_empresa_candidato` | investigador | verificar_hechos |
| `nombre_empresa_descartado` | verificar_hechos (`{"nombre": ..., "causa": ...}`) | traza |
| `hechos_candidatos`, `instrucciones_detectadas` | investigador | verificar_hechos |
| `hechos` (verificados), `hechos_descartados` | verificar_hechos | estratega, redactor, validar_borrador |
| `estrategia` | estratega → verificar_estrategia | redactor |
| `borrador`, `intento` | redactor | validar_borrador |
| `texto_borrador_anterior` | redactor (en un reintento, el texto del intento anterior) | validar_borrador (borrador repetido) |
| `validacion` | validar_borrador | redactor (feedback), ruteo |
| `resultado` | nodo que corta (preparar_entrada, verificar_hechos, verificar_estrategia, validar_borrador) o finalizar | ruteo, CLI |

**Invariante de FR-012**: `texto_empresa` crudo solo se incluye en el prompt del investigador.
Estratega y redactor reciben de cada hecho verificado solo `id`, `cita` y `ancla`; nunca
`entrada.texto_empresa` ni la `descripcion` de los hechos. El redactor tampoco recibe la `razon`
de las conexiones, solo sus ids (research R3).

**Invariante de salida**: al usuario (CLI y `Resultado`) solo llegan citas literales verificadas
y anclas. Las `descripcion` de hechos y puntos del perfil, escritas por el modelo, quedan solo en
la traza.

## Transiciones de estado de una ejecución

```text
preparada → investigada → hechos_verificados → estrategia_verificada → redactada(n)
    → validada_ok                       → resultado: borrador
    → validada_falla, n ≤ max_reintentos → redactada(n+1)
    → validada_falla, n > max_reintentos → resultado: invalido
Cualquier verificación con umbral no alcanzado → resultado: insuficiente
Error de proveedor o JSON inválido persistente → resultado: error
```
