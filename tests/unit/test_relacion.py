"""T023 (spec 002, research D4): relación por término compartido. Los ejemplos están inventados y
no son pares del mini-set."""

import json
from importlib import resources

from outreach_agent.verificacion.relacion import formas, terminos, terminos_compartidos


def test_go_cuenta_aunque_tenga_dos_letras():
    assert terminos_compartidos(
        "La API de pagos está escrita en Go.", "Mantuve microservicios en Go durante tres años."
    ) == ["go"]


def test_las_cifras_no_cuentan():
    assert terminos_compartidos(
        "Atienden 40.000 pedidos y 2.500 consultas en 2024.",
        "Migré 40.000 registros con 2.500 scripts en 2024.",
    ) == []


def test_imagenes_coincide_con_imagen():
    assert terminos_compartidos(
        "Clasifican imágenes de rayos X.", "Entrené un modelo de imagen médica."
    ) == ["imagen"]


def test_plural_con_s_coincide_con_el_singular():
    assert terminos_compartidos(
        "Orquestan pipelines nocturnos.", "Diseñé un pipeline de facturación."
    ) == ["pipeline"]


def test_los_terminos_genericos_no_cuentan():
    assert terminos_compartidos(
        "El equipo de la empresa trabaja en una plataforma propia cada semana.",
        "Lideré un equipo y migré la plataforma de la empresa en dos semanas.",
    ) == []
    assert terminos_compartidos(
        "Our team ships the platform every week.", "My team rebuilt the platform in a week."
    ) == []


def test_frase_que_afirma_el_encaje_sin_terminos_en_comun_no_es_relacion():
    # FR-011: solo cuentan las dos citas. Una cita que "afirma" la relación sin compartir
    # términos con el punto no produce relación.
    assert terminos_compartidos(
        "Este perfil encaja perfectamente con nosotros y la conexión es evidente.",
        "Construí tableros de ventas con Power BI.",
    ) == []


def test_stopwords_de_cualquier_idioma_no_cuentan():
    assert terminos_compartidos("We use it for the logs.", "Lo uso para que the logs.") == ["logs"]
    assert terminos_compartidos("Para todos los que están en el sector.", "Para todos.") == []


def test_puntuacion_dentro_de_palabra_se_conserva():
    assert terminos("Usan Node.js, CI/CD y Sentinel-2.") == ["usan", "node.js", "ci/cd", "sentinel-2"]
    assert terminos_compartidos("Procesan datos de Sentinel-2.", "Trabajé con Sentinel-2.") == [
        "sentinel-2"
    ]


def test_mayusculas_y_tildes_no_importan():
    assert terminos_compartidos("Usan PYTHON y Kubernetes.", "Programo en python.") == ["python"]
    assert terminos_compartidos("Automatización contable.", "Hice automatizacion de reportes.") == [
        "automatizacion"
    ]


def test_tokens_de_una_letra_no_cuentan():
    assert terminos("Usan R y C para x.") == ["usan"]


def test_formas_singulares():
    assert formas("imagenes") == {"imagenes", "imagene", "imagen"}
    assert formas("pipelines") == {"pipelines", "pipeline", "pipelin"}
    assert formas("claves") == {"claves", "clave", "clav"}
    assert formas("go") == {"go"}


def test_sin_relacion_con_citas_vacias():
    assert terminos_compartidos("", "Programo en Python.") == []
    assert terminos_compartidos("Usan Python.", "") == []


def test_la_lista_de_genericos_tiene_la_de_research_d4():
    datos = json.loads(
        resources.files("outreach_agent")
        .joinpath("data/terminos_genericos.json")
        .read_text("utf-8")
    )
    for termino in ("equipo", "empresa", "experiencia", "sistema", "plataforma", "año",
                    "semana", "día", "mes"):
        assert termino in datos["es"]
