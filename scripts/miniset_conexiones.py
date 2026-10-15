"""Mini-set de conexiones dato–punto para medir el evaluador de relación (spec 002, research D5;
contracts/miniset-conexiones.md).

Uso:
    python scripts/miniset_conexiones.py --corrida <carpeta de corrida> \
        [--corrida-extra <traza .jsonl>] [--casos eval/casos] --salida eval/conexiones

Lee solo trazas de desarrollo y el perfil de los casos de `--casos`. Arma el producto cartesiano
entre las citas de los hechos válidos (de los casos con al menos 2 hechos válidos) y las oraciones
del perfil, y le suma las conexiones que propuso el estratega en la corrida y en la traza extra.
Escribe dos archivos:

- `para_etiquetar.json`: definición de las etiquetas e ítems con id opaco, las dos citas y la
  etiqueta vacía, en orden mezclado con semilla fija. No incluye caso, tipo, razón, ángulo ni
  veredicto, para que el etiquetado no se sesgue.
- `origen.json`: de qué caso, hecho y oración del perfil sale cada ítem. No hace falta abrirlo
  para etiquetar.

Se niega a sobrescribir un `para_etiquetar.json` que ya tenga etiquetas.
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from outreach_agent.verificacion.texto import normalizar

SEMILLA_ORDEN = 42
MIN_HECHOS = 2
DEFINICION = (
    "Buena: el punto del perfil muestra experiencia en algo que el dato indica que la empresa "
    "hace, usa o busca (misma tecnología, dominio, tipo de problema o puesto). Mala: no hay esa "
    "relación; compartir cifras, volúmenes o la necesidad de escalar no cuenta. Dudosa: no se "
    "puede decidir con las dos citas."
)


class MinisetError(Exception):
    pass


def leer_traza(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as archivo:
        return [json.loads(linea) for linea in archivo if linea.strip()]


def nodo_fin(eventos: list[dict], nodo: str) -> dict | None:
    for evento in eventos:
        if evento["evento"] == "nodo_fin" and evento["nodo"] == nodo:
            return evento["detalle"]
    return None


def oraciones_del_perfil(perfil: str) -> list[str]:
    """Una oración por línea no vacía, sin el guion de viñeta."""
    oraciones = []
    for linea in perfil.splitlines():
        linea = linea.strip()
        if linea.startswith("- "):
            linea = linea[2:].strip()
        if linea:
            oraciones.append(linea)
    return oraciones


def perfil_de_los_casos(casos: Path) -> str:
    perfiles = {
        json.loads(ruta.read_text(encoding="utf-8"))["perfil"]
        for ruta in sorted(casos.glob("*.json"))
    }
    if len(perfiles) != 1:
        raise MinisetError(f"se esperaba un único perfil en {casos}; hay {len(perfiles)}")
    return perfiles.pop()


def id_opaco(cita_dato: str, cita_punto: str) -> str:
    clave = f"{normalizar(cita_dato)}\x00{normalizar(cita_punto)}"
    return "c-" + hashlib.sha1(clave.encode("utf-8")).hexdigest()[:8]


def indice_de_oracion(cita_punto: str, oraciones: list[str]) -> int | None:
    """Índice de la oración del perfil que contiene la cita del punto, si hay una."""
    cita = normalizar(cita_punto)
    for i, oracion in enumerate(oraciones):
        if cita and cita in normalizar(oracion):
            return i
    return None


def caso_de_traza(eventos: list[dict], caso: str) -> dict:
    """Hechos válidos (con su cita) y conexiones propuestas de una traza."""
    investigador = nodo_fin(eventos, "investigador") or {}
    verificacion = nodo_fin(eventos, "verificar_hechos") or {}
    estratega = nodo_fin(eventos, "estratega")
    hechos = {h["id"]: h["cita"] for h in investigador.get("hechos", [])}
    validos = {i: hechos[i] for i in verificacion.get("validos", []) if i in hechos}
    propuestas = []
    if estratega:
        puntos = {p["id"]: p["cita"] for p in estratega.get("puntos_perfil", [])}
        for conexion in estratega.get("conexiones", []):
            hecho, punto = conexion["hecho_id"], conexion["punto_id"]
            if hecho in validos and punto in puntos:
                propuestas.append((hecho, puntos[punto]))
    return {"caso": caso, "validos": validos, "propuestas": propuestas}


def trazas_de_corrida(corrida: Path) -> list[dict]:
    casos = []
    for ruta in sorted((corrida / "resultados").glob("*.json")):
        run_id = json.loads(ruta.read_text(encoding="utf-8"))["run_id"]
        eventos = leer_traza(corrida / "trazas" / f"{run_id}.jsonl")
        casos.append(caso_de_traza(eventos, ruta.stem))
    return casos


def armar_items(casos: list[dict], oraciones: list[str]) -> tuple[list[dict], dict]:
    items: dict[str, dict] = {}
    origen: dict[str, dict] = {}

    def agregar(caso, hecho_id, cita_dato, cita_punto, indice, propuesta):
        id_ = id_opaco(cita_dato, cita_punto)
        if id_ not in items:
            items[id_] = {
                "id": id_,
                "cita_dato": cita_dato,
                "cita_punto": cita_punto,
                "etiqueta": "",
                "nota": "",
            }
            origen[id_] = {"casos": [], "punto_perfil": indice, "propuesta_por_estratega": False}
        registro = origen[id_]
        if {"caso": caso, "hecho_id": hecho_id} not in registro["casos"]:
            registro["casos"].append({"caso": caso, "hecho_id": hecho_id})
        registro["propuesta_por_estratega"] = registro["propuesta_por_estratega"] or propuesta

    for caso in casos:
        if len(caso["validos"]) >= MIN_HECHOS:
            for hecho_id, cita in caso["validos"].items():
                for indice, oracion in enumerate(oraciones):
                    agregar(caso["caso"], hecho_id, cita, oracion, indice, False)
    for caso in casos:
        for hecho_id, cita_punto in caso["propuestas"]:
            indice = indice_de_oracion(cita_punto, oraciones)
            # Si la cita del punto está dentro de una oración del perfil, el par es el mismo que
            # el del producto cartesiano; si no, entra como un ítem propio con la cita tal cual.
            punto = oraciones[indice] if indice is not None else cita_punto
            agregar(caso["caso"], hecho_id, caso["validos"][hecho_id], punto, indice, True)

    ordenados = sorted(items.values(), key=lambda item: item["id"])
    random.Random(SEMILLA_ORDEN).shuffle(ordenados)
    return ordenados, origen


def tiene_etiquetas(ruta: Path) -> bool:
    if not ruta.exists():
        return False
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return any(item.get("etiqueta") for item in datos.get("items", []))


def _escribir_json(ruta: Path, datos) -> None:
    with open(ruta, "w", encoding="utf-8", newline="\n") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def generar(corrida: Path, extras: list[Path], casos: Path, salida: Path) -> int:
    destino = salida / "para_etiquetar.json"
    if tiene_etiquetas(destino):
        raise MinisetError(f"{destino} ya tiene etiquetas; no se sobrescribe")
    oraciones = oraciones_del_perfil(perfil_de_los_casos(casos))
    trazas = trazas_de_corrida(corrida)
    trazas += [caso_de_traza(leer_traza(ruta), f"run:{ruta.stem}") for ruta in extras]
    items, origen = armar_items(trazas, oraciones)
    salida.mkdir(parents=True, exist_ok=True)
    _escribir_json(
        destino, {"definicion": DEFINICION, "semilla_orden": SEMILLA_ORDEN, "items": items}
    )
    _escribir_json(salida / "origen.json", origen)
    return len(items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corrida", type=Path, required=True, help="carpeta de corrida")
    parser.add_argument(
        "--corrida-extra", type=Path, action="append", default=[], help="traza .jsonl extra"
    )
    parser.add_argument("--casos", type=Path, default=Path("eval/casos"), help="casos (perfil)")
    parser.add_argument("--salida", type=Path, required=True, help="carpeta de salida")
    args = parser.parse_args(argv)
    try:
        cantidad = generar(args.corrida, args.corrida_extra, args.casos, args.salida)
    except MinisetError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"{cantidad} conexiones escritas en {args.salida / 'para_etiquetar.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
