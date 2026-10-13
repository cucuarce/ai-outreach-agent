"""Agente estratega: elige qué datos de la empresa usar y con qué puntos del perfil conectarlos.

Recibe de cada hecho solo `id`, `cita` y `ancla`; nunca el texto crudo de la empresa ni la
`descripcion` de los hechos (research R3).
"""

from outreach_agent.agentes.base import exigir_lista, exigir_texto, llamar_json
from outreach_agent.agentes.prompts import mensajes_estratega
from outreach_agent.config import Config
from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Conexion, Estrategia, Hecho, PuntoPerfil
from outreach_agent.proveedores.base import LLMProvider

TEMPERATURA = 0.3


def hechos_disponibles(estado: EstadoGrafo) -> list[Hecho]:
    """Los hechos verificados si ya pasaron por verificar_hechos; si no, los candidatos."""
    if "hechos" in estado:
        return estado["hechos"]
    return estado.get("hechos_candidatos", [])


def _validar(datos: dict) -> None:
    exigir_texto(datos, "angulo", "la respuesta")
    exigir_lista(datos, "hechos_elegidos", str, "la respuesta")
    for i, punto in enumerate(exigir_lista(datos, "puntos_perfil", dict, "la respuesta")):
        for campo in ("id", "descripcion", "cita", "ancla"):
            exigir_texto(punto, campo, f"puntos_perfil[{i}]")
    for i, conexion in enumerate(exigir_lista(datos, "conexiones", dict, "la respuesta")):
        for campo in ("hecho_id", "punto_id", "razon"):
            exigir_texto(conexion, campo, f"conexiones[{i}]")


def estratega(estado: EstadoGrafo, provider: LLMProvider, config: Config) -> dict:
    system, user = mensajes_estratega(
        hechos_disponibles(estado), estado["entrada"].perfil, estado.get("idioma_objetivo")
    )
    datos = llamar_json(
        provider,
        system,
        user,
        _validar,
        max_tokens=config.max_tokens_estratega,
        temperatura=TEMPERATURA,
    )
    estrategia = Estrategia(
        angulo=datos["angulo"],
        hechos_elegidos=list(datos["hechos_elegidos"]),
        puntos_perfil=[
            PuntoPerfil(id=p["id"], descripcion=p["descripcion"], cita=p["cita"], ancla=p["ancla"])
            for p in datos["puntos_perfil"]
        ],
        conexiones=[
            Conexion(hecho_id=c["hecho_id"], punto_id=c["punto_id"], razon=c["razon"])
            for c in datos["conexiones"]
        ],
    )
    return {"estrategia": estrategia}


def resumir(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    """Decisión para la traza: ángulo e ids elegidos (con descripciones y razones del modelo)."""
    e = actualizacion["estrategia"]
    decision = (
        f"ángulo: {e.angulo}; hechos {', '.join(e.hechos_elegidos) or '(ninguno)'}; "
        f"puntos {', '.join(p.id for p in e.puntos_perfil) or '(ninguno)'}"
    )
    return decision, {
        "angulo": e.angulo,
        "hechos_elegidos": e.hechos_elegidos,
        "puntos_perfil": [
            {"id": p.id, "descripcion": p.descripcion, "cita": p.cita, "ancla": p.ancla}
            for p in e.puntos_perfil
        ],
        "conexiones": [
            {"hecho_id": c.hecho_id, "punto_id": c.punto_id, "razon": c.razon} for c in e.conexiones
        ],
    }
