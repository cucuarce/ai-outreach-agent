"""Nodo determinista preparar_entrada (versión mínima de T017).

La detección de idioma (T024), los controles de entradas vacías (T036) y el nonce (T043) se
agregan en tareas posteriores.
"""

import secrets
from datetime import datetime

from outreach_agent.estado import EstadoGrafo


def nuevo_run_id() -> str:
    """Formato AAAAMMDD-HHMMSS-<6 hex>."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def preparar_entrada(estado: EstadoGrafo) -> dict:
    entrada = estado["entrada"]
    return {
        # ejecutar() ya asigna el run_id para poder informarlo aunque el grafo falle.
        "run_id": estado.get("run_id") or nuevo_run_id(),
        "idioma_objetivo": entrada.idioma_solicitado or "es",
    }
