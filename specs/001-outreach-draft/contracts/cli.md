# Contrato: CLI `outreach`

## Uso

```text
outreach generar --empresa RUTA|- --perfil RUTA [--idioma CODIGO] [--modelo NOMBRE]
                 [--ollama-host URL] [--timeout SEG] [--num-ctx TOKENS] [--reintentos N]
                 [--temp-redactor T] [--nombre-empresa NOMBRE]
                 [--registros DIR] [--json]
```

| Flag | Obligatorio | Descripción |
|------|-------------|-------------|
| `--empresa` | sí | Archivo de texto UTF-8 con el texto de la empresa; `-` lee de stdin. |
| `--perfil` | sí | Archivo de texto UTF-8 con el perfil del usuario. |
| `--idioma` | no | `es`, `en`, `pt`, `fr`, `de` o `it`. Fuerza el idioma del borrador (FR-018). |
| `--nombre-empresa` | no | Nombre de la empresa destinataria. Tiene prioridad sobre el extraído del texto (FR-019). |
| `--modelo`, `--ollama-host`, `--timeout`, `--num-ctx`, `--reintentos`, `--temp-redactor`, `--registros` | no | Ver research R9 (flag > variable de entorno > default). |
| `--json` | no | Imprime el `Resultado` como JSON en stdout en lugar del formato legible. |

No existe ningún flag ni subcomando para enviar mensajes ni para elegir Bedrock (principios III y
IV).

## Salida legible (stdout), estado `borrador`

```text
=== Borrador (es, 112 palabras) ===
Empresa: Campo Claro (tomado del texto)   ← o "(indicado por vos)", o "no identificada; el borrador no nombra ninguna empresa"
<texto del borrador>

=== Datos de la empresa usados ===
[H1] "<cita literal verificada>"
[H3] "<cita literal verificada>"

=== Puntos de tu perfil usados ===
[P1] "<cita literal verificada>"

(Las descripciones escritas por el modelo no se muestran; quedan solo en la traza.)

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
| 5 | `error`: proveedor no disponible, contexto excedido (`--num-ctx` insuficiente) o respuesta del LLM inválida |
