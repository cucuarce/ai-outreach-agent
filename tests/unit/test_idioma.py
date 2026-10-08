import pytest

from outreach_agent.verificacion.idioma import detectar_idioma

PARRAFOS = {
    "es": (
        "Somos una empresa de software que desarrolla herramientas para la gestión de "
        "inventario. Nuestro equipo trabaja desde Buenos Aires y tiene clientes en toda la "
        "región, con una plataforma que se usa todos los días en más de mil comercios."
    ),
    "en": (
        "We are a software company that builds tools for inventory management. Our team "
        "works from Buenos Aires and has clients across the region, with a platform that is "
        "used every day by more than a thousand stores."
    ),
    "pt": (
        "Somos uma empresa de software que desenvolve ferramentas para a gestão de estoque. "
        "Nossa equipe trabalha em São Paulo e tem clientes em toda a região, com uma "
        "plataforma que é usada todos os dias em mais de mil lojas."
    ),
    "fr": (
        "Nous sommes une entreprise de logiciels qui développe des outils pour la gestion "
        "des stocks. Notre équipe travaille depuis Lyon et elle a des clients dans toute la "
        "région, avec une plateforme qui est utilisée tous les jours par plus de mille magasins."
    ),
    "de": (
        "Wir sind ein Softwareunternehmen, das Werkzeuge für die Lagerverwaltung entwickelt. "
        "Unser Team arbeitet in Berlin und hat Kunden in der ganzen Region, mit einer "
        "Plattform, die jeden Tag von mehr als tausend Geschäften genutzt wird."
    ),
    "it": (
        "Siamo un'azienda di software che sviluppa strumenti per la gestione del magazzino. "
        "Il nostro team lavora da Milano e ha clienti in tutta la regione, con una "
        "piattaforma che è usata ogni giorno da più di mille negozi."
    ),
}


@pytest.mark.parametrize("idioma", list(PARRAFOS))
def test_detecta_cada_idioma_soportado(idioma):
    assert detectar_idioma(PARRAFOS[idioma]) == idioma


def test_texto_mixto_gana_el_predominante():
    texto = PARRAFOS["en"] + " " + PARRAFOS["en"] + " Gracias por la oportunidad."
    assert detectar_idioma(texto) == "en"


def test_texto_de_tres_palabras_es_indeterminado():
    assert detectar_idioma("Kubernetes Python Go") is None


def test_texto_vacio_es_indeterminado():
    assert detectar_idioma("") is None


def test_idioma_no_soportado_es_indeterminado():
    japones = (
        "私たちは在庫管理のためのツールを開発するソフトウェア会社です。"
        "チームは東京で働いており、地域全体に顧客がいます。"
    )
    assert detectar_idioma(japones) is None
