"""Traza estructurada y registro legible de cada ejecución (contracts/trace.md, research R7).

Cada ejecución escribe `<run_id>.jsonl` (un evento por línea, principio V de la constitución) y,
al terminar, `<run_id>.md`, una vista legible generada a partir de los mismos eventos.
"""

import json
import secrets
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path

from outreach_agent.estado import EstadoGrafo

# resumir(estado, actualizacion) -> (decision, detalle)
Resumir = Callable[[EstadoGrafo, dict], tuple[str, dict]]


def nuevo_run_id() -> str:
    """Formato AAAAMMDD-HHMMSS-<6 hex>."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


class Traza:
    """Escribe los eventos de una ejecución a medida que ocurren."""

    def __init__(self, directorio: Path | str, run_id: str):
        self.run_id = run_id
        directorio = Path(directorio)
        directorio.mkdir(parents=True, exist_ok=True)
        self.ruta_jsonl = directorio / f"{run_id}.jsonl"
        self.ruta_md = directorio / f"{run_id}.md"
        self.eventos: list[dict] = []

    def emitir(
        self,
        evento: str,
        *,
        nodo: str | None = None,
        tipo_nodo: str | None = None,
        intento: int | None = None,
        decision: str = "",
        detalle: dict | None = None,
        duracion_ms: int | None = None,
    ) -> dict:
        registro = {
            "run_id": self.run_id,
            "seq": len(self.eventos) + 1,
            "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "evento": evento,
            "nodo": nodo,
            "tipo_nodo": tipo_nodo,
            "intento": intento,
            "decision": decision,
            "detalle": detalle or {},
            "duracion_ms": duracion_ms,
        }
        self.eventos.append(registro)
        with self.ruta_jsonl.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
        return registro

    def escribir_md(self) -> None:
        self.ruta_md.write_text(renderizar_md(self.eventos), encoding="utf-8")

    def rutas(self) -> dict[str, str]:
        return {"jsonl": str(self.ruta_jsonl), "md": str(self.ruta_md)}


def trazado(
    traza: Traza,
    nombre: str,
    tipo_nodo: str,
    resumir: Resumir,
    intento_de: Callable[[EstadoGrafo], int | None] | None = None,
):
    """Decorador que envuelve un nodo del grafo: emite `nodo_inicio`, ejecuta el nodo y emite
    `nodo_fin` con la decisión que arma `resumir`, o `nodo_error` si el nodo lanza una
    excepción (que se vuelve a lanzar sin cambios)."""

    def decorar(funcion: Callable[[EstadoGrafo], dict]) -> Callable[[EstadoGrafo], dict]:
        @wraps(funcion)
        def nodo(estado: EstadoGrafo) -> dict:
            intento = intento_de(estado) if intento_de else None
            comun = {"nodo": nombre, "tipo_nodo": tipo_nodo, "intento": intento}
            traza.emitir("nodo_inicio", **comun)
            inicio = time.perf_counter()
            try:
                actualizacion = funcion(estado)
            except Exception as error:
                traza.emitir(
                    "nodo_error",
                    **comun,
                    decision=f"error: {type(error).__name__}",
                    detalle={"error": type(error).__name__, "mensaje": str(error)},
                    duracion_ms=_ms_desde(inicio),
                )
                raise
            decision, detalle = resumir(estado, actualizacion)
            traza.emitir(
                "nodo_fin", **comun, decision=decision, detalle=detalle, duracion_ms=_ms_desde(inicio)
            )
            return actualizacion

        return nodo

    return decorar


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


# --- Registro legible ---------------------------------------------------------------------


def _formatear(valor) -> str:
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list) and all(isinstance(x, (str, int, float)) for x in valor):
        return ", ".join(str(x) for x in valor) if valor else "(ninguno)"
    if valor is None:
        return "—"
    return json.dumps(valor, ensure_ascii=False, default=str)


def renderizar_md(eventos: list[dict]) -> str:
    inicio = next((ev for ev in eventos if ev["evento"] == "ejecucion_inicio"), None)
    fin = next((ev for ev in eventos if ev["evento"] == "ejecucion_fin"), None)
    run_id = eventos[0]["run_id"] if eventos else "?"
    final = fin["detalle"] if fin else {}

    lineas = [f"# Registro de ejecución {run_id}", ""]
    if inicio:
        det = inicio["detalle"]
        lineas.append(f"- Fecha: {inicio['ts']}")
        lineas.append(f"- Proveedor: {det.get('proveedor')} · Modelo: {det.get('modelo')}")
    estado = final.get("estado", "sin terminar")
    motivo = f" ({final['motivo']})" if final.get("motivo") else ""
    lineas.append(f"- Estado final: **{estado}**{motivo}")
    if fin and fin.get("duracion_ms") is not None:
        lineas.append(f"- Duración total: {fin['duracion_ms'] / 1000:.1f} s")

    paso = 0
    for ev in eventos:
        if ev["evento"] not in ("nodo_fin", "nodo_error"):
            continue
        paso += 1
        tipo = "agente" if ev["tipo_nodo"] == "agente" else "verificación"
        titulo = f"## {paso}. {ev['nodo']} ({tipo})"
        if ev["intento"] is not None:
            titulo += f" · intento {ev['intento']}"
        etiqueta = "Error" if ev["evento"] == "nodo_error" else "Decisión"
        lineas += ["", titulo, "", f"**{etiqueta}:** {ev['decision']}", ""]
        lineas += [f"- {clave}: {_formatear(valor)}" for clave, valor in ev["detalle"].items()]

    lineas += ["", "## Resultado", "", f"- Estado: **{estado}**{motivo}"]
    if final.get("detalle"):
        lineas.append(f"- Detalle: {final['detalle']}")
    for fallo in final.get("fallos") or []:
        lineas.append(f"- Criterio incumplido · {fallo['criterio']}: {fallo['detalle']}")
    if final.get("borrador"):
        lineas += ["", "### Borrador", "", *[f"> {linea}" for linea in final["borrador"].splitlines()]]
    return "\n".join(lineas) + "\n"
