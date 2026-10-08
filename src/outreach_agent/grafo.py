"""Grafo LangGraph del flujo de outreach (plan.md § Diseño, research R1 y R2).

    START → preparar_entrada ─(sin idioma)→ END
                ↓
            investigador → verificar_hechos → estratega → verificar_estrategia
                → redactor → validar_borrador ─(ok)→ finalizar → END
                     ↑             │
                     └─(falla y quedan reintentos)
                                   └─(falla sin reintentos)→ finalizar → END

Los tres agentes (investigador, estratega, redactor) llaman al LLM; el resto de los nodos son
deterministas. Las decisiones de ruteo dependen solo de campos ya verificados del estado.
Los cortes por datos insuficientes después de verificar_hechos y verificar_estrategia se
agregan en la Historia 2.
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
from outreach_agent.verificacion.borrador import nodo_validar_borrador
from outreach_agent.verificacion.entrada import nuevo_run_id, preparar_entrada
from outreach_agent.verificacion.estrategia import verificar_estrategia
from outreach_agent.verificacion.hechos import verificar_hechos


def finalizar(estado: EstadoGrafo) -> dict:
    """Arma el Resultado a partir del estado final. Si un nodo anterior ya cortó la ejecución
    con un resultado, lo deja como está."""
    if "resultado" in estado:
        return {}
    empresa = {
        "nombre_empresa": estado.get("nombre_empresa"),
        "origen_nombre_empresa": estado.get("origen_nombre_empresa"),
    }
    validacion = estado.get("validacion")
    if validacion is not None and not validacion.ok:
        intentos = estado.get("intento", 0)
        resultado = Resultado(
            estado=Estado.INVALIDO,
            run_id=estado["run_id"],
            idioma=estado.get("idioma_objetivo"),
            motivo=Motivo.VALIDACION_FALLIDA,
            detalle=f"No se logró un borrador válido en {intentos} intento(s) de redacción.",
            fallos=validacion.fallos,
            **empresa,
        )
        return {"resultado": resultado}

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
        **empresa,
    )
    return {"resultado": resultado}


def ruta_despues_de_preparar(estado: EstadoGrafo) -> str:
    return END if "resultado" in estado else "investigador"


def ruta_despues_de_validar(max_reintentos: int):
    def ruta(estado: EstadoGrafo) -> str:
        if estado["validacion"].ok:
            return "finalizar"
        if estado["intento"] < 1 + max_reintentos:
            return "redactor"
        return "finalizar"

    return ruta


def construir_grafo(provider: LLMProvider, config: Config):
    """Compila el grafo. Los agentes reciben el proveedor y la configuración por clausura, así
    el estado solo contiene datos."""
    grafo = StateGraph(EstadoGrafo)

    grafo.add_node("preparar_entrada", preparar_entrada)
    grafo.add_node("investigador", lambda estado: investigador(estado, provider, config))
    grafo.add_node("verificar_hechos", verificar_hechos)
    grafo.add_node("estratega", lambda estado: estratega(estado, provider, config))
    grafo.add_node("verificar_estrategia", verificar_estrategia)
    grafo.add_node("redactor", lambda estado: redactor(estado, provider, config))
    grafo.add_node("validar_borrador", nodo_validar_borrador)
    grafo.add_node("finalizar", finalizar)

    grafo.add_edge(START, "preparar_entrada")
    grafo.add_conditional_edges(
        "preparar_entrada", ruta_despues_de_preparar, ["investigador", END]
    )
    grafo.add_edge("investigador", "verificar_hechos")
    grafo.add_edge("verificar_hechos", "estratega")
    grafo.add_edge("estratega", "verificar_estrategia")
    grafo.add_edge("verificar_estrategia", "redactor")
    grafo.add_edge("redactor", "validar_borrador")
    grafo.add_conditional_edges(
        "validar_borrador",
        ruta_despues_de_validar(config.max_reintentos),
        ["redactor", "finalizar"],
    )
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
