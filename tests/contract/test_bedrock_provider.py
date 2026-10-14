"""T053: contrato de BedrockProvider (contracts/llm-provider.md), solo bajo Moto (principio IV).

Moto no genera texto: responde `{}` a `invoke_model`. Los tests capturan la petición que arma
boto3 y verifican su forma; la respuesta vacía de Moto debe terminar en ProviderError.
"""

import json
from urllib.parse import unquote

import boto3
import pytest
from moto import mock_aws

from outreach_agent.proveedores.base import ProviderError
from outreach_agent.proveedores.bedrock import BedrockProvider

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
REGION = "us-east-1"


@pytest.fixture
def cliente():
    with mock_aws():
        yield boto3.client("bedrock-runtime", region_name=REGION)


@pytest.fixture
def capturadas(cliente):
    """Registra cada petición InvokeModel tal como la serializa boto3, antes de enviarla."""
    peticiones: list[dict] = []

    def capturar(params, **kwargs):
        peticiones.append(params)

    cliente.meta.events.register("before-call.bedrock-runtime.InvokeModel", capturar)
    return peticiones


def generar(provider, **extra):
    argumentos = {"max_tokens": 512, "temperatura": 0.2, "json": True, **extra}
    return provider.generar("reglas del sistema", "datos del usuario", **argumentos)


def test_la_peticion_tiene_model_id_headers_y_cuerpo_del_contrato(cliente, capturadas):
    provider = BedrockProvider(MODEL_ID, REGION, client=cliente)

    with pytest.raises(ProviderError):  # Moto responde {}: sin texto generado
        generar(provider)

    [peticion] = capturadas
    assert unquote(peticion["url_path"]) == f"/model/{MODEL_ID}/invoke"
    assert peticion["headers"]["Content-Type"] == "application/json"
    assert peticion["headers"]["Accept"] == "application/json"
    cuerpo = json.loads(peticion["body"])
    assert cuerpo == {
        "anthropic_version": "bedrock-2023-05-31",
        "system": "reglas del sistema",
        "messages": [{"role": "user", "content": "datos del usuario"}],
        "max_tokens": 512,
        "temperature": 0.2,
    }


def test_system_lleva_solo_las_reglas_y_hay_un_unico_mensaje_user(cliente, capturadas):
    provider = BedrockProvider(MODEL_ID, REGION, client=cliente)

    with pytest.raises(ProviderError):
        generar(provider, json=False, max_tokens=64, temperatura=0.0)

    cuerpo = json.loads(capturadas[0]["body"])
    assert [m["role"] for m in cuerpo["messages"]] == ["user"]
    assert "datos del usuario" not in cuerpo["system"]
    assert cuerpo["max_tokens"] == 64
    assert cuerpo["temperature"] == 0.0


def test_respuesta_vacia_de_moto_produce_provider_error(cliente):
    provider = BedrockProvider(MODEL_ID, REGION, client=cliente)

    with pytest.raises(ProviderError) as error:
        generar(provider)
    assert error.value.motivo == "proveedor_no_disponible"


def test_concatena_los_bloques_de_texto_de_content():
    class ClienteFalso:
        def invoke_model(self, **kwargs):
            cuerpo = {"content": [{"type": "text", "text": '{"ok": '}, {"type": "text", "text": "true}"}]}
            return {"body": _Cuerpo(json.dumps(cuerpo).encode("utf-8"))}

    provider = BedrockProvider(MODEL_ID, REGION, client=ClienteFalso())
    assert generar(provider) == '{"ok": true}'


def test_error_del_cliente_produce_provider_error():
    class ClienteQueFalla:
        def invoke_model(self, **kwargs):
            from botocore.exceptions import EndpointConnectionError

            raise EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1")

    provider = BedrockProvider(MODEL_ID, REGION, client=ClienteQueFalla())
    with pytest.raises(ProviderError):
        generar(provider)


def test_el_constructor_exige_model_id():
    with pytest.raises(TypeError):
        BedrockProvider(region=REGION)  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        BedrockProvider("", REGION, client=object())


def test_nombre():
    assert BedrockProvider(MODEL_ID, REGION, client=object()).nombre == "bedrock"


class _Cuerpo:
    def __init__(self, datos: bytes):
        self._datos = datos

    def read(self) -> bytes:
        return self._datos
