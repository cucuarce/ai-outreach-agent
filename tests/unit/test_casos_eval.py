"""Coherencia de los casos de evaluación (T056, contracts/eval.md): cada caso se puede medir con
su propio texto, y los textos sorteados de ofertas reales están anonimizados (research R8)."""

import json
import re
from pathlib import Path

import pytest

CASOS_DIR = Path(__file__).resolve().parents[2] / "eval" / "casos"
CASOS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASOS_DIR.glob("*.json"))]
VALIDOS = [c for c in CASOS if c["tipo"] == "valido"]
EMPLEADORES_REALES = ("humand", "capgemini", "dept")


def normalizar(s: str) -> str:
    """Regla de coincidencia de contracts/eval.md: minúsculas y espacios colapsados."""
    return " ".join(s.lower().split())


def por_id(casos):
    return pytest.mark.parametrize("caso", casos, ids=[c["id"] for c in casos])


def test_hay_13_casos():
    assert len(CASOS) == 13


@por_id(VALIDOS)
def test_fragmentos_esperados_aparecen_en_el_texto(caso):
    texto = normalizar(caso["texto_empresa"])
    assert caso["hechos_legitimos_esperados"]
    faltantes = [f for f in caso["hechos_legitimos_esperados"] if normalizar(f) not in texto]
    assert faltantes == []


@por_id([c for c in CASOS if c["nombre_esperado"]])
def test_nombre_esperado_aparece_en_el_texto(caso):
    assert normalizar(caso["nombre_esperado"]) in normalizar(caso["texto_empresa"])


@por_id([c for c in CASOS if c["canario"]])
def test_canario_aparece_en_el_texto(caso):
    assert caso["canario"] in caso["texto_empresa"]


def test_canarios_no_repetidos():
    canarios = [c["canario"] for c in CASOS if c["canario"]]
    assert len(canarios) == len(set(canarios))


@por_id(CASOS)
def test_sin_mencion_de_empleadores_reales(caso):
    texto = json.dumps(caso, ensure_ascii=False)
    encontrados = [n for n in EMPLEADORES_REALES if re.search(n, texto, re.IGNORECASE)]
    assert encontrados == []
