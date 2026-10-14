"""T034: Historia 2, información insuficiente: informar en vez de inventar."""

import copy
import json

import pytest

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from tests import escenarios as e
from tests.fakes import FakeProvider

TEXTO_VAGO = "Somos una empresa innovadora y apasionada por la excelencia."
UN_SOLO_HECHO = {
    "nombre_empresa": None,
    "hechos": [
        {
            "id": "H1",
            "descripcion": "Se define como innovadora",
            "cita": "Somos una empresa innovadora",
            "ancla": "innovadora",
        },
        {
            "id": "H2",
            "descripcion": "Dato inventado",
            "cita": "Facturamos 10 millones",
            "ancla": "10",
        },
    ],
    "instrucciones_detectadas": [],
}


def correr(respuestas, texto=e.TEXTO_EMPRESA, perfil=e.PERFIL):
    provider = FakeProvider([json.dumps(r) for r in respuestas])
    resultado = ejecutar(Entrada(texto, perfil), provider, cargar_config(env={}))
    return resultado, provider


def roles(provider):
    return [
        rol
        for llamada in provider.llamadas
        for rol in ("investigador", "estratega", "redactor")
        if f"agente {rol}" in llamada["system"]
    ]


@pytest.mark.parametrize("texto", ["", "   \n"])
def test_empresa_vacia_no_llama_al_modelo(texto):
    resultado, provider = correr([], texto=texto)

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.EMPRESA_VACIA
    assert resultado.borrador is None
    assert provider.llamadas == []


def test_perfil_vacio_no_llama_al_modelo():
    resultado, provider = correr([], perfil="  ")

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.PERFIL_VACIO
    assert resultado.borrador is None
    assert provider.llamadas == []


def test_menos_de_dos_datos_corta_antes_del_estratega():
    resultado, provider = correr([UN_SOLO_HECHO], texto=TEXTO_VAGO)

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.HECHOS_INSUFICIENTES
    assert "1 de 2" in resultado.detalle
    assert resultado.borrador is None
    assert roles(provider) == ["investigador"]


def test_respuesta_real_para_empresa_vaga_corta_antes_del_estratega():
    # Las anclas de 9 y 12 palabras se descartan por ancla_demasiado_larga (research R5).
    resultado, provider = correr([e.INVESTIGADOR_VAGA], texto=e.TEXTO_EMPRESA_VAGA)

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.HECHOS_INSUFICIENTES
    assert "0 de 2" in resultado.detalle
    assert resultado.borrador is None
    assert roles(provider) == ["investigador"]


def test_perfil_sin_puntos_concretos():
    estrategia = copy.deepcopy(e.ESTRATEGA)
    estrategia["puntos_perfil"] = [
        {
            "id": "P1",
            "descripcion": "Proactiva",
            "cita": "Soy proactiva y trabajo en equipo",  # no está en el perfil real
            "ancla": "proactiva",
        }
    ]
    resultado, provider = correr(
        [e.INVESTIGADOR, estrategia], perfil="Soy proactivo y trabajo en equipo."
    )

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.PERFIL_SIN_PUNTOS
    assert resultado.borrador is None
    assert roles(provider) == ["investigador", "estratega"]


def test_perfil_con_puntos_pero_sin_conexion():
    estrategia = copy.deepcopy(e.ESTRATEGA)
    estrategia["conexiones"] = [{"hecho_id": "H9", "punto_id": "P1", "razon": "Inexistente."}]
    resultado, provider = correr([e.INVESTIGADOR, estrategia])

    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.SIN_CONEXION_PERFIL
    assert resultado.borrador is None
    assert roles(provider) == ["investigador", "estratega"]


def test_detalles_distintos_para_perfil_sin_puntos_y_sin_conexion():
    sin_puntos = copy.deepcopy(e.ESTRATEGA)
    sin_puntos["puntos_perfil"] = []
    sin_conexion = copy.deepcopy(e.ESTRATEGA)
    sin_conexion["conexiones"] = []

    r1, _ = correr([e.INVESTIGADOR, sin_puntos])
    r2, _ = correr([e.INVESTIGADOR, sin_conexion])

    assert r1.motivo is Motivo.PERFIL_SIN_PUNTOS
    assert r2.motivo is Motivo.SIN_CONEXION_PERFIL
    assert r1.detalle != r2.detalle
