"""T048: Historia 4, traza estructurada y registro legible (FR-013–FR-015, contracts/trace.md)."""

import json
import re
from dataclasses import replace
from pathlib import Path

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado
from outreach_agent.proveedores.base import ProviderError
from tests import escenarios as e
from tests.fakes import FakeProvider

LARGO = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Además" * 68)  # falla longitud


def correr(tmp_path, respuestas, texto=e.TEXTO_EMPRESA):
    config = replace(cargar_config(env={}), dir_registros=tmp_path / "registros")
    provider = FakeProvider([r if isinstance(r, Exception) else json.dumps(r) for r in respuestas])
    return ejecutar(Entrada(texto, e.PERFIL), provider, config)


def eventos(resultado):
    lineas = Path(resultado.rutas_registro["jsonl"]).read_text(encoding="utf-8").splitlines()
    return [json.loads(linea) for linea in lineas]


def test_ejecucion_exitosa_con_reintento(tmp_path):
    resultado = correr(tmp_path, [e.INVESTIGADOR, e.ESTRATEGA, LARGO, e.REDACTOR])
    assert resultado.estado is Estado.BORRADOR
    traza = eventos(resultado)

    assert traza[0]["evento"] == "ejecucion_inicio"
    assert traza[-1]["evento"] == "ejecucion_fin"
    assert traza[-1]["detalle"]["estado"] == "borrador"
    assert [ev["seq"] for ev in traza] == list(range(1, len(traza) + 1))
    assert all(ev["run_id"] == resultado.run_id for ev in traza)

    # Pares nodo_inicio / nodo_fin en el orden real, incluido el reintento.
    nodos = [(ev["evento"], ev["nodo"], ev["intento"]) for ev in traza[1:-1]]
    esperado = [
        ("preparar_entrada", None),
        ("investigador", None),
        ("verificar_hechos", None),
        ("estratega", None),
        ("verificar_estrategia", None),
        ("redactor", 1),
        ("validar_borrador", 1),
        ("redactor", 2),
        ("validar_borrador", 2),
        ("finalizar", None),
    ]
    assert nodos == [
        (evento, nodo, intento)
        for nodo, intento in esperado
        for evento in ("nodo_inicio", "nodo_fin")
    ]

    tipos = {ev["nodo"]: ev["tipo_nodo"] for ev in traza if ev["nodo"]}
    assert {n for n, t in tipos.items() if t == "agente"} == {"investigador", "estratega", "redactor"}
    assert {n for n, t in tipos.items() if t == "determinista"} == {
        "preparar_entrada",
        "verificar_hechos",
        "verificar_estrategia",
        "validar_borrador",
        "finalizar",
    }

    validaciones = [ev for ev in traza if ev["nodo"] == "validar_borrador" and ev["evento"] == "nodo_fin"]
    assert "longitud" in validaciones[0]["decision"] and "reintento" in validaciones[0]["decision"]
    assert validaciones[1]["decision"].startswith("ok")


def test_corte_por_datos_insuficientes_queda_registrado(tmp_path):
    texto = "Somos una empresa innovadora y apasionada por la excelencia."
    investigador = {
        "nombre_empresa": None,
        "hechos": [
            {"id": "H1", "descripcion": "x", "cita": "Somos una empresa innovadora", "ancla": "innovadora"}
        ],
        "instrucciones_detectadas": [],
    }
    resultado = correr(tmp_path, [investigador], texto=texto)
    traza = eventos(resultado)

    finales = [ev for ev in traza if ev["evento"] == "nodo_fin"]
    verificar = next(ev for ev in finales if ev["nodo"] == "verificar_hechos")
    assert "hechos_insuficientes" in verificar["decision"]
    assert finales[-1]["nodo"] == "finalizar"
    assert traza[-1]["detalle"]["motivo"] == "hechos_insuficientes"


def test_cada_ejecucion_tiene_su_run_id(tmp_path):
    r1 = correr(tmp_path, e.respuestas_flujo_valido_dicts())
    r2 = correr(tmp_path, e.respuestas_flujo_valido_dicts())

    for resultado in (r1, r2):
        assert re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", resultado.run_id)
        assert Path(resultado.rutas_registro["jsonl"]).name == f"{resultado.run_id}.jsonl"
        assert Path(resultado.rutas_registro["md"]).name == f"{resultado.run_id}.md"
    assert r1.run_id != r2.run_id


def test_detalle_nunca_contiene_el_texto_completo_ni_el_perfil(tmp_path):
    resultado = correr(tmp_path, e.respuestas_flujo_valido_dicts())
    contenido = Path(resultado.rutas_registro["jsonl"]).read_text(encoding="utf-8")
    contenido += Path(resultado.rutas_registro["md"]).read_text(encoding="utf-8")

    assert e.TEXTO_EMPRESA not in contenido
    assert e.PERFIL not in contenido
    assert e.ORACION_FUERA_DE_CITAS not in contenido


def test_registro_legible_tiene_cada_paso_y_el_resultado(tmp_path):
    resultado = correr(tmp_path, e.respuestas_flujo_valido_dicts())
    md = Path(resultado.rutas_registro["md"]).read_text(encoding="utf-8")

    assert f"# Registro de ejecución {resultado.run_id}" in md
    for nodo in ("preparar_entrada", "investigador", "verificar_hechos", "estratega",
                 "verificar_estrategia", "redactor", "validar_borrador", "finalizar"):
        assert nodo in md
    assert "(agente)" in md and "(verificación)" in md
    assert "**Decisión:**" in md
    assert "Estado final: **borrador**" in md
    assert e.TEXTO_BORRADOR in md  # el borrador final


def test_error_del_proveedor_queda_como_nodo_error(tmp_path):
    resultado = correr(tmp_path, [ProviderError("Ollama caído")])
    traza = eventos(resultado)

    assert resultado.estado is Estado.ERROR
    errores = [ev for ev in traza if ev["evento"] == "nodo_error"]
    assert [ev["nodo"] for ev in errores] == ["investigador"]
    assert "Ollama caído" in errores[0]["detalle"]["mensaje"]
    assert traza[-1]["evento"] == "ejecucion_fin"
    assert traza[-1]["detalle"]["estado"] == "error"
    assert Path(resultado.rutas_registro["md"]).exists()
