"""Frases genéricas de relleno (FR-007).

La lista de `data/relleno.json` es de ejemplos, no exhaustiva: es la verificación mínima
automática. Se puede ampliar editando el JSON, sin tocar código. Los "…" y las alternativas con
"/" de la spec están expandidos en frases separadas.
"""

import json
from functools import cache
from importlib import resources

from outreach_agent.verificacion.texto import contiene_palabra


@cache
def _listas() -> dict[str, tuple[str, ...]]:
    datos = json.loads(
        resources.files("outreach_agent").joinpath("data/relleno.json").read_text("utf-8")
    )
    return {idioma: tuple(frases) for idioma, frases in datos.items()}


def frases_relleno(idioma: str) -> list[str]:
    return list(_listas().get(idioma, ()))


def ejemplos_relleno(idioma: str | None, n: int = 3) -> list[str]:
    """Primeros `n` ejemplos del idioma, para mostrarle al redactor qué evitar."""
    return frases_relleno(idioma or "")[:n]


def encontrar_relleno(texto: str) -> list[str]:
    """Frases de la lista (de cualquier idioma) presentes en el texto, comparadas sin
    mayúsculas, tildes ni puntuación y por palabras completas."""
    return [
        frase
        for frases in _listas().values()
        for frase in frases
        if contiene_palabra(texto, frase)
    ]
