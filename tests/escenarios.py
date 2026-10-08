"""Entradas y respuestas de agentes reutilizadas por varios tests.

Las respuestas siguen los esquemas de contracts/agent-outputs.md y son coherentes entre sí:
cada cita aparece literal en el texto de la empresa o en el perfil, y cada ancla en su cita.
"""

import json

# La última oración no forma parte de ninguna cita: sirve para comprobar que el estratega y
# el redactor no reciben el texto crudo de la empresa.
ORACION_FUERA_DE_CITAS = "Nuestra oficina tiene una terraza con vista al río."

TEXTO_EMPRESA = (
    "Nubeluz es una fintech de Montevideo fundada en 2019. Nuestra plataforma de pagos "
    "procesa 2 millones de transacciones al mes para comercios de Uruguay y Paraguay. "
    "Migramos toda la infraestructura a Kubernetes en 2024 y estamos sumando un equipo de "
    "datos para detección de fraude en tiempo real. Buscamos una ingeniera o ingeniero "
    "backend con experiencia en Python. " + ORACION_FUERA_DE_CITAS
)

PERFIL = (
    "Ingeniera backend con 5 años de experiencia en Python y Go. En Pagosur lideré la "
    "migración de 40 microservicios a Kubernetes. Implementé un sistema de alertas "
    "antifraude que redujo un 30% los contracargos."
)

INVESTIGADOR = {
    "hechos": [
        {
            "id": "H1",
            "descripcion": "Procesa 2 millones de transacciones por mes",
            "cita": "procesa 2 millones de transacciones al mes",
            "ancla": "2",
        },
        {
            "id": "H2",
            "descripcion": "Migró su infraestructura a Kubernetes en 2024",
            "cita": "Migramos toda la infraestructura a Kubernetes en 2024",
            "ancla": "Kubernetes",
        },
        {
            "id": "H3",
            "descripcion": "Busca perfil backend con Python",
            "cita": "Buscamos una ingeniera o ingeniero backend con experiencia en Python.",
            "ancla": "Python",
        },
    ],
    "instrucciones_detectadas": [],
}

ESTRATEGA = {
    "angulo": "Experiencia migrando pagos a Kubernetes y reduciendo fraude a escala.",
    "hechos_elegidos": ["H1", "H2"],
    "puntos_perfil": [
        {
            "id": "P1",
            "descripcion": "Lideró la migración de 40 microservicios a Kubernetes",
            "cita": "lideré la migración de 40 microservicios a Kubernetes",
            "ancla": "Kubernetes",
        },
        {
            "id": "P2",
            "descripcion": "Sistema antifraude que redujo 30% los contracargos",
            "cita": "Implementé un sistema de alertas antifraude que redujo un 30% los contracargos",
            "ancla": "30",
        },
    ],
    "conexiones": [
        {"hecho_id": "H2", "punto_id": "P1", "razon": "Misma migración a Kubernetes."},
        {"hecho_id": "H1", "punto_id": "P2", "razon": "Volumen alto expuesto a fraude."},
    ],
}

TEXTO_BORRADOR = (
    "Hola, equipo de Nubeluz. Vi que migraron toda la infraestructura a Kubernetes en 2024 y "
    "que la plataforma ya procesa 2 millones de transacciones al mes. En Pagosur lideré la "
    "migración de 40 microservicios a Kubernetes, así que conozco de cerca los problemas de "
    "observabilidad y despliegue que aparecen en ese cambio. También implementé un sistema de "
    "alertas antifraude que redujo un 30% los contracargos, algo que podría servirle al "
    "equipo de datos que están armando para detectar fraude en tiempo real. Trabajo hace 5 "
    "años con Python en backend. ¿Tendrían quince minutos para conversar sobre cómo podría "
    "sumar a ese equipo?"
)

REDACTOR = {"texto": TEXTO_BORRADOR, "hechos_usados": ["H1", "H2"], "puntos_usados": ["P1", "P2"]}


def respuestas_flujo_valido() -> list[str]:
    """Respuestas del investigador, el estratega y el redactor, en ese orden."""
    return [json.dumps(INVESTIGADOR), json.dumps(ESTRATEGA), json.dumps(REDACTOR)]
