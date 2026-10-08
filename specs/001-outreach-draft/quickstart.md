# Quickstart: validar la funcionalidad de punta a punta

Guía para comprobar que el borrador de outreach funciona. Los formatos están en `contracts/` y el
modelo de datos en `data-model.md`.

## Requisitos

- Python 3.11+
- Para ejecuciones reales y la evaluación: [Ollama](https://ollama.com) instalado y el modelo
  descargado (`ollama pull qwen2.5:7b-instruct`, o el que se configure con `--modelo`).
- No se necesita cuenta de AWS ni credenciales: Bedrock solo se usa contra Moto en los tests.

## Instalación

```powershell
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

## 1. Tests (sin red, sin Ollama)

```powershell
pytest
```

Resultado esperado: todo en verde. Ningún test abre conexiones de red (fixture de
`tests/conftest.py`). Cobertura mínima por requisito:

| Escenario | Dónde se verifica |
|-----------|-------------------|
| Borrador válido con ≥ 2 hechos y ≥ 1 punto de perfil, 80–150 palabras, sin relleno (Historia 1) | `tests/integration/test_grafo_borrador.py` |
| Texto vacío / < 2 datos / perfil vacío / sin conexión (Historia 2) | `tests/integration/test_grafo_insuficiente.py` |
| Instrucciones incrustadas: nonce, saneamiento, filtro, enlaces y canario rechazados (Historia 3) | `tests/integration/test_grafo_inyeccion.py` |
| Registro por ejecución, pasos en orden, motivo de corte (Historia 4) | `tests/integration/test_trazas.py` |
| Reintento acotado y criterio incumplido (FR-011) | `tests/integration/test_grafo_reintentos.py` |
| Idioma solicitado y detectado (FR-018) | `tests/unit/test_idioma.py`, `tests/integration/test_grafo_borrador.py` |
| Forma de la llamada de BedrockProvider bajo `@mock_aws` | `tests/contract/test_bedrock_provider.py` |
| Petición de OllamaProvider (`urlopen` reemplazado con monkeypatch, sin socket) | `tests/contract/test_ollama_provider.py` |
| CLI: flags, códigos de salida, ausencia de envío | `tests/contract/test_cli.py` |

## 2. Ejecución real con Ollama

```powershell
ollama serve            # en otra terminal, si no corre como servicio
outreach generar --empresa ejemplos/empresa_es.txt --perfil ejemplos/perfil.txt
```

Esperado (código 0): borrador de 80–150 palabras en español, lista de datos de la empresa y
puntos del perfil usados con sus citas, y las rutas del registro en `runs/`.

Variantes:

```powershell
# Idioma forzado (FR-018)
outreach generar --empresa ejemplos/empresa_en.txt --perfil ejemplos/perfil.txt --idioma es

# Datos insuficientes (FR-009) → código 3, sin borrador
outreach generar --empresa ejemplos/empresa_vaga.txt --perfil ejemplos/perfil.txt

# Instrucción incrustada (FR-012) → código 0, borrador sin el texto pedido por la instrucción
outreach generar --empresa ejemplos/empresa_inyeccion.txt --perfil ejemplos/perfil.txt

# Otro modelo
outreach generar --empresa ejemplos/empresa_es.txt --perfil ejemplos/perfil.txt --modelo llama3.1:8b
```

Abrir el `runs/<run_id>.md` indicado y comprobar que lista cada paso, si es agente o
verificación, y su decisión.

## 3. Evaluación con modelo real (SC-001 a SC-005, SC-009)

```powershell
python scripts/evaluar.py --modelo qwen2.5:7b-instruct
```

Esperado: reporte en `eval/reportes/` con porcentajes por criterio, la tasa de aprobación en el
primer intento y una sección de borradores para revisión humana. Código 0 si todas las métricas
están al 100%.
