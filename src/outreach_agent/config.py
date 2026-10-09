"""Configuración con precedencia flag > variable de entorno > default (research R9)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# campo de Config -> (atributo del flag en argparse o None, variable de entorno, default, tipo)
_PARAMETROS = {
    "modelo": ("modelo", "OUTREACH_OLLAMA_MODEL", "qwen2.5:7b", str),
    "ollama_host": ("ollama_host", "OLLAMA_HOST", "http://localhost:11434", str),
    "timeout_s": ("timeout", "OUTREACH_TIMEOUT_S", 180.0, float),
    "num_ctx": ("num_ctx", "OUTREACH_OLLAMA_NUM_CTX", 16384, int),
    "max_reintentos": ("reintentos", "OUTREACH_MAX_REINTENTOS", 2, int),
    "dir_registros": ("registros", "OUTREACH_RUNS_DIR", Path("runs"), Path),
    "temperatura_redactor": ("temp_redactor", "OUTREACH_TEMP_REDACTOR", 0.3, float),
    # Los max_tokens por agente solo se configuran por variable de entorno, sin flag.
    "max_tokens_investigador": (None, "OUTREACH_MAX_TOKENS_INVESTIGADOR", 2000, int),
    "max_tokens_estratega": (None, "OUTREACH_MAX_TOKENS_ESTRATEGA", 1200, int),
    "max_tokens_redactor": (None, "OUTREACH_MAX_TOKENS_REDACTOR", 800, int),
}


@dataclass(frozen=True)
class Config:
    modelo: str
    ollama_host: str
    timeout_s: float
    num_ctx: int
    max_reintentos: int
    dir_registros: Path
    temperatura_redactor: float
    max_tokens_investigador: int
    max_tokens_estratega: int
    max_tokens_redactor: int


def cargar_config(args=None, env: Mapping[str, str] | None = None) -> Config:
    """Arma la configuración. `args` es el Namespace de argparse (o None); un flag con valor
    None se considera no indicado. `env` por defecto es `os.environ`."""
    env = os.environ if env is None else env
    valores = {}
    for campo, (flag, variable, default, tipo) in _PARAMETROS.items():
        valor_flag = getattr(args, flag, None) if (args is not None and flag) else None
        if valor_flag is not None:
            valores[campo] = tipo(valor_flag)
        elif env.get(variable):
            try:
                valores[campo] = tipo(env[variable])
            except ValueError:
                raise ValueError(
                    f"Valor inválido en la variable de entorno {variable}: {env[variable]!r}"
                ) from None
        else:
            valores[campo] = default
    return Config(**valores)
