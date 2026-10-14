"""T055: dependencias prohibidas, comprobadas con `ast` sobre el código fuente.

- Principio IV: los agentes dependen solo de la interfaz `LLMProvider`, nunca de un proveedor
  concreto ni de un cliente de red.
- Principio III: ningún módulo del paquete puede enviar mensajes.
"""

import ast
from pathlib import Path

import pytest

PAQUETE = Path(__file__).resolve().parents[2] / "src" / "outreach_agent"
AGENTES = PAQUETE / "agentes"

PROHIBIDOS_EN_AGENTES = (
    "outreach_agent.proveedores.ollama",
    "outreach_agent.proveedores.bedrock",
    "boto3",
    "urllib",
)
PROHIBIDOS_EN_PAQUETE = (
    "smtplib",
    "email.mime",
    # clientes de mensajería
    "twilio",
    "slack_sdk",
    "slack",
    "sendgrid",
    "telegram",
    "discord",
    "yagmail",
    "linkedin_api",
)


def modulos_importados(codigo: str, paquete: str) -> set[str]:
    """Nombres completos importados por el código. Los imports relativos se resuelven contra
    `paquete` (el del archivo); `from a import b` cuenta como `a` y `a.b`."""
    modulos: set[str] = set()
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if nodo.level:
                partes = paquete.split(".")
                partes = partes[: len(partes) - (nodo.level - 1)]
                base = ".".join([*partes, base] if base else partes)
            modulos.add(base)
            modulos.update(f"{base}.{alias.name}" for alias in nodo.names)
    return modulos


def violaciones(codigo: str, paquete: str, prohibidos: tuple[str, ...]) -> list[str]:
    return sorted(
        modulo
        for modulo in modulos_importados(codigo, paquete)
        for prohibido in prohibidos
        if modulo == prohibido or modulo.startswith(prohibido + ".")
    )


def violaciones_en(archivo: Path, prohibidos: tuple[str, ...]) -> list[str]:
    paquete = ".".join(archivo.relative_to(PAQUETE.parent).parent.parts)
    return violaciones(archivo.read_text(encoding="utf-8"), paquete, prohibidos)


@pytest.mark.parametrize("archivo", sorted(AGENTES.glob("*.py")), ids=lambda p: p.name)
def test_agentes_no_importan_proveedores_concretos_ni_red(archivo):
    assert violaciones_en(archivo, PROHIBIDOS_EN_AGENTES) == []


@pytest.mark.parametrize(
    "archivo",
    sorted(PAQUETE.rglob("*.py")),
    ids=lambda p: p.relative_to(PAQUETE).as_posix(),
)
def test_ningun_modulo_puede_enviar_mensajes(archivo):
    assert violaciones_en(archivo, PROHIBIDOS_EN_PAQUETE) == []


def test_el_analisis_detecta_imports_absolutos_relativos_y_submodulos():
    """Control del propio test, con código de ejemplo ubicado en `outreach_agent.agentes`."""
    codigo = (
        "import boto3\n"
        "from urllib.request import urlopen\n"
        "from ..proveedores.ollama import OllamaProvider\n"
        "from ..proveedores.base import LLMProvider\n"
        "from email.mime.text import MIMEText\n"
    )
    paquete = "outreach_agent.agentes"
    assert violaciones(codigo, paquete, PROHIBIDOS_EN_AGENTES) == [
        "boto3",
        "outreach_agent.proveedores.ollama",
        "outreach_agent.proveedores.ollama.OllamaProvider",
        "urllib.request",
        "urllib.request.urlopen",
    ]
    assert violaciones(codigo, paquete, PROHIBIDOS_EN_PAQUETE) == [
        "email.mime.text",
        "email.mime.text.MIMEText",
    ]
