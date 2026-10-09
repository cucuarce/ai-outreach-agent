"""T012: flujo mínimo de punta a punta con FakeProvider (Historia 1, paso A)."""

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from outreach_agent.proveedores.base import ProviderError
from tests import escenarios
from tests.fakes import FakeProvider


def correr(provider):
    entrada = Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL, idioma_solicitado=None)
    return ejecutar(entrada, provider, cargar_config(env={}))


def test_flujo_completo_devuelve_borrador():
    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    resultado = correr(provider)

    assert resultado.estado is Estado.BORRADOR
    assert resultado.borrador.texto == escenarios.TEXTO_BORRADOR
    assert [h.id for h in resultado.hechos_usados] == ["H1", "H2"]
    assert resultado.hechos_usados[0].cita == "procesa 2 millones de transacciones al mes"
    assert [p.id for p in resultado.puntos_usados] == ["P1", "P2"]
    assert resultado.puntos_usados[0].cita.startswith("lideré la migración")
    assert resultado.run_id


def test_tres_llamadas_en_orden_investigador_estratega_redactor():
    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    correr(provider)

    assert len(provider.llamadas) == 3
    roles = ["investigador", "estratega", "redactor"]
    for llamada, rol in zip(provider.llamadas, roles):
        assert f"agente {rol}" in llamada["system"]
        assert llamada["json"] is True


def test_texto_de_empresa_nunca_va_en_system():
    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    correr(provider)

    assert escenarios.TEXTO_EMPRESA in provider.llamadas[0]["user"]
    for llamada in provider.llamadas:
        assert escenarios.TEXTO_EMPRESA not in llamada["system"]
        assert escenarios.ORACION_FUERA_DE_CITAS not in llamada["system"]


def test_cada_agente_usa_su_max_tokens():
    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    correr(provider)

    assert [llamada["max_tokens"] for llamada in provider.llamadas] == [2000, 1200, 800]


def test_error_del_proveedor_termina_en_estado_error():
    provider = FakeProvider([ProviderError("Ollama caído")])
    resultado = correr(provider)

    assert resultado.estado is Estado.ERROR
    assert resultado.motivo is Motivo.PROVEEDOR_NO_DISPONIBLE
    assert "Ollama caído" in resultado.detalle
    assert resultado.borrador is None


def test_contexto_excedido_conserva_el_motivo():
    provider = FakeProvider([ProviderError("muy largo", motivo="contexto_excedido")])
    resultado = correr(provider)

    assert resultado.estado is Estado.ERROR
    assert resultado.motivo is Motivo.CONTEXTO_EXCEDIDO


def test_json_invalido_dos_veces_termina_en_respuesta_invalida():
    provider = FakeProvider(["no es json", "tampoco"])
    resultado = correr(provider)

    assert resultado.estado is Estado.ERROR
    assert resultado.motivo is Motivo.RESPUESTA_INVALIDA_LLM


def test_temperatura_del_redactor_llega_al_proveedor():
    from dataclasses import replace

    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    correr(provider)
    assert provider.llamadas[2]["temperatura"] == 0.3  # default

    provider = FakeProvider(escenarios.respuestas_flujo_valido())
    config = replace(cargar_config(env={}), temperatura_redactor=0.9)
    entrada = Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL)
    ejecutar(entrada, provider, config)
    assert provider.llamadas[2]["temperatura"] == 0.9
