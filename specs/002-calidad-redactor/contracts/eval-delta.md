# Contrato: cambios en la evaluación

Solo se describen los cambios respecto de `specs/001-outreach-draft/contracts/eval.md`.

## config.json (D7)

`evaluar.py` lo escribe antes del primer caso, con dos campos nuevos:

```json
{
  "fecha": "...", "modelo": "qwen2.5:7b", "ollama_host": "...", "num_ctx": 8192,
  "timeout_s": 900.0, "temperatura_redactor": 0.3, "max_reintentos": 2,
  "git_commit": "551f803…", "git_cambios_sin_commit": false
}
```

- Si `git` no está disponible o el directorio no es un repositorio, los dos campos valen `null`.
- `--reanudar` conserva los valores de la corrida original y no los recalcula.
- El encabezado de `reporte.md` muestra el commit. Si `git_cambios_sin_commit` es `true`, lo
  advierte.

## Métrica nueva: conexiones legítimas descartadas (D6, SC-006)

- **Clave en `reporte.json → totales`**: `conexiones_legitimas_descartadas`, con la forma
  `{"descartadas_legitimas": k, "evaluadas": n, "sin_etiqueta": m, "casos": [...]}`.
- **Universo**: los casos `valido` que llegaron a `verificar_estrategia`.
- **Definición de legítima**: el par (cita del dato, cita del punto), normalizado, está etiquetado
  `buena` en `eval/conexiones/etiquetado.json`. El script recibe la ruta con
  `--etiquetado`; si falta, la métrica se reporta como "sin mini-set".
- **Pares sin etiqueta**: se cuentan aparte y se listan para revisión.
- **Código de salida**: es una métrica informativa y no lo cambia.

## Comparación con la línea base (D8)

```text
python scripts/comparar_reportes.py eval/reportes/20261014-192524-qwen2.5-7b/reporte.json \
    eval/reportes/<corrida nueva>/reporte.json
```

Imprime una tabla Markdown con una fila por cada clave de `totales` y las columnas línea base,
nueva y diferencia. Incluye siempre estas filas por separado:
- SC-005;
- "Inyecciones sin prohibidos en lo entregado";
- "Inyecciones con borrador entregado".

Después agrega una tabla por caso con el estado y el motivo en cada corrida. Si las
configuraciones de las dos corridas no coinciden en modelo, `num_ctx`, temperatura o reintentos,
lo advierte.

## Casos de validación (D7)

- **Ubicación**: `eval/validacion/casos/<id>.json`, con el mismo esquema que `eval/casos/`.
- **Construcción**: se arman en la fase de validación y son la primera lectura de esas ofertas.
- **Corrida**: `python scripts/evaluar.py --casos eval/validacion/casos`, una sola vez y con el
  árbol limpio.
- **Uso**: no se usan en ninguna corrida de desarrollo.
