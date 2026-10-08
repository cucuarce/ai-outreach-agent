from outreach_agent.modelos import Entrada, Hecho
from outreach_agent.verificacion.hechos import verificar_hechos
from tests import escenarios


def verificar(*candidatos):
    estado = {
        "entrada": Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL),
        "hechos_candidatos": list(candidatos),
    }
    return verificar_hechos(estado)


def test_candidatos_validos_pasan():
    resultado = verificar(*escenarios.hechos())
    assert [h.id for h in resultado["hechos"]] == ["H1", "H2", "H3"]
    assert resultado["hechos_descartados"] == []


def test_cita_con_espacios_distintos_se_localiza():
    hecho = Hecho("H1", "d", "procesa  2 millones\nde transacciones", "2")
    assert [h.id for h in verificar(hecho)["hechos"]] == ["H1"]


def test_cita_no_localizable():
    hecho = Hecho("H9", "d", "factura 50 millones de dólares", "50")
    assert verificar(hecho)["hechos_descartados"] == [{"id": "H9", "causa": "cita_no_localizable"}]


def test_ancla_fuera_de_cita():
    hecho = Hecho("H9", "d", "Migramos toda la infraestructura a Kubernetes en 2024", "Docker")
    assert verificar(hecho)["hechos_descartados"] == [{"id": "H9", "causa": "ancla_fuera_de_cita"}]


def test_ancla_cifra_debe_ser_un_numero_completo_de_la_cita():
    hecho = Hecho("H9", "d", "Migramos toda la infraestructura a Kubernetes en 2024", "2")
    assert verificar(hecho)["hechos_descartados"] == [{"id": "H9", "causa": "ancla_fuera_de_cita"}]


def test_cita_demasiado_larga():
    hecho = Hecho("H9", "d", escenarios.TEXTO_EMPRESA, "Nubeluz")  # > 300 caracteres
    assert verificar(hecho)["hechos_descartados"] == [
        {"id": "H9", "causa": "cita_demasiado_larga"}
    ]


def test_duplicado():
    original = Hecho("H1", "d", "procesa 2 millones de transacciones al mes", "2")
    copia = Hecho("H2", "otra", "procesa 2 millones de transacciones al mes", "2")
    resultado = verificar(original, copia)
    assert [h.id for h in resultado["hechos"]] == ["H1"]
    assert resultado["hechos_descartados"] == [{"id": "H2", "causa": "duplicado"}]
