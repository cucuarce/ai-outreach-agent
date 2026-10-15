"""Regenera el reporte de una corrida de evaluación desde lo guardado en disco.

Uso:
    python scripts/regenerar_reporte.py <carpeta de corrida> [--casos eval/casos]

Arma de nuevo `reporte.md`, `reporte.json` y `revision_humana.json` con `evaluar.armar_reporte`,
la misma función que usa `evaluar.py` al final de una corrida. Sirve para incorporar la revisión
humana (`afirmaciones_sin_respaldo`) después de completarla a mano.

No usa la red: a diferencia de `evaluar.py --reanudar`, no consulta si Ollama está disponible, no
crea el proveedor y no corre casos. Los casos sin resultado quedan como pendientes en el reporte.
`config.json` y lo completado a mano en `revision_humana.json` no se modifican.

Código de salida: el mismo que `evaluar.py` (0 si todas las métricas están al 100%, sin errores
ni pendientes; 1 si no), o 2 si la carpeta no es una corrida (no tiene `config.json`).
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # ejecutado como `python scripts/regenerar_reporte.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import evaluar

CODIGO_NO_ES_CORRIDA = 2


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="regenerar_reporte", description="Regenera el reporte de una corrida sin red."
    )
    p.add_argument("corrida", help="Carpeta de la corrida (con config.json y resultados/).")
    p.add_argument("--casos", default="eval/casos", help="Carpeta de casos o un único caso .json.")
    return p


def main(argv: list[str] | None = None, log=print) -> int:
    args = construir_parser().parse_args(argv)
    corrida = Path(args.corrida)
    if not (corrida / "config.json").is_file():
        log(f"{corrida} no es una corrida de evaluación: falta config.json.")
        return CODIGO_NO_ES_CORRIDA
    reporte = evaluar.armar_reporte(corrida, evaluar.cargar_casos(Path(args.casos)))
    log(f"Reporte: {corrida / 'reporte.md'}")
    return evaluar.codigo_de_salida(reporte)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
