import pytest

from outreach_agent.agentes.base import RespuestaInvalidaLLM, llamar_json
from outreach_agent.proveedores.base import ProviderError
from tests.fakes import FakeProvider


def exigir_hechos(datos: dict) -> None:
    if not isinstance(datos.get("hechos"), list):
        raise ValueError("falta la lista 'hechos'")


def llamar(provider, max_tokens=2000):
    return llamar_json(
        provider, "reglas", "datos", exigir_hechos, max_tokens=max_tokens, temperatura=0.2
    )


def test_json_valido():
    provider = FakeProvider(['{"hechos": []}'])
    assert llamar(provider) == {"hechos": []}
    assert len(provider.llamadas) == 1
    assert provider.llamadas[0]["json"] is True


def test_invalido_y_luego_valido_reintenta_con_el_error():
    provider = FakeProvider(["no es json", '{"hechos": [1]}'])
    assert llamar(provider) == {"hechos": [1]}
    assert len(provider.llamadas) == 2
    segundo_user = provider.llamadas[1]["user"]
    assert segundo_user.startswith("datos")
    assert "no era válida" in segundo_user


def test_esquema_incumplido_y_luego_valido():
    provider = FakeProvider(['{"otra": 1}', '{"hechos": []}'])
    assert llamar(provider) == {"hechos": []}
    assert "falta la lista 'hechos'" in provider.llamadas[1]["user"]


def test_invalido_dos_veces_lanza_respuesta_invalida():
    provider = FakeProvider(["[]", '{"otra": 1}'])
    with pytest.raises(RespuestaInvalidaLLM, match="hechos"):
        llamar(provider)
    assert len(provider.llamadas) == 2


def test_max_tokens_llega_sin_cambios_al_proveedor():
    provider = FakeProvider(["roto", '{"hechos": []}'])
    llamar(provider, max_tokens=1234)
    assert [llamada["max_tokens"] for llamada in provider.llamadas] == [1234, 1234]


def test_provider_error_se_propaga_sin_reintentar():
    provider = FakeProvider([ProviderError("caído")])
    with pytest.raises(ProviderError):
        llamar(provider)
    assert len(provider.llamadas) == 1
