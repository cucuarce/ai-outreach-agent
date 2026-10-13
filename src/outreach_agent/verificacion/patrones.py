"""Detección determinista de instrucciones incrustadas (research R3).

Es una red de seguridad: se aplica a las citas de los hechos y al nombre de la empresa que
propone el investigador. Los patrones viven en `data/patrones_instruccion.json` y son acotados
para no descartar citas legítimas de empresas de IA.
"""

import json
import re
from functools import cache
from importlib import resources


@cache
def _patrones() -> tuple[re.Pattern, ...]:
    datos = json.loads(
        resources.files("outreach_agent")
        .joinpath("data/patrones_instruccion.json")
        .read_text("utf-8")
    )
    return tuple(
        re.compile(patron, re.IGNORECASE | re.MULTILINE)
        for clave, patrones in datos.items()
        if not clave.startswith("_")
        for patron in patrones
    )


def es_instruccion(texto: str) -> bool:
    return any(patron.search(texto) for patron in _patrones())
