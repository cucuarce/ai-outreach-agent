"""Nodo determinista verificar_hechos (research R3, R5 y R12).

Pasa a `hechos` los candidatos del investigador que se pueden comprobar contra el texto de la
empresa y deja el resto en `hechos_descartados` con su causa. También verifica el nombre de la
empresa que propuso el investigador, salvo que el usuario haya indicado uno.
"""

from dataclasses import replace

from outreach_agent.estado import EstadoGrafo
from outreach_agent.modelos import MAX_CITA, Hecho, Motivo
from outreach_agent.verificacion.cortes import cortar, detalle_hechos_insuficientes
from outreach_agent.verificacion.patrones import es_instruccion
from outreach_agent.verificacion.texto import (
    contar_palabras,
    contiene_ancla,
    contiene_literal,
    normalizar,
    reducir_ancla,
)

MAX_NOMBRE_EMPRESA = 80
MIN_HECHOS = 2  # umbral de "datos concretos suficientes" (FR-009)
# Heurística (research R5): un ancla es un nombre propio, una cifra o un término técnico; una
# frase más larga es una paráfrasis del texto promocional, no un dato concreto.
MAX_PALABRAS_ANCLA = 6


def causa_de_descarte(hecho: Hecho, texto_empresa: str, citas_vistas: set[str]) -> str | None:
    if len(hecho.cita) > MAX_CITA:
        return "cita_demasiado_larga"
    if not contiene_literal(texto_empresa, hecho.cita):
        return "cita_no_localizable"
    if es_instruccion(hecho.cita):
        return "patron_de_instruccion"
    if contar_palabras(hecho.ancla) > MAX_PALABRAS_ANCLA:
        return "ancla_demasiado_larga"
    if not contiene_ancla(hecho.cita, hecho.ancla):
        return "ancla_fuera_de_cita"
    if normalizar(hecho.cita) in citas_vistas:
        return "duplicado"
    return None


def causa_de_descarte_nombre(nombre: str, texto_empresa: str) -> str | None:
    if len(nombre) > MAX_NOMBRE_EMPRESA:
        return "nombre_demasiado_largo"
    if not contiene_literal(texto_empresa, nombre):
        return "nombre_no_localizable"
    if es_instruccion(nombre):
        return "patron_de_instruccion"
    return None


def _verificar_nombre(estado: EstadoGrafo, texto_empresa: str) -> dict:
    if estado.get("origen_nombre_empresa") == "usuario":
        return {}  # el nombre del usuario tiene prioridad
    nombre = (estado.get("nombre_empresa_candidato") or "").strip()
    if not nombre:
        return {}
    causa = causa_de_descarte_nombre(nombre, texto_empresa)
    if causa:
        return {"nombre_empresa_descartado": {"nombre": nombre, "causa": causa}}
    return {"nombre_empresa": nombre, "origen_nombre_empresa": "texto"}


def verificar_hechos(estado: EstadoGrafo) -> dict:
    texto_empresa = estado["entrada"].texto_empresa
    validos: list[Hecho] = []
    descartados: list[dict] = []
    citas_vistas: set[str] = set()
    for hecho in estado.get("hechos_candidatos", []):
        hecho = replace(hecho, ancla=reducir_ancla(hecho.ancla))
        causa = causa_de_descarte(hecho, texto_empresa, citas_vistas)
        if causa:
            descartados.append({"id": hecho.id, "causa": causa})
        else:
            validos.append(hecho)
            citas_vistas.add(normalizar(hecho.cita))
    actualizacion = {
        "hechos": validos,
        "hechos_descartados": descartados,
        **_verificar_nombre(estado, texto_empresa),
    }
    if len(validos) < MIN_HECHOS:
        detalle = detalle_hechos_insuficientes(len(validos), MIN_HECHOS)
        actualizacion.update(
            cortar({**estado, **actualizacion}, Motivo.HECHOS_INSUFICIENTES, detalle)
        )
    return actualizacion


def resumir(estado: EstadoGrafo, actualizacion: dict) -> tuple[str, dict]:
    """Decisión para la traza: válidos y descartados por causa, nombre de empresa y corte."""
    validos = [h.id for h in actualizacion["hechos"]]
    descartados = actualizacion["hechos_descartados"]
    decision = f"{len(validos)} válidos, {len(descartados)} descartados"
    if descartados:
        causas: dict[str, int] = {}
        for d in descartados:
            causas[d["causa"]] = causas.get(d["causa"], 0) + 1
        decision += " (" + ", ".join(f"{c}: {n}" for c, n in causas.items()) + ")"
    detalle: dict = {"validos": validos, "descartados": descartados}
    if "nombre_empresa" in actualizacion:
        detalle["nombre_empresa"] = f"{actualizacion['nombre_empresa']} (verificado en el texto)"
    elif "nombre_empresa_descartado" in actualizacion:
        detalle["nombre_empresa_descartado"] = actualizacion["nombre_empresa_descartado"]
    if "resultado" in actualizacion:
        decision += f"; corte: {actualizacion['resultado'].motivo.value}"
        detalle["detalle"] = actualizacion["resultado"].detalle
    return decision, detalle
