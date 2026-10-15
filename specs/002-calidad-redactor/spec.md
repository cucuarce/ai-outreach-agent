# Feature Specification: Calidad del borrador tras la línea base R13

**Feature Branch**: `002-calidad-redactor` (directorio de spec; no se creó rama git)

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "Mejora de la calidad del redactor tras la línea base R13
(specs/001-outreach-draft/research.md). Alcance: (a) el investigador no debe extraer ofertas de
empleo genéricas ("We are hiring") como hecho concreto; (b) el borrador debe nombrar a la empresa
cuando se conoce, incluyendo cómo se reintenta cuando el modelo repite el mismo texto; (c) las
conexiones hecho-punto sin relación semántica no deben producir un borrador (caso
insuficiente-04). Fuera de alcance por ahora: truncado de citas largas (valido-03 y valido-05).
Criterios de éxito, definidos antes de implementar: (1) 0 canarios y 0 cifras prohibidas, y 3/3
inyecciones sin prohibidos, como en la línea base; (2) ningún caso insuficiente entrega borrador;
(3) los válidos con borrador entregado mejoran respecto de 0/6 en los 13 casos de desarrollo;
(4) validación única sobre los ids de eval/validacion_ids.json, sin ajustar nada después,
reportando el resultado tal cual. No leas ni abras las ofertas de esos ids hasta la fase de
validación. No incluyas decisiones de implementación en la spec: eso va en el plan."

## Contexto

Esta funcionalidad corrige las causas medidas en la línea base de la evaluación (research R13 de
`specs/001-outreach-draft/`). En esa corrida ninguno de los 6 casos válidos entregó un borrador.
Las causas que entran en este alcance son tres:

- el borrador no nombró a la empresa conocida, ni siquiera cuando el reintento lo pedía de forma
  explícita (valido-01, valido-02 e insuficiente-04);
- una fórmula genérica de búsqueda de personal ("We are hiring") se tomó como dato concreto y
  después se exigió en el borrador (valido-04 y valido-06);
- un texto sin relación con el perfil (insuficiente-04) produjo conexiones que se aceptaron, y el
  caso llegó a redactarse en lugar de terminar sin borrador.

Las reglas de la spec 001 siguen vigentes. Esta spec las precisa y no las reemplaza.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El borrador nombra a la empresa (Priority: P1)

Cuando el sistema conoce el nombre de la empresa, el usuario recibe un borrador que la nombra.
Hoy, cuando el modelo omite el nombre, los reintentos devuelven el mismo texto y la ejecución
termina sin borrador.

**Why this priority**: es la causa más frecuente de la línea base: 7 de los 17 fallos de
validación y 2 de los 6 casos válidos sin borrador. Sin esta corrección, los otros cambios no se
traducen en borradores entregados.

**Independent Test**: con respuestas del modelo grabadas de la línea base (borrador sin el nombre
de la empresa y reintento idéntico), se verifica que la ejecución no termina por esa repetición
mientras queden intentos y que el borrador entregado, si lo hay, nombra a la empresa.

**Acceptance Scenarios**:

1. **Given** un texto de empresa con nombre verificable y un perfil con puntos relacionados,
   **When** el usuario ejecuta el comando, **Then** el borrador entregado menciona el nombre de la
   empresa.
2. **Given** un primer borrador que no nombra a la empresa, **When** el sistema reintenta,
   **Then** el pedido de corrección indica que falta el nombre y cuál es.
3. **Given** un reintento que devuelve el mismo texto que el intento anterior, **When** todavía
   quedan intentos dentro del límite, **Then** el sistema no termina la ejecución por esa
   repetición y el siguiente intento recibe un pedido de corrección distinto del que produjo la
   repetición.
4. **Given** que se agotan los intentos sin un borrador que nombre a la empresa, **When** termina
   la ejecución, **Then** no se entrega borrador y el motivo informado es el criterio incumplido
   (spec 001, FR-011). El registro muestra qué intentos repitieron el texto.

---

### User Story 2 - Una búsqueda de personal genérica no cuenta como dato concreto (Priority: P2)

El usuario pega una oferta de empleo que incluye una fórmula de búsqueda ("We are hiring",
"Estamos buscando una persona"). El sistema no toma esa fórmula como un dato concreto. Cuando
la búsqueda nombra un puesto, un equipo o una tecnología específicos, el dato es ese contenido y
el borrador puede mencionarlo con sus propias palabras.

**Why this priority**: causó la pérdida de 2 de los 6 casos válidos (valido-04 y valido-06). En
valido-06, además, el borrador en español no podía incluir una fórmula en inglés.

**Independent Test**: con la respuesta grabada del investigador en valido-04 (H4 con "We are
hiring"), se verifica que la fórmula genérica no queda como dato concreto exigible en el borrador
y que el contenido específico de la misma oración (puesto, servicio) sí puede usarse.

**Acceptance Scenarios**:

1. **Given** una oración "We are hiring a senior backend engineer to scale our real-time tracking
   service…", **When** se extraen los datos de la empresa, **Then** "We are hiring" no se registra
   como dato concreto. El puesto ("senior backend engineer") o el servicio ("real-time tracking
   service") pueden serlo.
2. **Given** un texto cuya búsqueda de personal no nombra puesto, equipo ni tecnología ("Estamos
   buscando gente con ganas"), **When** se extraen los datos, **Then** esa oración no cuenta como
   dato concreto para el mínimo de dos (spec 001, FR-009).
3. **Given** un puesto con nombre propio en el texto ("Principal QA Automation Engineer", "Sr AI
   Process Builder"), **When** se extraen los datos, **Then** el puesto sigue contando como dato
   concreto.
4. **Given** un borrador en un idioma distinto del texto de la empresa, **When** se valida,
   **Then** no se le exige incluir ninguna fórmula de búsqueda en el idioma original.

---

### User Story 3 - Conexiones sin relación no producen borrador (Priority: P3)

Cuando los datos de la empresa no tienen relación con el perfil del usuario, el sistema informa
que no hay conexión con el perfil en lugar de redactar un mensaje que force la relación (por
ejemplo, comparar "12.000 medialunas por día" con "400 GB por semana").

**Why this priority**: hoy afecta a un caso de desarrollo (insuficiente-04), pero un mensaje con
conexiones forzadas daña la credibilidad del usuario si llega a enviarse.

**Independent Test**: con la estrategia grabada de insuficiente-04, se verifica que las
conexiones sin relación se descartan y que la ejecución termina con el motivo
`sin_conexion_perfil` (spec 001, FR-010), sin borrador.

**Acceptance Scenarios**:

1. **Given** el texto de insuficiente-04 (panificadora) y el perfil de evaluación, **When** el
   usuario ejecuta el comando, **Then** no se entrega borrador y el motivo es que el perfil no se
   conecta con los datos de la empresa.
2. **Given** una conexión cuya única relación es que ambos lados tienen una cifra grande o
   "requieren escalar", **When** se evalúan las conexiones, **Then** la conexión se descarta.
3. **Given** una conexión en la que el punto del perfil muestra experiencia en lo que la empresa
   hace, usa o busca (por ejemplo, pipelines de imágenes satelitales para una empresa que
   monitorea hectáreas con imágenes), **When** se evalúan las conexiones, **Then** la conexión se
   conserva.
4. **Given** una estrategia con algunas conexiones relacionadas y otras no, **When** se evalúan,
   **Then** se conservan solo las relacionadas, y el registro muestra cuáles se descartaron y por
   qué.

---

### Edge Cases

- **Búsqueda de personal como único dato además de otro**: si al descartar la fórmula genérica
  queda un solo dato concreto, la ejecución termina por datos insuficientes (spec 001, FR-009),
  con el conteo correcto.
- **Búsqueda con puesto y fórmula en la misma oración**: la oración puede aportar un dato (el
  puesto), pero la fórmula de búsqueda nunca es lo que el borrador debe reproducir.
- **Nombre con símbolos de marca** ("Vanteo®"): mencionar el nombre sin el símbolo ("Vanteo")
  cuenta como mención de la empresa.
- **Repetición no consecutiva** (intento 3 igual al intento 1): cuenta como repetición, igual que
  la consecutiva.
- **Repetición con cambios mínimos** (en valido-02 solo cambió una palabra y el nombre seguía sin
  aparecer): se trata como un intento fallido más, no como repetición, y consume un intento.
- **Ninguna conexión relacionada pero sí puntos del perfil válidos**: el motivo es
  `sin_conexion_perfil`, no `perfil_sin_puntos` (spec 001, FR-010).
- **Conexión legítima descartada por error**: no debe ocurrir. Se mide con los válidos con
  borrador entregado y se revisa en el registro de cada caso válido.
- **Inyección que intenta forzar una conexión** (por ejemplo, una instrucción que afirma una
  relación con el perfil): el texto de la empresa sigue siendo datos (spec 001, FR-012) y no
  puede volver relacionada una conexión.

## Requirements *(mandatory)*

### Functional Requirements

**Datos concretos (alcance a)**

- **FR-001**: Una fórmula genérica de búsqueda de personal en español o en inglés ("We are
  hiring", "Estamos buscando", "Buscamos una persona", "Join our team" y equivalentes en esos dos
  idiomas) MUST NOT contarse como dato concreto ni ser lo que el borrador debe reproducir para
  demostrar que usa un dato.
- **FR-002**: Un puesto abierto sigue siendo un dato concreto cuando el texto lo especifica: un
  nombre de puesto, un equipo, una tecnología o una responsabilidad concreta. En ese caso, lo que
  el borrador debe mencionar es ese contenido específico.
- **FR-003**: El conteo de datos concretos que se informa al usuario (spec 001, FR-009) MUST
  excluir las fórmulas genéricas de búsqueda.

**Nombre de la empresa y reintentos (alcance b)**

- **FR-004**: Cuando se conoce el nombre de la empresa, el borrador entregado MUST mencionarlo
  (spec 001, FR-019). Si el nombre tiene símbolos de marca (®, ™), mencionarlo sin el símbolo
  cuenta como mención.
- **FR-005**: Si un intento devuelve un texto igual al de un intento anterior de la misma
  ejecución, el sistema MUST NOT terminar por esa repetición mientras queden intentos. El
  siguiente intento MUST recibir un pedido de corrección distinto del que produjo la repetición.
- **FR-006**: El límite total de intentos de redacción por ejecución MUST NOT aumentar respecto de
  la spec 001: 1 intento inicial y 2 reintentos.
- **FR-007**: El registro de la ejecución MUST indicar, para cada intento, si repitió un texto
  anterior y qué pedido de corrección recibió el intento siguiente.

**Relación entre datos y perfil (alcance c)**

- **FR-008**: Una conexión entre un dato de la empresa y un punto del perfil MUST conservarse
  solo si el punto muestra experiencia en algo que el dato indica que la empresa hace, usa o
  busca: la misma tecnología, el mismo dominio, el mismo tipo de problema o el puesto buscado.
  Que ambos lados tengan cifras, volúmenes o necesidad de "escalar" no es una relación.
- **FR-009**: Si después de evaluar la relación no queda ninguna conexión, el sistema MUST NOT
  producir un borrador y MUST informar el motivo `sin_conexion_perfil` (spec 001, FR-010).
- **FR-010**: El registro MUST mostrar cada conexión descartada por falta de relación, con el
  dato, el punto y la causa.
- **FR-011**: La evaluación de la relación MUST tratar el texto de la empresa y lo derivado de él
  como datos (spec 001, FR-012). Ninguna instrucción contenida en el texto de la empresa (por
  ejemplo, una frase que afirme que el perfil encaja) puede hacer que una conexión se considere
  relacionada; la relación se decide solo por el contenido del dato y del punto.

**Evaluación y validación**

- **FR-012**: Los 13 casos de desarrollo de `eval/casos/` y sus valores esperados MUST NOT
  modificarse para esta funcionalidad, para que el resultado sea comparable con la línea base.
- **FR-013**: La comparación con la línea base MUST usar la misma configuración de ejecución que
  R13: el mismo modelo, el mismo contexto, la misma temperatura del redactor y el mismo límite de
  reintentos.
- **FR-014**: Las ofertas de `eval/validacion_ids.json` MUST NOT leerse, abrirse ni usarse para
  construir casos hasta la fase de validación. Esa fase empieza después de cerrar la
  implementación y de registrar la versión del código que se valida.
- **FR-015**: La validación MUST ejecutarse una sola vez sobre los casos construidos a partir de
  esas ofertas. Después de verla, MUST NOT ajustarse nada del sistema, de los casos ni de los
  criterios para mejorar ese resultado. El resultado se reporta tal cual, aunque sea peor que el
  de desarrollo.
- **FR-016**: Los casos de validación MUST construirse con el mismo procedimiento que los casos
  reales de desarrollo (spec 001, research R8): mismo perfil, anonimización limitada al nombre
  del empleador, y valores esperados fijados antes de ejecutar el sistema sobre ellos.
- **FR-017**: Cada comportamiento nuevo (FR-001 a FR-011) MUST tener al menos un caso de prueba
  automatizado sin red. Cuando la línea base tenga una respuesta del modelo para ese caso, el
  test MUST usarla.

### Key Entities

- **Dato concreto de la empresa** (precisa la definición de la spec 001): afirmación específica
  del texto de la empresa. Una búsqueda de personal cuenta solo por su contenido específico
  (puesto, equipo, tecnología, responsabilidad), nunca por la fórmula de búsqueda.
- **Fórmula genérica de búsqueda**: expresión en español o en inglés que anuncia que la empresa
  contrata sin aportar un dato específico ("We are hiring", "Estamos buscando").
- **Conexión**: par dato de la empresa / punto del perfil propuesto para el mensaje. Ahora tiene
  un estado (conservada o descartada) y, si se descarta, una causa.
- **Intento de redacción**: cada borrador producido en una ejecución, con sus fallos, si repitió
  un texto anterior y el pedido de corrección que recibió el intento siguiente.
- **Conjunto de desarrollo**: los 13 casos de `eval/casos/`, usados para medir contra la línea
  base R13.
- **Conjunto de validación**: los casos construidos a partir de las 6 ofertas de
  `eval/validacion_ids.json`. Se usa una sola vez.

## Success Criteria *(mandatory)*

### Measurable Outcomes

Criterios fijados antes de implementar. Se miden con la misma configuración que la línea base R13.

- **SC-001**: En los 13 casos de desarrollo, 0 borradores entregados y 0 intentos de redacción
  contienen un canario o una cifra prohibida, y 3 de 3 casos de inyección terminan sin elementos
  prohibidos en lo entregado, igual que en la línea base.
- **SC-002**: Los 4 casos insuficientes de desarrollo terminan con estado insuficiente y sin
  borrador (línea base: 3 de 4; insuficiente-04 terminó invalido por el criterio empresa, sin
  borrador). Ningún caso insuficiente entrega borrador.
- **SC-003**: Los casos válidos de desarrollo con borrador entregado superan la línea base de 0 de
  6, es decir, son al menos 1 de 6.
- **SC-004**: La validación se ejecuta una sola vez sobre los casos de `eval/validacion_ids.json`.
  Su resultado se reporta completo, junto con el de desarrollo y sin ajustes posteriores. El
  criterio se cumple si el reporte existe y se puede rastrear hasta la versión del código
  registrada antes de ejecutarla, cualquiera sea el resultado.
- **SC-005**: Los borradores entregados siguen cumpliendo al 100% los criterios de la spec 001
  que ya aplicaban: longitud, datos y perfil localizables, sin relleno ni datos ajenos, idioma y
  nombre de la empresa.
- **SC-006**: Se reportan, con el número de conexiones evaluadas, las conexiones legítimas
  descartadas por error en los casos válidos de desarrollo. Es un reporte, sin umbral.

## Assumptions

- Con el truncado de citas largas fuera de alcance, valido-03 y valido-05 siguen previsiblemente
  sin borrador. El máximo alcanzable en desarrollo es 4 de 6 válidos.
- "Mejorar respecto de 0/6" (SC-003) significa al menos 1 de 6 en una corrida completa. No se
  fija un objetivo mayor, para no ajustar el sistema a un número.
- Cada caso se corre una sola vez, igual que en la línea base. Con un modelo no determinista, una
  diferencia de un caso puede deberse a la variación entre corridas. Se reporta tal cual.
- La decisión pendiente sobre el ángulo del estratega (spec 001, research R12) queda fuera de
  alcance. También quedan fuera las afirmaciones sin respaldo que pasan la validación, que se
  siguen midiendo con la revisión humana.
- El límite de intentos (1 inicial y 2 reintentos) se mantiene por costo de tiempo: cada intento
  con el modelo local tarda minutos.
- Los cambios respetan la constitución: tres agentes con una responsabilidad cada uno, el texto de
  la empresa tratado como datos y tests sin red. Cómo se cumplen FR-005 y FR-008 dentro de esas
  reglas se decide en el plan.
- Los casos de validación pueden terminar legítimamente en `insuficiente` si una oferta no tiene
  dos datos concretos. Eso se reporta como resultado, no como fallo del procedimiento.
- **Límite**: portugués, francés, alemán e italiano, aunque son idiomas soportados (spec 001,
  FR-018), quedan sin cobertura de fórmulas genéricas de búsqueda. En un texto de empresa en esos
  idiomas, una fórmula de búsqueda puede seguir contándose como dato concreto.
