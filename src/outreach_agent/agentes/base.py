"""Llamada a un agente con salida JSON y un reintento ante respuesta inválida
(contracts/agent-outputs.md)."""

import json
from collections.abc import Callable

from outreach_agent.proveedores.base import LLMProvider


class RespuestaInvalidaLLM(Exception):
    """El LLM no devolvió un JSON válido para el esquema, ni siquiera tras un reintento."""


def exigir_texto(objeto: dict, campo: str, donde: str) -> str:
    valor = objeto.get(campo)
    if not isinstance(valor, str):
        raise ValueError(f"'{campo}' en {donde} debe ser un texto")
    return valor


def exigir_lista(objeto: dict, campo: str, tipo: type, donde: str) -> list:
    valor = objeto.get(campo)
    if not isinstance(valor, list) or not all(isinstance(x, tipo) for x in valor):
        nombre = "objetos" if tipo is dict else "textos"
        raise ValueError(f"'{campo}' en {donde} debe ser una lista de {nombre}")
    return valor


def llamar_json(
    provider: LLMProvider,
    system: str,
    user: str,
    validar: Callable[[dict], None],
    *,
    max_tokens: int,
    temperatura: float,
) -> dict:
    """Pide un objeto JSON al proveedor y lo valida con `validar`, que lanza ValueError si el
    esquema no se cumple. Ante un fallo reintenta una vez, informando el error en el `user`.
    Los ProviderError se propagan sin reintentar."""
    mensaje_user = user
    for intento in range(2):
        respuesta = provider.generar(
            system, mensaje_user, max_tokens=max_tokens, temperatura=temperatura, json=True
        )
        try:
            datos = json.loads(respuesta)
            if not isinstance(datos, dict):
                raise ValueError("la respuesta debe ser un objeto JSON")
            validar(datos)
            return datos
        except ValueError as error:  # json.JSONDecodeError es un ValueError
            if intento == 1:
                raise RespuestaInvalidaLLM(str(error)) from error
            mensaje_user = (
                f"{user}\n\nTu respuesta anterior no era válida: {error}. "
                "Respondé solo con un objeto JSON que cumpla el esquema indicado."
            )
    raise AssertionError("inalcanzable")
