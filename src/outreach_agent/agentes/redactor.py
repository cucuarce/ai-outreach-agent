"""Agente redactor: escribe el mensaje según la estrategia.

Recibe el ángulo, los ids de las conexiones y, de cada hecho y punto del perfil, solo `id`, `cita`
y `ancla`. Nunca recibe el texto crudo de la empresa, la `descripcion` de los hechos ni la
`razon` de las conexiones (research R3). En los reintentos recibe los fallos del intento
anterior.
"""

from outreach_agent.agentes.base import exigir_lista, exigir_texto, llamar_json
from outreach_agent.agentes.estratega import hechos_disponibles
from outreach_agent.agentes.prompts import mensajes_redactor
from outreach_agent.config import Config
from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Borrador
from outreach_agent.proveedores.base import LLMProvider
from outreach_agent.verificacion.relleno import ejemplos_relleno


def _validar(datos: dict) -> None:
    if not exigir_texto(datos, "texto", "la respuesta").strip():
        raise ValueError("'texto' no puede estar vacío")
    exigir_lista(datos, "hechos_usados", str, "la respuesta")
    exigir_lista(datos, "puntos_usados", str, "la respuesta")


def redactor(estado: EstadoGrafo, provider: LLMProvider, config: Config) -> dict:
    estrategia = estado["estrategia"]
    elegidos = set(estrategia.hechos_elegidos)
    hechos_elegidos = [h for h in hechos_disponibles(estado) if h.id in elegidos]
    validacion = estado.get("validacion")
    fallos = validacion.fallos if validacion and not validacion.ok else []
    # En un reintento, el redactor recibe el borrador anterior para corregir solo lo que falló.
    anterior = estado["borrador"].texto if fallos and "borrador" in estado else None

    idioma = estado.get("idioma_objetivo")
    system, user = mensajes_redactor(
        estrategia,
        hechos_elegidos,
        idioma,
        ejemplos_relleno(idioma),
        fallos,
        estado.get("nombre_empresa"),
        anterior,
    )
    datos = llamar_json(
        provider,
        system,
        user,
        _validar,
        max_tokens=config.max_tokens_redactor,
        temperatura=config.temperatura_redactor,
    )
    borrador = Borrador(
        texto=datos["texto"],
        hechos_usados=list(datos["hechos_usados"]),
        puntos_usados=list(datos["puntos_usados"]),
    )
    return {"borrador": borrador, "intento": estado.get("intento", 0) + 1}


def resumir(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    """Decisión para la traza: intento y cantidad de palabras."""
    borrador = actualizacion["borrador"]
    palabras = len(borrador.texto.split())
    return f"intento {actualizacion['intento']}: {palabras} palabras", {
        "palabras": palabras,
        "hechos_usados": borrador.hechos_usados,
        "puntos_usados": borrador.puntos_usados,
        "texto": borrador.texto,
    }
