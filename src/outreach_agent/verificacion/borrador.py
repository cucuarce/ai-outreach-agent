"""Validación determinista del borrador (research R2 y R5).

Cada criterio es independiente y se devuelven todos los fallos, para que el redactor pueda
corregirlos juntos en el reintento. Los criterios `numeros` y `enlaces` se agregan en la
Historia 3.
"""

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Fallo, ResultadoValidacion
from outreach_agent.verificacion.idioma import detectar_idioma
from outreach_agent.verificacion.relleno import encontrar_relleno
from outreach_agent.verificacion.texto import (
    contar_palabras,
    contiene_ancla,
    contiene_palabra,
    extraer_numeros,
)

MIN_PALABRAS = 80
MAX_PALABRAS = 150
MIN_HECHOS = 2
MIN_PUNTOS = 1


def _longitud(texto: str) -> Fallo | None:
    palabras = contar_palabras(texto)
    if MIN_PALABRAS <= palabras <= MAX_PALABRAS:
        return None
    return Fallo("longitud", f"{palabras} palabras; rango {MIN_PALABRAS}–{MAX_PALABRAS}")


def _relleno(texto: str) -> Fallo | None:
    encontradas = encontrar_relleno(texto)
    if not encontradas:
        return None
    lista = "; ".join(f'"{frase}"' for frase in encontradas)
    return Fallo("relleno", f"frases genéricas de relleno: {lista}")


def _idioma(texto: str, objetivo: str | None) -> Fallo | None:
    detectado = detectar_idioma(texto)
    if detectado == objetivo:
        return None
    return Fallo(
        "idioma",
        f"el borrador está en '{detectado or 'indeterminado'}'; debe estar en '{objetivo}'",
    )


def _anclas(texto: str, usados: list[str], disponibles: dict, minimo: int, criterio: str):
    """Cuenta los elementos usados que existen (verificados) y cuya ancla aparece en el texto."""
    presentes, faltantes = [], []
    for id_ in usados:
        elemento = disponibles.get(id_)
        if elemento is None:
            continue
        if contiene_ancla(texto, elemento.ancla):
            presentes.append(id_)
        else:
            faltantes.append(f'{id_} (ancla "{elemento.ancla}")')
    if len(presentes) >= minimo:
        return None
    detalle = f"se mencionan {len(presentes)} de {minimo} requeridos"
    if faltantes:
        detalle += "; falta el ancla en el texto: " + ", ".join(faltantes)
    return Fallo(criterio, detalle)


def _empresa(texto: str, nombre: str | None) -> Fallo | None:
    """Si se conoce el nombre de la empresa, debe aparecer en el borrador (FR-019). Sin nombre,
    el criterio no aplica: que el borrador no nombre otra empresa depende del prompt (R12)."""
    if not nombre or contiene_palabra(texto, nombre):
        return None
    return Fallo("empresa", f'el borrador no menciona a "{nombre}"')


def numeros_permitidos_por_nombre(estado: EstadoGrafo) -> set[str]:
    """Dígitos del nombre de la empresa que el criterio `numeros` (T046) acepta: solo los de un
    nombre indicado por el usuario, nunca los de uno extraído del texto (research R12)."""
    if estado.get("origen_nombre_empresa") != "usuario":
        return set()
    return set(extraer_numeros(estado.get("nombre_empresa") or ""))


def validar_borrador(estado: EstadoGrafo) -> ResultadoValidacion:
    borrador = estado["borrador"]
    texto = borrador.texto
    hechos = {h.id: h for h in estado.get("hechos", [])}
    puntos = {p.id: p for p in estado["estrategia"].puntos_perfil}

    fallos = [
        fallo
        for fallo in (
            _longitud(texto),
            _relleno(texto),
            _idioma(texto, estado.get("idioma_objetivo")),
            _anclas(texto, borrador.hechos_usados, hechos, MIN_HECHOS, "hechos"),
            _anclas(texto, borrador.puntos_usados, puntos, MIN_PUNTOS, "perfil"),
            _empresa(texto, estado.get("nombre_empresa")),
        )
        if fallo is not None
    ]
    return ResultadoValidacion(ok=not fallos, fallos=fallos)


def nodo_validar_borrador(estado: EstadoGrafo) -> dict:
    return {"validacion": validar_borrador(estado)}
