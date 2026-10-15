"""T001 (spec 002): mini-set de conexiones con trazas armadas a mano, sin Ollama."""

import json
from pathlib import Path

import pytest

from scripts import miniset_conexiones as m

PERFIL = (
    "Ingeniera de software con 6 años de experiencia en backend y datos.\n\n"
    "- Construí pipelines de imágenes en Python.\n"
    "- Diseñé un servicio en Go que recibe 50.000 eventos por minuto.\n"
)
CITA_H1 = "Hornean 12.000 medialunas por día."
CITA_H2 = "En 2023 abrieron su sexta sucursal."
CITA_H3 = "Usan Python para procesar imágenes."


def fin(nodo: str, detalle: dict) -> dict:
    return {"evento": "nodo_fin", "nodo": nodo, "intento": None, "detalle": detalle}


def eventos(validos: list[str], conexiones: list[tuple[str, str]] | None = None) -> list[dict]:
    hechos = [
        {"id": "H1", "descripcion": "d", "cita": CITA_H1, "ancla": "12.000"},
        {"id": "H2", "descripcion": "d", "cita": CITA_H2, "ancla": "2023"},
        {"id": "H3", "descripcion": "d", "cita": CITA_H3, "ancla": "Python"},
    ]
    lista = [
        fin("investigador", {"hechos": hechos}),
        fin("verificar_hechos", {"validos": validos}),
    ]
    if conexiones is not None:
        puntos = [
            {"id": "P1", "descripcion": "d", "cita": "Construí pipelines de imágenes", "ancla": "x"},
            {"id": "P9", "descripcion": "d", "cita": "Lidera equipos remotos", "ancla": "x"},
        ]
        lista.append(
            fin(
                "estratega",
                {
                    "angulo": "ángulo secreto",
                    "puntos_perfil": puntos,
                    "conexiones": [
                        {"hecho_id": h, "punto_id": p, "razon": "razón secreta"}
                        for h, p in conexiones
                    ],
                },
            )
        )
    return lista


def escribir_traza(ruta: Path, lista: list[dict]) -> None:
    ruta.write_text("".join(json.dumps(e) + "\n" for e in lista), encoding="utf-8")


@pytest.fixture
def entorno(tmp_path):
    corrida = tmp_path / "corrida"
    (corrida / "resultados").mkdir(parents=True)
    (corrida / "trazas").mkdir()
    casos = tmp_path / "casos"
    casos.mkdir()
    definiciones = {
        "valido-x": (["H1", "H2"], [("H1", "P1"), ("H2", "P9")]),
        "valido-y": (["H1", "H3"], None),  # H1 repetido en otro caso
        "insuficiente-z": (["H3"], None),  # menos de 2 válidos: no aporta pares
    }
    for caso, (validos, conexiones) in definiciones.items():
        run_id = f"run-{caso}"
        (corrida / "resultados" / f"{caso}.json").write_text(
            json.dumps({"run_id": run_id}), encoding="utf-8"
        )
        escribir_traza(corrida / "trazas" / f"{run_id}.jsonl", eventos(validos, conexiones))
        (casos / f"{caso}.json").write_text(json.dumps({"perfil": PERFIL}), encoding="utf-8")
    extra = tmp_path / "extra.jsonl"
    escribir_traza(extra, eventos(["H1", "H2"], [("H2", "P1")]))
    return corrida, extra, casos, tmp_path / "salida"


def generar(entorno) -> tuple[dict, dict]:
    corrida, extra, casos, salida = entorno
    m.generar(corrida, [extra], casos, salida)
    para = json.loads((salida / "para_etiquetar.json").read_text(encoding="utf-8"))
    origen = json.loads((salida / "origen.json").read_text(encoding="utf-8"))
    return para, origen


def test_oraciones_del_perfil_sin_vinetas_ni_lineas_vacias():
    assert m.oraciones_del_perfil(PERFIL) == [
        "Ingeniera de software con 6 años de experiencia en backend y datos.",
        "Construí pipelines de imágenes en Python.",
        "Diseñé un servicio en Go que recibe 50.000 eventos por minuto.",
    ]


def test_producto_cartesiano_sin_duplicados_mas_propuesta_fuera_del_perfil(entorno):
    para, origen = generar(entorno)
    pares = [(i["cita_dato"], i["cita_punto"]) for i in para["items"]]
    # 3 citas distintas (H1, H2 de valido-x; H3 de valido-y) × 3 oraciones = 9,
    # más la propuesta H2→P9, cuya cita no está en ninguna oración del perfil.
    assert len(pares) == 10
    assert len(set(pares)) == len(pares)
    assert (CITA_H2, "Lidera equipos remotos") in pares
    # H1→P1 propuesta: se funde con el par del cartesiano (misma oración del perfil).
    id_h1_p1 = m.id_opaco(CITA_H1, "Construí pipelines de imágenes en Python.")
    assert origen[id_h1_p1]["propuesta_por_estratega"] is True
    assert {"caso": "valido-y", "hecho_id": "H1"} in origen[id_h1_p1]["casos"]


def test_casos_con_menos_de_dos_validos_no_aportan(entorno):
    _, origen = generar(entorno)
    casos = {c["caso"] for registro in origen.values() for c in registro["casos"]}
    assert "insuficiente-z" not in casos


def test_para_etiquetar_no_filtra_origen_razon_angulo_ni_veredicto(entorno):
    para, _ = generar(entorno)
    assert para["definicion"].startswith("Buena:") and "Dudosa:" in para["definicion"]
    texto = json.dumps(para, ensure_ascii=False)
    for prohibido in ("valido-x", "valido-y", "insuficiente", "run:", "razón secreta",
                      "ángulo secreto", "propuesta", "veredicto", "caso"):
        assert prohibido not in texto
    for item in para["items"]:
        assert set(item) == {"id", "cita_dato", "cita_punto", "etiqueta", "nota"}
        assert item["etiqueta"] == ""


def test_ids_estables_y_orden_reproducible(entorno, tmp_path):
    para_1, _ = generar(entorno)
    corrida, extra, casos, _ = entorno
    otra = tmp_path / "otra"
    m.generar(corrida, [extra], casos, otra)
    para_2 = json.loads((otra / "para_etiquetar.json").read_text(encoding="utf-8"))
    assert [i["id"] for i in para_1["items"]] == [i["id"] for i in para_2["items"]]
    assert all(i["id"] == m.id_opaco(i["cita_dato"], i["cita_punto"]) for i in para_1["items"])


def test_no_sobrescribe_un_archivo_con_etiquetas(entorno):
    corrida, extra, casos, salida = entorno
    m.generar(corrida, [extra], casos, salida)
    ruta = salida / "para_etiquetar.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["items"][0]["etiqueta"] = "buena"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(m.MinisetError):
        m.generar(corrida, [extra], casos, salida)
    assert json.loads(ruta.read_text(encoding="utf-8"))["items"][0]["etiqueta"] == "buena"


def test_sin_etiquetas_se_puede_regenerar(entorno):
    corrida, extra, casos, salida = entorno
    m.generar(corrida, [extra], casos, salida)
    assert m.generar(corrida, [extra], casos, salida) == 10


def test_perfiles_distintos_es_error(entorno):
    corrida, extra, casos, salida = entorno
    (casos / "otro.json").write_text(json.dumps({"perfil": "otro perfil"}), encoding="utf-8")
    with pytest.raises(m.MinisetError):
        m.generar(corrida, [extra], casos, salida)


def test_el_script_no_lee_las_ofertas_de_validacion():
    fuente = Path(m.__file__).read_text(encoding="utf-8")
    assert "validacion_ids" not in fuente
    assert "ofertas" not in fuente
