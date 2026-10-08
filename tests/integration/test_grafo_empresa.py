"""T033a: nombre de la empresa (FR-019, research R12), con FakeProvider."""

import json
from dataclasses import replace

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from tests import escenarios as e
from tests.fakes import FakeProvider

ORDEN_SIN_NOMBRE = "no nombres a ninguna empresa como destinataria"
DIRIGIDO_A_PAGOSUR = e.TEXTO_BORRADOR.replace("Hola, equipo de Nubeluz.", "Hola, equipo de Pagosur.")


def correr(investigador, redactor=e.REDACTOR, nombre_solicitado=None, max_reintentos=None):
    config = cargar_config(env={})
    if max_reintentos is not None:
        config = replace(config, max_reintentos=max_reintentos)
    respuestas = [investigador, e.ESTRATEGA, redactor]
    provider = FakeProvider([json.dumps(r) for r in respuestas])
    entrada = Entrada(e.TEXTO_EMPRESA, e.PERFIL, nombre_empresa_solicitado=nombre_solicitado)
    return ejecutar(entrada, provider, config), provider


def user_del_redactor(provider):
    return next(ll["user"] for ll in provider.llamadas if "agente redactor" in ll["system"])


def con_nombre(nombre):
    return dict(e.INVESTIGADOR, nombre_empresa=nombre)


def test_nombre_verificado_llega_al_redactor_y_al_resultado():
    resultado, provider = correr(con_nombre("Nubeluz"))

    assert resultado.estado is Estado.BORRADOR
    assert resultado.nombre_empresa == "Nubeluz"
    assert resultado.origen_nombre_empresa == "texto"
    user = user_del_redactor(provider)
    assert "dirigido a Nubeluz" in user
    assert ORDEN_SIN_NOMBRE not in user


def test_caso_granix_borrador_dirigido_a_otra_empresa_falla_por_empresa():
    redactor = dict(e.REDACTOR, texto=DIRIGIDO_A_PAGOSUR)
    resultado, _ = correr(con_nombre("Nubeluz"), redactor=redactor, max_reintentos=0)

    assert resultado.estado is Estado.INVALIDO
    assert resultado.motivo is Motivo.VALIDACION_FALLIDA
    assert [f.criterio for f in resultado.fallos] == ["empresa"]
    assert '"Nubeluz"' in resultado.fallos[0].detalle


def test_nombre_no_literal_se_descarta_y_se_pide_no_nombrar_empresa():
    redactor = dict(e.REDACTOR, texto=DIRIGIDO_A_PAGOSUR)  # el criterio empresa no aplica
    resultado, provider = correr(con_nombre("Nube Luz SA"), redactor=redactor)

    assert resultado.estado is Estado.BORRADOR
    assert resultado.nombre_empresa is None
    assert resultado.origen_nombre_empresa is None
    assert ORDEN_SIN_NOMBRE in user_del_redactor(provider)


def test_nombre_null_se_comporta_igual_sin_descarte():
    resultado, provider = correr(con_nombre(None))

    assert resultado.estado is Estado.BORRADOR
    assert resultado.nombre_empresa is None
    assert ORDEN_SIN_NOMBRE in user_del_redactor(provider)


def test_nombre_del_usuario_tiene_prioridad():
    # El investigador dice "Nubeluz"; el usuario indica "Campo Claro".
    texto = e.TEXTO_BORRADOR.replace("Hola, equipo de Nubeluz.", "Hola, equipo de Campo Claro.")
    resultado, provider = correr(
        con_nombre("Nubeluz"), redactor=dict(e.REDACTOR, texto=texto), nombre_solicitado="Campo Claro"
    )

    assert resultado.estado is Estado.BORRADOR
    assert resultado.nombre_empresa == "Campo Claro"
    assert resultado.origen_nombre_empresa == "usuario"
    assert "dirigido a Campo Claro" in user_del_redactor(provider)


def test_nombre_del_usuario_se_exige_en_el_borrador():
    resultado, _ = correr(con_nombre("Nubeluz"), nombre_solicitado="Campo Claro", max_reintentos=0)

    assert resultado.estado is Estado.INVALIDO
    assert [f.criterio for f in resultado.fallos] == ["empresa"]
    assert '"Campo Claro"' in resultado.fallos[0].detalle
