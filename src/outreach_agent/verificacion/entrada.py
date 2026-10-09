"""Nodo determinista preparar_entrada.

Controla que las entradas no estén vacías (FR-009, FR-010), fija el idioma objetivo del borrador
(FR-018) y, si el usuario lo indicó, el nombre de la empresa (FR-019). Si algo impide seguir,
corta la ejecución antes de llamar al modelo. El nonce (T043) se agrega en la Historia 3.
"""

import secrets
from datetime import datetime

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Motivo
from outreach_agent.verificacion.cortes import cortar
from outreach_agent.verificacion.idioma import detectar_idioma


def nuevo_run_id() -> str:
    """Formato AAAAMMDD-HHMMSS-<6 hex>."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def preparar_entrada(estado: EstadoGrafo) -> dict:
    entrada = estado["entrada"]
    # ejecutar() ya asigna el run_id para poder informarlo aunque el grafo falle.
    actualizacion = {"run_id": estado.get("run_id") or nuevo_run_id()}
    contexto = {**estado, **actualizacion}

    if not entrada.texto_empresa.strip():
        return {**actualizacion, **cortar(contexto, Motivo.EMPRESA_VACIA)}
    if not entrada.perfil.strip():
        return {**actualizacion, **cortar(contexto, Motivo.PERFIL_VACIO)}

    idioma_empresa = detectar_idioma(entrada.texto_empresa)
    actualizacion["idioma_empresa"] = idioma_empresa
    actualizacion["idioma_objetivo"] = entrada.idioma_solicitado or idioma_empresa

    nombre_usuario = (entrada.nombre_empresa_solicitado or "").strip()
    if nombre_usuario:
        # Entrada del usuario: tiene prioridad y no se verifica contra el texto (research R12).
        actualizacion["nombre_empresa"] = nombre_usuario
        actualizacion["origen_nombre_empresa"] = "usuario"

    if actualizacion["idioma_objetivo"] is None:
        contexto = {**estado, **actualizacion}
        return {**actualizacion, **cortar(contexto, Motivo.IDIOMA_INDETERMINADO)}
    return actualizacion
