import pytest

from outreach_agent.verificacion.texto import (
    contar_palabras,
    contiene_ancla,
    contiene_literal,
    contiene_normalizado,
    contiene_palabra,
    es_cifra,
    extraer_numeros,
    extraer_urls_emails,
    normalizar,
    normalizar_espacios,
)


def test_normalizar_espacios():
    assert normalizar_espacios("  hola \n\t mundo  ") == "hola mundo"


def test_normalizar_quita_mayusculas_tildes_y_puntuacion():
    assert normalizar("¡Espero que este MENSAJE te encuentre BIÉN!") == (
        "espero que este mensaje te encuentre bien"
    )
    assert normalizar("Diseño, niño") == "diseno nino"


def test_contar_palabras_separa_por_espacios():
    assert contar_palabras("Hola,  mundo.\nSegunda línea") == 4
    assert contar_palabras("") == 0


def test_contiene_literal_ignora_espacios_pero_no_mayusculas():
    texto = "Procesamos 2 millones\nde documentos al mes."
    assert contiene_literal(texto, "2 millones de documentos")
    assert not contiene_literal(texto, "2 MILLONES de documentos")
    assert not contiene_literal(texto, "")


def test_contiene_normalizado():
    assert contiene_normalizado("Usamos KUBERNETES en producción", "kubernetes en produccion")
    assert not contiene_normalizado("algo", "")


def test_contiene_palabra_no_encuentra_fragmentos():
    assert contiene_palabra("Soluciones de IA para bancos", "IA")
    assert not contiene_palabra("Trabajo en media y publicidad", "IA")
    assert contiene_palabra("Trabajamos con Mercado Libre.", "mercado libre")


def test_es_cifra():
    assert es_cifra("2")
    assert es_cifra("10.000")
    assert es_cifra("30%")
    assert not es_cifra("2 millones")
    assert not es_cifra("Kubernetes")


@pytest.mark.parametrize(
    "texto, ancla, esperado",
    [
        ("Lanzamos en 2024", "2", False),
        ("Trabajo en media y publicidad", "IA", False),
        ("Procesan 2 millones", "2", True),
        ("10,000 queries", "10.000", True),
        ("Redujo un 30% los tiempos", "30", True),
        ("Usamos Kubernetes", "kubernetes", True),
    ],
)
def test_contiene_ancla(texto, ancla, esperado):
    assert contiene_ancla(texto, ancla) is esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("En 2024 crecimos", ["2024"]),
        ("10.000 consultas y 10,000 queries", ["10000", "10000"]),
        ("1.234.567 usuarios", ["1234567"]),
        ("un 3,5% más y 3.14", ["3.5", "3.14"]),
        ("1.234,5 y 1,234.5", ["1234.5", "1234.5"]),
        ("un 30% menos", ["30"]),
        ("ZEBRA-7731", ["7731"]),
        ("sin números.", []),
    ],
)
def test_extraer_numeros(texto, esperado):
    assert extraer_numeros(texto) == esperado


def test_extraer_urls_emails():
    texto = "Mirá https://evil.example/x, www.empresa.com. Escribime a ana.perez@mail.com."
    assert extraer_urls_emails(texto) == [
        "https://evil.example/x",
        "www.empresa.com",
        "ana.perez@mail.com",
    ]
    assert extraer_urls_emails("sin enlaces") == []
