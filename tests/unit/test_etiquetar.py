"""Etiquetado manual del mini-set (spec 002, T003) con un archivo chico en tmp_path."""

import json
from pathlib import Path

import pytest

from scripts import etiquetar as m

ITEMS = [
    {"id": "c-aaaa1111", "cita_dato": "Dato uno.", "cita_punto": "Punto uno.",
     "etiqueta": "", "nota": ""},
    {"id": "c-bbbb2222", "cita_dato": "Dato dos.", "cita_punto": "Punto dos.",
     "etiqueta": "", "nota": ""},
    {"id": "c-cccc3333", "cita_dato": "Dato tres.", "cita_punto": "Punto tres.",
     "etiqueta": "", "nota": ""},
]


@pytest.fixture
def rutas(tmp_path):
    entrada = tmp_path / "para_etiquetar.json"
    entrada.write_text(
        json.dumps({"definicion": "Buena: ...", "semilla_orden": 42, "items": ITEMS}),
        encoding="utf-8",
    )
    return entrada, tmp_path / "etiquetado.json"


def respuestas(*valores):
    pendientes = list(valores)

    def leer(_prompt):
        if not pendientes:
            raise EOFError
        return pendientes.pop(0)

    return leer


def correr(rutas, *valores) -> list[str]:
    salida = []
    m.etiquetar(*rutas, leer=respuestas(*valores), escribir=salida.append)
    return salida


def etiquetas(salida: Path) -> list[str]:
    return [i["etiqueta"] for i in json.loads(salida.read_text(encoding="utf-8"))["items"]]


def test_muestra_solo_las_citas_y_el_contador(rutas):
    texto = "\n".join(correr(rutas, "q"))
    assert "1 de 3" in texto
    assert "Dato:  Dato uno." in texto and "Punto: Punto uno." in texto
    assert "c-aaaa1111" not in texto
    for prohibido in ("caso", "razon", "razón", "veredicto", "origen"):
        assert prohibido not in texto.lower()


def test_b_m_d_etiquetan_y_avanzan(rutas):
    correr(rutas, "b", "m", "d")
    assert etiquetas(rutas[1]) == ["buena", "mala", "dudosa"]


def test_guarda_despues_de_cada_respuesta(rutas):
    entrada, salida = rutas
    vistos = []

    def leer(_prompt):
        vistos.append(etiquetas(salida) if salida.exists() else None)
        if len(vistos) == 1:
            return "b"
        if len(vistos) == 2:
            return "m"
        raise EOFError

    m.etiquetar(entrada, salida, leer=leer, escribir=lambda _: None)
    assert vistos == [None, ["buena", "", ""], ["buena", "mala", ""]]


def test_retoma_desde_el_primer_item_sin_etiqueta(rutas):
    correr(rutas, "b", "q")
    texto = "\n".join(correr(rutas, "q"))
    assert "2 de 3" in texto and "1 de 3" not in texto


def test_a_vuelve_al_anterior_y_permite_cambiar_la_etiqueta(rutas):
    texto = "\n".join(correr(rutas, "b", "a", "m", "q"))
    assert "(ya etiquetado por vos: buena)" in texto
    assert etiquetas(rutas[1]) == ["mala", "", ""]


def test_a_en_el_primer_item_no_se_mueve(rutas):
    texto = "\n".join(correr(rutas, "a", "q"))
    assert "Ya estás en el primer ítem." in texto
    assert texto.count("1 de 3") == 2


def test_respuesta_invalida_repite_el_item(rutas):
    texto = "\n".join(correr(rutas, "x", "b", "q"))
    assert "Respuesta no válida." in texto
    assert etiquetas(rutas[1]) == ["buena", "", ""]


def test_al_llegar_al_final_vuelve_al_primero_sin_etiqueta(rutas):
    # Quedan etiquetados el 1 y el 3; al retomar se muestra el 2, y después de responderlo no
    # queda ninguno sin etiqueta.
    correr(rutas, "b", "q")
    entrada, salida = rutas
    datos = json.loads(salida.read_text(encoding="utf-8"))
    datos["items"][2]["etiqueta"] = "mala"
    salida.write_text(json.dumps(datos), encoding="utf-8")
    correr(rutas, "d")
    assert etiquetas(salida) == ["buena", "dudosa", "mala"]


def test_todo_etiquetado_no_pregunta(rutas):
    correr(rutas, "b", "b", "b")
    texto = "\n".join(correr(rutas))
    assert "Los 3 ítems ya están etiquetados." in texto


def test_fin_de_entrada_guarda_y_sale(rutas):
    texto = "\n".join(correr(rutas, "m"))
    assert etiquetas(rutas[1]) == ["mala", "", ""]
    assert "Etiquetados: 1/3." in texto


def test_no_modifica_el_archivo_de_entrada(rutas):
    entrada, _ = rutas
    antes = entrada.read_text(encoding="utf-8")
    correr(rutas, "b", "m", "d")
    assert entrada.read_text(encoding="utf-8") == antes


def test_etiquetado_de_otro_mini_set_es_error(rutas):
    entrada, salida = rutas
    salida.write_text(json.dumps({"items": [{"id": "c-otro", "etiqueta": "buena"}]}),
                      encoding="utf-8")
    with pytest.raises(m.EtiquetadoError):
        m.etiquetar(entrada, salida, leer=respuestas("q"), escribir=lambda _: None)


def test_el_script_no_evalua_ni_lee_origen():
    fuente = Path(m.__file__).read_text(encoding="utf-8")
    assert "origen.json" not in fuente
    assert "import outreach_agent" not in fuente and "from outreach_agent" not in fuente
