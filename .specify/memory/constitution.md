<!--
Sync Impact Report
- Version change: 2.0.0 → 2.1.0 (MINOR: ampliación material del principio IV)
- Principios modificados:
  - IV. Agrega una excepción acotada: un proveedor compatible con la API de OpenAI (Groq),
    solo en scripts/ para experimentos de evaluación sobre eval/casos, con ocho condiciones:
    solo en scripts/ y sobre eval/casos; nunca desde la CLI ni desde src/; clave solo desde el
    entorno; sección de experimento escrita y commiteada antes de la corrida; resultados junto
    a los de Ollama, sin reemplazarlos; sin casos de eval/validacion; solo plan gratuito, sin
    tarjeta ni gasto; solo contenido anonimizado y perfil ficticio, nunca un perfil real.
    "Dos implementaciones" pasa a "dos implementaciones del sistema, más una excepción
    acotada". BedrockProvider y OllamaProvider no cambian.
- Secciones modificadas: Stack Tecnológico (agrega la excepción), Fuera de Alcance (v1)
  (las APIs de terceros siguen fuera de alcance salvo esa excepción)
- Secciones añadidas: Historial de enmiendas (en Governance)
- Secciones eliminadas: ninguna
- Plantillas dependientes: no modificadas (leen la constitución en tiempo de ejecución)
- TODOs diferidos: ninguno
-->

# AI Outreach Agent Constitution

## Core Principles

### I. Alcance acotado: búsqueda laboral, no ventas

El sistema recibe dos entradas, el texto de una empresa pegado a mano por el usuario y el perfil
del usuario, y produce un mensaje de outreach personalizado para su búsqueda laboral.

- NO es un agente de ventas: MUST NOT enviar emails, prospectar leads ni trackear respuestas.
- MUST NOT hacer scraping ni llamar APIs de terceros para obtener información de la empresa;
  la única fuente es el texto que pega el usuario.
- La interfaz de v1 es CLI o script. MUST NOT incluir UI.

**Rationale**: mantener el sistema pequeño, predecible y alineado con un único caso de uso.

### II. Un agente, una responsabilidad

La v1 es un grafo LangGraph con exactamente tres agentes, cada uno con una responsabilidad única:

- **Investigador**: extrae y organiza la información relevante del texto de la empresa.
- **Estratega**: define el enfoque del mensaje cruzando la investigación con el perfil del usuario.
- **Redactor**: escribe el mensaje final según la estrategia.

Un agente MUST NOT asumir la responsabilidad de otro. Agregar, fusionar o dividir agentes requiere
enmendar esta constitución.

### III. El sistema nunca envía

La salida del sistema es texto para revisión humana. El usuario revisa el mensaje y lo envía
manualmente. Ningún componente MUST tener capacidad de enviar mensajes (sin clientes SMTP, APIs
de mensajería ni integraciones de envío).

### IV. Proveedor de LLM detrás de una interfaz, sin costo de AWS

El sistema accede al LLM exclusivamente a través de una interfaz de proveedor. Los agentes MUST
depender de esa interfaz y MUST NOT depender de un proveedor concreto. Hay dos implementaciones
del sistema, más una excepción acotada:

- **BedrockProvider**: boto3 + Bedrock Runtime vía `invoke_model`. MUST probarse solo con Moto
  (`@mock_aws`). Sus tests validan la forma de la llamada; no genera texto.
- **OllamaProvider**: modelo local gratuito, usado para ejecuciones reales y demos.

**Excepción acotada: proveedor compatible con la API de OpenAI (Groq).** Se permite una tercera
implementación de la interfaz, que llama a una API compatible con la de OpenAI (Groq), solo si se
cumplen todas estas condiciones:

1. MUST vivir solo en `scripts/` y usarse solo para experimentos de evaluación sobre
   `eval/casos`.
2. MUST NOT estar disponible desde la CLI ni desde `src/`: ningún módulo del paquete la importa
   ni la referencia.
3. La clave MUST leerse solo del entorno. MUST NOT aparecer en flags, archivos de configuración,
   trazas, reportes ni mensajes de error.
4. Cada uso MUST tener antes una sección de experimento en `research.md` de la feature, con
   objetivo, predicciones y regla de lectura, escrita y commiteada antes de la corrida.
5. Sus resultados MUST reportarse siempre junto a los de Ollama y MUST NOT reemplazarlos.
6. MUST NOT enviarse a ese proveedor los casos de `eval/validacion`.
7. MUST usarse solo con el plan gratuito del proveedor, sin tarjeta cargada ni gasto.
8. MUST enviarse solo contenido anonimizado de `eval/casos` y un perfil ficticio de prueba;
   MUST NOT enviarse un perfil real.

MUST NOT usarse una cuenta real de AWS, ni en desarrollo, ni en tests, ni en ejecuciones reales.
Los tests de los agentes MUST inyectar respuestas de prueba en la interfaz del proveedor; no
invocan Bedrock ni Ollama.

**Rationale**: es una decisión de costo, documentada como tal. No es una limitación técnica ni
un juicio sobre la calidad de Bedrock. Ollama permite ejecuciones reales sin costo, y la interfaz
mantiene a los agentes independientes del proveedor. La excepción de Groq existe para separar
el efecto del modelo del efecto del diseño en experimentos puntuales; no es un proveedor del
sistema, y por eso queda fuera de la CLI y de `src/`.

### V. Tests sin red y trazas estructuradas

- Los tests usan pytest y MUST NOT realizar llamadas de red reales.
- Cada transición de nodo del grafo MUST registrarse como una traza estructurada.

### VI. Contenido externo como datos, nunca como instrucciones

El texto de la empresa es contenido externo no confiable. MUST tratarse como datos de entrada en
todos los agentes y MUST NOT interpretarse como instrucciones (mitigación de prompt injection).

## Stack Tecnológico

- Lenguaje: Python.
- Orquestación de agentes: LangGraph.
- Acceso al LLM: interfaz de proveedor con dos implementaciones del sistema, más una excepción
  acotada:
  - AWS Bedrock Runtime vía boto3 (`invoke_model`), solo contra Moto.
  - Ollama (modelo local gratuito) para ejecuciones reales y demos.
  - Excepción: un proveedor compatible con la API de OpenAI (Groq), solo en `scripts/` para
    experimentos de evaluación, con las condiciones del principio IV.
- Simulación de AWS: Moto (`@mock_aws`).
- Testing: pytest.

Cambiar cualquier componente de este stack requiere enmendar esta constitución.

## Fuera de Alcance (v1)

- Envío de mensajes, prospección de leads y seguimiento de respuestas.
- Scraping web y APIs de terceros, salvo la excepción de Groq del principio IV.
- Interfaz gráfica o web.
- Uso de una cuenta real de AWS, en cualquier contexto.
- Generación de texto con Bedrock: BedrockProvider solo se valida contra Moto.
- Llamadas a Bedrock u Ollama desde los tests de los agentes.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del proyecto. Las specs, planes y tareas
generados con Spec Kit MUST verificar su cumplimiento; cualquier desviación MUST justificarse
explícitamente o resolverse enmendando la constitución.

- **Enmiendas**: se documentan en este archivo, actualizando versión y fecha de última enmienda.
- **Versionado** (semver):
  - MAJOR: eliminación o redefinición incompatible de un principio.
  - MINOR: principio o sección nueva, o ampliación material de una guía existente.
  - PATCH: aclaraciones y correcciones de redacción sin cambio semántico.

### Historial de enmiendas

- **2.1.0** (2026-10-17): excepción acotada en el principio IV y en el Stack para un proveedor
  compatible con la API de OpenAI (Groq), con ocho condiciones: solo en `scripts/` y solo para
  experimentos sobre `eval/casos`; nunca desde la CLI ni desde `src/`; clave solo desde el
  entorno; sección de experimento escrita y commiteada antes de cada corrida; resultados siempre
  junto a los de Ollama, sin reemplazarlos; sin casos de `eval/validacion`; solo plan gratuito,
  sin tarjeta ni gasto; solo contenido anonimizado y perfil ficticio, nunca un perfil real.
  Motivo: en la spec 002, la validación dio 1 de 6 válidos con borrador entregado y todos los
  `invalido` fallaron por longitud; hace falta saber si qwen2.5:7b es el cuello de botella.
  Referencia: sección "Experimento de modelo (Groq)" de `specs/002-calidad-redactor/research.md`.
- **2.0.0** (2026-10-07): redefinición del principio IV ("Costo cero: solo Moto, nunca AWS
  real" → "Proveedor de LLM detrás de una interfaz, sin costo de AWS").

**Version**: 2.1.0 | **Ratified**: 2026-10-07 | **Last Amended**: 2026-10-17
