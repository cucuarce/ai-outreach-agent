# Implementation Plan: Borrador de mensaje de outreach personalizado

**Branch**: `001-outreach-draft` | **Date**: 2026-10-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-outreach-draft/spec.md`

## Summary

Un CLI (`outreach generar`) recibe el texto de una empresa y el perfil del usuario y devuelve un
borrador de 80–150 palabras para que el usuario lo revise y envíe por su cuenta. Un grafo
LangGraph encadena tres agentes LLM (investigador → estratega → redactor) con nodos deterministas
de verificación entre ellos y un validador final con reintento acotado del redactor. Los agentes
dependen de una interfaz `LLMProvider`: `OllamaProvider` para ejecuciones reales y
`BedrockProvider` probado solo con Moto. Cada transición de nodo se registra como traza JSONL más
un registro legible en Markdown. Un script de evaluación aparte mide los criterios de éxito con
un modelo real de Ollama. Detalle de decisiones en [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `langgraph`, `boto3` (ejecución); `pytest`, `moto` (desarrollo). Ollama
se consume por HTTP con `urllib` de la biblioteca estándar (research R4).

**Storage**: archivos locales: trazas en `runs/` (JSONL + Markdown); listas de frases de relleno,
patrones de instrucción y stopwords en `src/outreach_agent/data/*.json`.

**Testing**: pytest con `FakeProvider` (respuestas inyectadas), `@mock_aws` para Bedrock y un
fixture que bloquea sockets (research R10).

**Target Platform**: CLI local (Windows, macOS, Linux) con Ollama local.

**Project Type**: CLI de un solo proyecto (paquete Python).

**Performance Goals**: sin metas de rendimiento estrictas; con el modelo por defecto en una
laptop sin GPU dedicada, una ejecución debería terminar en pocos minutos. Timeout por llamada
configurable (default 180 s).

**Constraints**: textos largos sin recorte silencioso (`num_ctx` configurable, default 16384;
research R4); sin cuenta real de AWS; sin red en los tests; sin scraping ni APIs de terceros;
sin envío de mensajes; máximo 3 intentos de redacción por defecto.

**Scale/Scope**: un usuario, una ejecución a la vez; textos de entrada de hasta unas pocas
páginas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cómo lo cumple el diseño | Estado |
|-----------|--------------------------|--------|
| I. Alcance acotado | Entradas solo pegadas por el usuario (archivo o stdin); sin scraping, APIs de terceros, envío, prospección ni UI. | ✅ |
| II. Un agente, una responsabilidad | Exactamente tres agentes LLM con responsabilidades disjuntas (`contracts/agent-outputs.md`). Los cuatro nodos de verificación son deterministas: no llaman al LLM ni deciden contenido, solo verifican y rutean (research R1). | ✅ |
| III. El sistema nunca envía | No hay nodo, flag ni dependencia capaz de enviar. La salida va a stdout y a archivos locales. El CLI termina recordando que el usuario debe revisar y enviar. | ✅ |
| IV. Proveedor detrás de interfaz, sin costo de AWS | Agentes dependen de `LLMProvider` por inyección. `BedrockProvider` solo en tests con `@mock_aws` y no expuesto en el CLI; `OllamaProvider` para ejecuciones reales; tests de agentes con `FakeProvider`. | ✅ |
| V. Tests sin red y trazas estructuradas | Fixture que bloquea sockets en toda la suite; decorador de traza en cada nodo que emite JSONL (`contracts/trace.md`). La evaluación con Ollama es un script aparte, no un test. | ✅ |
| VI. Contenido externo como datos | Defensa en capas a nivel de prompt y de grafo (research R3). | ✅ |
| Stack tecnológico | Python, LangGraph, boto3/Bedrock (vía Moto), Ollama, Moto, pytest. Sin componentes nuevos; Ollama vía `urllib`. | ✅ |

**Re-check post-diseño (Fase 1)**: sin cambios. El contrato del CLI confirma que no hay
subcomando de envío ni selección de Bedrock; el contrato de proveedor y el invariante de
`data-model.md` confirman que estratega y redactor no reciben el texto crudo de la empresa.
No hay violaciones que justificar.

## Diseño

### Grafo

```text
START → preparar_entrada ─(vacío / idioma indeterminado)→ END [insuficiente]
            ↓
        investigador* → verificar_hechos ─(< 2 hechos válidos)→ END [insuficiente]
                              ↓
                          estratega* → verificar_estrategia ─(0 puntos o 0 conexiones)→ END [insuficiente]
                                             ↓
                                         redactor* → validar_borrador ─(ok)→ END [borrador]
                                             ↑              ├─(falla, intento ≤ max)→ redactor*
                                             └──feedback────┘
                                                            └─(falla, intento > max)→ END [invalido]
(* = agente LLM; resto = nodo determinista)
```

### Validación determinista final (FR-011)

`validar_borrador` evalúa siete criterios independientes (longitud, relleno, idioma, hechos,
perfil, números, enlaces) y devuelve todos los incumplidos. Con fallos y reintentos disponibles,
vuelve al redactor con feedback estructurado; agotados (default 2 reintentos = 3 intentos), el
resultado es `invalido` con los criterios del último intento. Reglas exactas en research R2 y R5.

### FR-012: contenido de la empresa como datos

Resumen; la justificación completa está en research R3.

- **Prompt**: reglas solo en `system` y datos solo en `user`; texto de la empresa envuelto en
  delimitadores con un nonce aleatorio por ejecución y saneado de `<<<`/`>>>`; regla explícita de
  no obedecer ni contar instrucciones como hechos y reportarlas en `instrucciones_detectadas`;
  salida JSON con esquema fijo.
- **Grafo**: solo el investigador ve el texto crudo; estratega y redactor ven de cada hecho
  verificado solo `id`, `cita` (≤ 300 caracteres) y `ancla`, nunca la `descripcion`;
  `verificar_hechos` exige citas literales y descarta citas que coinciden con patrones de
  instrucción; el ruteo es determinista; `validar_borrador` rechaza enlaces y emails que no
  vengan del perfil y números que no estén en citas verificadas o en el perfil.
- **Verificación**: pytest cubre las capas deterministas; el comportamiento del modelo real ante
  inyecciones lo mide el script de evaluación con casos de canario (SC-005).

### Evaluación con modelo real

`scripts/evaluar.py` ejecuta el grafo con `OllamaProvider` sobre `eval/casos/*.json` y reporta
SC-001 a SC-005 y SC-009 (`contracts/eval.md`, research R8). Modelo configurable por flag o por
`OUTREACH_OLLAMA_MODEL` (research R9).

## Project Structure

### Documentation (this feature)

```text
specs/001-outreach-draft/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── llm-provider.md
│   ├── agent-outputs.md
│   ├── trace.md
│   └── eval.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
pyproject.toml
src/outreach_agent/
├── __init__.py
├── cli.py                 # argparse, carga de entradas, impresión, códigos de salida
├── config.py              # precedencia flag > env > default (R9)
├── modelos.py             # dataclasses: Hecho, PuntoPerfil, Estrategia, Borrador, Resultado…
├── estado.py              # EstadoGrafo (TypedDict)
├── grafo.py               # construcción del StateGraph y aristas condicionales
├── trazas.py              # decorador trazado(), escritor JSONL y render Markdown
├── agentes/
│   ├── prompts.py         # system prompts y armado de mensajes user
│   ├── investigador.py
│   ├── estratega.py
│   └── redactor.py
├── verificacion/
│   ├── entrada.py         # preparar_entrada: vacíos, idioma, nonce, saneamiento
│   ├── hechos.py          # verificar_hechos: citas, anclas, patrones de instrucción
│   ├── estrategia.py      # verificar_estrategia
│   ├── borrador.py        # validar_borrador: 7 criterios
│   ├── idioma.py          # detector por stopwords (R6)
│   └── texto.py           # normalización, conteo de palabras, URLs, números
├── proveedores/
│   ├── base.py            # LLMProvider, ProviderError
│   ├── ollama.py
│   └── bedrock.py
└── data/
    ├── relleno.json       # frases de ejemplo por idioma (FR-007)
    ├── patrones_instruccion.json
    └── stopwords.json

scripts/evaluar.py
eval/casos/*.json          # dataset de evaluación (versionado)
eval/reportes/             # salida del script (ignorado por git)
ejemplos/                  # entradas de ejemplo para el quickstart
runs/                      # trazas (ignorado por git)

tests/
├── conftest.py            # bloqueo de sockets, fixtures de entradas
├── fakes.py               # FakeProvider
├── unit/                  # texto, idioma, relleno, hechos, estrategia, borrador, trazas, config
├── integration/           # grafo completo con FakeProvider
└── contract/              # CLI, OllamaProvider, BedrockProvider (@mock_aws)
```

**Structure Decision**: proyecto único con layout `src/`. Los agentes (`agentes/`) y las
verificaciones deterministas (`verificacion/`) están en paquetes separados para que la
distinción del principio II sea visible en el código. Los proveedores concretos están aislados en
`proveedores/`, y un test verifica que `agentes/` no los importa.

## Complexity Tracking

No hay violaciones de la constitución que justificar.
