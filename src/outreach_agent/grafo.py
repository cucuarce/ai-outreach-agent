"""Grafo LangGraph del flujo de outreach (plan.md § Diseño, research R1).

Versión mínima de la Historia 1 (paso A): lineal y sin verificaciones.

    START → preparar_entrada → investigador → estratega → redactor → finalizar → END

Los nodos de verificación (verificar_hechos, verificar_estrategia, validar_borrador) y las
aristas condicionales se agregan en el paso B.
"""

from langgraph.graph import END, START, StateGraph

from outreach_agent.agentes.base import RespuestaInvalidaLLM
from outreach_agent.agentes.estratega import estratega, hechos_disponibles
from outreach_agent.agentes.investigador import investigador
from outreach_agent.agentes.redactor import redactor
from outreach_agent.config import Config
from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import Entrada, Estado, Motivo, Resultado
from outreach_agent.proveedores.base import LLMProvider, ProviderError
from outreach_agent.verificacion.entrada import nuevo_run_id, preparar_entrada


def finalizar(estado: EstadoGrafo) -> dict:
    """Arma el Resultado a partir del estado final. Si un nodo anterior ya cortó la ejecución
    con un resultado, lo deja como está."""
    if "resultado" in estado:
        return {}
    borrador = estado["borrador"]
    usados_h = set(borrador.hechos_usados)
    usados_p = set(borrador.puntos_usados)
    resultado = Resultado(
        estado=Estado.BORRADOR,
        run_id=estado["run_id"],
        idioma=estado.get("idioma_objetivo"),
        borrador=borrador,
        hechos_usados=[h for h in hechos_disponibles(estado) if h.id in usados_h],
        puntos_usados=[p for p in estado["estrategia"].puntos_perfil if p.id in usados_p],
    )
    return {"resultado": resultado}


def construir_grafo(provider: LLMProvider, config: Config):
    """Compila el grafo. Los agentes reciben el proveedor y la configuración por clausura, así
    el estado solo contiene datos."""
    grafo = StateGraph(EstadoGrafo)

    grafo.add_node("preparar_entrada", preparar_entrada)
    grafo.add_node("investigador", lambda estado: investigador(estado, provider, config))
    grafo.add_node("estratega", lambda estado: estratega(estado, provider, config))
    grafo.add_node("redactor", lambda estado: redactor(estado, provider, config))
    grafo.add_node("finalizar", finalizar)

    grafo.add_edge(START, "preparar_entrada")
    grafo.add_edge("preparar_entrada", "investigador")
    grafo.add_edge("investigador", "estratega")
    grafo.add_edge("estratega", "redactor")
    grafo.add_edge("redactor", "finalizar")
    grafo.add_edge("finalizar", END)

    return grafo.compile()


def ejecutar(entrada: Entrada, provider: LLMProvider, config: Config) -> Resultado:
    """Corre el grafo completo y siempre devuelve un Resultado, también ante errores del
    proveedor o respuestas inválidas del LLM."""
    run_id = nuevo_run_id()
    try:
        final = construir_grafo(provider, config).invoke({"entrada": entrada, "run_id": run_id})
    except ProviderError as error:
        return Resultado(
            estado=Estado.ERROR, run_id=run_id, motivo=Motivo(error.motivo), detalle=str(error)
        )
    except RespuestaInvalidaLLM as error:
        return Resultado(
            estado=Estado.ERROR,
            run_id=run_id,
            motivo=Motivo.RESPUESTA_INVALIDA_LLM,
            detalle=f"El modelo no devolvió una respuesta válida: {error}",
        )
    return final["resultado"]
