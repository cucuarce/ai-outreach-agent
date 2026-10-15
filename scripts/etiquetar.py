"""Etiquetado manual del mini-set de conexiones (spec 002, T003; contracts/miniset-conexiones.md).

Uso:
    python scripts/etiquetar.py [--entrada eval/conexiones/para_etiquetar.json]
                                [--salida eval/conexiones/etiquetado.json]

Muestra de a un ítem solo la cita del dato y la cita del punto, con el contador "n de N". Nunca
muestra el id, el origen, el caso, la razón del estratega ni un veredicto, y no evalúa ni sugiere
nada. Respuestas: b (buena), m (mala), d (dudosa), a (volver al anterior), q (salir).

Guarda en `--salida` después de cada respuesta. Al volver a ejecutarse retoma desde el primer ítem
sin etiqueta. `--entrada` no se modifica.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable

ETIQUETAS = {"b": "buena", "m": "mala", "d": "dudosa"}
OPCIONES = "[b] buena  [m] mala  [d] dudosa  [a] anterior  [q] salir: "


class EtiquetadoError(Exception):
    pass


def cargar(entrada: Path, salida: Path) -> dict:
    """El etiquetado en curso si existe; si no, una copia de `entrada` sin etiquetas."""
    base = json.loads(entrada.read_text(encoding="utf-8"))
    if not salida.exists():
        return base
    guardado = json.loads(salida.read_text(encoding="utf-8"))
    ids_base = [item["id"] for item in base["items"]]
    ids_guardados = [item["id"] for item in guardado["items"]]
    if ids_base != ids_guardados:
        raise EtiquetadoError(f"{salida} no corresponde a {entrada}: los ítems no coinciden")
    return guardado


def guardar(datos: dict, salida: Path) -> None:
    """Escribe a un archivo temporal y lo reemplaza, para no dejar un JSON a medias."""
    temporal = salida.with_suffix(salida.suffix + ".tmp")
    with open(temporal, "w", encoding="utf-8", newline="\n") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    os.replace(temporal, salida)


def primero_sin_etiqueta(items: list[dict]) -> int | None:
    for i, item in enumerate(items):
        if not item.get("etiqueta"):
            return i
    return None


def siguiente(items: list[dict], actual: int) -> int | None:
    """El ítem que sigue; al llegar al final, el primero que quede sin etiqueta."""
    if actual + 1 < len(items):
        return actual + 1
    return primero_sin_etiqueta(items)


def mostrar(item: dict, posicion: int, total: int, escribir: Callable[[str], None]) -> None:
    escribir("")
    escribir(f"{posicion} de {total}")
    escribir(f"Dato:  {item['cita_dato']}")
    escribir(f"Punto: {item['cita_punto']}")
    if item.get("etiqueta"):
        escribir(f"(ya etiquetado por vos: {item['etiqueta']})")


def etiquetar(
    entrada: Path,
    salida: Path,
    leer: Callable[[str], str] = input,
    escribir: Callable[[str], None] = print,
) -> int:
    datos = cargar(entrada, salida)
    items = datos["items"]
    total = len(items)
    actual = primero_sin_etiqueta(items)
    if actual is None:
        escribir(f"Los {total} ítems ya están etiquetados.")
        return 0
    escribir(datos.get("definicion", ""))
    while actual is not None:
        mostrar(items[actual], actual + 1, total, escribir)
        try:
            respuesta = leer(OPCIONES).strip().lower()
        except EOFError:
            respuesta = "q"
        if respuesta in ETIQUETAS:
            items[actual]["etiqueta"] = ETIQUETAS[respuesta]
            guardar(datos, salida)
            actual = siguiente(items, actual)
        elif respuesta == "a":
            if actual == 0:
                escribir("Ya estás en el primer ítem.")
            else:
                actual -= 1
        elif respuesta == "q":
            break
        else:
            escribir("Respuesta no válida.")
    hechas = sum(1 for item in items if item.get("etiqueta"))
    escribir(f"Etiquetados: {hechas}/{total}. Guardado en {salida}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--entrada", type=Path, default=Path("eval/conexiones/para_etiquetar.json")
    )
    parser.add_argument("--salida", type=Path, default=Path("eval/conexiones/etiquetado.json"))
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        return etiquetar(args.entrada, args.salida)
    except EtiquetadoError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
