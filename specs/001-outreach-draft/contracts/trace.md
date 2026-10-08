# Contrato: traza estructurada y registro legible

Cada ejecución del grafo produce dos archivos en la carpeta de registros (default `runs/`, en
`.gitignore`):

- `<run_id>.jsonl`: una línea JSON por evento (traza estructurada, principio V).
- `<run_id>.md`: vista legible generada a partir de los mismos eventos (FR-013, SC-006).

`run_id` = `AAAAMMDD-HHMMSS-<6 hex>` (FR-015).

## Evento (una línea del `.jsonl`)

```json
{
  "run_id": "20261008-153012-a1b2c3",
  "seq": 4,
  "ts": "2026-10-08T15:30:19.412-03:00",
  "evento": "nodo_fin",
  "nodo": "verificar_hechos",
  "tipo_nodo": "determinista",
  "intento": null,
  "decision": "4 hechos válidos, 1 descartado (patron_de_instruccion)",
  "detalle": {"validos": ["H1","H2","H3","H5"], "descartados": [{"id":"H4","causa":"patron_de_instruccion"}]},
  "duracion_ms": 3
}
```

| Campo | Valores |
|-------|---------|
| `evento` | `ejecucion_inicio`, `nodo_inicio`, `nodo_fin`, `nodo_error`, `ejecucion_fin` |
| `tipo_nodo` | `agente` \| `determinista` |
| `intento` | número de intento del redactor y de `validar_borrador`; `null` en el resto |
| `decision` | resumen de una línea, legible |
| `detalle` | objeto con los datos de la decisión; nunca incluye el texto crudo de la empresa completo ni el perfil completo |

`ejecucion_inicio.detalle` incluye: proveedor, modelo, idioma solicitado, longitudes de las
entradas y `max_reintentos`. `ejecucion_fin.detalle` incluye `estado`, `motivo` y la duración
total.

## Decisiones mínimas que cada nodo registra

| Nodo | `decision` |
|------|-----------|
| `preparar_entrada` | idioma objetivo y cómo se obtuvo (solicitado / detectado), o motivo de corte |
| `investigador` | cantidad de hechos candidatos e instrucciones detectadas |
| `verificar_hechos` | válidos y descartados por causa; nombre de empresa aceptado o descartado con su causa; corte si < 2 |
| `estratega` | ángulo e ids elegidos |
| `verificar_estrategia` | conexiones válidas; corte si 0 |
| `redactor` | intento y cantidad de palabras |
| `validar_borrador` | ok o lista de criterios incumplidos; próximo paso (fin / reintento / inválido) |

## Registro legible (`.md`)

Encabezado con `run_id`, fecha, modelo y estado final, seguido de una sección numerada por evento
`nodo_fin`/`nodo_error`: nombre del paso, si es agente o verificación, decisión y detalle
formateado como lista. Termina con el resultado y, si hay, el borrador final.
