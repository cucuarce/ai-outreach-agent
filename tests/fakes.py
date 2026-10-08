"""Proveedor de LLM con respuestas programadas, para tests sin red (contracts/llm-provider.md)."""


class FakeProvider:
    nombre = "fake"

    def __init__(self, respuestas: list[str | Exception]):
        self._respuestas = list(respuestas)
        self.llamadas: list[dict] = []

    def generar(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperatura: float,
        json: bool,
    ) -> str:
        self.llamadas.append(
            {
                "system": system,
                "user": user,
                "json": json,
                "max_tokens": max_tokens,
                "temperatura": temperatura,
            }
        )
        if not self._respuestas:
            raise AssertionError(
                f"FakeProvider sin respuestas programadas (llamada n.º {len(self.llamadas)})"
            )
        respuesta = self._respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta
