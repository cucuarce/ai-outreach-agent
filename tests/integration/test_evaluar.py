"""T058: scripts/evaluar.py con FakeProvider inyectado, sin red ni Ollama."""

import json
import os
from datetime import datetime
from pathlib import Path

from outreach_agent.proveedores.base import ProviderError
from scripts import evaluar
from tests import escenarios as e
from tests.fakes import FakeProvider

FECHA = datetime(2026, 10, 15, 9, 30, 0)


def caso(id_: str, tipo: str, texto: str, **extra) -> dict:
    return {
        "id": id_,
        "tipo": tipo,
        "texto_empresa": texto,
        "perfil": e.PERFIL,
        "idioma": None,
        "idioma_esperado": "es",
        "canario": None,
        "nombre_esperado": None,
        **extra,
    }


VALIDO = caso("a-valido", "valido", e.TEXTO_EMPRESA, nombre_esperado="Nubeluz",
              hechos_legitimos_esperados=["Kubernetes"])
INSUFICIENTE = caso("b-insuficiente", "insuficiente", "   ")  # empresa vacía: sin llamadas
INYECCION = caso("c-inyeccion", "inyeccion", e.TEXTO_EMPRESA_INYECCION, canario="ZEBRA-7731")

FLUJO_VALIDO = [json.dumps(r) for r in (e.INVESTIGADOR, e.ESTRATEGA, e.REDACTOR)]


def escribir_casos(carpeta: Path, *casos: dict) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    for c in casos:
        (carpeta / f"{c['id']}.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return carpeta


def correr(tmp_path, casos_dir, respuestas, *flags, disponible=True, fecha=FECHA):
    """Corre evaluar.main con un FakeProvider; devuelve (código, carpeta, proveedor, configs)."""
    provider = FakeProvider(respuestas)
    configs = []

    def fabrica(config):
        configs.append(config)
        return provider

    salida = tmp_path / "reportes"
    codigo = evaluar.main(
        ["--casos", str(casos_dir), "--salida", str(salida), *flags],
        crear_proveedor=fabrica,
        disponible=lambda config: disponible,
        ahora=lambda: fecha,
        log=lambda *a: None,
    )
    corridas = sorted(salida.glob("*")) if salida.exists() else []
    return codigo, (corridas[-1] if corridas else None), provider, configs


def leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


# --- Corrida completa ---


def test_corrida_persiste_config_resultados_trazas_y_reporte(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE, INYECCION)
    respuestas = [*FLUJO_VALIDO, ProviderError("Ollama no respondió en 900 s.")]
    codigo, corrida, _, _ = correr(tmp_path, casos_dir, respuestas, "--temp-redactor", "0.1")

    assert corrida.name == "20261015-093000-qwen2.5-7b"
    config = leer(corrida / "config.json")
    assert config["modelo"] == "qwen2.5:7b"
    assert config["num_ctx"] == 8192
    assert config["timeout_s"] == 900
    assert config["temperatura_redactor"] == 0.1
    assert config["max_reintentos"] == 2
    assert config["fecha"].startswith("2026-10-15T09:30:00")

    resultados = {p.stem: leer(p) for p in (corrida / "resultados").glob("*.json")}
    assert {k: v["estado"] for k, v in resultados.items()} == {
        "a-valido": "borrador",
        "b-insuficiente": "insuficiente",
        "c-inyeccion": "error",
    }
    for datos in resultados.values():
        assert (corrida / "trazas" / f"{datos['run_id']}.jsonl").exists()

    reporte = leer(corrida / "reporte.json")
    assert reporte["errores"] == ["c-inyeccion"]
    assert reporte["pendientes"] == []
    assert reporte["totales"]["SC-004"]["porcentaje"] == 100
    assert reporte["totales"]["validos_con_borrador_entregado"] == {
        "cumplen": 1, "total": 1, "porcentaje": 100, "incumplen": []
    }
    md = (corrida / "reporte.md").read_text(encoding="utf-8")
    assert "Modelo: qwen2.5:7b · num_ctx: 8192 · timeout: 900 s · temperatura del redactor: 0.1" in md
    assert "max_reintentos: 2" in md
    assert "- Válidos con borrador entregado: 100% (1/1)" in md
    assert codigo == evaluar.CODIGO_METRICAS  # hubo un error


def test_todo_al_100_termina_con_codigo_0(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    codigo, _, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    assert codigo == evaluar.CODIGO_OK


def test_un_caso_unico_por_archivo(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    codigo, corrida, provider, _ = correr(tmp_path, casos_dir / "b-insuficiente.json", [])
    assert [p.stem for p in (corrida / "resultados").glob("*.json")] == ["b-insuficiente"]
    assert provider.llamadas == []
    assert codigo == evaluar.CODIGO_OK


# --- Orden y errores ---


def test_los_casos_corren_en_orden_de_id(tmp_path):
    otro = caso("0-primero", "valido", e.TEXTO_EMPRESA_EN, idioma_esperado="en")
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, otro)  # escritos en otro orden
    _, _, provider, _ = correr(tmp_path, casos_dir, [ProviderError("x"), ProviderError("y")])
    assert e.TEXTO_EMPRESA_EN.split(".")[0] in provider.llamadas[0]["user"]
    assert "Nubeluz" in provider.llamadas[1]["user"]


def test_una_excepcion_inesperada_queda_como_error_y_la_corrida_sigue(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INYECCION)
    respuestas = [RuntimeError("se cayó algo"), *[json.dumps(r) for r in (
        e.INVESTIGADOR_INYECCION, e.ESTRATEGA, e.REDACTOR)]]
    _, corrida, _, _ = correr(tmp_path, casos_dir, respuestas)

    valido = leer(corrida / "resultados" / "a-valido.json")
    assert valido["estado"] == "error"
    assert "RuntimeError: se cayó algo" in valido["detalle"]
    assert leer(corrida / "resultados" / "c-inyeccion.json")["estado"] == "borrador"


def test_ollama_no_disponible_termina_con_2_sin_correr_ni_crear_carpeta(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO)
    codigo, corrida, provider, configs = correr(tmp_path, casos_dir, [], disponible=False)
    assert codigo == evaluar.CODIGO_SIN_OLLAMA
    assert corrida is None
    assert configs == [] and provider.llamadas == []


# --- Reanudación ---


def test_reanudar_salta_los_casos_con_resultado_y_usa_la_config_guardada(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO, "--num-ctx", "4096")
    insuficiente = corrida / "resultados" / "b-insuficiente.json"
    antes = insuficiente.read_text(encoding="utf-8")
    os.utime(insuficiente, (0, 0))
    (corrida / "resultados" / "a-valido.json").unlink()  # como si se hubiera cortado ahí

    provider = FakeProvider(list(FLUJO_VALIDO))
    configs = []
    codigo = evaluar.main(
        ["--casos", str(casos_dir), "--reanudar", str(corrida)],
        crear_proveedor=lambda c: configs.append(c) or provider,
        disponible=lambda c: True,
        log=lambda *a: None,
    )

    assert len(provider.llamadas) == 3  # solo a-valido
    assert insuficiente.read_text(encoding="utf-8") == antes
    assert insuficiente.stat().st_mtime == 0  # no se reescribió
    assert configs[0].num_ctx == 4096
    assert configs[0].dir_registros == corrida / "trazas"
    assert leer(corrida / "resultados" / "a-valido.json")["estado"] == "borrador"
    assert codigo == evaluar.CODIGO_OK


def test_el_reporte_lista_los_casos_pendientes(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    (corrida / "resultados" / "a-valido.json").unlink()

    reporte = evaluar.armar_reporte(corrida, evaluar.cargar_casos(casos_dir))
    assert reporte["pendientes"] == ["a-valido"]
    assert evaluar.codigo_de_salida(reporte) == evaluar.CODIGO_METRICAS


def test_valido_sin_borrador_se_informa_pero_no_cambia_el_codigo_de_salida(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    datos = json.loads((corrida / "resultados" / "a-valido.json").read_text(encoding="utf-8"))
    datos.update(estado="invalido", motivo="validacion_fallida", borrador=None,
                 hechos_usados=[], puntos_usados=[])
    (corrida / "resultados" / "a-valido.json").write_text(json.dumps(datos), encoding="utf-8")

    reporte = evaluar.armar_reporte(corrida, evaluar.cargar_casos(casos_dir))
    assert reporte["totales"]["validos_con_borrador_entregado"]["incumplen"] == ["a-valido"]
    md = (corrida / "reporte.md").read_text(encoding="utf-8")
    assert "- Válidos con borrador entregado: 0% (0/1) · incumplen: a-valido" in md
    assert evaluar.codigo_de_salida(reporte) == evaluar.CODIGO_OK


# --- nombre_esperado ---


def test_nombre_esperado_no_se_pasa_al_sistema(tmp_path):
    marcado = {**VALIDO, "nombre_esperado": "EmpresaSoloParaEvaluar"}
    casos_dir = escribir_casos(tmp_path / "casos", marcado)
    _, corrida, provider, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)

    for llamada in provider.llamadas:
        assert "EmpresaSoloParaEvaluar" not in llamada["system"] + llamada["user"]
    resultado = leer(corrida / "resultados" / "a-valido.json")
    assert resultado["origen_nombre_empresa"] == "texto"
    assert resultado["nombre_empresa"] == "Nubeluz"


# --- Revisión humana ---


def test_revision_humana_tiene_un_registro_por_borrador_entregado(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)

    [registro] = leer(corrida / "revision_humana.json")
    assert registro["id"] == "a-valido"
    assert registro["texto"] == e.TEXTO_BORRADOR
    assert {h["id"] for h in registro["hechos_usados"]} == {"H1", "H2"}
    assert all(h["cita"] for h in registro["hechos_usados"] + registro["puntos_usados"])
    assert registro["afirmaciones_sin_respaldo"] is None
    md = (corrida / "reporte.md").read_text(encoding="utf-8")
    assert "## Para revisión humana" in md
    assert '- Dato [H1] "procesa 2 millones de transacciones al mes" (ancla: 2)' in md


def test_lo_completado_a_mano_se_conserva_y_se_cuenta(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO, INSUFICIENTE)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    ruta = corrida / "revision_humana.json"
    registros = leer(ruta)
    registros[0]["afirmaciones_sin_respaldo"] = ["dice que su equipo enfrenta un desafío"]
    ruta.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")

    reporte = evaluar.armar_reporte(corrida, evaluar.cargar_casos(casos_dir))

    assert leer(ruta)[0]["afirmaciones_sin_respaldo"] == ["dice que su equipo enfrenta un desafío"]
    assert reporte["totales"]["afirmaciones_sin_respaldo"] == {
        "con_afirmaciones": ["a-valido"],
        "revisados": 1,
        "pendientes": [],
    }


# --- Utilidades ---


def test_resultado_ida_y_vuelta_por_json(tmp_path):
    casos_dir = escribir_casos(tmp_path / "casos", VALIDO)
    _, corrida, _, _ = correr(tmp_path, casos_dir, FLUJO_VALIDO)
    datos = leer(corrida / "resultados" / "a-valido.json")
    resultado = evaluar.resultado_desde_dict(datos)
    assert {**resultado.a_dict(), "duracion_s": datos["duracion_s"]} == datos


def test_nombre_de_corrida_sin_caracteres_invalidos_en_windows():
    assert evaluar.nombre_corrida(FECHA, "qwen2.5:7b") == "20261015-093000-qwen2.5-7b"
