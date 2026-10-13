"""Nodo determinista preparar_entrada.

Controla que las entradas no estén vacías (FR-009, FR-010), fija el idioma objetivo del borrador
(FR-018) y, si el usuario lo indicó, el nombre de la empresa (FR-019). Si algo impide seguir,
corta la ejecución antes de llamar al modelo. También genera el nonce de los delimitadores y
sanea el texto de la empresa para el investigador (research R3).
"""

import re
import secrets

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Motivo
from outreach_agent.trazas import nuevo_run_id
from outreach_agent.verificacion.cortes import cortar
from outreach_agent.verificacion.idioma import detectar_idioma


_DELIMITADOR = re.compile(r"<{3,}|>{3,}")


def sanear(texto: str) -> str:
    """Quita toda secuencia de 3 o más `<` o `>`, para que el texto no pueda simular un
    delimitador. Se repite hasta que no quede ninguna (quitar una puede formar otra)."""
    while True:
        saneado = _DELIMITADOR.sub("", texto)
        if saneado == texto:
            return saneado
        texto = saneado


def preparar_entrada(estado: EstadoGrafo) -> dict:
    entrada = estado["entrada"]
    # ejecutar() ya asigna el run_id para poder informarlo aunque el grafo falle.
    actualizacion = {"run_id": estado.get("run_id") or nuevo_run_id()}
    contexto = {**estado, **actualizacion}

    if not entrada.texto_empresa.strip():
        return {**actualizacion, **cortar(contexto, Motivo.EMPRESA_VACIA)}
    if not entrada.perfil.strip():
        return {**actualizacion, **cortar(contexto, Motivo.PERFIL_VACIO)}

    actualizacion["nonce"] = secrets.token_hex(8)
    actualizacion["texto_empresa_saneado"] = sanear(entrada.texto_empresa)
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


def resumir(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    """Decisión para la traza: idioma objetivo y cómo se obtuvo, o motivo de corte."""
    entrada = estado["entrada"]
    detalle = {
        "caracteres_empresa": len(entrada.texto_empresa),
        "caracteres_perfil": len(entrada.perfil),
    }
    if "resultado" in actualizacion:
        resultado = actualizacion["resultado"]
        detalle["detalle"] = resultado.detalle
        return f"corte: {resultado.motivo.value}", detalle
    origen = "solicitado" if entrada.idioma_solicitado else "detectado"
    detalle.update(
        idioma_objetivo=actualizacion["idioma_objetivo"],
        origen_idioma=origen,
        idioma_empresa=actualizacion.get("idioma_empresa"),
    )
    if actualizacion.get("origen_nombre_empresa") == "usuario":
        detalle["nombre_empresa"] = f"{actualizacion['nombre_empresa']} (indicado por el usuario)"
    return f"idioma {actualizacion['idioma_objetivo']} ({origen})", detalle
