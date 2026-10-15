"""T024 (spec 002): medición del evaluador con un etiquetado chico armado a mano, sin el mini-set
real."""

import json
from pathlib import Path

import pytest

from scripts import medir_relacion as m


def item(id_, etiqueta, dato="Dato.", punto="Punto."):
    return {"id": id_, "cita_dato": dato, "cita_punto": punto, "etiqueta": etiqueta, "nota": ""}


def origen(*casos):
    return {"casos": [{"caso": c, "hecho_id": "H1"} for c in casos], "punto_perfil": 0,
            "propuesta_por_estratega": False}


# Evaluador falso: conserva el par si la cita del dato empieza con "SI".
def falso(cita_dato, _cita_punto):
    return ["x"] if cita_dato.startswith("SI") else []


def medir(items, origenes, evaluador=falso):
    return m.evaluar(items, origenes, evaluador)


def criterios(pares):
    return {c.nombre.split(" (")[0]: c for c in m.puerta(pares)}


BASE_ITEMS = [
    item("c-1", "mala", dato="NO medialunas"),        # insuficiente-04
    item("c-2", "mala", dato="NO sucursal"),          # insuficiente-04
    item("c-3", "buena", dato="SI python"),           # valido-01
    item("c-4", "buena", dato="SI go"),               # valido-04 y valido-06
    item("c-5", "mala", dato="NO hectareas"),         # valido-01
    item("c-6", "dudosa", dato="SI algo"),            # valido-02
    item("c-7", "mala", dato="NO otra"),              # valido-02
]
BASE_ORIGEN = {
    "c-1": origen("insuficiente-04"),
    "c-2": origen("insuficiente-04"),
    "c-3": origen("valido-01"),
    "c-4": origen("valido-04", "valido-06", "inyeccion-02"),
    "c-5": origen("valido-01"),
    "c-6": origen("valido-02"),
    "c-7": origen("valido-02"),
}


def test_todo_bien_pasa_la_puerta():
    pares = medir(BASE_ITEMS, BASE_ORIGEN)
    assert all(c.pasa for c in m.puerta(pares))
    assert "**Resultado: pasa**" in m.reporte(pares)


def test_un_falso_acepto_en_insuficiente_04_no_pasa():
    items = [dict(i) for i in BASE_ITEMS]
    items[0]["cita_dato"] = "SI medialunas"
    c = criterios(medir(items, BASE_ORIGEN))["Falsos aceptos en insuficiente-04"]
    assert (c.cumplen, c.total, c.pasa) == (1, 2, False)


def test_falsos_aceptos_hasta_el_10_por_ciento_de_las_malas():
    # 10 malas: 1 aceptada (10%) pasa; 2 (20%) no pasa.
    items = [item(f"c-{n}", "mala", dato="SI" if n < 1 else "NO") for n in range(10)]
    origenes = {i["id"]: origen("valido-09") for i in items}
    assert criterios(medir(items, origenes))["Falsos aceptos sobre las `mala`"].pasa
    items[1]["cita_dato"] = "SI"
    c = criterios(medir(items, origenes))["Falsos aceptos sobre las `mala`"]
    assert (c.cumplen, c.total, c.pasa) == (2, 10, False)


def test_falsos_rechazos_con_4_buenas_maximo_1():
    items = [item(f"c-{n}", "buena", dato="SI") for n in range(4)]
    origenes = {i["id"]: origen("valido-01") for i in items}
    items[0]["cita_dato"] = "NO"
    c = criterios(medir(items, origenes))["Falsos rechazos sobre las `buena`"]
    assert (c.cumplen, c.total, c.pasa) == (1, 4, True)
    assert "1 de 4" in c.detalle
    items[1]["cita_dato"] = "NO"
    assert not criterios(medir(items, origenes))["Falsos rechazos sobre las `buena`"].pasa


def test_caso_valido_con_buena_debe_conservar_alguna():
    items = [dict(i) for i in BASE_ITEMS]
    items[2]["cita_dato"] = "NO python"  # valido-01 pierde su única buena
    c = criterios(medir(items, BASE_ORIGEN))["Casos válidos con al menos una `buena` conservada"]
    assert (c.cumplen, c.total, c.pasa) == (2, 3, False)
    assert "sin ninguna conservada: valido-01" in c.detalle


def test_caso_valido_sin_buenas_se_lista_aparte_y_no_cuenta():
    c = criterios(medir(BASE_ITEMS, BASE_ORIGEN))[
        "Casos válidos con al menos una `buena` conservada"
    ]
    assert (c.cumplen, c.total) == (3, 3)
    assert "no cuentan): valido-02" in c.detalle


def test_las_dudosas_no_cuentan_en_los_umbrales_y_van_aparte():
    pares = medir(BASE_ITEMS, BASE_ORIGEN)
    totales = {c.nombre.split(" (")[0]: c.total for c in m.puerta(pares)}
    assert totales["Falsos aceptos sobre las `mala`"] == 4
    assert totales["Falsos rechazos sobre las `buena`"] == 2
    texto = m.reporte(pares)
    assert "## `dudosa` (fuera de los umbrales: 1)" in texto
    assert "Veredicto: conserva" in texto


def test_reporte_con_conteo_junto_al_porcentaje_y_listas_con_citas():
    items = [dict(i) for i in BASE_ITEMS]
    items[4]["cita_dato"] = "SI hectareas"
    texto = m.reporte(medir(items, BASE_ORIGEN))
    assert "1/4, 25,0%" in texto
    assert "## Falsos aceptos (1)" in texto and "Dato: SI hectareas" in texto
    assert "## Falsos rechazos (0)" in texto
    assert "| valido-01 | 1/1, 100,0% | 1/1, 100,0% | 0/0, sin muestra |" in texto


def test_usa_el_evaluador_real_por_defecto():
    items = [item("c-1", "buena", dato="Usan Go.", punto="Programo en Go.")]
    pares = m.evaluar(items, {"c-1": origen("valido-01")})
    assert pares[0].terminos == ("go",)


def escribir(tmp_path, items, origenes):
    etiquetado, orig = tmp_path / "etiquetado.json", tmp_path / "origen.json"
    etiquetado.write_text(json.dumps({"items": items}), encoding="utf-8")
    orig.write_text(json.dumps(origenes), encoding="utf-8")
    return etiquetado, orig


def test_items_sin_etiquetar_salen_con_codigo_distinto_de_0(tmp_path, capsys):
    items = [dict(i) for i in BASE_ITEMS]
    items[0]["etiqueta"] = ""
    etiquetado, orig = escribir(tmp_path, items, BASE_ORIGEN)
    assert m.main(["--etiquetado", str(etiquetado), "--origen", str(orig)]) == 1
    assert "sin etiquetar" in capsys.readouterr().err


def test_origen_que_no_corresponde_es_error(tmp_path):
    etiquetado, orig = escribir(tmp_path, BASE_ITEMS, {"c-1": origen("valido-01")})
    with pytest.raises(m.MedicionError):
        m.cargar(etiquetado, orig)


def test_no_modifica_los_archivos(tmp_path, capsys):
    etiquetado, orig = escribir(tmp_path, BASE_ITEMS, BASE_ORIGEN)
    antes = (etiquetado.read_bytes(), orig.read_bytes())
    assert m.main(["--etiquetado", str(etiquetado), "--origen", str(orig)]) == 0
    assert (etiquetado.read_bytes(), orig.read_bytes()) == antes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["etiquetado.json", "origen.json"]
    assert "# Medición de D4" in capsys.readouterr().out


def test_umbrales_fijos_en_el_codigo():
    assert (m.MAX_FALSOS_ACEPTOS_INSUFICIENTE, m.MAX_FALSOS_ACEPTOS_PCT,
            m.MAX_FALSOS_RECHAZOS_PCT) == (0, 10, 25)


def test_no_tiene_rutas_por_defecto_al_mini_set_real():
    # Para que solo se mida pasando las rutas a mano (T025).
    fuente = Path(m.__file__).read_text(encoding="utf-8")
    assert "default=" not in fuente
