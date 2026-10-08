"""Proveedor de LLM para Ollama local (contracts/llm-provider.md, research R4).

Usa solo la biblioteca estándar. Detecta prompts que no entran en la ventana de contexto antes
de enviarlos y, después, si Ollama los recortó, para no trabajar con un texto incompleto.
"""

import json as jsonlib
import urllib.error
import urllib.request

from outreach_agent.proveedores.base import ProviderError

FRACCION_MAX_PROMPT = 0.85  # control previo
FRACCION_RECORTE = 0.95  # control posterior


class OllamaProvider:
    nombre = "ollama"

    def __init__(self, modelo: str, host: str, timeout_s: float, num_ctx: int):
        self.modelo = modelo
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s
        self.num_ctx = num_ctx

    def _estimar_tokens(self, system: str, user: str) -> int:
        """Estimación aproximada: 3 caracteres por token."""
        return (len(system) + len(user)) // 3

    def _contexto_excedido(self, detalle: str) -> ProviderError:
        return ProviderError(
            f"El texto no entra en la ventana de contexto del modelo ({detalle}). "
            f"Subí el límite con --num-ctx (actual: {self.num_ctx}) o acortá el texto.",
            motivo="contexto_excedido",
        )

    def generar(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperatura: float,
        json: bool,
    ) -> str:
        estimado = self._estimar_tokens(system, user)
        if estimado > FRACCION_MAX_PROMPT * self.num_ctx or estimado + max_tokens > self.num_ctx:
            raise self._contexto_excedido(
                f"≈{estimado} tokens de entrada + {max_tokens} de respuesta"
            )

        cuerpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": temperatura,
                "num_predict": max_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        if json:
            cuerpo["format"] = "json"
        peticion = urllib.request.Request(
            f"{self.host}/api/chat",
            data=jsonlib.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout_s) as respuesta:
                datos = jsonlib.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detalle = error.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"Ollama respondió {error.code}: {detalle}. Si el modelo no está descargado, "
                f"corré `ollama pull {self.modelo}`."
            ) from error
        except (urllib.error.URLError, OSError) as error:
            if isinstance(error, TimeoutError) or isinstance(
                getattr(error, "reason", None), TimeoutError
            ):
                raise ProviderError(
                    f"Ollama no respondió en {self.timeout_s:g} s. Subí el límite con --timeout, "
                    "bajá --num-ctx o usá un modelo más chico."
                ) from error
            raise ProviderError(
                f"No se pudo conectar con Ollama en {self.host} ({error}). Iniciá Ollama con "
                f"`ollama serve` y descargá el modelo con `ollama pull {self.modelo}`."
            ) from error
        except ValueError as error:
            raise ProviderError(f"Ollama devolvió una respuesta que no es JSON: {error}") from error

        procesados = datos.get("prompt_eval_count")
        if isinstance(procesados, int) and procesados >= FRACCION_RECORTE * self.num_ctx:
            raise self._contexto_excedido(f"Ollama procesó {procesados} tokens de entrada")

        contenido = (datos.get("message") or {}).get("content") or ""
        if not contenido.strip():
            raise ProviderError("Ollama devolvió una respuesta vacía.")
        return contenido
