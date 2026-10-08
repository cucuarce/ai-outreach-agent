"""T033i: hechos_disponibles distingue "sin verificar" de "todos descartados"."""

from outreach_agent.agentes.estratega import hechos_disponibles
from tests import escenarios


def test_todos_los_candidatos_descartados_devuelve_lista_vacia():
    estado = {"hechos_candidatos": escenarios.hechos(), "hechos": []}
    assert hechos_disponibles(estado) == []


def test_sin_verificacion_devuelve_los_candidatos():
    estado = {"hechos_candidatos": escenarios.hechos()}
    assert hechos_disponibles(estado) == escenarios.hechos()


def test_con_verificacion_devuelve_los_verificados():
    verificados = escenarios.hechos()[:1]
    estado = {"hechos_candidatos": escenarios.hechos(), "hechos": verificados}
    assert hechos_disponibles(estado) == verificados
