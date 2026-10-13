"""T029: escenarios de la Historia 1 sobre el grafo completo, con FakeProvider."""

import copy
import json
from dataclasses import replace

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from outreach_agent.proveedores.base import ProviderError
from outreach_agent.verificacion.idioma import detectar_idioma
from outreach_agent.verificacion.relleno import encontrar_relleno
from outreach_agent.verificacion.texto import contar_palabras, contiene_ancla, contiene_literal
from tests import escenarios as e
from tests.fakes import FakeProvider


def correr(respuestas, texto=e.TEXTO_EMPRESA, idioma=None, max_reintentos=None):
    config = cargar_config(env={})
    if max_reintentos is not None:
        config = replace(config, max_reintentos=max_reintentos)
    provider = FakeProvider([r if isinstance(r, str) else json.dumps(r) for r in respuestas])
    resultado = ejecutar(Entrada(texto, e.PERFIL, idioma), provider, config)
    return resultado, provider


def test_borrador_cumple_los_criterios_de_la_historia_1():
    resultado, _ = correr(e.respuestas_flujo_valido())
    texto = resultado.borrador.texto

    assert resultado.estado is Estado.BORRADOR
    # Escenario 1: ≥ 2 datos de la empresa localizables en el texto de la empresa
    assert len(resultado.hechos_usados) >= 2
    for hecho in resultado.hechos_usados:
        assert contiene_literal(e.TEXTO_EMPRESA, hecho.cita)
        assert contiene_ancla(texto, hecho.ancla)
    # Escenario 2: ≥ 1 punto del perfil localizable y reconocible en el borrador
    assert resultado.puntos_usados
    for punto in resultado.puntos_usados:
        assert contiene_literal(e.PERFIL, punto.cita)
        assert contiene_ancla(texto, punto.ancla)
    # Escenarios 3 y 4: longitud y relleno
    assert 80 <= contar_palabras(texto) <= 150
    assert encontrar_relleno(texto) == []
    # Escenario 6: el resultado trae los datos y puntos usados, con citas
    assert all(h.cita for h in resultado.hechos_usados)
    assert all(p.cita for p in resultado.puntos_usados)


def test_empresa_en_ingles_sin_idioma_da_borrador_en_ingles():
    resultado, _ = correr(
        [e.INVESTIGADOR_EN, e.ESTRATEGA, e.REDACTOR_EN], texto=e.TEXTO_EMPRESA_EN
    )
    assert resultado.estado is Estado.BORRADOR
    assert resultado.idioma == "en"
    assert detectar_idioma(resultado.borrador.texto) == "en"


def test_empresa_en_ingles_con_idioma_es_da_borrador_en_espanol():
    # El borrador en español conserva las anclas sin traducir ("2", "Kubernetes").
    resultado, provider = correr(
        [e.INVESTIGADOR_EN, e.ESTRATEGA, e.REDACTOR], texto=e.TEXTO_EMPRESA_EN, idioma="es"
    )
    assert resultado.estado is Estado.BORRADOR
    assert resultado.idioma == "es"
    assert "español" in provider.llamadas[2]["user"]


def test_borrador_en_otro_idioma_que_el_pedido_falla_por_idioma():
    resultado, _ = correr(
        [e.INVESTIGADOR_EN, e.ESTRATEGA, e.REDACTOR_EN],
        texto=e.TEXTO_EMPRESA_EN,
        idioma="es",
        max_reintentos=0,
    )
    assert resultado.estado is Estado.INVALIDO
    assert [f.criterio for f in resultado.fallos] == ["idioma"]


def test_punto_declarado_sin_su_ancla_falla_por_perfil():
    # P3 tiene ancla "Go", que no aparece en el borrador.
    estrategia = copy.deepcopy(e.ESTRATEGA)
    estrategia["puntos_perfil"] = [
        {
            "id": "P3",
            "descripcion": "Experiencia en Python y Go",
            "cita": "5 años de experiencia en Python y Go",
            "ancla": "Go",
        }
    ]
    estrategia["conexiones"] = [{"hecho_id": "H2", "punto_id": "P3", "razon": "Backend."}]
    redactor = dict(e.REDACTOR, puntos_usados=["P3"])

    resultado, _ = correr([e.INVESTIGADOR, estrategia, redactor], max_reintentos=0)

    assert resultado.estado is Estado.INVALIDO
    assert resultado.motivo is Motivo.VALIDACION_FALLIDA
    assert [f.criterio for f in resultado.fallos] == ["perfil"]
    assert 'P3 (ancla "Go")' in resultado.fallos[0].detalle


def test_texto_largo_llega_completo_y_se_verifican_datos_del_principio_y_del_final():
    resultado, provider = correr(
        [e.INVESTIGADOR_LARGO, e.ESTRATEGA_LARGO, e.REDACTOR_LARGO], texto=e.TEXTO_EMPRESA_LARGO
    )
    assert len(e.TEXTO_EMPRESA_LARGO) > 40_000
    assert e.TEXTO_EMPRESA_LARGO in provider.llamadas[0]["user"]
    assert resultado.estado is Estado.BORRADOR
    assert [h.id for h in resultado.hechos_usados] == ["H1", "H2"]


def test_estratega_y_redactor_no_reciben_texto_crudo_ni_descripciones():
    _, provider = correr(e.respuestas_flujo_valido())
    descripciones = [h["descripcion"] for h in e.INVESTIGADOR["hechos"]]
    for llamada in provider.llamadas[1:]:
        contenido = llamada["system"] + llamada["user"]
        assert e.ORACION_FUERA_DE_CITAS not in contenido
        for descripcion in descripciones:
            assert descripcion not in contenido


def test_idioma_indeterminado_sin_idioma_pedido_corta_antes_de_los_agentes():
    resultado, provider = correr([], texto="Kubernetes Python Go")
    assert resultado.estado is Estado.INSUFICIENTE
    assert resultado.motivo is Motivo.IDIOMA_INDETERMINADO
    assert "--idioma" in resultado.detalle
    assert provider.llamadas == []


def test_idioma_indeterminado_con_idioma_pedido_continua():
    config = cargar_config(env={})
    provider = FakeProvider([ProviderError("fin de la prueba")])
    resultado = ejecutar(Entrada("Kubernetes Python Go", e.PERFIL, "es"), provider, config)
    # Llegó al investigador: no cortó por idioma.
    assert len(provider.llamadas) == 1
    assert "agente investigador" in provider.llamadas[0]["system"]
    assert resultado.motivo is Motivo.PROVEEDOR_NO_DISPONIBLE


def test_el_redactor_no_recibe_la_razon_de_las_conexiones():
    _, provider = correr(e.respuestas_flujo_valido())
    razones = [c["razon"] for c in e.ESTRATEGA["conexiones"]]
    llamadas_redactor = [ll for ll in provider.llamadas if "agente redactor" in ll["system"]]
    assert llamadas_redactor
    for llamada in llamadas_redactor:
        contenido = llamada["system"] + llamada["user"]
        assert '"razon"' not in contenido
        for razon in razones:
            assert razon not in contenido
