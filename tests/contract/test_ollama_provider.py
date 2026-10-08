"""T019: contrato de OllamaProvider (contracts/llm-provider.md), sin red: se reemplaza urlopen."""

import io
import json
import urllib.error
import urllib.request

import pytest

from outreach_agent.proveedores.base import ProviderError
from outreach_agent.proveedores.ollama import OllamaProvider


class RespuestaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@pytest.fixture
def capturar(monkeypatch):
    """Reemplaza urlopen; devuelve la lista de peticiones y permite fijar la respuesta."""
    estado = {"peticiones": [], "respuesta": {"message": {"content": '{"ok": true}'}}}

    def urlopen_falso(peticion, timeout=None):
        estado["peticiones"].append({"peticion": peticion, "timeout": timeout})
        respuesta = estado["respuesta"]
        if isinstance(respuesta, Exception):
            raise respuesta
        return RespuestaFalsa(json.dumps(respuesta).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    return estado


def proveedor(num_ctx=16384):
    return OllamaProvider("qwen2.5:7b-instruct", "http://localhost:11434/", 30.0, num_ctx)


def test_peticion_y_cuerpo(capturar):
    texto = proveedor().generar("reglas", "datos", max_tokens=800, temperatura=0.4, json=True)

    assert texto == '{"ok": true}'
    [enviada] = capturar["peticiones"]
    peticion = enviada["peticion"]
    assert peticion.full_url == "http://localhost:11434/api/chat"
    assert peticion.get_method() == "POST"
    assert enviada["timeout"] == 30.0
    cuerpo = json.loads(peticion.data)
    assert cuerpo == {
        "model": "qwen2.5:7b-instruct",
        "messages": [
            {"role": "system", "content": "reglas"},
            {"role": "user", "content": "datos"},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.4, "num_predict": 800, "num_ctx": 16384},
    }


def test_sin_json_no_envia_format(capturar):
    proveedor().generar("reglas", "datos", max_tokens=100, temperatura=0.0, json=False)
    cuerpo = json.loads(capturar["peticiones"][0]["peticion"].data)
    assert "format" not in cuerpo


def test_control_previo_rechaza_prompt_grande_sin_llamar(capturar):
    # 3.000 caracteres ≈ 1.000 tokens estimados > 85% de 1.000
    with pytest.raises(ProviderError, match="--num-ctx") as error:
        proveedor(1000).generar("", "x" * 3000, max_tokens=10, temperatura=0.0, json=True)
    assert error.value.motivo == "contexto_excedido"
    assert capturar["peticiones"] == []


def test_control_previo_deja_pasar_prompt_que_entra(capturar):
    # 2.400 caracteres ≈ 800 tokens; 800 + 100 ≤ 1.000
    proveedor(1000).generar("", "x" * 2400, max_tokens=100, temperatura=0.0, json=True)
    assert len(capturar["peticiones"]) == 1


def test_control_previo_exige_lugar_para_la_respuesta(capturar):
    # 800 estimados + 300 de respuesta > 1.000
    with pytest.raises(ProviderError) as error:
        proveedor(1000).generar("", "x" * 2400, max_tokens=300, temperatura=0.0, json=True)
    assert error.value.motivo == "contexto_excedido"
    assert capturar["peticiones"] == []


def test_control_posterior_detecta_recorte(capturar):
    capturar["respuesta"] = {"message": {"content": "{}"}, "prompt_eval_count": 950}
    with pytest.raises(ProviderError, match="--num-ctx") as error:
        proveedor(1000).generar("", "corto", max_tokens=10, temperatura=0.0, json=True)
    assert error.value.motivo == "contexto_excedido"


def test_control_posterior_acepta_conteo_bajo_el_margen(capturar):
    capturar["respuesta"] = {"message": {"content": "{}"}, "prompt_eval_count": 900}
    assert proveedor(1000).generar("", "corto", max_tokens=10, temperatura=0.0, json=True) == "{}"


@pytest.mark.parametrize(
    "falla",
    [
        ConnectionRefusedError("rechazada"),
        urllib.error.URLError(ConnectionRefusedError("rechazada")),
    ],
)
def test_ollama_no_disponible(capturar, falla):
    capturar["respuesta"] = falla
    with pytest.raises(ProviderError) as error:
        proveedor().generar("reglas", "datos", max_tokens=10, temperatura=0.0, json=True)
    mensaje = str(error.value)
    assert "ollama serve" in mensaje
    assert "ollama pull qwen2.5:7b-instruct" in mensaje
    assert error.value.motivo == "proveedor_no_disponible"


@pytest.mark.parametrize(
    "falla", [TimeoutError("timed out"), urllib.error.URLError(TimeoutError("timed out"))]
)
def test_timeout_no_se_confunde_con_ollama_caido(capturar, falla):
    capturar["respuesta"] = falla
    with pytest.raises(ProviderError) as error:
        proveedor().generar("reglas", "datos", max_tokens=10, temperatura=0.0, json=True)
    mensaje = str(error.value)
    assert "no respondió en 30 s" in mensaje
    assert "--timeout" in mensaje
    assert "ollama serve" not in mensaje


def test_respuesta_vacia_es_error(capturar):
    capturar["respuesta"] = {"message": {"content": "  "}}
    with pytest.raises(ProviderError, match="vacía"):
        proveedor().generar("reglas", "datos", max_tokens=10, temperatura=0.0, json=True)
