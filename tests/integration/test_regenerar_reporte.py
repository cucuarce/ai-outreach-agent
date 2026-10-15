"""scripts/regenerar_reporte.py: rearma el reporte de una corrida desde disco, sin red ni proveedor."""

import json
import urllib.request

import pytest

from scripts import evaluar
from scripts import regenerar_reporte as r
from tests.integration.test_evaluar import (
    FLUJO_VALIDO,
    INSUFICIENTE,
    VALIDO,
    correr,
    escribir_casos,
    leer,
)


@pytest.fixture
def sin_red(monkeypatch):
    """Devuelve una función que, una vez armada la corrida, hace fallar el test ante cualquier
    intento de contactar a Ollama, crear el proveedor o ejecutar el grafo."""

    def prohibido(*args, **kwargs):
        raise AssertionError("regenerar_reporte no debe usar la red ni crear el proveedor")

    def activar():
        monkeypatch.setattr(urllib.request, "urlopen", prohibido)
        monkeypatch.setattr(evaluar, "ollama_disponible", prohibido)
        monkeypatch.setattr(evaluar, "crear_proveedor_ollama", prohibido)
        monkeypatch.setattr(evaluar, "OllamaProvider", prohibido)
        monkeypatch.setattr(evaluar, "ejecutar", prohibido)

    return activar


def corrida_con_revision(tmp_path, afirmaciones):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    ruta = corrida / "revision_humana.json"
    registros = leer(ruta)
    registros[0]["afirmaciones_sin_respaldo"] = afirmaciones
    ruta.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
    return casos_dir, corrida


def regenerar(corrida, casos_dir, sin_red, salida=None):
    sin_red()
    log = salida.append if salida is not None else (lambda *a: None)
    return r.main([str(corrida), "--casos", str(casos_dir)], log=log)


def test_regenera_el_reporte_con_la_revision_humana_completada(tmp_path, sin_red):
    casos_dir, corrida = corrida_con_revision(tmp_path, ["dice que su equipo enfrenta un desafío"])
    assert "pendientes de revisar: a-valido" in (corrida / "reporte.md").read_text(encoding="utf-8")

    regenerar(corrida, casos_dir, sin_red)

    totales = leer(corrida / "reporte.json")["totales"]
    assert totales["afirmaciones_sin_respaldo"] == {
        "con_afirmaciones": ["a-valido"], "revisados": 1, "pendientes": []
    }
    assert "1 de 1 revisados (a-valido)" in (corrida / "reporte.md").read_text(encoding="utf-8")


def test_conserva_la_revision_humana_y_la_config(tmp_path, sin_red):
    casos_dir, corrida = corrida_con_revision(tmp_path, [])
    revision = leer(corrida / "revision_humana.json")
    config = (corrida / "config.json").read_bytes()

    regenerar(corrida, casos_dir, sin_red)

    assert leer(corrida / "revision_humana.json") == revision
    assert (corrida / "config.json").read_bytes() == config


def test_no_corre_casos_sin_resultado(tmp_path, sin_red):
    casos_dir, corrida = corrida_con_revision(tmp_path, [])
    (corrida / "resultados" / "a-valido.json").unlink()

    codigo = regenerar(corrida, casos_dir, sin_red)

    assert not (corrida / "resultados" / "a-valido.json").exists()
    assert leer(corrida / "reporte.json")["pendientes"] == ["a-valido"]
    assert codigo == evaluar.CODIGO_METRICAS


def test_codigo_de_salida_igual_al_de_evaluar(tmp_path, sin_red):
    casos_dir, corrida = corrida_con_revision(tmp_path, [])
    codigo = regenerar(corrida, casos_dir, sin_red)
    assert codigo == evaluar.codigo_de_salida(leer(corrida / "reporte.json"))


def test_informa_la_ruta_del_reporte(tmp_path, sin_red):
    casos_dir, corrida = corrida_con_revision(tmp_path, [])
    salida = []
    regenerar(corrida, casos_dir, sin_red, salida)
    assert f"Reporte: {corrida / 'reporte.md'}" in salida


def test_carpeta_que_no_es_una_corrida_termina_con_2_sin_escribir(tmp_path, sin_red):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO)
    carpeta = tmp_path / "vacia"
    carpeta.mkdir()
    salida = []

    codigo = regenerar(carpeta, casos_dir, sin_red, salida)

    assert codigo == r.CODIGO_NO_ES_CORRIDA
    assert list(carpeta.iterdir()) == []
    assert any("config.json" in linea for linea in salida)
