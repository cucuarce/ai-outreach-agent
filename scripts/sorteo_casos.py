"""Sorteo reproducible de las ofertas de los casos de evaluación valido-02, -03 y -05 (T056,
research R8).

Uso:
    python scripts/sorteo_casos.py <ruta a ofertas.json>

El dataset (98 ofertas, campos `id`, `origen`, `titulo`, `texto_completo`, `n_caracteres`) vive
en el proyecto hermano ai-job-matcher (`job-embeddings-search/data/raw/ofertas.json`) y no se
copia a este repositorio: solo el texto anonimizado de las ofertas sorteadas está en
`eval/casos/`. Resultado con el dataset de 2026-10-14: caso 2 → id 19, caso 3 → id 86,
caso 5 → id 83.

Filtros (definidos antes del sorteo y no modificados después):
- caso 2: idioma es + una frase de búsqueda (`_BUSQUEDA`) + al menos 1 cifra o 1 tecnología.
- caso 3: idioma es + al menos 3 tecnologías + 0 cifras.
- caso 5: idioma en + al menos 5 cifras.

El idioma se detecta con `detectar_idioma` y las cifras se cuentan con `extraer_numeros`, ambos
del proyecto. Las tecnologías salen de la lista fija `TECNOLOGIAS`, buscadas como palabra
completa (`contiene_palabra`). Antes de filtrar se quita el índice "N- " con que empiezan las
ofertas de Ofertas_V1.docx, porque contaba como cifra.

Sorteo: `random.Random(SEMILLA).choice(candidatas)` sobre las candidatas ordenadas por id, con
un generador nuevo por caso; así, cambiar el filtro de un caso no cambia el sorteo de los otros.
"""

import json
import random
import re
import sys

from outreach_agent.verificacion.idioma import detectar_idioma
from outreach_agent.verificacion.texto import contiene_palabra, extraer_numeros

SEMILLA = 42

# Índice "12- " al inicio del texto (formato de Ofertas_V1.docx): no es una cifra de la oferta.
_INDICE = re.compile(r"^\s*\d+\s*-\s*")

TECNOLOGIAS = [
    "Python", "SQL", "PostgreSQL", "PostGIS", "MySQL", "MongoDB", "Redis", "Airflow", "AWS",
    "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Spark", "Kafka", "dbt", "Snowflake",
    "BigQuery", "TensorFlow", "PyTorch", "Pandas", "FastAPI", "Django", "Flask", "React",
    "Node.js", "TypeScript", "JavaScript", "Java", "n8n", "Zapier", "LangChain", "LangGraph",
    "OpenAI", "Git", "Linux", "Power BI", "Tableau", "Make.com", "HubSpot", "Salesforce",
]

# "busca una persona para un puesto"
_BUSQUEDA = re.compile(
    r"\b(buscamos|estamos buscando|busca|buscando|en búsqueda de|en busqueda de|incorporar)\b",
    re.IGNORECASE,
)


def texto(oferta: dict) -> str:
    return _INDICE.sub("", oferta["texto_completo"], count=1)


def tecnologias(t: str) -> list[str]:
    return [tec for tec in TECNOLOGIAS if contiene_palabra(t, tec)]


def caso_2(oferta: dict) -> bool:
    t = texto(oferta)
    concreto = bool(extraer_numeros(t)) or bool(tecnologias(t))
    return detectar_idioma(t) == "es" and _BUSQUEDA.search(t) is not None and concreto


def caso_3(oferta: dict) -> bool:
    t = texto(oferta)
    return detectar_idioma(t) == "es" and len(tecnologias(t)) >= 3 and not extraer_numeros(t)


def caso_5(oferta: dict) -> bool:
    t = texto(oferta)
    return detectar_idioma(t) == "en" and len(extraer_numeros(t)) >= 5


FILTROS = {"caso 2": caso_2, "caso 3": caso_3, "caso 5": caso_5}


def main(ruta: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with open(ruta, encoding="utf-8") as archivo:
        ofertas = sorted(json.load(archivo), key=lambda o: int(o["id"]))
    for nombre, filtro in FILTROS.items():
        candidatas = [o for o in ofertas if filtro(o)]
        print(f"== {nombre}: {len(candidatas)} candidatas: {[o['id'] for o in candidatas]}")
        if not candidatas:
            continue
        elegida = random.Random(SEMILLA).choice(candidatas)  # un generador nuevo por caso
        t = texto(elegida)
        print(f"elegida: id {elegida['id']} ({elegida['origen']}, {len(t)} caracteres)")
        print(f"tecnologías: {tecnologias(t)}; cifras: {extraer_numeros(t)}")
        print(t[:300])
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python scripts/sorteo_casos.py <ruta a ofertas.json>")
    main(sys.argv[1])
