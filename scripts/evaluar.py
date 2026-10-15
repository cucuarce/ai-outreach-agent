"""Evaluación contra Ollama (T058, research R8, contracts/eval.md). No forma parte de pytest.

Uso:
    python scripts/evaluar.py [--casos eval/casos | eval/casos/<id>.json] [--modelo NOMBRE]
        [--ollama-host URL] [--timeout SEG] [--num-ctx N] [--temp-redactor T] [--reintentos N]
        [--salida eval/reportes] [--reanudar CARPETA_DE_CORRIDA]

Corre los casos en secuencia, en orden de id. Cada corrida tiene su carpeta en `--salida`:

    <AAAAMMDD-HHMMSS>-<modelo>/
        config.json            configuración de la corrida (modelo, num_ctx, timeout, commit de git, ...)
        resultados/<id>.json   Resultado de cada caso, guardado apenas termina
        trazas/                trazas .jsonl y registros .md de la corrida
        reporte.md, reporte.json
        revision_humana.json   un registro por borrador entregado, para completar a mano

Un error de un caso (timeout, proveedor, excepción inesperada) queda como estado `error` y la
corrida sigue. Con `--reanudar CARPETA` se saltan los casos que ya tienen resultado y se usa el
`config.json` de esa corrida. El reporte se arma siempre desde lo guardado en disco.

`nombre_esperado` no se pasa al sistema: solo se usa para evaluar.

Código de salida: 0 si todas las métricas están al 100%, no hubo errores y no quedan casos
pendientes; 1 si no; 2 si Ollama no está disponible.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):  # ejecutado como `python scripts/evaluar.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outreach_agent.config import Config, cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import (
    Borrador,
    ElementoUsado,
    Entrada,
    Estado,
    Fallo,
    Motivo,
    Resultado,
)
from outreach_agent.proveedores.base import LLMProvider
from outreach_agent.proveedores.ollama import OllamaProvider
from scripts import metricas_eval as m

TIMEOUT_DEFAULT = 900.0
NUM_CTX_DEFAULT = 8192
CODIGO_OK, CODIGO_METRICAS, CODIGO_SIN_OLLAMA = 0, 1, 2

FabricaProveedor = Callable[[Config], LLMProvider]
Disponible = Callable[[Config], bool]
EstadoGit = Callable[[], tuple[str | None, bool | None]]
RAIZ_REPO = Path(__file__).resolve().parent.parent


def consultar_git(directorio: Path = RAIZ_REPO) -> tuple[str | None, bool | None]:
    """El commit actual y si hay cambios sin commit (spec 002, research D7). (None, None) si git
    no está disponible o `directorio` no es un repositorio."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=directorio, capture_output=True, text=True,
            check=True, timeout=30,
        ).stdout.strip()
        cambios = subprocess.run(
            ["git", "status", "--porcelain"], cwd=directorio, capture_output=True, text=True,
            check=True, timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, None
    return commit or None, bool(cambios)


# --- Proveedor real (se reemplaza en los tests) ---


def crear_proveedor_ollama(config: Config) -> LLMProvider:
    return OllamaProvider(config.modelo, config.ollama_host, config.timeout_s, config.num_ctx)


def ollama_disponible(config: Config) -> bool:
    try:
        with urllib.request.urlopen(f"{config.ollama_host.rstrip('/')}/api/tags", timeout=5):
            return True
    except (urllib.error.URLError, OSError):
        return False


# --- Casos y persistencia ---


def cargar_casos(ruta: Path) -> list[dict]:
    """Casos de una carpeta o de un único archivo, ordenados por id."""
    archivos = [ruta] if ruta.is_file() else sorted(ruta.glob("*.json"))
    casos = [json.loads(a.read_text(encoding="utf-8")) for a in archivos]
    return sorted(casos, key=lambda c: c["id"])


def resultado_desde_dict(datos: dict) -> Resultado:
    """Inversa de `Resultado.a_dict()`."""
    borrador = datos.get("borrador")
    return Resultado(
        estado=Estado(datos["estado"]),
        run_id=datos["run_id"],
        idioma=datos.get("idioma"),
        nombre_empresa=datos.get("nombre_empresa"),
        origen_nombre_empresa=datos.get("origen_nombre_empresa"),
        borrador=Borrador(**borrador) if borrador else None,
        hechos_usados=[ElementoUsado(**h) for h in datos.get("hechos_usados", [])],
        puntos_usados=[ElementoUsado(**p) for p in datos.get("puntos_usados", [])],
        motivo=Motivo(datos["motivo"]) if datos.get("motivo") else None,
        detalle=datos.get("detalle"),
        fallos=[Fallo(**f) for f in datos.get("fallos", [])],
        rutas_registro=datos.get("rutas_registro"),
    )


def _escribir_json(ruta: Path, datos) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def config_a_dict(
    config: Config, fecha: str, git: tuple[str | None, bool | None] = (None, None)
) -> dict:
    return {
        "fecha": fecha,
        "modelo": config.modelo,
        "ollama_host": config.ollama_host,
        "num_ctx": config.num_ctx,
        "timeout_s": config.timeout_s,
        "temperatura_redactor": config.temperatura_redactor,
        "max_reintentos": config.max_reintentos,
        "git_commit": git[0],
        "git_cambios_sin_commit": git[1],
    }


def config_desde_dict(datos: dict, dir_registros: Path) -> Config:
    base = cargar_config(env={})
    return replace(
        base,
        modelo=datos["modelo"],
        ollama_host=datos["ollama_host"],
        num_ctx=datos["num_ctx"],
        timeout_s=datos["timeout_s"],
        temperatura_redactor=datos["temperatura_redactor"],
        max_reintentos=datos["max_reintentos"],
        dir_registros=dir_registros,
    )


def nombre_corrida(fecha: datetime, modelo: str) -> str:
    return f"{fecha:%Y%m%d-%H%M%S}-{re.sub(r'[^A-Za-z0-9._-]', '-', modelo)}"


# --- Ejecución ---


def correr_caso(caso: dict, provider: LLMProvider, config: Config) -> Resultado:
    """Corre un caso. Nunca lanza: una excepción inesperada queda como estado `error`."""
    entrada = Entrada(
        texto_empresa=caso["texto_empresa"],
        perfil=caso["perfil"],
        idioma_solicitado=caso.get("idioma"),
        nombre_empresa_solicitado=None,  # nombre_esperado es solo para evaluar
    )
    try:
        return ejecutar(entrada, provider, config)
    except Exception as error:  # noqa: BLE001 — la corrida sigue con el próximo caso
        return Resultado(
            estado=Estado.ERROR,
            run_id="sin-run",
            detalle=f"Excepción no controlada: {type(error).__name__}: {error}",
        )


def correr(casos: list[dict], corrida: Path, config: Config, provider: LLMProvider, log=print):
    dir_resultados = corrida / "resultados"
    dir_resultados.mkdir(parents=True, exist_ok=True)
    for caso in casos:
        destino = dir_resultados / f"{caso['id']}.json"
        if destino.exists():
            log(f"{caso['id']}: ya tiene resultado, se salta")
            continue
        inicio = time.perf_counter()
        resultado = correr_caso(caso, provider, config)
        datos = resultado.a_dict()
        datos["duracion_s"] = round(time.perf_counter() - inicio, 1)
        _escribir_json(destino, datos)  # apenas termina, para poder reanudar
        motivo = f" ({resultado.motivo.value})" if resultado.motivo else ""
        log(f"{caso['id']}: {resultado.estado.value}{motivo} en {datos['duracion_s']} s")


# --- Reporte ---


def _cargar_resultados(corrida: Path) -> dict[str, dict]:
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((corrida / "resultados").glob("*.json"))
    }


def _eventos(corrida: Path, run_id: str) -> list[dict]:
    ruta = corrida / "trazas" / f"{run_id}.jsonl"
    return m.leer_traza(ruta) if ruta.exists() else []


def actualizar_revision_humana(corrida: Path, casos: list[dict], resultados: dict[str, dict]):
    """Un registro por borrador entregado, con `afirmaciones_sin_respaldo` en null. Conserva lo
    que ya se completó a mano para el mismo caso y el mismo texto."""
    ruta = corrida / "revision_humana.json"
    previos = {}
    if ruta.exists():
        previos = {r["id"]: r for r in json.loads(ruta.read_text(encoding="utf-8"))}
    registros = []
    for caso in casos:
        datos = resultados.get(caso["id"])
        if not datos or datos["estado"] != Estado.BORRADOR.value:
            continue
        texto = datos["borrador"]["texto"]
        previo = previos.get(caso["id"])
        registros.append(
            {
                "id": caso["id"],
                "run_id": datos["run_id"],
                "texto": texto,
                "hechos_usados": datos["hechos_usados"],
                "puntos_usados": datos["puntos_usados"],
                "afirmaciones_sin_respaldo": (
                    previo.get("afirmaciones_sin_respaldo")
                    if previo and previo.get("texto") == texto
                    else None
                ),
            }
        )
    _escribir_json(ruta, registros)
    return ruta


def _tasa_a_dict(valor):
    if isinstance(valor, m.Tasa):
        return {
            "cumplen": valor.cumplen,
            "total": valor.total,
            "porcentaje": valor.porcentaje,
            "incumplen": list(valor.incumplen),
        }
    return valor


def armar_reporte(corrida: Path, casos: list[dict]) -> dict:
    """Arma `reporte.json`, `reporte.md` y `revision_humana.json` desde lo guardado en disco."""
    config = json.loads((corrida / "config.json").read_text(encoding="utf-8"))
    resultados = _cargar_resultados(corrida)
    con_resultado = [c for c in casos if c["id"] in resultados]
    evaluaciones = [
        m.evaluar_caso(
            c,
            resultado_desde_dict(resultados[c["id"]]),
            _eventos(corrida, resultados[c["id"]]["run_id"]),
        )
        for c in con_resultado
    ]
    ruta_revision = actualizar_revision_humana(corrida, casos, resultados)
    totales = m.totales(con_resultado, evaluaciones, m.leer_revision_humana(ruta_revision))
    reporte = {
        "config": config,
        "totales": {k: _tasa_a_dict(v) for k, v in totales.items()},
        "errores": [e.id for e in evaluaciones if e.estado == Estado.ERROR.value],
        "pendientes": [c["id"] for c in casos if c["id"] not in resultados],
        "casos": [
            {
                **asdict(e),
                "run_id": resultados[e.id]["run_id"],
                "detalle": resultados[e.id].get("detalle"),
                "duracion_s": resultados[e.id].get("duracion_s"),
                "registro": f"trazas/{resultados[e.id]['run_id']}.md",
            }
            for e in evaluaciones
        ],
    }
    _escribir_json(corrida / "reporte.json", reporte)
    (corrida / "reporte.md").write_text(
        reporte_md(reporte, casos, resultados), encoding="utf-8"
    )
    return reporte


def _porcentaje(t: dict) -> str:
    if t["total"] == 0:
        return "sin casos"
    texto = f"{t['porcentaje']:.0f}% ({t['cumplen']}/{t['total']})"
    return texto + (f" · incumplen: {', '.join(t['incumplen'])}" if t["incumplen"] else "")


def reporte_md(reporte: dict, casos: list[dict], resultados: dict[str, dict]) -> str:
    c, t = reporte["config"], reporte["totales"]
    lineas = [
        f"# Evaluación {c['fecha']}",
        "",
        f"- Modelo: {c['modelo']} · num_ctx: {c['num_ctx']} · timeout: {c['timeout_s']:g} s · "
        f"temperatura del redactor: {c['temperatura_redactor']:g} · "
        f"max_reintentos: {c['max_reintentos']}",
        f"- Commit: {c.get('git_commit') or 'desconocido'}",
    ]
    if c.get("git_cambios_sin_commit"):
        lineas.append("- **Atención: la corrida se hizo con cambios sin commit.**")
    lineas += [f"- Casos {tipo}: {desc}" for tipo, desc in t["composicion"].items()]
    if reporte["errores"]:
        lineas.append(f"- Errores: {', '.join(reporte['errores'])}")
    if reporte["pendientes"]:
        lineas.append(f"- Pendientes (sin resultado): {', '.join(reporte['pendientes'])}")
    lineas += ["", "## Totales", ""]
    etiquetas = {
        "validos_con_borrador_entregado": "Válidos con borrador entregado",
        "SC-001": "SC-001 (80–150 palabras)",
        "SC-002": "SC-002 (datos y perfil localizables)",
        "SC-003": "SC-003 (sin relleno ni números/enlaces ajenos a las entradas)",
        "SC-004": "SC-004 (insuficiente sin borrador)",
        "SC-005": "SC-005 (inyección)",
        "inyecciones_sin_prohibidos_en_lo_entregado": "Inyecciones sin prohibidos en lo entregado",
        "inyecciones_con_borrador_entregado": "Inyecciones con borrador entregado",
        "SC-009": "SC-009 (idioma)",
        "SC-010": "SC-010 (nombre de la empresa)",
        "aprobacion_primer_intento": "Aprobación en el primer intento",
    }
    lineas += [f"- {etiqueta}: {_porcentaje(t[clave])}" for clave, etiqueta in etiquetas.items()]
    invalidos = t["invalido"]
    lineas.append(
        f"- Resultados invalido: {len(invalidos['casos'])}/{invalidos['total']}"
        + (f" ({', '.join(invalidos['casos'])})" if invalidos["casos"] else "")
    )
    lineas.append(f"- Canarios o cifras prohibidas en borradores entregados: {t['prohibidos_en_entregados']}")
    lineas.append(f"- Intentos de redacción con canario o cifra prohibida: {t['intentos_con_prohibidos']}")
    legitimos = t["legitimos_descartados_por_ancla"]
    lineas.append(
        "- Hechos legítimos descartados por ancla_demasiado_larga: "
        + ("; ".join(f"{i}: {', '.join(f)}" for i, f in legitimos.items()) if legitimos else "ninguno")
    )
    a = t["afirmaciones_sin_respaldo"]
    lineas.append(
        f"- Borradores con al menos una afirmación sin respaldo (revisión humana): "
        f"{len(a['con_afirmaciones'])} de {a['revisados']} revisados"
        + (f" ({', '.join(a['con_afirmaciones'])})" if a["con_afirmaciones"] else "")
        + (f"; pendientes de revisar: {', '.join(a['pendientes'])}" if a["pendientes"] else "")
    )

    lineas += ["", "## Por caso", "", "| Caso | Tipo | Estado | Intentos | Palabras | Registro |",
               "|------|------|--------|----------|----------|----------|"]
    for caso in reporte["casos"]:
        estado = caso["estado"] + (f" ({caso['motivo']})" if caso["motivo"] else "")
        lineas.append(
            f"| {caso['id']} | {caso['tipo']} | {estado} | {caso['intentos']} | "
            f"{caso['palabras'] if caso['palabras'] is not None else '—'} | {caso['registro']} |"
        )

    lineas += ["", "## Para revisión humana", "",
               "Completá `afirmaciones_sin_respaldo` en `revision_humana.json` (lista de "
               "afirmaciones, o `[]` si no hay ninguna).", ""]
    for caso in casos:
        datos = resultados.get(caso["id"])
        if not datos or datos["estado"] != Estado.BORRADOR.value:
            continue
        lineas += [f"### {caso['id']}", "", "> " + datos["borrador"]["texto"], ""]
        lineas += [f'- Dato [{h["id"]}] "{h["cita"]}" (ancla: {h["ancla"]})' for h in datos["hechos_usados"]]
        lineas += [f'- Perfil [{p["id"]}] "{p["cita"]}" (ancla: {p["ancla"]})' for p in datos["puntos_usados"]]
        lineas.append("")
    return "\n".join(lineas) + "\n"


def codigo_de_salida(reporte: dict) -> int:
    """0 solo si los criterios SC están al 100%, sin errores ni pendientes. La aprobación en el
    primer intento es informativa: los reintentos están permitidos."""
    t = reporte["totales"]
    tasas = [v for k, v in t.items() if k.startswith("SC-")]
    al_100 = all(v["total"] == 0 or v["cumplen"] == v["total"] for v in tasas)
    if al_100 and not reporte["errores"] and not reporte["pendientes"]:
        return CODIGO_OK
    return CODIGO_METRICAS


# --- CLI ---


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evaluar", description="Evalúa el sistema contra Ollama.")
    p.add_argument("--casos", default="eval/casos", help="Carpeta de casos o un único caso .json.")
    p.add_argument("--modelo", help="Modelo de Ollama.")
    p.add_argument("--ollama-host", help="URL de Ollama.")
    p.add_argument("--timeout", type=float, default=TIMEOUT_DEFAULT, help="Segundos por llamada.")
    p.add_argument("--num-ctx", type=int, default=NUM_CTX_DEFAULT, help="Ventana de contexto.")
    p.add_argument("--temp-redactor", type=float, help="Temperatura del redactor.")
    p.add_argument("--reintentos", type=int, help="Reintentos de redacción.")
    p.add_argument("--salida", default="eval/reportes", help="Carpeta de las corridas.")
    p.add_argument("--reanudar", help="Carpeta de una corrida anterior para completarla.")
    return p


def main(
    argv: list[str] | None = None,
    crear_proveedor: FabricaProveedor = crear_proveedor_ollama,
    disponible: Disponible = ollama_disponible,
    ahora: Callable[[], datetime] = datetime.now,
    log=print,
    estado_git: EstadoGit = consultar_git,
) -> int:
    args = construir_parser().parse_args(argv)
    casos = cargar_casos(Path(args.casos))

    if args.reanudar:
        corrida = Path(args.reanudar)
        guardada = json.loads((corrida / "config.json").read_text(encoding="utf-8"))
        config = config_desde_dict(guardada, corrida / "trazas")
    else:
        config = cargar_config(args)

    if not disponible(config):  # antes de crear la carpeta de la corrida
        log(
            f"Ollama no está disponible en {config.ollama_host}. Iniciá Ollama con `ollama serve` "
            f"y descargá el modelo con `ollama pull {config.modelo}`."
        )
        return CODIGO_SIN_OLLAMA

    if args.reanudar:
        log(f"Reanudando {corrida} con su configuración guardada ({config.modelo}).")
    else:
        fecha = ahora()
        corrida = Path(args.salida) / nombre_corrida(fecha, config.modelo)
        corrida.mkdir(parents=True, exist_ok=False)
        config = replace(config, dir_registros=corrida / "trazas")
        _escribir_json(
            corrida / "config.json",
            config_a_dict(
                config, fecha.astimezone().isoformat(timespec="seconds"), estado_git()
            ),
        )

    correr(casos, corrida, config, crear_proveedor(config), log)
    reporte = armar_reporte(corrida, casos)
    log(f"Reporte: {corrida / 'reporte.md'}")
    return codigo_de_salida(reporte)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
