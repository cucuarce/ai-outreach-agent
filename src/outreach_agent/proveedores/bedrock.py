"""Proveedor de LLM para Bedrock Runtime (contracts/llm-provider.md, principio IV).

Solo se usa en tests bajo Moto (`@mock_aws`): nunca contra una cuenta real de AWS, y la CLI no
lo referencia. Bedrock no tiene un modo JSON como Ollama; con `json=True` el agente igual parsea
y valida la respuesta.
"""

import json as jsonlib

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from outreach_agent.proveedores.base import ProviderError

ANTHROPIC_VERSION = "bedrock-2023-05-31"


class BedrockProvider:
    nombre = "bedrock"

    def __init__(self, model_id: str, region: str, client=None):
        if not model_id:
            raise ValueError("BedrockProvider requiere model_id")
        self.model_id = model_id
        self.region = region
        self.client = client or boto3.client("bedrock-runtime", region_name=region)

    def generar(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperatura: float,
        json: bool,
    ) -> str:
        cuerpo = {
            "anthropic_version": ANTHROPIC_VERSION,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperatura,
        }
        try:
            respuesta = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=jsonlib.dumps(cuerpo),
            )
            datos = jsonlib.loads(respuesta["body"].read())
        except (BotoCoreError, ClientError) as error:
            raise ProviderError(f"Bedrock falló al invocar {self.model_id}: {error}") from error
        except ValueError as error:
            raise ProviderError(f"Bedrock devolvió una respuesta que no es JSON: {error}") from error

        bloques = datos.get("content") if isinstance(datos, dict) else None
        texto = "".join(
            b.get("text", "") for b in bloques or [] if isinstance(b, dict)
        )
        if not texto.strip():
            raise ProviderError("Bedrock devolvió una respuesta vacía.")
        return texto
