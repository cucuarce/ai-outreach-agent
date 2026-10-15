# Contrato: cambios en la traza

Solo se describen los campos nuevos o modificados respecto de
`specs/001-outreach-draft/contracts/trace.md`. Todos van en el `detalle` del evento `nodo_fin`.

## verificar_hechos

- `descartados[].causa` admite el valor nuevo `ancla_formula_busqueda`.
- `anclas_sin_formula` (solo si hubo alguna): `[{"id": "H1", "ancla": "Sr AI Process Builder",
  "ancla_original": "Buscamos Sr AI Process Builder"}]`, los hechos válidos a cuya ancla se le
  quitó una fórmula de búsqueda (research D1).

## verificar_estrategia

```json
{
  "hechos_elegidos": ["H1", "H2"],
  "puntos_validos": ["P1", "P2"],
  "puntos_descartados": [],
  "conexiones": ["H2→P1"],
  "conexiones_evaluadas": 2,
  "conexiones_descartadas": [
    {"hecho_id": "H1", "punto_id": "P2", "causa": "sin_relacion"}
  ],
  "terminos_compartidos": {"H2→P1": ["imagen"]}
}
```

- `causa` puede ser `sin_relacion` o `id_no_valido`. Hoy las conexiones con id no válido se
  filtran sin registro.
- Si no queda ninguna conexión, se mantienen la `decision` y el `detalle` de corte actuales, con
  el motivo `sin_conexion_perfil`.

## redactor

- `modo_correccion`: `"inicial"`, `"conservar"` o `"reescribir"`.

## validar_borrador

- `repite_intento`: un entero (el número del intento repetido) o `null`.
- `proximo_paso`: deja de tomar el valor `"inválido (borrador repetido)"`. Los valores posibles
  son `"fin"`, `"reintento"`, `"reintento (reescribir)"` e `"inválido"`.
