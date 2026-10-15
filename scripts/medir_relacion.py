"""Medición del evaluador de relación sobre el mini-set etiquetado (spec 002, T024; research D5;
contracts/miniset-conexiones.md).

Uso:
    python scripts/medir_relacion.py --etiquetado eval/conexiones/etiquetado.json \
        --origen eval/conexiones/origen.json

Aplica `terminos_compartidos` (research D4) a cada par y escribe en stdout un reporte en
Markdown: tabla de confusión, puerta de integración criterio por criterio, falsos aceptos y
falsos rechazos con sus citas, las `dudosa` aparte y el resultado por caso.

Los umbrales están fijos acá desde antes de la primera medición (plan.md, decisión a y nota del
2026-10-15) y no se modifican después de ver los números (decisión c). Las `dudosa` quedan fuera
de los umbrales y de los denominadores (decisión b).

Sale con código 1 si hay ítems sin etiquetar o si el etiquetado no corresponde a `--origen`. El
resultado de la puerta no cambia el código de salida. No escribe ni modifica ningún archivo.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):  # ejecutado como `python scripts/medir_relacion.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outreach_agent.verificacion.relacion import terminos_compartidos

# Puerta de integración (plan.md, decisión a; nota del 2026-10-15). Fija antes de medir.
CASO_INSUFICIENTE = "insuficiente-04"
MAX_FALSOS_ACEPTOS_INSUFICIENTE = 0
MAX_FALSOS_ACEPTOS_PCT = 10  # % de las `mala`
MAX_FALSOS_RECHAZOS_PCT = 25  # % de las `buena`
PREFIJO_VALIDO = "valido-"
ETIQUETAS = ("buena", "mala", "dudosa")


class MedicionError(Exception):
    pass


@dataclass(frozen=True)
class Par:
    id: str
    cita_dato: str
    cita_punto: str
    etiqueta: str
    casos: tuple[str, ...]
    terminos: tuple[str, ...]

    @property
    def conservada(self) -> bool:
        return bool(self.terminos)


@dataclass(frozen=True)
class Criterio:
    nombre: str
    cumplen: int  # numerador del criterio (falsos aceptos, rechazos o casos)
    total: int
    pasa: bool
    detalle: str = ""


def cargar(etiquetado: Path, origen: Path) -> tuple[list[dict], dict]:
    items = json.loads(etiquetado.read_text(encoding="utf-8"))["items"]
    origenes = json.loads(origen.read_text(encoding="utf-8"))
    sin_etiqueta = [i["id"] for i in items if i.get("etiqueta") not in ETIQUETAS]
    if sin_etiqueta:
        raise MedicionError(f"{len(sin_etiqueta)} ítems sin etiquetar o con etiqueta no válida")
    if {i["id"] for i in items} != set(origenes):
        raise MedicionError(f"{etiquetado} no corresponde a {origen}: los ids no coinciden")
    return items, origenes


def evaluar(
    items: list[dict],
    origenes: dict,
    evaluador: Callable[[str, str], list[str]] = terminos_compartidos,
) -> list[Par]:
    return [
        Par(
            id=item["id"],
            cita_dato=item["cita_dato"],
            cita_punto=item["cita_punto"],
            etiqueta=item["etiqueta"],
            casos=tuple(dict.fromkeys(c["caso"] for c in origenes[item["id"]]["casos"])),
            terminos=tuple(evaluador(item["cita_dato"], item["cita_punto"])),
        )
        for item in items
    ]


def _del(pares: list[Par], etiqueta: str) -> list[Par]:
    return [p for p in pares if p.etiqueta == etiqueta]


def casos_validos(pares: list[Par]) -> list[str]:
    """Los casos válidos del mini-set. El mini-set solo tiene casos con al menos 2 hechos
    válidos, que son los que llegan a `verificar_estrategia`."""
    return sorted({c for p in pares for c in p.casos if c.startswith(PREFIJO_VALIDO)})


def puerta(pares: list[Par]) -> list[Criterio]:
    malas, buenas = _del(pares, "mala"), _del(pares, "buena")
    malas_insuf = [p for p in malas if CASO_INSUFICIENTE in p.casos]
    fa_insuf = sum(p.conservada for p in malas_insuf)
    fa = sum(p.conservada for p in malas)
    fr = sum(not p.conservada for p in buenas)

    con_buena = [c for c in casos_validos(pares) if any(c in p.casos for p in buenas)]
    sin_buena = [c for c in casos_validos(pares) if c not in con_buena]
    con_buena_conservada = [
        c for c in con_buena if any(c in p.casos and p.conservada for p in buenas)
    ]
    sin_conservar = [c for c in con_buena if c not in con_buena_conservada]

    return [
        Criterio(
            f"Falsos aceptos en {CASO_INSUFICIENTE} (máximo {MAX_FALSOS_ACEPTOS_INSUFICIENTE})",
            fa_insuf, len(malas_insuf), fa_insuf <= MAX_FALSOS_ACEPTOS_INSUFICIENTE,
        ),
        Criterio(
            f"Falsos aceptos sobre las `mala` (máximo {MAX_FALSOS_ACEPTOS_PCT}%)",
            fa, len(malas), fa * 100 <= MAX_FALSOS_ACEPTOS_PCT * len(malas),
        ),
        Criterio(
            f"Falsos rechazos sobre las `buena` (máximo {MAX_FALSOS_RECHAZOS_PCT}%)",
            fr, len(buenas), fr * 100 <= MAX_FALSOS_RECHAZOS_PCT * len(buenas),
            f"tamaño de muestra: {len(buenas)} `buena`; el máximo equivale a "
            f"{MAX_FALSOS_RECHAZOS_PCT * len(buenas) // 100} de {len(buenas)}",
        ),
        Criterio(
            "Casos válidos con al menos una `buena` conservada (entre los que tienen alguna)",
            len(con_buena_conservada), len(con_buena), not sin_conservar,
            ("sin ninguna conservada: " + ", ".join(sin_conservar) + ". " if sin_conservar else "")
            + "Sin ninguna `buena` en el mini-set (no cuentan): "
            + (", ".join(sin_buena) if sin_buena else "ninguno"),
        ),
    ]


def fraccion(k: int, n: int) -> str:
    if n == 0:
        return f"{k}/{n}, sin muestra"
    return f"{k}/{n}, {100 * k / n:.1f}%".replace(".", ",")


def _citas(par: Par) -> list[str]:
    linea = [f"- Dato: {par.cita_dato}", f"  Punto: {par.cita_punto}"]
    if par.terminos:
        linea.append(f"  Términos compartidos: {', '.join(par.terminos)}")
    return linea


def reporte(pares: list[Par]) -> str:
    buenas, malas, dudosas = (_del(pares, e) for e in ETIQUETAS)
    criterios = puerta(pares)
    lineas = [
        "# Medición de D4 sobre el mini-set",
        "",
        f"Pares: {len(pares)} ({len(buenas)} `buena`, {len(malas)} `mala`, "
        f"{len(dudosas)} `dudosa`).",
        "",
        "## Confusión",
        "",
        "| Etiqueta | Conserva | Descarta |",
        "|---|---|---|",
    ]
    for etiqueta, grupo in (("buena", buenas), ("mala", malas)):
        conserva = sum(p.conservada for p in grupo)
        lineas.append(
            f"| `{etiqueta}` | {fraccion(conserva, len(grupo))} | "
            f"{fraccion(len(grupo) - conserva, len(grupo))} |"
        )
    lineas += ["", "## Puerta de integración", ""]
    for c in criterios:
        lineas.append(f"- {c.nombre}: {fraccion(c.cumplen, c.total)} → "
                      f"**{'pasa' if c.pasa else 'no pasa'}**")
        if c.detalle:
            lineas.append(f"  {c.detalle}")
    lineas += ["", f"**Resultado: {'pasa' if all(c.pasa for c in criterios) else 'no pasa'}**"]

    falsos_aceptos = [p for p in malas if p.conservada]
    falsos_rechazos = [p for p in buenas if not p.conservada]
    lineas += ["", f"## Falsos aceptos ({len(falsos_aceptos)})", ""]
    for p in falsos_aceptos:
        lineas += _citas(p)
    lineas += ["", f"## Falsos rechazos ({len(falsos_rechazos)})", ""]
    for p in falsos_rechazos:
        lineas += _citas(p)

    lineas += ["", f"## `dudosa` (fuera de los umbrales: {len(dudosas)})", ""]
    lineas.append(f"Conservadas: {fraccion(sum(p.conservada for p in dudosas), len(dudosas))}.")
    lineas.append("")
    for p in dudosas:
        lineas += _citas(p) + [f"  Veredicto: {'conserva' if p.conservada else 'descarta'}"]

    lineas += [
        "",
        "## Por caso",
        "",
        "| Caso | `buena` conservadas | `mala` conservadas | `dudosa` conservadas |",
        "|---|---|---|---|",
    ]
    for caso in sorted({c for p in pares for c in p.casos}):
        del_caso = [p for p in pares if caso in p.casos]
        celdas = []
        for etiqueta in ETIQUETAS:
            grupo = _del(del_caso, etiqueta)
            celdas.append(fraccion(sum(p.conservada for p in grupo), len(grupo)))
        lineas.append(f"| {caso} | " + " | ".join(celdas) + " |")
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--etiquetado", type=Path, required=True)
    parser.add_argument("--origen", type=Path, required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        items, origenes = cargar(args.etiquetado, args.origen)
    except MedicionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(reporte(evaluar(items, origenes)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
