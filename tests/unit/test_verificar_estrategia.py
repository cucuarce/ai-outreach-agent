import copy

from outreach_agent.modelos import Entrada
from outreach_agent.verificacion.estrategia import verificar_estrategia
from tests import escenarios


def verificar(datos_estrategia, hechos=None):
    estado = {
        "run_id": "prueba",
        "entrada": Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL),
        "hechos": escenarios.hechos() if hechos is None else hechos,
        "estrategia": escenarios.estrategia(datos_estrategia),
    }
    return verificar_estrategia(estado)


def test_estrategia_valida_queda_igual():
    resultado = verificar(escenarios.ESTRATEGA)
    assert resultado["estrategia"] == escenarios.estrategia()
    assert resultado["puntos_descartados"] == []


def test_filtra_hechos_no_verificados():
    datos = copy.deepcopy(escenarios.ESTRATEGA)
    datos["hechos_elegidos"] = ["H1", "H2", "H7"]
    resultado = verificar(datos)
    assert resultado["estrategia"].hechos_elegidos == ["H1", "H2"]


def test_descarta_punto_con_cita_inventada_y_sus_conexiones():
    datos = copy.deepcopy(escenarios.ESTRATEGA)
    datos["puntos_perfil"][0]["cita"] = "lideré un equipo de 200 personas en Google"
    resultado = verificar(datos)
    assert [p.id for p in resultado["estrategia"].puntos_perfil] == ["P2"]
    assert resultado["puntos_descartados"] == [{"id": "P1", "causa": "cita_no_localizable"}]
    assert [c.punto_id for c in resultado["estrategia"].conexiones] == ["P2"]


def test_descarta_punto_con_ancla_fuera_de_cita():
    datos = copy.deepcopy(escenarios.ESTRATEGA)
    datos["puntos_perfil"][1]["ancla"] = "50"
    resultado = verificar(datos)
    assert resultado["puntos_descartados"] == [{"id": "P2", "causa": "ancla_fuera_de_cita"}]


def test_descarta_conexiones_con_hecho_no_verificado():
    hechos = [h for h in escenarios.hechos() if h.id != "H2"]
    resultado = verificar(escenarios.ESTRATEGA, hechos=hechos)
    assert [(c.hecho_id, c.punto_id) for c in resultado["estrategia"].conexiones] == [
        ("H1", "P2")
    ]
