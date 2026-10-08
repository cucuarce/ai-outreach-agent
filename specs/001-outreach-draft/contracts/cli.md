# Contrato: CLI `outreach`

## Uso

```text
outreach generar --empresa RUTA|- --perfil RUTA [--idioma CODIGO] [--modelo NOMBRE]
                 [--ollama-host URL] [--timeout SEG] [--reintentos N]
                 [--registros DIR] [--json]
```

| Flag | Obligatorio | Descripción |
|------|-------------|-------------|
| `--empresa` | sí | Archivo de texto UTF-8 con el texto de la empresa; `-` lee de stdin. |
| `--perfil` | sí | Archivo de texto UTF-8 con el perfil del usuario. |
| `--idioma` | no | `es`, `en`, `pt`, `fr`, `de` o `it`. Fuerza el idioma del borrador (FR-018). |
| `--modelo`, `--ollama-host`, `--timeout`, `--reintentos`, `--registros` | no | Ver research R9 (flag > variable de entorno > default). |
| `--json` | no | Imprime el `Resultado` como JSON en stdout en lugar del formato legible. |

No existe ningún flag ni subcomando para enviar mensajes ni para elegir Bedrock (principios III y
IV).

## Salida legible (stdout), estado `borrador`

```text
=== Borrador (es, 112 palabras) ===
<texto del borrador>

=== Datos de la empresa usados ===
[H1] <descripcion>  —  "<cita>"
[H3] <descripcion>  —  "<cita>"

=== Puntos de tu perfil usados ===
[P1] <descripcion>  —  "<cita>"

Revisá el borrador antes de enviarlo. Este programa no envía nada.
Registro: runs/20261008-153012-a1b2c3.md (traza: runs/20261008-153012-a1b2c3.jsonl)
```

En los estados `insuficiente`, `invalido` y `error` se imprime el motivo, el detalle y, si
aplica, los criterios incumplidos (`criterio: detalle`) en stderr, más las rutas de registro.

## Salida `--json`

El objeto `Resultado` de `data-model.md`, serializado con claves en español y `ensure_ascii=false`.

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | `borrador` entregado |
| 2 | Uso incorrecto: falta `--empresa` o `--perfil`, archivo inexistente, idioma no soportado (FR-017). No se ejecuta el grafo ni se crea registro. |
| 3 | `insuficiente` (FR-009, FR-010) |
| 4 | `invalido`: no se logró un borrador válido tras los reintentos (FR-011) |
| 5 | `error`: proveedor no disponible o respuesta del LLM inválida |
