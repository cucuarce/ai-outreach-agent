# Contrato: interfaz de proveedor de LLM

```python
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
    ) -> str: ...

class ProviderError(Exception):
    """Fallo del proveedor: red, timeout, respuesta vacía o mal formada, contexto excedido."""
    motivo: str  # "proveedor_no_disponible" (default) | "contexto_excedido"
```

## Reglas comunes

- `system` contiene solo reglas; `user` contiene solo datos (research R3). Ningún agente pasa
  datos de la empresa en `system`.
- Devuelve el texto generado. Si `json=True`, el texto debe ser un objeto JSON; el parseo y la
  validación del esquema los hace el agente.
- Cualquier fallo se reporta como `ProviderError`; nunca devuelve una cadena vacía.
- Los agentes reciben un `LLMProvider` por inyección y no importan ninguna implementación
  concreta (principio IV). Un test verifica esto inspeccionando los imports de `agentes/`.

## OllamaProvider

- Constructor: `OllamaProvider(modelo: str, host: str, timeout_s: float, num_ctx: int)`.
- Petición: `POST {host}/api/chat`, cuerpo:
  `{"model": modelo, "messages": [{"role":"system","content":system},{"role":"user","content":user}],
  "stream": false, "format": "json" (solo si json=True), "options": {"temperature": temperatura,
  "num_predict": max_tokens, "num_ctx": num_ctx}}`.
- **Control previo**: antes de enviar, se calcula `estimado = self._estimar_tokens(system, user)`
  (= `(len(system) + len(user)) / 3`). Si `estimado > 0,85 × num_ctx` o
  `estimado + max_tokens > num_ctx`, no se hace la petición y se lanza `ProviderError` con
  motivo `contexto_excedido` y un mensaje que sugiere subir `--num-ctx` (research R4).
- **Control posterior**: si la respuesta trae `prompt_eval_count ≥ 0,95 × num_ctx`, se asume que
  Ollama recortó el prompt → el mismo `ProviderError` con motivo `contexto_excedido`.
- Respuesta: `message.content`. Conexión rechazada → `ProviderError` con un mensaje que indica
  iniciar Ollama (`ollama serve`) y descargar el modelo (`ollama pull <modelo>`).

## BedrockProvider

- Constructor: `BedrockProvider(model_id: str, region: str, client=None)`. Sin valor por defecto
  para `model_id`.
- Llamada: `client.invoke_model(modelId=model_id, contentType="application/json",
  accept="application/json", body=json.dumps(cuerpo))` con
  `cuerpo = {"anthropic_version": "bedrock-2023-05-31", "system": system, "messages":
  [{"role": "user", "content": user}], "max_tokens": max_tokens, "temperature": temperatura}`.
- Respuesta: concatenación de `content[*].text` del cuerpo. Cuerpo vacío o sin `content` →
  `ProviderError`.
- Solo se usa en tests bajo `@mock_aws` (principio IV). Los tests verifican: el `modelId`, los
  headers, que el cuerpo sea JSON válido con los campos anteriores y que la respuesta vacía de
  Moto produzca `ProviderError`.

## FakeProvider (tests)

- `FakeProvider(respuestas: list[str | Exception])`: devuelve (o lanza) en orden; si se agotan,
  falla el test.
- `llamadas: list[dict]`: registra `system`, `user`, `json` de cada llamada para aserciones sobre
  los prompts (por ejemplo, que el redactor nunca reciba el texto crudo de la empresa).
