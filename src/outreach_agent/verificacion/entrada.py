"""Nodo determinista preparar_entrada.

Fija el idioma objetivo del borrador (FR-018): el que indicó el usuario o, si no indicó
ninguno, el detectado en el texto de la empresa. Si no hay ninguno, corta la ejecución.
Los controles de entradas vacías (T036) y el nonce (T043) se agregan en tareas posteriores.
"""

import secrets
from datetime import datetime

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Estado, Motivo, Resultado
from outreach_agent.verificacion.idioma import detectar_idioma


def nuevo_run_id() -> str:
    """Formato AAAAMMDD-HHMMSS-<6 hex>."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def preparar_entrada(estado: EstadoGrafo) -> dict:
    entrada = estado["entrada"]
    # ejecutar() ya asigna el run_id para poder informarlo aunque el grafo falle.
    run_id = estado.get("run_id") or nuevo_run_id()
    idioma_empresa = detectar_idioma(entrada.texto_empresa)
    idioma_objetivo = entrada.idioma_solicitado or idioma_empresa
    actualizacion = {
        "run_id": run_id,
        "idioma_empresa": idioma_empresa,
        "idioma_objetivo": idioma_objetivo,
    }
    if idioma_objetivo is None:
        actualizacion["resultado"] = Resultado(
            estado=Estado.INSUFICIENTE,
            run_id=run_id,
            motivo=Motivo.IDIOMA_INDETERMINADO,
            detalle=(
                "No se pudo determinar el idioma del texto de la empresa, o no es uno de los "
                "soportados (es, en, pt, fr, de, it). Indicá el idioma del borrador con --idioma."
            ),
        )
    return actualizacion
