"""Agente investigador: extrae datos concretos del texto de la empresa.

Es el único agente que recibe el texto crudo de la empresa (research R3).
"""

from outreach_agent.agentes.base import exigir_lista, exigir_texto, llamar_json
from outreach_agent.agentes.prompts import mensajes_investigador
from outreach_agent.config import Config
from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Hecho
from outreach_agent.proveedores.base import LLMProvider

TEMPERATURA = 0.1


def _validar(datos: dict) -> None:
    # nombre_empresa puede faltar o ser null: los modelos chicos a veces lo omiten.
    if datos.get("nombre_empresa") is not None and not isinstance(datos["nombre_empresa"], str):
        raise ValueError("'nombre_empresa' debe ser un texto o null")
    for i, hecho in enumerate(exigir_lista(datos, "hechos", dict, "la respuesta")):
        for campo in ("id", "descripcion", "cita", "ancla"):
            exigir_texto(hecho, campo, f"hechos[{i}]")
    if "instrucciones_detectadas" in datos:
        exigir_lista(datos, "instrucciones_detectadas", str, "la respuesta")


def investigador(estado: EstadoGrafo, provider: LLMProvider, config: Config) -> dict:
    system, user = mensajes_investigador(estado["texto_empresa_saneado"], estado["nonce"])
    datos = llamar_json(
        provider,
        system,
        user,
        _validar,
        max_tokens=config.max_tokens_investigador,
        temperatura=TEMPERATURA,
    )
    hechos = [
        Hecho(id=h["id"], descripcion=h["descripcion"], cita=h["cita"], ancla=h["ancla"])
        for h in datos["hechos"]
    ]
    return {
        "nombre_empresa_candidato": datos.get("nombre_empresa"),
        "hechos_candidatos": hechos,
        "instrucciones_detectadas": datos.get("instrucciones_detectadas", []),
    }


def resumir(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    """Decisión para la traza. Las descripciones escritas por el modelo quedan solo acá."""
    hechos = actualizacion["hechos_candidatos"]
    instrucciones = actualizacion["instrucciones_detectadas"]
    decision = f"{len(hechos)} hechos candidatos, {len(instrucciones)} instrucciones detectadas"
    return decision, {
        "nombre_empresa_candidato": actualizacion.get("nombre_empresa_candidato"),
        "hechos": [
            {"id": h.id, "descripcion": h.descripcion, "cita": h.cita, "ancla": h.ancla}
            for h in hechos
        ],
        "instrucciones_detectadas": instrucciones,
    }
