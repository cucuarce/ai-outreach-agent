"""Cortes por información insuficiente (Historia 2, FR-009 y FR-010).

Los nodos deterministas que detectan que no se puede seguir dejan un `resultado` en el estado;
las aristas condicionales del grafo ven ese campo y saltan a `finalizar`, que lo devuelve tal
cual. El texto de cada detalle incluye cómo corregir la entrada.
"""

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Estado, Motivo, Resultado

DETALLES = {
    Motivo.EMPRESA_VACIA: (
        "El texto de la empresa está vacío. Pegá el texto de la página de la empresa o de la "
        "oferta de empleo."
    ),
    Motivo.PERFIL_VACIO: (
        "El perfil está vacío. Pegá tu perfil profesional con tu experiencia, proyectos y logros."
    ),
    Motivo.IDIOMA_INDETERMINADO: (
        "No se pudo determinar el idioma del texto de la empresa, o no es uno de los soportados "
        "(es, en, pt, fr, de, it). Indicá el idioma del borrador con --idioma."
    ),
    Motivo.PERFIL_SIN_PUNTOS: (
        "Tu perfil no tiene puntos concretos verificables (experiencias, proyectos o logros "
        "específicos). Agregá logros concretos, por ejemplo con cifras o tecnologías."
    ),
    Motivo.SIN_CONEXION_PERFIL: (
        "Tu perfil tiene puntos concretos, pero ninguno se pudo conectar con los datos de la "
        "empresa. Puede que esta empresa no encaje con tu perfil, o que el texto de la empresa "
        "no cuente lo suficiente sobre lo que hacen."
    ),
}


def detalle_hechos_insuficientes(encontrados: int, requeridos: int) -> str:
    return (
        f"Se encontraron {encontrados} de {requeridos} datos concretos en el texto de la "
        "empresa. Pegá un texto con más información concreta: productos, cifras, tecnologías, "
        "proyectos o puestos abiertos."
    )


def cortar(estado: EstadoGrafo, motivo: Motivo, detalle: str | None = None) -> dict:
    """Actualización de estado que termina la ejecución como `insuficiente`."""
    resultado = Resultado(
        estado=Estado.INSUFICIENTE,
        run_id=estado["run_id"],
        idioma=estado.get("idioma_objetivo"),
        nombre_empresa=estado.get("nombre_empresa"),
        origen_nombre_empresa=estado.get("origen_nombre_empresa"),
        motivo=motivo,
        detalle=detalle or DETALLES[motivo],
    )
    return {"resultado": resultado}
