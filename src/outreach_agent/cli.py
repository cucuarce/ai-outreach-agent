"""CLI `outreach` (contracts/cli.md).

Solo genera un borrador para revisar: no existe ningún subcomando ni flag para mandar mensajes
ni para elegir Bedrock (principios III y IV de la constitución).
"""

import argparse
import json
import sys
from pathlib import Path

from outreach_agent.config import Config, cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import IDIOMAS_SOPORTADOS, Entrada, Estado, Resultado
from outreach_agent.proveedores.ollama import OllamaProvider
from outreach_agent.verificacion.texto import contar_palabras

CODIGOS_SALIDA = {
    Estado.BORRADOR: 0,
    Estado.INSUFICIENTE: 3,
    Estado.INVALIDO: 4,
    Estado.ERROR: 5,
}
CODIGO_USO_INCORRECTO = 2


class ErrorDeUso(Exception):
    """Entrada del usuario inválida: termina con código 2 sin ejecutar el grafo."""


def crear_proveedor(config: Config) -> OllamaProvider:
    return OllamaProvider(config.modelo, config.ollama_host, config.timeout_s, config.num_ctx)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="outreach",
        description=(
            "Genera un borrador de mensaje de outreach para tu búsqueda laboral a partir del "
            "texto de una empresa y tu perfil. El borrador es para que lo revises vos."
        ),
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    generar = subcomandos.add_parser("generar", help="Genera un borrador de mensaje.")
    generar.add_argument("--empresa", help="Archivo de texto con el texto de la empresa; - lee stdin.")
    generar.add_argument("--perfil", help="Archivo de texto con tu perfil profesional.")
    generar.add_argument(
        "--idioma", choices=IDIOMAS_SOPORTADOS, help="Idioma del borrador (por defecto, el de la empresa)."
    )
    generar.add_argument(
        "--nombre-empresa",
        help="Nombre de la empresa destinataria (por defecto, el que aparece en el texto).",
    )
    generar.add_argument("--modelo", help="Modelo de Ollama.")
    generar.add_argument("--ollama-host", help="URL de Ollama.")
    generar.add_argument("--timeout", type=float, help="Segundos máximos por llamada al modelo.")
    generar.add_argument("--num-ctx", type=int, help="Ventana de contexto del modelo, en tokens.")
    generar.add_argument("--reintentos", type=int, help="Reintentos de redacción.")
    generar.add_argument("--registros", help="Carpeta donde se guardan los registros.")
    generar.add_argument("--json", action="store_true", help="Imprime el resultado como JSON.")
    return parser


def _leer(ruta: str | None, flag: str, permite_stdin: bool) -> str:
    if ruta is None:
        raise ErrorDeUso(f"Falta {flag}: indicá el archivo de texto.")
    if ruta == "-" and permite_stdin:
        return sys.stdin.read()
    try:
        return Path(ruta).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ErrorDeUso(f"No existe el archivo indicado en {flag}: {ruta}") from None
    except (OSError, UnicodeDecodeError) as error:
        raise ErrorDeUso(f"No se pudo leer {ruta} ({flag}) como texto UTF-8: {error}") from None


def _imprimir_borrador(resultado: Resultado) -> None:
    borrador = resultado.borrador
    print(f"=== Borrador ({resultado.idioma}, {contar_palabras(borrador.texto)} palabras) ===")
    print(_linea_empresa(resultado))
    print(borrador.texto)
    print()
    print("=== Datos de la empresa usados ===")
    for hecho in resultado.hechos_usados:
        print(f'[{hecho.id}] {hecho.descripcion}  —  "{hecho.cita}"')
    print()
    print("=== Puntos de tu perfil usados ===")
    for punto in resultado.puntos_usados:
        print(f'[{punto.id}] {punto.descripcion}  —  "{punto.cita}"')
    print()
    print("Revisá el borrador antes de enviarlo. Este programa no envía nada.")
    _imprimir_registro(resultado, sys.stdout)


def _linea_empresa(resultado: Resultado) -> str:
    if not resultado.nombre_empresa:
        return "Empresa: no identificada; el borrador no nombra ninguna empresa"
    origen = "indicado por vos" if resultado.origen_nombre_empresa == "usuario" else "tomado del texto"
    return f"Empresa: {resultado.nombre_empresa} ({origen})"


def _imprimir_sin_borrador(resultado: Resultado) -> None:
    err = sys.stderr
    print(f"No se generó un borrador ({resultado.estado.value}).", file=err)
    if resultado.motivo:
        print(f"Motivo: {resultado.motivo.value}", file=err)
    if resultado.detalle:
        print(resultado.detalle, file=err)
    for fallo in resultado.fallos:
        print(f"- {fallo.criterio}: {fallo.detalle}", file=err)
    _imprimir_registro(resultado, err)


def _imprimir_registro(resultado: Resultado, destino) -> None:
    if resultado.rutas_registro:
        rutas = resultado.rutas_registro
        print(f"Registro: {rutas['md']} (traza: {rutas['jsonl']})", file=destino)


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        texto_empresa = _leer(args.empresa, "--empresa", permite_stdin=True)
        perfil = _leer(args.perfil, "--perfil", permite_stdin=False)
        config = cargar_config(args)
    except (ErrorDeUso, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return CODIGO_USO_INCORRECTO

    entrada = Entrada(
        texto_empresa=texto_empresa,
        perfil=perfil,
        idioma_solicitado=args.idioma,
        nombre_empresa_solicitado=(args.nombre_empresa or "").strip() or None,
    )
    resultado = ejecutar(entrada, crear_proveedor(config), config)

    if args.json:
        print(json.dumps(resultado.a_dict(), ensure_ascii=False, indent=2))
    elif resultado.estado is Estado.BORRADOR:
        _imprimir_borrador(resultado)
    else:
        _imprimir_sin_borrador(resultado)
    return CODIGOS_SALIDA[resultado.estado]
