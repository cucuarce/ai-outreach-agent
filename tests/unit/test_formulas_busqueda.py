"""T005 (spec 002, research D1): fórmulas genéricas de búsqueda de personal, en español e inglés."""

import json

import pytest

from outreach_agent.verificacion.formulas import es_formula_busqueda
from outreach_agent.verificacion.texto import contiene_palabra
from tests.escenarios import RAIZ

# Frases que no salen de los casos de desarrollo (lo comprueba
# test_las_frases_marcadas_no_estan_en_los_casos_de_desarrollo).
FRASES_NUEVAS = [
    "Estamos contratando",
    "Join our team",
    "Unite a nuestro equipo",
    "We're hiring",
    "Now hiring",
    "Súmate a nuestro equipo",
    "Se busca",
    "Únete al equipo",
    "Come work with us",
]
# "Sumate" aparece en valido-02 ("¡Sumate al equipo de Lumora…"): se marca, pero no cuenta como
# frase nueva (research D1).
DEBEN_MARCARSE = FRASES_NUEVAS + ["Sumate"]

# Anclas legítimas: puestos, nombres propios y palabras sueltas que no son fórmulas.
NO_DEBEN_MARCARSE = [
    "Principal QA Automation Engineer",
    "Sr AI Process Builder",
    "senior backend engineer",
    "Tidewise",
    "Lote360",
    "equipo de datos",
    "Hiring Manager",
    "búsqueda semántica",
]


@pytest.mark.parametrize("texto", DEBEN_MARCARSE)
def test_marca_formulas_de_busqueda(texto):
    assert es_formula_busqueda(texto)


@pytest.mark.parametrize("texto", NO_DEBEN_MARCARSE)
def test_no_marca_anclas_legitimas(texto):
    assert not es_formula_busqueda(texto)


def test_las_frases_marcadas_no_estan_en_los_casos_de_desarrollo():
    textos = [
        json.loads(ruta.read_text(encoding="utf-8"))["texto_empresa"]
        for ruta in sorted((RAIZ / "eval" / "casos").glob("*.json"))
    ]
    assert textos
    for frase in FRASES_NUEVAS:
        assert not any(contiene_palabra(texto, frase) for texto in textos), frase


def test_ignora_mayusculas_tildes_y_espacios():
    assert es_formula_busqueda("ESTAMOS   contratando")
    assert es_formula_busqueda("únete AL equipo")
    assert es_formula_busqueda("We’re  Hiring")  # apóstrofo tipográfico


def test_la_formula_dentro_de_una_frase_mas_larga_se_marca():
    assert es_formula_busqueda("We are hiring a senior backend engineer")
    assert es_formula_busqueda("Buscamos una analista de datos con experiencia en dbt")


def test_texto_vacio_no_se_marca():
    assert not es_formula_busqueda("")
