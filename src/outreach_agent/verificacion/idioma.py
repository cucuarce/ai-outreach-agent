"""Detector de idioma determinista por frecuencia de stopwords (research R6).

Soporta los idiomas de IDIOMAS_SOPORTADOS. Devuelve None ("indeterminado") si el texto no tiene
suficientes stopwords o si dos idiomas quedan demasiado parejos; un texto en un idioma no
soportado cae en ese caso.
"""

import json
from functools import cache
from importlib import resources

from outreach_agent.verificacion.texto import normalizar

PROPORCION_MINIMA = 0.05
DIFERENCIA_MINIMA = 0.02


@cache
def _stopwords() -> dict[str, frozenset[str]]:
    datos = json.loads(
        resources.files("outreach_agent").joinpath("data/stopwords.json").read_text("utf-8")
    )
    return {idioma: frozenset(palabras) for idioma, palabras in datos.items()}


def es_stopword(palabra: str) -> bool:
    """La palabra, normalizada, es stopword de alguno de los idiomas soportados."""
    return any(normalizar(palabra) in palabras for palabras in _stopwords().values())


def proporciones(texto: str) -> dict[str, float]:
    """Proporción de tokens del texto que son stopwords de cada idioma."""
    tokens = normalizar(texto).split()
    if not tokens:
        return {idioma: 0.0 for idioma in _stopwords()}
    return {
        idioma: sum(token in palabras for token in tokens) / len(tokens)
        for idioma, palabras in _stopwords().items()
    }


def detectar_idioma(texto: str) -> str | None:
    ranking = sorted(proporciones(texto).items(), key=lambda par: par[1], reverse=True)
    (mejor, p1), (_, p2) = ranking[0], ranking[1]
    if p1 < PROPORCION_MINIMA or p1 - p2 < DIFERENCIA_MINIMA:
        return None
    return mejor
