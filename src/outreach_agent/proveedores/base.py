"""Interfaz de proveedor de LLM (contracts/llm-provider.md).

Los agentes dependen solo de esta interfaz, nunca de una implementación concreta
(principio IV de la constitución).
"""

from typing import Protocol


class LLMProvider(Protocol):
    nombre: str  # "ollama", "bedrock", "fake"; se registra en la traza

    def generar(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperatura: float,
        json: bool,
    ) -> str:
        """Devuelve el texto generado. Nunca devuelve una cadena vacía: ante un fallo
        lanza ProviderError."""
        ...


class ProviderError(Exception):
    """Fallo del proveedor: red, timeout, respuesta vacía o mal formada, contexto excedido."""

    def __init__(self, mensaje: str, motivo: str = "proveedor_no_disponible"):
        super().__init__(mensaje)
        self.motivo = motivo  # "proveedor_no_disponible" | "contexto_excedido"
