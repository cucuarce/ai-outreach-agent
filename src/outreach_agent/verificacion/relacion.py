"""Relación entre la cita de un dato y la cita de un punto del perfil (spec 002, research D4).

Evaluador determinista por término compartido: una conexión tiene relación si las dos citas
comparten al menos un término de contenido. Mira solo las dos citas; nunca la `razon` del
estratega ni el ángulo (FR-011).

Pasos (research D4):
1. Normaliza: minúsculas, sin tildes y sin puntuación, salvo `.`, `-` y `/` dentro de una
   palabra ("node.js", "sentinel-2", "ci/cd").
2. Tokeniza.
3. Quita stopwords (de todos los idiomas de `data/stopwords.json`), números y los términos
   genéricos de `data/terminos_genericos.json`.
4. Forma singular simple: se quita una "s" final, o "es" después de consonante.
5. Solo cuentan los tokens de 2 letras o más, para que "Go" cuente.

En el paso 4 las dos reglas no siempre llevan a la misma forma ("pipelines" → "pipeline" con la
primera; "imágenes" → "imagen" con la segunda). Por eso cada token se compara con todas sus
formas candidatas: dos tokens coinciden si comparten alguna.
"""

import json
import re
import unicodedata
from functools import cache
from importlib import resources

_TOKEN = re.compile(r"\w+(?:[./-]\w+)*")
_NUMERO = re.compile(r"[0-9]+(?:[.,/-][0-9]+)*")
_VOCALES = frozenset("aeiou")
LARGO_MINIMO = 2


def _sin_tildes(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _leer(nombre: str) -> dict:
    return json.loads(
        resources.files("outreach_agent").joinpath(f"data/{nombre}").read_text("utf-8")
    )


@cache
def _stopwords() -> frozenset[str]:
    return frozenset(
        _sin_tildes(palabra)
        for palabras in _leer("stopwords.json").values()
        for palabra in palabras
    )


@cache
def _genericos() -> frozenset[str]:
    return frozenset(
        _sin_tildes(palabra)
        for clave, palabras in _leer("terminos_genericos.json").items()
        if not clave.startswith("_")
        for palabra in palabras
    )


def formas(token: str) -> frozenset[str]:
    """El token y sus formas singulares simples de 2 letras o más."""
    candidatas = {token}
    if token.endswith("s"):
        candidatas.add(token[:-1])
    if token.endswith("es") and len(token) > 2 and token[-3] not in _VOCALES:
        candidatas.add(token[:-2])
    return frozenset(f for f in candidatas if len(f) >= LARGO_MINIMO)


def terminos(cita: str) -> list[str]:
    """Los tokens de contenido de una cita, normalizados y sin repetir, en orden."""
    vistos: list[str] = []
    for token in _TOKEN.findall(_sin_tildes(cita)):
        token = token.strip("_")
        if len(token) < LARGO_MINIMO or token in vistos:
            continue
        if token in _stopwords() or _NUMERO.fullmatch(token):
            continue
        if formas(token) & _genericos():
            continue
        vistos.append(token)
    return vistos


def terminos_compartidos(cita_dato: str, cita_punto: str) -> list[str]:
    """Los términos que comparten las dos citas, en el orden de la cita del dato. Una lista
    vacía significa que no hay relación. Cada término se informa en la forma común más larga."""
    formas_punto = frozenset().union(*(formas(t) for t in terminos(cita_punto)))
    compartidos: list[str] = []
    for token in terminos(cita_dato):
        comunes = formas(token) & formas_punto
        if comunes:
            termino = max(sorted(comunes), key=len)
            if termino not in compartidos:
                compartidos.append(termino)
    return compartidos
