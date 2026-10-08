"""Estado compartido del grafo LangGraph (data-model.md, tabla "EstadoGrafo")."""

from typing import TypedDict

from outreach_agent.modelos import (
    Borrador,
    Entrada,
    Estrategia,
    Hecho,
    Resultado,
    ResultadoValidacion,
)


class EstadoGrafo(TypedDict, total=False):
    entrada: Entrada
    run_id: str
    nonce: str
    idioma_objetivo: str | None
    idioma_empresa: str | None
    nombre_empresa: str | None  # el del usuario o el del texto, verificado
    origen_nombre_empresa: str | None  # "usuario" | "texto"
    nombre_empresa_candidato: str | None  # el que devolvió el investigador
    nombre_empresa_descartado: dict  # {"nombre": ..., "causa": ...}
    hechos_candidatos: list[Hecho]
    instrucciones_detectadas: list[str]
    hechos: list[Hecho]  # verificados
    hechos_descartados: list[dict]  # {"id": ..., "causa": ...}
    estrategia: Estrategia
    puntos_descartados: list[dict]  # {"id": ..., "causa": ...}
    borrador: Borrador
    intento: int
    validacion: ResultadoValidacion
    resultado: Resultado
