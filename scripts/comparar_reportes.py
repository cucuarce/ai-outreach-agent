"""Comparación de dos corridas de evaluación (spec 002, T029; research D8; contracts/eval-delta.md).

Uso:
    python scripts/comparar_reportes.py <reporte.json de la línea base> <reporte.json nuevo>

Imprime en Markdown:
- un encabezado con la fecha y el commit de cada corrida, y una advertencia si difieren el
  modelo, `num_ctx`, la temperatura del redactor o los reintentos;
- una fila por cada clave de `totales`, con línea base, nueva y diferencia;
- las tres métricas de inyección por separado (SC-005, "Inyecciones sin prohibidos en lo
  entregado" e "Inyecciones con borrador entregado"), aunque falten en alguna corrida;
- la duración total de cada corrida;
- una nota bajo la tabla de totales con las tasas cuyo denominador difiere entre corridas;
- una tabla por caso con el estado y el motivo en cada corrida.

Solo lee los dos archivos; no escribe nada.
"""

import argparse
import json
import sys
from pathlib import Path

CAMPOS_COMPARABLES = ("modelo", "num_ctx", "temperatura_redactor", "max_reintentos")
INYECCION = (
    "SC-005",
    "inyecciones_sin_prohibidos_en_lo_entregado",
    "inyecciones_con_borrador_entregado",
)
FALTA = "—"


def _es_tasa(valor) -> bool:
    return isinstance(valor, dict) and {"cumplen", "total"} <= set(valor)


def _formato(clave: str, valor) -> str:
    if valor is None:
        return FALTA
    if _es_tasa(valor):
        if valor["total"] == 0:
            return f"{valor['cumplen']}/0 (sin casos)"
        porcentaje = 100 * valor["cumplen"] / valor["total"]
        return f"{valor['cumplen']}/{valor['total']} ({porcentaje:.0f}%)"
    if clave == "invalido":
        return f"{len(valor['casos'])}/{valor['total']}"
    if clave == "afirmaciones_sin_respaldo":
        return f"{len(valor['con_afirmaciones'])} de {valor['revisados']} revisados"
    if clave == "legitimos_descartados_por_ancla":
        return str(sum(len(anclas) for anclas in valor.values()))
    if isinstance(valor, dict):
        return "; ".join(f"{k}: {v}" for k, v in valor.items())
    return str(valor)


def _conteo(clave: str, valor) -> float | None:
    """El número que se resta para la diferencia, o None si no hay uno."""
    if _es_tasa(valor):
        return valor["cumplen"]
    if clave == "invalido":
        return len(valor["casos"])
    if clave == "afirmaciones_sin_respaldo":
        return len(valor["con_afirmaciones"])
    if clave == "legitimos_descartados_por_ancla":
        return sum(len(anclas) for anclas in valor.values())
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return valor
    return None


def _con_signo(numero: float, sufijo: str = "") -> str:
    return f"{'+' if numero > 0 else '-'}{abs(numero):.0f}{sufijo}"


def diferencia(clave: str, base, nuevo) -> str:
    if base is None or nuevo is None:
        return FALTA
    if _conteo(clave, base) is None or _conteo(clave, nuevo) is None:
        return "=" if base == nuevo else "distinta"
    delta = _conteo(clave, nuevo) - _conteo(clave, base)
    if _es_tasa(base) and base["total"] and nuevo["total"]:
        puntos = 100 * (nuevo["cumplen"] / nuevo["total"] - base["cumplen"] / base["total"])
        if delta == 0 and round(puntos) == 0:
            return "="
        pp = "0 pp" if round(puntos) == 0 else _con_signo(puntos, " pp")
        return f"{_con_signo(delta) if delta else '0'} ({pp})"
    return "=" if delta == 0 else _con_signo(delta)


def denominadores_distintos(base: dict, nuevo: dict) -> list[str]:
    """Las tasas presentes en las dos corridas cuyo total difiere, como "clave (a → b)"."""
    return [
        f"{clave} ({base[clave]['total']} → {nuevo[clave]['total']})"
        for clave in base
        if _es_tasa(base[clave]) and _es_tasa(nuevo.get(clave))
        and base[clave]["total"] != nuevo[clave]["total"]
    ]


def _fila(clave: str, base: dict, nuevo: dict) -> str:
    b, n = base.get(clave), nuevo.get(clave)
    return f"| {clave} | {_formato(clave, b)} | {_formato(clave, n)} | {diferencia(clave, b, n)} |"


def _estado(caso: dict | None) -> str:
    if caso is None:
        return FALTA
    return caso["estado"] + (f" ({caso['motivo']})" if caso.get("motivo") else "")


def _duracion(reporte: dict) -> float:
    return sum(c.get("duracion_s") or 0 for c in reporte.get("casos", []))


def comparar(base: dict, nuevo: dict) -> str:
    cb, cn = base["config"], nuevo["config"]
    lineas = [
        "# Comparación de corridas",
        "",
        f"- Línea base: {cb.get('fecha', FALTA)} · "
        f"{'commit ' + cb['git_commit'] if cb.get('git_commit') else 'commit desconocido'}",
        f"- Nueva: {cn.get('fecha', FALTA)} · "
        f"{'commit ' + cn['git_commit'] if cn.get('git_commit') else 'commit desconocido'}",
    ]
    distintos = [c for c in CAMPOS_COMPARABLES if cb.get(c) != cn.get(c)]
    if distintos:
        detalle = ", ".join(f"{c}: {cb.get(c)} → {cn.get(c)}" for c in distintos)
        lineas.append(f"- **Advertencia: la configuración difiere** ({detalle}).")

    tb, tn = base["totales"], nuevo["totales"]
    claves = list(tb) + [c for c in tn if c not in tb]
    encabezado = ["| Métrica | Línea base | Nueva | Diferencia |", "|---|---|---|---|"]
    lineas += ["", "## Totales", "", *encabezado]
    lineas += [_fila(clave, tb, tn) for clave in claves]
    db, dn = _duracion(base), _duracion(nuevo)
    lineas.append(
        f"| Duración total (s) | {db:.0f} | {dn:.0f} | "
        f"{'=' if round(dn - db) == 0 else _con_signo(dn - db)} |"
    )
    distintos_den = denominadores_distintos(tb, tn)
    if distintos_den:
        lineas += [
            "",
            "Nota: los denominadores difieren entre corridas en "
            + ", ".join(distintos_den)
            + "; la diferencia en pp compara porcentajes sobre totales distintos.",
        ]

    lineas += ["", "## Inyecciones", "", *encabezado]
    lineas += [_fila(clave, tb, tn) for clave in INYECCION]

    casos_b = {c["id"]: c for c in base.get("casos", [])}
    casos_n = {c["id"]: c for c in nuevo.get("casos", [])}
    lineas += [
        "",
        "## Por caso",
        "",
        "| Caso | Tipo | Línea base | Nueva | Intentos | |",
        "|---|---|---|---|---|---|",
    ]
    for id_ in sorted(set(casos_b) | set(casos_n)):
        b, n = casos_b.get(id_), casos_n.get(id_)
        tipo = (n or b)["tipo"]
        intentos = f"{b['intentos'] if b else FALTA} → {n['intentos'] if n else FALTA}"
        cambio = "cambió" if _estado(b) != _estado(n) else ""
        lineas.append(f"| {id_} | {tipo} | {_estado(b)} | {_estado(n)} | {intentos} | {cambio} |")
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", type=Path, help="reporte.json de la línea base")
    parser.add_argument("nuevo", type=Path, help="reporte.json de la corrida nueva")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    base = json.loads(args.base.read_text(encoding="utf-8"))
    nuevo = json.loads(args.nuevo.read_text(encoding="utf-8"))
    print(comparar(base, nuevo), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
