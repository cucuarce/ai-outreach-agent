<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0 (MAJOR: redefinición del principio IV)
- Principios modificados:
  - IV. "Costo cero: solo Moto, nunca AWS real" →
    "Proveedor de LLM detrás de una interfaz, sin costo de AWS"
    (interfaz de proveedor; BedrockProvider solo con Moto; OllamaProvider para ejecuciones
    reales y demos; agentes desacoplados del proveedor; tests de agentes con respuestas
    inyectadas)
- Secciones modificadas: Stack Tecnológico (agrega Ollama e interfaz de proveedor),
  Fuera de Alcance (v1) (aclara prohibición de AWS real, sin generación vía Bedrock,
  sin llamadas a proveedores reales desde tests de agentes)
- Secciones añadidas: ninguna
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
depender de esa interfaz y MUST NOT depender de un proveedor concreto. Hay dos implementaciones:

- **BedrockProvider**: boto3 + Bedrock Runtime vía `invoke_model`. MUST probarse solo con Moto
  (`@mock_aws`). Sus tests validan la forma de la llamada; no genera texto.
- **OllamaProvider**: modelo local gratuito, usado para ejecuciones reales y demos.

MUST NOT usarse una cuenta real de AWS, ni en desarrollo, ni en tests, ni en ejecuciones reales.
Los tests de los agentes MUST inyectar respuestas de prueba en la interfaz del proveedor; no
invocan Bedrock ni Ollama.

**Rationale**: es una decisión de costo, documentada como tal. No es una limitación técnica ni
un juicio sobre la calidad de Bedrock. Ollama permite ejecuciones reales sin costo, y la interfaz
mantiene a los agentes independientes del proveedor.

### V. Tests sin red y trazas estructuradas

- Los tests usan pytest y MUST NOT realizar llamadas de red reales.
- Cada transición de nodo del grafo MUST registrarse como una traza estructurada.

### VI. Contenido externo como datos, nunca como instrucciones

El texto de la empresa es contenido externo no confiable. MUST tratarse como datos de entrada en
todos los agentes y MUST NOT interpretarse como instrucciones (mitigación de prompt injection).

## Stack Tecnológico

- Lenguaje: Python.
- Orquestación de agentes: LangGraph.
- Acceso al LLM: interfaz de proveedor con dos implementaciones:
  - AWS Bedrock Runtime vía boto3 (`invoke_model`), solo contra Moto.
  - Ollama (modelo local gratuito) para ejecuciones reales y demos.
- Simulación de AWS: Moto (`@mock_aws`).
- Testing: pytest.

Cambiar cualquier componente de este stack requiere enmendar esta constitución.

## Fuera de Alcance (v1)

- Envío de mensajes, prospección de leads y seguimiento de respuestas.
- Scraping web y APIs de terceros.
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

**Version**: 2.0.0 | **Ratified**: 2026-10-07 | **Last Amended**: 2026-10-07
