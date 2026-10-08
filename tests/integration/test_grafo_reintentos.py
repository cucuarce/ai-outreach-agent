"""T030: reintento acotado del redactor y resultado inválido (FR-011)."""

import json
from dataclasses import replace

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from tests import escenarios as e
from tests.fakes import FakeProvider

LARGO = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Además" * 68)  # 170 palabras
CON_RELLENO = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Quedo a la espera de su respuesta.")


def correr(redacciones, max_reintentos=2):
    config = replace(cargar_config(env={}), max_reintentos=max_reintentos)
    respuestas = [e.INVESTIGADOR, e.ESTRATEGA, *redacciones]
    provider = FakeProvider([json.dumps(r) for r in respuestas])
    resultado = ejecutar(Entrada(e.TEXTO_EMPRESA, e.PERFIL), provider, config)
    return resultado, provider


def llamadas_al_redactor(provider):
    return [ll for ll in provider.llamadas if "agente redactor" in ll["system"]]


def test_falla_y_luego_valido_da_borrador_en_el_segundo_intento():
    resultado, provider = correr([LARGO, e.REDACTOR])

    assert resultado.estado is Estado.BORRADOR
    redactor = llamadas_al_redactor(provider)
    assert len(redactor) == 2
    assert "longitud" in redactor[1]["user"]
    assert "170 palabras" in redactor[1]["user"]
    assert "longitud" not in redactor[0]["user"].split("Longitud:")[0]


def test_tres_fallos_con_dos_reintentos_da_invalido_con_los_fallos_del_ultimo():
    resultado, provider = correr([LARGO, LARGO, CON_RELLENO], max_reintentos=2)

    assert resultado.estado is Estado.INVALIDO
    assert resultado.motivo is Motivo.VALIDACION_FALLIDA
    assert [f.criterio for f in resultado.fallos] == ["relleno"]
    assert resultado.borrador is None
    assert len(llamadas_al_redactor(provider)) == 3


def test_sin_reintentos_hay_un_solo_intento():
    resultado, provider = correr([LARGO], max_reintentos=0)

    assert resultado.estado is Estado.INVALIDO
    assert [f.criterio for f in resultado.fallos] == ["longitud"]
    assert len(llamadas_al_redactor(provider)) == 1
