"""Experimento de modelo con Groq (spec 002, research "Experimento de modelo (Groq)").

Excepción acotada del principio IV de la constitución (2.1.0): este proveedor vive solo en
`scripts/`, no lo importa nada de `src/` ni la CLI, y solo corre sobre `eval/casos`. Reutiliza
`scripts/evaluar.py` inyectando el proveedor; el pipeline, los prompts y los criterios son los
mismos que con Ollama.

Uso (la clave solo desde el entorno, nunca en un flag ni en un archivo):
    $env:GROQ_API_KEY = "..."
    python scripts/evaluar_groq.py [--modelo openai/gpt-oss-120b] [--casos eval/casos]
        [--temp-redactor T] [--reintentos N] [--timeout SEG] [--salida eval/reportes]
        [--reanudar CARPETA]

Diferencias con Ollama:
- Modo JSON: con `json=True` se envía `response_format: {"type": "json_object"}`. Ese modo exige
  que los mensajes mencionen "JSON"; los tres system prompts del pipeline ya lo hacen (regla
  común "Respondé solo con un objeto JSON…"), así que no hace falta cambiarlos. Ollama usa
  `format: "json"`, que no tiene ese requisito.
- Tokens: el modelo razona antes de responder y esos tokens se cuentan dentro de
  `completion_tokens`. A cada llamada se le suma MARGEN_RAZONAMIENTO a los `max_tokens` que fija
  el pipeline (`Config.max_tokens_investigador/estratega/redactor`: 2000, 1200 y 800 por
  defecto). `num_ctx` no se usa: la ventana de contexto la fija el modelo de Groq.
- Solo se lee `choices[0].message.content`. `message.reasoning` no se lee ni se guarda. En la
  traza queda un evento `llamada_proveedor` por llamada, con `finish_reason` y los tokens, y un
  evento `espera_proveedor` por cada espera del limitador o reintento ante 429.
- `finish_reason == "length"` es un ProviderError: no se entrega un texto cortado.

`config.json` registra `proveedor: "groq"`, `base_url`, el margen y los límites del limitador;
`ollama_host` queda en null. La clave no se escribe en ningún archivo ni mensaje.

Código de salida: el de `evaluar.py`, o 2 si falta la clave, Groq la rechaza o los casos no son
de `eval/casos`.
"""

import json as jsonlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):  # ejecutado como `python scripts/evaluar_groq.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outreach_agent import grafo
from outreach_agent.config import Config
from outreach_agent.proveedores.base import ProviderError
from scripts import evaluar

VARIABLE_CLAVE = "GROQ_API_KEY"
BASE_URL = "https://api.groq.com/openai/v1"
MODELO_DEFAULT = "openai/gpt-oss-120b"
USER_AGENT = "outreach-agent-eval/0.1"

# Se suma a los max_tokens que fija el pipeline, para que el razonamiento no se coma la respuesta.
MARGEN_RAZONAMIENTO = 4000
# Limitador de ritmo: intervalo mínimo entre llamadas (como mucho 24 por minuto).
INTERVALO_MIN_S = 2.5
# Reintentos ante 429 y espera máxima por reintento; si el proveedor pide más (por ejemplo, el
# límite diario), se corta con un error en vez de esperar.
MAX_REINTENTOS_429 = 5
ESPERA_MAX_S = 120.0
ESPERA_BASE_429_S = 5.0  # sin Retry-After ni headers de límite: 5, 10, 20, 40, 80 s

CODIGO_SIN_PROVEEDOR = 2
RAIZ_CASOS = evaluar.RAIZ_REPO / "eval" / "casos"

Registrar = Callable[[str, str, dict], None]  # (evento, decision, detalle)


def _sin_registro(evento: str, decision: str, detalle: dict) -> None:
    pass


# --- Headers de límite de uso ---


def _header(headers, nombre: str) -> str | None:
    if headers is None:
        return None
    valor = headers.get(nombre)
    return valor.strip() if isinstance(valor, str) and valor.strip() else None


def duracion_s(texto: str | None) -> float | None:
    """Segundos de un valor como "7.66s", "2m59.56s", "1h2m3s", "120ms" o "3" (Retry-After)."""
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        pass
    partes = re.fullmatch(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m(?!s))?"
                          r"(?:(\d+(?:\.\d+)?)s)?(?:(\d+(?:\.\d+)?)ms)?", texto)
    if not partes or not any(partes.groups()):
        return None
    h, m, s, ms = (float(g) if g else 0.0 for g in partes.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def _entero(texto: str | None) -> int | None:
    try:
        return int(float(texto)) if texto is not None else None
    except ValueError:
        return None


class Limitador:
    """Espacia las llamadas y respeta lo que informan los headers `x-ratelimit-*`."""

    def __init__(self, intervalo_min_s: float = INTERVALO_MIN_S, reloj=time.monotonic,
                 dormir=time.sleep):
        self.intervalo_min_s = intervalo_min_s
        self.reloj = reloj
        self.dormir = dormir
        self._proxima = 0.0  # instante (reloj) desde el que se puede llamar
        self._tokens_restantes: int | None = None
        self._tokens_reset = 0.0  # instante en que se reponen los tokens

    def esperar(self, tokens_necesarios: int) -> tuple[float, str]:
        """Duerme lo necesario antes de la próxima llamada; devuelve (segundos, motivo)."""
        ahora = self.reloj()
        espera, motivo = max(0.0, self._proxima - ahora), "intervalo"
        if (self._tokens_restantes is not None and tokens_necesarios > self._tokens_restantes
                and self._tokens_reset > ahora):
            espera_tokens = self._tokens_reset - ahora
            if espera_tokens > espera:
                espera, motivo = espera_tokens, "tokens_por_minuto"
        if espera > 0:
            self.dormir(espera)
        return espera, motivo

    def registrar(self, headers) -> None:
        ahora = self.reloj()
        self._proxima = ahora + self.intervalo_min_s
        if _entero(_header(headers, "x-ratelimit-remaining-requests")) == 0:
            reset = duracion_s(_header(headers, "x-ratelimit-reset-requests"))
            if reset is not None:
                self._proxima = max(self._proxima, ahora + reset)
        restantes = _entero(_header(headers, "x-ratelimit-remaining-tokens"))
        if restantes is not None:
            self._tokens_restantes = restantes
            self._tokens_reset = ahora + (
                duracion_s(_header(headers, "x-ratelimit-reset-tokens")) or 0.0)

    def config(self) -> dict:
        return {
            "intervalo_min_s": self.intervalo_min_s,
            "max_reintentos_429": MAX_REINTENTOS_429,
            "espera_max_s": ESPERA_MAX_S,
            "espera_base_429_s": ESPERA_BASE_429_S,
        }


# --- Proveedor ---


class GroqProvider:
    """LLMProvider para la API de Groq compatible con OpenAI. Solo para este script."""

    nombre = "groq"

    def __init__(
        self,
        modelo: str,
        clave: str,
        timeout_s: float,
        *,
        base_url: str = BASE_URL,
        margen_razonamiento: int = MARGEN_RAZONAMIENTO,
        limitador: Limitador | None = None,
        registrar: Registrar = _sin_registro,
    ):
        if not clave:
            raise ValueError(f"Falta la clave de Groq en la variable de entorno {VARIABLE_CLAVE}.")
        self.modelo = modelo
        self._clave = clave
        self.timeout_s = timeout_s
        self.base_url = base_url.rstrip("/")
        self.margen_razonamiento = margen_razonamiento
        self.limitador = limitador or Limitador()
        self.registrar = registrar

    def __repr__(self) -> str:
        return f"GroqProvider(modelo={self.modelo!r}, base_url={self.base_url!r})"

    def _limpio(self, texto: str) -> str:
        """El texto sin la clave, por si un mensaje del proveedor la repitiera."""
        return texto.replace(self._clave, "***")

    def _error(self, mensaje: str, motivo: str = "proveedor_no_disponible") -> ProviderError:
        return ProviderError(self._limpio(mensaje), motivo=motivo)

    def generar(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperatura: float,
        json: bool,
    ) -> str:
        max_completion = max_tokens + self.margen_razonamiento
        cuerpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperatura,
            "max_completion_tokens": max_completion,
        }
        if json:
            cuerpo["response_format"] = {"type": "json_object"}
        datos_cuerpo = jsonlib.dumps(cuerpo).encode("utf-8")
        tokens_necesarios = (len(system) + len(user)) // 3 + max_completion

        reintentos_429 = 0
        while True:
            espera, motivo = self.limitador.esperar(tokens_necesarios)
            if espera > 0:
                self.registrar("espera_proveedor", f"espera de {espera:.1f} s ({motivo})",
                               {"motivo": motivo, "espera_s": round(espera, 2)})
            peticion = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=datos_cuerpo,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._clave}",
                    "User-Agent": USER_AGENT,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(peticion, timeout=self.timeout_s) as respuesta:
                    headers = getattr(respuesta, "headers", None)
                    datos = jsonlib.loads(respuesta.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                self.limitador.registrar(error.headers)
                if error.code == 429:
                    reintentos_429 += 1
                    espera_429 = self._espera_429(error.headers, reintentos_429)
                    if reintentos_429 > MAX_REINTENTOS_429 or espera_429 > ESPERA_MAX_S:
                        self.registrar("espera_proveedor", "429: se agotan los reintentos",
                                       {"motivo": "429", "reintento": reintentos_429,
                                        "espera_pedida_s": round(espera_429, 2),
                                        "abandona": True})
                        raise self._error(
                            f"Groq respondió 429 (límite de uso) {reintentos_429} veces o pidió "
                            f"esperar {espera_429:.0f} s (tope: {MAX_REINTENTOS_429} reintentos "
                            f"y {ESPERA_MAX_S:.0f} s por espera). Puede ser el límite diario "
                            "del plan gratuito: reanudá la corrida más tarde con --reanudar."
                        ) from None
                    self.registrar("espera_proveedor", f"429: reintento {reintentos_429} en "
                                   f"{espera_429:.1f} s",
                                   {"motivo": "429", "reintento": reintentos_429,
                                    "espera_s": round(espera_429, 2), "abandona": False})
                    self.limitador.dormir(espera_429)
                    continue
                detalle = error.read().decode("utf-8", errors="replace")
                if error.code == 401:
                    raise self._error(
                        f"Groq rechazó la clave (401). Revisá la variable de entorno "
                        f"{VARIABLE_CLAVE}."
                    ) from None
                if "context_length" in detalle:
                    raise self._error(
                        f"El texto no entra en la ventana de contexto de {self.modelo} "
                        f"(Groq respondió {error.code}).", motivo="contexto_excedido"
                    ) from None
                raise self._error(f"Groq respondió {error.code}: {detalle}") from None
            except (urllib.error.URLError, OSError) as error:
                if isinstance(error, TimeoutError) or isinstance(
                    getattr(error, "reason", None), TimeoutError
                ):
                    raise self._error(
                        f"Groq no respondió en {self.timeout_s:g} s. Subí el límite con --timeout."
                    ) from None
                raise self._error(f"No se pudo conectar con Groq en {self.base_url} ({error}).") \
                    from None
            except ValueError as error:
                raise self._error(f"Groq devolvió una respuesta que no es JSON: {error}") from None

        self.limitador.registrar(headers)
        return self._contenido(datos, max_completion, reintentos_429)

    def _espera_429(self, headers, reintento: int) -> float:
        for nombre in ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
            segundos = duracion_s(_header(headers, nombre))
            if segundos is not None:
                return segundos
        return ESPERA_BASE_429_S * 2 ** (reintento - 1)

    def _contenido(self, datos, max_completion: int, reintentos_429: int) -> str:
        """Lee solo `choices[0].message.content`; `message.reasoning` no se toca."""
        try:
            eleccion = datos["choices"][0]
            mensaje = eleccion.get("message") or {}
        except (KeyError, IndexError, TypeError, AttributeError):
            raise self._error("Groq devolvió una respuesta sin choices[0].") from None
        uso = datos.get("usage") or {}
        detalles = uso.get("completion_tokens_details") or {}
        finish_reason = eleccion.get("finish_reason")
        registro = {
            "finish_reason": finish_reason,
            "reasoning_tokens": detalles.get("reasoning_tokens"),
            "prompt_tokens": uso.get("prompt_tokens"),
            "completion_tokens": uso.get("completion_tokens"),
            "max_completion_tokens": max_completion,
            "reintentos_429": reintentos_429,
        }
        self.registrar("llamada_proveedor", f"finish_reason: {finish_reason}", registro)
        if finish_reason == "length":
            raise self._error(
                f"Groq cortó la respuesta por longitud (finish_reason=length): "
                f"{registro['completion_tokens']} tokens de {max_completion}, "
                f"{registro['reasoning_tokens']} de razonamiento. No se usa un texto cortado; "
                f"subí MARGEN_RAZONAMIENTO en scripts/evaluar_groq.py."
            )
        contenido = mensaje.get("content") or ""
        if not isinstance(contenido, str) or not contenido.strip():
            raise self._error("Groq devolvió una respuesta vacía.")
        return contenido


# --- Traza: los eventos del proveedor van a la traza de la ejecución en curso ---


class _TrazaEnCurso:
    traza = None

    def registrar(self, evento: str, decision: str, detalle: dict) -> None:
        if self.traza is not None:
            self.traza.emitir(evento, decision=decision, detalle=detalle)


def _instalar_traza(en_curso: _TrazaEnCurso) -> Callable[[], None]:
    """`grafo.ejecutar` crea su Traza internamente; esta subclase se anota en `en_curso` para
    que el proveedor escriba en ella. No modifica `src/`: reemplaza el nombre en el módulo
    mientras dura la corrida. Devuelve la función que lo restaura."""
    original = grafo.Traza

    class TrazaAnotada(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            en_curso.traza = self

    grafo.Traza = TrazaAnotada
    return lambda: setattr(grafo, "Traza", original)


def _instalar_config(limitador: Limitador) -> Callable[[], None]:
    """Agrega a config.json los campos de Groq sin modificar evaluar.py."""
    original = evaluar.config_a_dict

    def config_a_dict(config: Config, fecha: str, git=(None, None)) -> dict:
        datos = original(config, fecha, git)
        datos["ollama_host"] = None  # no se usa
        datos.update(
            proveedor="groq",
            base_url=BASE_URL,
            margen_razonamiento_tokens=MARGEN_RAZONAMIENTO,
            max_tokens_pipeline={
                "investigador": config.max_tokens_investigador,
                "estratega": config.max_tokens_estratega,
                "redactor": config.max_tokens_redactor,
            },
            num_ctx_se_usa=False,
            limitador=limitador.config(),
        )
        return datos

    evaluar.config_a_dict = config_a_dict
    return lambda: setattr(evaluar, "config_a_dict", original)


# --- Comprobaciones previas ---


def clave_groq(env=None) -> str | None:
    env = os.environ if env is None else env
    clave = (env.get(VARIABLE_CLAVE) or "").strip()
    return clave or None


def verificar_clave(clave: str, timeout_s: float = 30.0) -> str | None:
    """GET /models con la clave. Devuelve None si Groq la acepta, o un mensaje sin la clave."""
    peticion = urllib.request.Request(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {clave}", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout_s):
            return None
    except urllib.error.HTTPError as error:
        if error.code == 401:
            return f"Groq rechazó la clave (401). Revisá la variable de entorno {VARIABLE_CLAVE}."
        return f"Groq respondió {error.code} al verificar la clave."
    except (urllib.error.URLError, OSError) as error:
        return f"No se pudo conectar con Groq en {BASE_URL} ({type(error).__name__})."


def _dentro_de(ruta: Path, raiz: Path) -> bool:
    ruta, raiz = ruta.resolve(), raiz.resolve()
    return ruta == raiz or raiz in ruta.parents


def main(
    argv: list[str] | None = None,
    env=None,
    raiz_casos: Path = RAIZ_CASOS,
    log=print,
    verificar: Callable[[str], str | None] = verificar_clave,
    limitador: Limitador | None = None,
    **inyectado,
) -> int:
    """`inyectado` se pasa a evaluar.main (ahora, estado_git) para los tests."""
    argv = list(sys.argv[1:] if argv is None else argv)
    args = evaluar.construir_parser().parse_args(argv)

    if args.ollama_host:
        log("--ollama-host no aplica a Groq.")
        return CODIGO_SIN_PROVEEDOR
    casos = Path(args.casos)
    if "validacion" in casos.resolve().parts or not _dentro_de(casos, raiz_casos):
        log(f"Groq solo corre sobre {raiz_casos} (constitución, principio IV): {casos} no.")
        return CODIGO_SIN_PROVEEDOR
    if args.reanudar:
        guardada = jsonlib.loads((Path(args.reanudar) / "config.json").read_text(encoding="utf-8"))
        if guardada.get("proveedor") != "groq":
            log(f"{args.reanudar} no es una corrida de Groq: no se reanuda con este script.")
            return CODIGO_SIN_PROVEEDOR
    if not args.modelo:
        argv += ["--modelo", MODELO_DEFAULT]

    clave = clave_groq(env)
    if clave is None:  # antes de crear la carpeta de la corrida
        log(f"Falta la variable de entorno {VARIABLE_CLAVE}. Definila solo en la sesión "
            f'(PowerShell: $env:{VARIABLE_CLAVE} = "...") y volvé a correr.')
        return CODIGO_SIN_PROVEEDOR
    problema = verificar(clave)
    if problema:
        log(problema.replace(clave, "***"))
        return CODIGO_SIN_PROVEEDOR

    limitador = limitador or Limitador()
    en_curso = _TrazaEnCurso()

    def crear_proveedor(config: Config) -> GroqProvider:
        return GroqProvider(config.modelo, clave, config.timeout_s, limitador=limitador,
                            registrar=en_curso.registrar)

    restaurar = [_instalar_traza(en_curso), _instalar_config(limitador)]
    try:
        return evaluar.main(argv, crear_proveedor=crear_proveedor, disponible=lambda c: True,
                            log=log, **inyectado)
    finally:
        for deshacer in restaurar:
            deshacer()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
