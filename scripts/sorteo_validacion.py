"""Sorteo reproducible de 6 ofertas para validación, fuera de las usadas en los casos de
evaluación (research R8 y R13).

Uso:
    python scripts/sorteo_validacion.py --ofertas <ruta a ofertas.json> [--salida <ruta>]

El dataset vive en el proyecto hermano ai-job-matcher (`job-embeddings-search/data/raw/ofertas.json`)
y no se copia a este repositorio. Del dataset se usa solo el campo `id`: el script no imprime ni
guarda textos. Excluye las ofertas ya usadas en `eval/casos/` (19 → valido-02, 83 → valido-05,
86 → valido-03), ordena los ids restantes y sortea 6 con `random.Random(42).sample`. Escribe la
semilla y los ids en `eval/validacion_ids.json`. Resultado con el dataset de 2026-10-14:
4, 15, 33, 37, 84, 98.
"""

import argparse
import json
import random
from pathlib import Path

SEMILLA = 42
CANTIDAD = 6
USADAS = {19, 83, 86}  # valido-02, valido-05, valido-03
SALIDA = Path(__file__).resolve().parent.parent / "eval" / "validacion_ids.json"


def sortear(ids: list[int]) -> list[int]:
    disponibles = sorted(i for i in ids if i not in USADAS)
    return sorted(random.Random(SEMILLA).sample(disponibles, CANTIDAD))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ofertas", required=True, help="ruta a ofertas.json")
    parser.add_argument("--salida", type=Path, default=SALIDA, help="archivo JSON de salida")
    args = parser.parse_args()

    with open(args.ofertas, encoding="utf-8") as archivo:
        ids = [int(oferta["id"]) for oferta in json.load(archivo)]
    elegidas = sortear(ids)
    with open(args.salida, "w", encoding="utf-8", newline="\n") as archivo:
        json.dump({"semilla": SEMILLA, "ids": elegidas}, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    print(f"{len(ids)} ofertas, {len(ids) - len(USADAS)} sin usar; ids sorteados: {elegidas}")
    print(f"escrito en {args.salida}")


if __name__ == "__main__":
    main()
