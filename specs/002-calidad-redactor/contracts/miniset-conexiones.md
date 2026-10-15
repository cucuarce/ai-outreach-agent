# Contrato: mini-set de conexiones (research D5)

## Generación

```text
python scripts/miniset_conexiones.py --corrida eval/reportes/20261014-192524-qwen2.5-7b \
    --corrida-extra runs/20261014-105553-9ba2f4.jsonl --salida eval/conexiones
```

El script escribe dos archivos:

- `eval/conexiones/para_etiquetar.json`:

  ```json
  {
    "definicion": "Buena: el punto del perfil muestra experiencia en algo que el dato indica que la empresa hace, usa o busca (misma tecnología, dominio, tipo de problema o puesto). Mala: no hay esa relación; compartir cifras, volúmenes o la necesidad de escalar no cuenta. Dudosa: no se puede decidir con las dos citas.",
    "semilla_orden": 42,
    "items": [
      {"id": "c-3f9a1b", "cita_dato": "...", "cita_punto": "...", "etiqueta": "", "nota": ""}
    ]
  }
  ```

- `eval/conexiones/origen.json`: `{"c-3f9a1b": {"caso": "...", "hecho_id": "H2",
  "punto_perfil": 1, "propuesta_por_estratega": true}}`.

**Invariantes** (cubiertos por `tests/unit/test_miniset_conexiones.py`):
- `para_etiquetar.json` no contiene ids de caso, tipos de caso, `razon`, ángulo ni veredictos.
- Los ids son opacos: un hash de las dos citas.
- El orden está mezclado con la semilla.
- Cada par (cita del dato, cita del punto), normalizado, aparece una sola vez.
- Ninguna cita proviene de las ofertas de `eval/validacion_ids.json`: solo se leen trazas de
  desarrollo.
- Si el archivo ya existe con etiquetas, el script se niega a sobrescribirlo.

## Etiquetado

- Lo hace el usuario editando `etiqueta` en `para_etiquetar.json`, con `buena`, `mala` o
  `dudosa`. El resultado se guarda como `eval/conexiones/etiquetado.json`.
- Antes de cualquier medición se commitea, y ese commit queda como referencia.
- No se modifica después de medir.

## Medición

```text
python scripts/medir_relacion.py --etiquetado eval/conexiones/etiquetado.json \
    --origen eval/conexiones/origen.json
```

**Salida** (Markdown):
- tabla de confusión: aceptos y rechazos del evaluador frente a las etiquetas `buena` y `mala`,
  con el conteo junto a cada porcentaje;
- las conexiones `dudosa`, aparte y con el veredicto del evaluador, fuera de los umbrales;
- lista de **falsos aceptos** y de **falsos rechazos**, con las dos citas;
- resultado por caso de origen;
- la puerta de research D5, criterio por criterio, con su resultado (pasa / no pasa).

**Comportamiento**:
- Sale con código distinto de 0 si hay ítems sin etiquetar.
- No escribe ni modifica el etiquetado.
- Los umbrales de la puerta están fijos en el script desde antes de la primera medición, igual
  que el evaluador (plan.md, decisiones a y c).
