"""T029 (spec 002, research D8): comparación de dos reporte.json armados a mano."""

import json

import pytest

from scripts import comparar_reportes as m


def tasa(cumplen, total, incumplen=()):
    return {"cumplen": cumplen, "total": total,
            "porcentaje": None if total == 0 else 100 * cumplen / total,
            "incumplen": list(incumplen)}


def caso(id_, tipo, estado, motivo=None, intentos=1, duracion=100.0):
    return {"id": id_, "tipo": tipo, "estado": estado, "motivo": motivo, "intentos": intentos,
            "duracion_s": duracion}


CONFIG = {"fecha": "2026-10-14T19:25:24-03:00", "modelo": "qwen2.5:7b", "num_ctx": 8192,
          "timeout_s": 900.0, "temperatura_redactor": 0.3, "max_reintentos": 2}

BASE = {
    "config": CONFIG,
    "totales": {
        "composicion": {"valido": "2 casos"},
        "validos_con_borrador_entregado": tasa(0, 2, ["valido-01", "valido-02"]),
        "SC-004": tasa(1, 2, ["insuficiente-04"]),
        "SC-005": tasa(2, 3, ["inyeccion-02"]),
        "inyecciones_sin_prohibidos_en_lo_entregado": tasa(3, 3),
        "inyecciones_con_borrador_entregado": tasa(2, 3, ["inyeccion-02"]),
        "invalido": {"casos": ["valido-01", "valido-02"], "total": 7},
        "prohibidos_en_entregados": 0,
        "legitimos_descartados_por_ancla": {"valido-03": ["Google ADK", "BigQuery"]},
        "afirmaciones_sin_respaldo": {"con_afirmaciones": ["inyeccion-01"], "revisados": 2,
                                      "pendientes": []},
    },
    "casos": [
        caso("valido-01", "valido", "invalido", "validacion_fallida", 2, 300.0),
        caso("valido-02", "valido", "invalido", "validacion_fallida", 3, 400.0),
        caso("insuficiente-04", "insuficiente", "invalido", "validacion_fallida", 2, 200.0),
    ],
}

NUEVO = {
    "config": {**CONFIG, "fecha": "2026-10-16T10:00:00-03:00", "git_commit": "abc1234",
               "git_cambios_sin_commit": False},
    "totales": {
        "composicion": {"valido": "2 casos"},
        "validos_con_borrador_entregado": tasa(1, 2, ["valido-02"]),
        "SC-004": tasa(0, 2, ["insuficiente-03", "insuficiente-04"]),
        "SC-005": tasa(3, 3),
        "inyecciones_sin_prohibidos_en_lo_entregado": tasa(3, 3),
        "inyecciones_con_borrador_entregado": tasa(3, 3),
        "invalido": {"casos": ["valido-02"], "total": 7},
        "prohibidos_en_entregados": 0,
        "legitimos_descartados_por_ancla": {},
        "afirmaciones_sin_respaldo": {"con_afirmaciones": [], "revisados": 3, "pendientes": []},
        "metrica_nueva": tasa(1, 1),
    },
    "casos": [
        caso("valido-01", "valido", "borrador", None, 3, 500.0),
        caso("valido-02", "valido", "invalido", "validacion_fallida", 3, 450.0),
        caso("insuficiente-04", "insuficiente", "borrador", None, 1, 150.0),
    ],
}


def comparar(base=BASE, nuevo=NUEVO):
    return m.comparar(base, nuevo)


def fila(texto, nombre):
    [linea] = [l for l in texto.splitlines() if l.startswith(f"| {nombre} |")]
    return [c.strip() for c in linea.strip("|").split("|")]


def test_una_fila_por_clave_de_totales_con_base_nueva_y_diferencia():
    texto = comparar()
    assert fila(texto, "validos_con_borrador_entregado") == [
        "validos_con_borrador_entregado", "0/2 (0%)", "1/2 (50%)", "+1 (+50 pp)"
    ]
    assert fila(texto, "SC-004") == ["SC-004", "1/2 (50%)", "0/2 (0%)", "-1 (-50 pp)"]
    assert fila(texto, "prohibidos_en_entregados") == ["prohibidos_en_entregados", "0", "0", "="]
    assert fila(texto, "invalido") == ["invalido", "2/7", "1/7", "-1"]
    assert fila(texto, "legitimos_descartados_por_ancla") == [
        "legitimos_descartados_por_ancla", "2", "0", "-2"
    ]
    assert fila(texto, "afirmaciones_sin_respaldo") == [
        "afirmaciones_sin_respaldo", "1 de 2 revisados", "0 de 3 revisados", "-1"
    ]
    assert fila(texto, "composicion") == ["composicion", "valido: 2 casos", "valido: 2 casos", "="]


def test_clave_presente_en_una_sola_corrida():
    assert fila(comparar(), "metrica_nueva") == ["metrica_nueva", "—", "1/1 (100%)", "—"]


def test_las_metricas_de_inyeccion_van_siempre_por_separado():
    texto = comparar()
    seccion = texto.split("## Inyecciones")[1].split("##")[0]
    for clave in ("SC-005", "inyecciones_sin_prohibidos_en_lo_entregado",
                  "inyecciones_con_borrador_entregado"):
        assert f"| {clave} |" in seccion
    assert fila(seccion, "SC-005") == ["SC-005", "2/3 (67%)", "3/3 (100%)", "+1 (+33 pp)"]


def test_las_metricas_de_inyeccion_aparecen_aunque_falten():
    base = {**BASE, "totales": {k: v for k, v in BASE["totales"].items() if k != "SC-005"}}
    seccion = comparar(base=base).split("## Inyecciones")[1].split("##")[0]
    assert fila(seccion, "SC-005") == ["SC-005", "—", "3/3 (100%)", "—"]


def test_tabla_por_caso_con_estado_y_motivo_en_cada_corrida():
    texto = comparar()
    assert fila(texto, "valido-01") == [
        "valido-01", "valido", "invalido (validacion_fallida)", "borrador", "2 → 3", "cambió"
    ]
    assert fila(texto, "valido-02") == [
        "valido-02", "valido", "invalido (validacion_fallida)", "invalido (validacion_fallida)",
        "3 → 3", ""
    ]


def test_caso_que_falta_en_una_corrida():
    nuevo = {**NUEVO, "casos": NUEVO["casos"][:2]}
    assert fila(comparar(nuevo=nuevo), "insuficiente-04")[3] == "—"


def test_duracion_total_de_cada_corrida():
    assert fila(comparar(), "Duración total (s)") == ["Duración total (s)", "900", "1100", "+200"]


def test_sin_advertencia_si_la_configuracion_coincide():
    assert "Advertencia" not in comparar()


@pytest.mark.parametrize("campo, valor", [("modelo", "llama3.1:8b"), ("num_ctx", 4096),
                                          ("temperatura_redactor", 0.7), ("max_reintentos", 1)])
def test_advierte_si_la_configuracion_difiere(campo, valor):
    nuevo = {**NUEVO, "config": {**NUEVO["config"], campo: valor}}
    texto = comparar(nuevo=nuevo)
    assert "Advertencia" in texto and campo in texto.split("##")[0]


def test_encabezado_con_fecha_y_commit_de_cada_corrida():
    encabezado = comparar().split("##")[0]
    assert "2026-10-14T19:25:24-03:00" in encabezado and "2026-10-16T10:00:00-03:00" in encabezado
    assert "commit desconocido" in encabezado and "abc1234" in encabezado


def test_main_lee_los_dos_archivos_e_imprime(tmp_path, capsys):
    base, nuevo = tmp_path / "base.json", tmp_path / "nuevo.json"
    base.write_text(json.dumps(BASE), encoding="utf-8")
    nuevo.write_text(json.dumps(NUEVO), encoding="utf-8")
    assert m.main([str(base), str(nuevo)]) == 0
    assert "| validos_con_borrador_entregado |" in capsys.readouterr().out
