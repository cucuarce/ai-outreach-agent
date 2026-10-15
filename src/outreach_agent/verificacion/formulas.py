"""Fórmulas genéricas de búsqueda de personal (spec 002, research D1; FR-001 a FR-003).

"We are hiring" o "Sumate a nuestro equipo" no son datos concretos de la empresa: lo que cuenta de
una búsqueda es su contenido específico (puesto, equipo, tecnología o responsabilidad). Los
patrones viven en `data/formulas_busqueda.json`, solo en español e inglés, y se comparan contra
el texto normalizado.
"""

import json
import re
from functools import cache
from importlib import resources

from outreach_agent.verificacion.texto import normalizar


CLAVE_RESTOS_VACIOS = "restos_vacios"


@cache
def _datos() -> dict:
    return json.loads(
        resources.files("outreach_agent")
        .joinpath("data/formulas_busqueda.json")
        .read_text("utf-8")
    )


@cache
def _patrones() -> tuple[re.Pattern, ...]:
    return tuple(
        re.compile(patron)
        for clave, patrones in _datos().items()
        if not clave.startswith("_") and clave != CLAVE_RESTOS_VACIOS
        for patron in patrones
    )


@cache
def _restos_vacios() -> frozenset[str]:
    return frozenset(normalizar(p) for p in _datos()[CLAVE_RESTOS_VACIOS])


def es_resto_vacio(palabra: str) -> bool:
    """La palabra no alcanza para ser ancla una vez quitada la fórmula ("equipo", "team")."""
    return normalizar(palabra) in _restos_vacios()


def es_formula_busqueda(texto: str) -> bool:
    normalizado = normalizar(texto)
    return any(patron.search(normalizado) for patron in _patrones())


# Palabras que suelen seguir a la fórmula y no forman parte del contenido: "Buscamos un …",
# "We are hiring a …".
CONECTORES = frozenset({"a", "un", "una", "an", "the"})
_BORDES = ".,;:!?¡¿()\"'“”‘’"


def quitar_formula(ancla: str) -> str | None:
    """El ancla sin la primera fórmula que contiene ni los conectores que la siguen, con el resto
    tal como estaba escrito. None si el ancla no contiene ninguna fórmula.

    La fórmula se busca por palabras completas del ancla: el tramo más corto que, normalizado,
    coincide entero con un patrón."""
    palabras = ancla.split()
    for inicio in range(len(palabras)):
        for fin in range(inicio + 1, len(palabras) + 1):
            tramo = normalizar(" ".join(palabras[inicio:fin]))
            if tramo and any(patron.fullmatch(tramo) for patron in _patrones()):
                despues = fin
                while (
                    despues < len(palabras)
                    and palabras[despues].strip(_BORDES).lower() in CONECTORES
                ):
                    despues += 1
                resto = palabras[:inicio] + palabras[despues:]
                return " ".join(resto).strip(_BORDES + " ")
    return None
