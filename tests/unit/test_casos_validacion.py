"""Coherencia de los casos de validación (T034, spec 002 FR-016): cada fragmento esperado y el
nombre esperado aparecen en el texto del caso, y el empleador real está anonimizado (research R8
de la 001)."""

import json
import re
from pathlib import Path

import pytest

from scripts.metricas_eval import normalizar_coincidencia

CASOS_DIR = Path(__file__).resolve().parents[2] / "eval" / "validacion" / "casos"
CASOS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASOS_DIR.glob("*.json"))]
EMPLEADORES_REALES = (r"\byuno\b", r"y\.uno", r"\brappi\b", r"or[ée]al", r"\bkinamic\b", r"\botif\b")


def por_id(casos):
    return pytest.mark.parametrize("caso", casos, ids=[c["id"] for c in casos])


def test_hay_6_casos_uno_por_id_de_validacion():
    ids = json.loads((CASOS_DIR.parents[1] / "validacion_ids.json").read_text(encoding="utf-8"))["ids"]
    assert [c["id"] for c in CASOS] == [f"oferta-{i:03d}" for i in sorted(ids)]


@por_id(CASOS)
def test_fragmentos_esperados_aparecen_en_el_texto(caso):
    texto = normalizar_coincidencia(caso["texto_empresa"])
    assert caso["hechos_legitimos_esperados"]
    faltantes = [f for f in caso["hechos_legitimos_esperados"]
                 if normalizar_coincidencia(f) not in texto]
    assert faltantes == []


def oraciones(texto: str) -> list[str]:
    """Líneas del texto partidas en oraciones por punto, signo de exclamación o de pregunta."""
    return [o for linea in texto.splitlines() for o in re.split(r"(?<=[.!?])\s+", linea) if o.strip()]


@por_id(CASOS)
def test_a_lo_sumo_un_fragmento_esperado_por_oracion(caso):
    # legitimos_descartados_por_ancla cuenta por fragmento: dos fragmentos de una misma oración
    # contarían dos veces una sola cita descartada.
    juntos = []
    for oracion in oraciones(caso["texto_empresa"]):
        en_oracion = [f for f in caso["hechos_legitimos_esperados"]
                      if normalizar_coincidencia(f) in normalizar_coincidencia(oracion)]
        if len(en_oracion) > 1:
            juntos.append(en_oracion)
    assert juntos == []


@por_id([c for c in CASOS if c["nombre_esperado"]])
def test_nombre_esperado_aparece_en_el_texto(caso):
    assert normalizar_coincidencia(caso["nombre_esperado"]) in normalizar_coincidencia(
        caso["texto_empresa"])


@por_id(CASOS)
def test_sin_mencion_de_empleadores_reales(caso):
    texto = json.dumps(caso, ensure_ascii=False)
    encontrados = [n for n in EMPLEADORES_REALES if re.search(n, texto, re.IGNORECASE)]
    assert encontrados == []
