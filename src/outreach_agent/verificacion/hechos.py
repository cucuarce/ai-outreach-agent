"""Nodo determinista verificar_hechos (research R3 y R5).

Pasa a `hechos` los candidatos del investigador que se pueden comprobar contra el texto de la
empresa y deja el resto en `hechos_descartados` con su causa.
"""

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import MAX_CITA, Hecho
from outreach_agent.verificacion.texto import contiene_ancla, contiene_literal, normalizar


def causa_de_descarte(hecho: Hecho, texto_empresa: str, citas_vistas: set[str]) -> str | None:
    if len(hecho.cita) > MAX_CITA:
        return "cita_demasiado_larga"
    if not contiene_literal(texto_empresa, hecho.cita):
        return "cita_no_localizable"
    if not contiene_ancla(hecho.cita, hecho.ancla):
        return "ancla_fuera_de_cita"
    if normalizar(hecho.cita) in citas_vistas:
        return "duplicado"
    return None


def verificar_hechos(estado: EstadoGrafo) -> dict:
    texto_empresa = estado["entrada"].texto_empresa
    validos: list[Hecho] = []
    descartados: list[dict] = []
    citas_vistas: set[str] = set()
    for hecho in estado.get("hechos_candidatos", []):
        causa = causa_de_descarte(hecho, texto_empresa, citas_vistas)
        if causa:
            descartados.append({"id": hecho.id, "causa": causa})
        else:
            validos.append(hecho)
            citas_vistas.add(normalizar(hecho.cita))
    return {"hechos": validos, "hechos_descartados": descartados}
