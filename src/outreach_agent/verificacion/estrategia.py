"""Nodo determinista verificar_estrategia.

Deja en la estrategia solo lo comprobable: hechos verificados, puntos del perfil con cita literal
y ancla dentro de la cita, y conexiones entre un hecho y un punto válidos. Los puntos
descartados quedan en `puntos_descartados` con su causa.
"""

from dataclasses import replace

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Motivo, PuntoPerfil
from outreach_agent.verificacion.cortes import cortar
from outreach_agent.verificacion.texto import contiene_ancla, contiene_literal


def causa_de_descarte_punto(punto: PuntoPerfil, perfil: str) -> str | None:
    if not contiene_literal(perfil, punto.cita):
        return "cita_no_localizable"
    if not contiene_ancla(punto.cita, punto.ancla):
        return "ancla_fuera_de_cita"
    return None


def verificar_estrategia(estado: EstadoGrafo) -> dict:
    estrategia = estado["estrategia"]
    perfil = estado["entrada"].perfil
    ids_hechos = {h.id for h in estado.get("hechos", [])}

    puntos: list[PuntoPerfil] = []
    descartados: list[dict] = []
    for punto in estrategia.puntos_perfil:
        causa = causa_de_descarte_punto(punto, perfil)
        if causa:
            descartados.append({"id": punto.id, "causa": causa})
        else:
            puntos.append(punto)
    ids_puntos = {p.id for p in puntos}

    verificada = replace(
        estrategia,
        hechos_elegidos=[i for i in estrategia.hechos_elegidos if i in ids_hechos],
        puntos_perfil=puntos,
        conexiones=[
            c
            for c in estrategia.conexiones
            if c.hecho_id in ids_hechos and c.punto_id in ids_puntos
        ],
    )
    actualizacion = {"estrategia": verificada, "puntos_descartados": descartados}
    if not verificada.puntos_perfil:
        actualizacion.update(cortar(estado, Motivo.PERFIL_SIN_PUNTOS))
    elif not verificada.conexiones:
        actualizacion.update(cortar(estado, Motivo.SIN_CONEXION_PERFIL))
    return actualizacion
