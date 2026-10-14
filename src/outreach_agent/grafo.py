"""Grafo LangGraph del flujo de outreach (plan.md § Diseño, research R1 y R2).

    START → preparar_entrada ─(sin idioma o entradas vacías)→ END
                ↓
            investigador → verificar_hechos ─(< 2 hechos)→ finalizar
                ↓
            estratega → verificar_estrategia ─(sin puntos o sin conexiones)→ finalizar
                ↓
            redactor → validar_borrador ─(ok)→ finalizar → END
                ↑             │
                └─(falla y quedan reintentos)
                              └─(falla sin reintentos o borrador repetido)→ finalizar → END

Los tres agentes (investigador, estratega, redactor) llaman al LLM; el resto de los nodos son
deterministas. Las decisiones de ruteo dependen solo de campos ya verificados del estado.

Cada nodo se envuelve con `trazas.trazado` al construir el grafo: cada transición queda en la
traza JSONL de la ejecución (principio V) y, al terminar, en el registro legible `.md`.
"""

import time
from dataclasses import replace

from langgraph.graph import END, START, StateGraph

from outreach_agent.agentes import estratega as mod_estratega
from outreach_agent.agentes import investigador as mod_investigador
from outreach_agent.agentes import redactor as mod_redactor
from outreach_agent.agentes.base import RespuestaInvalidaLLM
from outreach_agent.agentes.estratega import hechos_disponibles
from outreach_agent.config import Config
from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import ElementoUsado, Entrada, Estado, Motivo, Resultado
from outreach_agent.proveedores.base import LLMProvider, ProviderError
from outreach_agent.trazas import Traza, nuevo_run_id, trazado
from outreach_agent.verificacion import borrador as mod_borrador
from outreach_agent.verificacion import entrada as mod_entrada
from outreach_agent.verificacion import estrategia as mod_estrategia
from outreach_agent.verificacion import hechos as mod_hechos
from outreach_agent.verificacion.cortes import invalidar

AGENTE = "agente"
DETERMINISTA = "determinista"


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
        detalle = f"No se logró un borrador válido en {intentos} intento(s) de redacción."
        return invalidar(estado, validacion.fallos, detalle)

    borrador = estado["borrador"]
    usados_h = set(borrador.hechos_usados)
    usados_p = set(borrador.puntos_usados)
    resultado = Resultado(
        estado=Estado.BORRADOR,
        run_id=estado["run_id"],
        idioma=estado.get("idioma_objetivo"),
        borrador=borrador,
        hechos_usados=[
            ElementoUsado.de(h) for h in hechos_disponibles(estado) if h.id in usados_h
        ],
        puntos_usados=[
            ElementoUsado.de(p) for p in estado["estrategia"].puntos_perfil if p.id in usados_p
        ],
        **empresa,
    )
    return {"resultado": resultado}


def resumir_finalizar(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    resultado = actualizacion.get("resultado") or estado["resultado"]
    motivo = resultado.motivo.value if resultado.motivo else None
    decision = f"resultado: {resultado.estado.value}" + (f" ({motivo})" if motivo else "")
    return decision, {"estado": resultado.estado.value, "motivo": motivo}


def ruta_despues_de_preparar(estado: EstadoGrafo) -> str:
    return END if "resultado" in estado else "investigador"


def ruta_despues_de_verificar_hechos(estado: EstadoGrafo) -> str:
    # verificar_hechos deja un resultado si hay menos de 2 hechos válidos.
    return "finalizar" if "resultado" in estado else "estratega"


def ruta_despues_de_verificar_estrategia(estado: EstadoGrafo) -> str:
    # verificar_estrategia deja un resultado si no quedan puntos del perfil o conexiones.
    return "finalizar" if "resultado" in estado else "redactor"


def ruta_despues_de_validar(max_reintentos: int):
    def ruta(estado: EstadoGrafo) -> str:
        # validar_borrador deja un resultado si el redactor repitió el borrador anterior.
        if "resultado" in estado or estado["validacion"].ok:
            return "finalizar"
        if estado["intento"] < 1 + max_reintentos:
            return "redactor"
        return "finalizar"

    return ruta


def _intento_redactor(estado: EstadoGrafo) -> int:
    return estado.get("intento", 0) + 1  # el intento que está por empezar


def _intento_validacion(estado: EstadoGrafo) -> int | None:
    return estado.get("intento")  # el intento que se está validando


def construir_grafo(provider: LLMProvider, config: Config, traza: Traza):
    """Compila el grafo. Los agentes reciben el proveedor y la configuración por clausura, así
    el estado solo contiene datos. Cada nodo se envuelve con `trazado` para la traza de esta
    ejecución."""
    # nombre: (tipo de nodo, función del nodo, resumir para la traza, número de intento)
    nodos = {
        "preparar_entrada": (
            DETERMINISTA, mod_entrada.preparar_entrada, mod_entrada.resumir, None
        ),
        "investigador": (
            AGENTE,
            lambda estado: mod_investigador.investigador(estado, provider, config),
            mod_investigador.resumir,
            None,
        ),
        "verificar_hechos": (
            DETERMINISTA, mod_hechos.verificar_hechos, mod_hechos.resumir, None
        ),
        "estratega": (
            AGENTE,
            lambda estado: mod_estratega.estratega(estado, provider, config),
            mod_estratega.resumir,
            None,
        ),
        "verificar_estrategia": (
            DETERMINISTA, mod_estrategia.verificar_estrategia, mod_estrategia.resumir, None
        ),
        "redactor": (
            AGENTE,
            lambda estado: mod_redactor.redactor(estado, provider, config),
            mod_redactor.resumir,
            _intento_redactor,
        ),
        "validar_borrador": (
            DETERMINISTA,
            mod_borrador.nodo_validar_borrador,
            mod_borrador.resumidor(config.max_reintentos),
            _intento_validacion,
        ),
        "finalizar": (DETERMINISTA, finalizar, resumir_finalizar, None),
    }

    grafo = StateGraph(EstadoGrafo)
    for nombre, (tipo, funcion, resumir, intento_de) in nodos.items():
        grafo.add_node(nombre, trazado(traza, nombre, tipo, resumir, intento_de)(funcion))

    grafo.add_edge(START, "preparar_entrada")
    grafo.add_conditional_edges(
        "preparar_entrada", ruta_despues_de_preparar, ["investigador", END]
    )
    grafo.add_edge("investigador", "verificar_hechos")
    grafo.add_conditional_edges(
        "verificar_hechos", ruta_despues_de_verificar_hechos, ["estratega", "finalizar"]
    )
    grafo.add_edge("estratega", "verificar_estrategia")
    grafo.add_conditional_edges(
        "verificar_estrategia", ruta_despues_de_verificar_estrategia, ["redactor", "finalizar"]
    )
    grafo.add_edge("redactor", "validar_borrador")
    grafo.add_conditional_edges(
        "validar_borrador",
        ruta_despues_de_validar(config.max_reintentos),
        ["redactor", "finalizar"],
    )
    grafo.add_edge("finalizar", END)

    return grafo.compile()


def _correr_grafo(
    entrada: Entrada, provider: LLMProvider, config: Config, traza: Traza
) -> Resultado:
    run_id = traza.run_id
    try:
        grafo = construir_grafo(provider, config, traza)
        return grafo.invoke({"entrada": entrada, "run_id": run_id})["resultado"]
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


def ejecutar(entrada: Entrada, provider: LLMProvider, config: Config) -> Resultado:
    """Corre el grafo completo y siempre devuelve un Resultado, también ante errores del
    proveedor o respuestas inválidas del LLM. Siempre deja la traza y el registro legible."""
    traza = Traza(config.dir_registros, nuevo_run_id())
    inicio = time.perf_counter()
    traza.emitir(
        "ejecucion_inicio",
        decision="inicio de la ejecución",
        detalle={
            "proveedor": provider.nombre,
            "modelo": config.modelo,
            "idioma_solicitado": entrada.idioma_solicitado,
            "nombre_empresa_solicitado": entrada.nombre_empresa_solicitado,
            "caracteres_empresa": len(entrada.texto_empresa),
            "caracteres_perfil": len(entrada.perfil),
            "max_reintentos": config.max_reintentos,
        },
    )

    resultado = _correr_grafo(entrada, provider, config, traza)
    resultado = replace(resultado, rutas_registro=traza.rutas())

    traza.emitir(
        "ejecucion_fin",
        decision=f"estado final: {resultado.estado.value}",
        detalle={
            "estado": resultado.estado.value,
            "motivo": resultado.motivo.value if resultado.motivo else None,
            "detalle": resultado.detalle,
            "fallos": [{"criterio": f.criterio, "detalle": f.detalle} for f in resultado.fallos],
            "borrador": resultado.borrador.texto if resultado.borrador else None,
        },
        duracion_ms=round((time.perf_counter() - inicio) * 1000),
    )
    traza.escribir_md()
    return resultado
