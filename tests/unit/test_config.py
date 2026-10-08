from argparse import Namespace
from pathlib import Path

import pytest

from outreach_agent.config import cargar_config

VARIABLES = [
    "OUTREACH_OLLAMA_MODEL",
    "OLLAMA_HOST",
    "OUTREACH_TIMEOUT_S",
    "OUTREACH_OLLAMA_NUM_CTX",
    "OUTREACH_MAX_REINTENTOS",
    "OUTREACH_RUNS_DIR",
    "OUTREACH_MAX_TOKENS_INVESTIGADOR",
    "OUTREACH_MAX_TOKENS_ESTRATEGA",
    "OUTREACH_MAX_TOKENS_REDACTOR",
]


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)


def test_defaults():
    config = cargar_config()
    assert config.modelo == "qwen2.5:7b"
    assert config.ollama_host == "http://localhost:11434"
    assert config.timeout_s == 180.0
    assert config.num_ctx == 16384
    assert config.max_reintentos == 2
    assert config.dir_registros == Path("runs")
    assert config.max_tokens_investigador == 2000
    assert config.max_tokens_estratega == 1200
    assert config.max_tokens_redactor == 800


def test_variable_de_entorno_pisa_default(monkeypatch):
    monkeypatch.setenv("OUTREACH_OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("OUTREACH_OLLAMA_NUM_CTX", "32768")
    monkeypatch.setenv("OUTREACH_MAX_TOKENS_REDACTOR", "600")
    config = cargar_config()
    assert config.modelo == "llama3.1:8b"
    assert config.num_ctx == 32768
    assert config.max_tokens_redactor == 600


def test_flag_pisa_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("OUTREACH_OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("OUTREACH_MAX_REINTENTOS", "5")
    args = Namespace(modelo="mistral:7b", reintentos=0, num_ctx=None, registros="otra")
    config = cargar_config(args)
    assert config.modelo == "mistral:7b"
    assert config.max_reintentos == 0  # 0 es un valor indicado, no "ausente"
    assert config.num_ctx == 16384
    assert config.dir_registros == Path("otra")


def test_env_explicito_no_lee_os_environ(monkeypatch):
    monkeypatch.setenv("OUTREACH_OLLAMA_MODEL", "llama3.1:8b")
    config = cargar_config(env={})
    assert config.modelo == "qwen2.5:7b"


def test_variable_invalida_da_error_claro(monkeypatch):
    monkeypatch.setenv("OUTREACH_OLLAMA_NUM_CTX", "mucho")
    with pytest.raises(ValueError, match="OUTREACH_OLLAMA_NUM_CTX"):
        cargar_config()
