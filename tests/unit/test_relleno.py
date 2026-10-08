from outreach_agent.verificacion.relleno import (
    ejemplos_relleno,
    encontrar_relleno,
    frases_relleno,
)
from tests import escenarios


def test_lista_tiene_las_frases_de_la_spec_expandidas():
    es = frases_relleno("es")
    en = frases_relleno("en")
    assert "Espero que este mensaje te encuentre bien" in es
    assert {"Soy una persona apasionada", "Soy una persona proactiva"} <= set(es)
    assert "Me pongo en contacto con usted para" in es  # sin "…"
    assert "I am a results-driven professional" in en
    assert len(es) == 15 and len(en) == 14
    assert frases_relleno("pt") == []


def test_detecta_con_mayusculas_y_tildes_distintas():
    texto = "ESPERO QUE ESTE MENSAJE TE ENCUENTRE BIÉN. Quería contarte algo."
    assert encontrar_relleno(texto) == ["Espero que este mensaje te encuentre bien"]


def test_detecta_las_frases_del_checkpoint_de_la_historia_1():
    texto = "Me siento entusiasmado con la oportunidad de unirme a su equipo."
    assert encontrar_relleno(texto) == ["Me siento entusiasmado con la oportunidad"]
    assert encontrar_relleno("Estoy ansioso por contribuir a la innovación.") == [
        "Estoy ansioso por contribuir"
    ]


def test_detecta_frases_de_cualquier_idioma():
    texto = "Hola. I look forward to hearing from you."
    assert encontrar_relleno(texto) == ["I look forward to hearing from you"]


def test_sin_falsos_positivos_en_un_borrador_sin_relleno():
    assert encontrar_relleno(escenarios.TEXTO_BORRADOR) == []


def test_ejemplos_relleno():
    assert len(ejemplos_relleno("es")) == 3
    assert ejemplos_relleno("it") == []
    assert ejemplos_relleno(None) == []
