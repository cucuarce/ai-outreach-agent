"""scripts/evaluar_groq.py sin red: se reemplaza urlopen (constitución 2.1.0, principio IV)."""

import email.message
import io
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

from outreach_agent import grafo
from outreach_agent.proveedores.base import ProviderError
from scripts import evaluar
from scripts import evaluar_groq as g
from tests import escenarios as e

CLAVE = "gsk_test_CENTINELA_7731"
RAZONAMIENTO = "RAZONAMIENTO-OCULTO-4242"
URL_CHAT = "https://api.groq.com/openai/v1/chat/completions"


class RespuestaFalsa(io.BytesIO):
    def __init__(self, datos: bytes, headers=None):
        super().__init__(datos)
        self.headers = headers or email.message.Message()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def headers(**valores) -> email.message.Message:
    h = email.message.Message()
    for nombre, valor in valores.items():
        h[nombre.replace("_", "-")] = str(valor)
    return h


def completion(contenido: str, finish_reason: str = "stop", reasoning_tokens: int = 50) -> dict:
    return {
        "choices": [{
            "message": {"role": "assistant", "content": contenido, "reasoning": RAZONAMIENTO},
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 80 + reasoning_tokens,
            "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
        },
    }


def error_http(codigo: int, cuerpo: str = "{}", **cabeceras) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(URL_CHAT, codigo, "error", headers(**cabeceras),
                                  io.BytesIO(cuerpo.encode("utf-8")))


@pytest.fixture
def capturar(monkeypatch):
    """Reemplaza urlopen: cada llamada consume la próxima respuesta programada (dict, o una
    excepción que se lanza)."""
    estado = {"peticiones": [], "respuestas": []}

    def urlopen_falso(peticion, timeout=None):
        estado["peticiones"].append(peticion)
        if not estado["respuestas"]:
            raise AssertionError("urlopen sin respuestas programadas")
        respuesta = estado["respuestas"].pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return RespuestaFalsa(json.dumps(respuesta).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    return estado


class Reloj:
    def __init__(self):
        self.t = 1000.0
        self.dormidas: list[float] = []

    def __call__(self):
        return self.t

    def dormir(self, segundos):
        self.dormidas.append(segundos)
        self.t += segundos


def proveedor(reloj=None, eventos=None):
    reloj = reloj or Reloj()
    limitador = g.Limitador(intervalo_min_s=0.0, reloj=reloj, dormir=reloj.dormir)
    registrar = (lambda ev, dec, det: eventos.append((ev, det))) if eventos is not None else None
    extra = {"registrar": registrar} if registrar else {}
    return g.GroqProvider("openai/gpt-oss-120b", CLAVE, 30.0, limitador=limitador, **extra)


def generar(p, json_=True, max_tokens=800):
    return p.generar("reglas JSON", "datos", max_tokens=max_tokens, temperatura=0.3, json=json_)


# --- Petición y respuesta ---


def test_peticion_url_header_y_cuerpo(capturar):
    capturar["respuestas"] = [completion('{"ok": true}')]
    generar(proveedor())
    peticion = capturar["peticiones"][0]
    assert peticion.full_url == URL_CHAT
    assert peticion.get_method() == "POST"
    assert peticion.get_header("Authorization") == f"Bearer {CLAVE}"
    assert peticion.get_header("Content-type") == "application/json"
    cuerpo = json.loads(peticion.data)
    assert cuerpo == {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": "reglas JSON"},
            {"role": "user", "content": "datos"},
        ],
        "temperature": 0.3,
        "max_completion_tokens": 800 + g.MARGEN_RAZONAMIENTO,
        "response_format": {"type": "json_object"},
    }


def test_sin_json_no_envia_response_format(capturar):
    capturar["respuestas"] = [completion("texto")]
    generar(proveedor(), json_=False)
    assert "response_format" not in json.loads(capturar["peticiones"][0].data)


def test_lee_solo_content_y_registra_finish_reason_y_reasoning_tokens(capturar):
    capturar["respuestas"] = [completion('{"ok": true}', reasoning_tokens=321)]
    eventos = []
    assert generar(proveedor(eventos=eventos)) == '{"ok": true}'
    assert eventos == [("llamada_proveedor", {
        "finish_reason": "stop",
        "reasoning_tokens": 321,
        "prompt_tokens": 100,
        "completion_tokens": 401,
        "max_completion_tokens": 800 + g.MARGEN_RAZONAMIENTO,
        "reintentos_429": 0,
    })]
    assert RAZONAMIENTO not in repr(eventos)


def test_respuesta_vacia_es_error(capturar):
    capturar["respuestas"] = [completion("  ")]
    with pytest.raises(ProviderError, match="vacía"):
        generar(proveedor())


def test_finish_reason_length_es_error_y_queda_en_la_traza(capturar):
    capturar["respuestas"] = [completion('{"texto": "cortad', finish_reason="length")]
    eventos = []
    with pytest.raises(ProviderError, match="finish_reason=length"):
        generar(proveedor(eventos=eventos))
    assert eventos[0][0] == "llamada_proveedor"
    assert eventos[0][1]["finish_reason"] == "length"


# --- Errores HTTP ---


def test_401_es_error_que_nombra_la_variable_sin_la_clave(capturar):
    capturar["respuestas"] = [error_http(401, '{"error": {"message": "Invalid API Key"}}')]
    with pytest.raises(ProviderError) as error:
        generar(proveedor())
    assert "GROQ_API_KEY" in str(error.value)
    assert CLAVE not in str(error.value)


def test_un_error_que_repite_la_clave_se_limpia(capturar):
    capturar["respuestas"] = [error_http(400, f'{{"error": "clave {CLAVE} mal formada"}}')]
    with pytest.raises(ProviderError) as error:
        generar(proveedor())
    assert CLAVE not in str(error.value)
    assert "***" in str(error.value)


def test_contexto_excedido_tiene_su_motivo(capturar):
    capturar["respuestas"] = [error_http(400, '{"error": {"code": "context_length_exceeded"}}')]
    with pytest.raises(ProviderError) as error:
        generar(proveedor())
    assert error.value.motivo == "contexto_excedido"


def test_429_espera_lo_que_pide_retry_after_reintenta_y_lo_registra(capturar):
    capturar["respuestas"] = [error_http(429, retry_after=3), completion('{"ok": true}')]
    reloj, eventos = Reloj(), []
    assert generar(proveedor(reloj, eventos)) == '{"ok": true}'
    assert reloj.dormidas == [3.0]
    assert len(capturar["peticiones"]) == 2
    espera = [det for ev, det in eventos if ev == "espera_proveedor"]
    assert espera == [{"motivo": "429", "reintento": 1, "espera_s": 3.0, "abandona": False}]
    llamada = [det for ev, det in eventos if ev == "llamada_proveedor"]
    assert llamada[0]["reintentos_429"] == 1


def test_429_usa_los_headers_de_rate_limit_si_no_hay_retry_after(capturar):
    capturar["respuestas"] = [error_http(429, x_ratelimit_reset_tokens="7.66s"),
                              completion('{"ok": true}')]
    reloj = Reloj()
    generar(proveedor(reloj))
    assert reloj.dormidas == [pytest.approx(7.66)]


def test_429_con_tope_de_reintentos_es_error_registrado(capturar):
    capturar["respuestas"] = [error_http(429, retry_after=1)] * (g.MAX_REINTENTOS_429 + 1)
    eventos = []
    with pytest.raises(ProviderError, match="429") as error:
        generar(proveedor(eventos=eventos))
    assert CLAVE not in str(error.value)
    esperas = [det for ev, det in eventos if ev == "espera_proveedor"]
    assert len(esperas) == g.MAX_REINTENTOS_429 + 1
    assert esperas[-1]["abandona"] is True


def test_429_que_pide_esperar_mas_que_el_tope_corta_sin_esperar(capturar):
    capturar["respuestas"] = [error_http(429, retry_after=3600)]
    reloj = Reloj()
    with pytest.raises(ProviderError, match="límite diario"):
        generar(proveedor(reloj))
    assert reloj.dormidas == []


# --- Limitador ---


def test_limitador_respeta_el_intervalo_minimo():
    reloj = Reloj()
    limitador = g.Limitador(intervalo_min_s=2.5, reloj=reloj, dormir=reloj.dormir)
    limitador.registrar(headers())
    assert limitador.esperar(10) == (2.5, "intervalo")


def test_limitador_espera_el_reset_si_no_quedan_pedidos():
    reloj = Reloj()
    limitador = g.Limitador(intervalo_min_s=0.0, reloj=reloj, dormir=reloj.dormir)
    limitador.registrar(headers(x_ratelimit_remaining_requests=0,
                                x_ratelimit_reset_requests="2m3s"))
    espera, _ = limitador.esperar(10)
    assert espera == pytest.approx(123)


def test_limitador_espera_si_faltan_tokens_por_minuto():
    reloj = Reloj()
    limitador = g.Limitador(intervalo_min_s=0.0, reloj=reloj, dormir=reloj.dormir)
    limitador.registrar(headers(x_ratelimit_remaining_tokens=1000,
                                x_ratelimit_reset_tokens="30s"))
    assert limitador.esperar(500) == (0.0, "intervalo")
    assert limitador.esperar(5000) == (pytest.approx(30), "tokens_por_minuto")


@pytest.mark.parametrize("texto, segundos", [
    ("3", 3), ("7.66s", 7.66), ("2m59.56s", 179.56), ("1h2m3s", 3723), ("120ms", 0.12),
    ("", None), ("raro", None),
])
def test_duracion_s(texto, segundos):
    assert g.duracion_s(texto) == (pytest.approx(segundos) if segundos is not None else None)


def test_repr_no_muestra_la_clave():
    assert CLAVE not in repr(proveedor())


# --- main: comprobaciones previas ---


FECHA = datetime(2026, 10, 17, 12, 0, 0)
GIT = ("0123456789abcdef0123456789abcdef01234567", False)


def caso_valido() -> dict:
    return {
        "id": "a-valido", "tipo": "valido", "texto_empresa": e.TEXTO_EMPRESA,
        "perfil": e.PERFIL, "idioma": None, "idioma_esperado": "es", "canario": None,
        "nombre_esperado": "Nubeluz", "hechos_legitimos_esperados": ["Kubernetes"],
    }


def escribir_casos(carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    c = caso_valido()
    (carpeta / f"{c['id']}.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return carpeta


def correr_main(tmp_path, casos_dir=None, env=None, verificar=lambda clave: None, extra=()):
    casos_dir = casos_dir or escribir_casos(tmp_path / "eval" / "casos")
    salida = tmp_path / "reportes"
    mensajes = []
    reloj = Reloj()
    codigo = g.main(
        ["--casos", str(casos_dir), "--salida", str(salida), *extra],
        env={"GROQ_API_KEY": CLAVE} if env is None else env,
        raiz_casos=tmp_path / "eval" / "casos",
        log=mensajes.append,
        verificar=verificar,
        limitador=g.Limitador(intervalo_min_s=0.0, reloj=reloj, dormir=reloj.dormir),
        ahora=lambda: FECHA,
        estado_git=lambda: GIT,
    )
    corridas = sorted(salida.glob("*")) if salida.exists() else []
    return codigo, (corridas[-1] if corridas else None), mensajes


def textos_de(carpeta: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in carpeta.rglob("*") if p.is_file())


def test_sin_clave_termina_con_2_sin_verificar_ni_crear_carpeta(tmp_path):
    verificadas = []
    codigo, corrida, mensajes = correr_main(tmp_path, env={}, verificar=verificadas.append)
    assert codigo == g.CODIGO_SIN_PROVEEDOR
    assert corrida is None
    assert verificadas == []
    assert "GROQ_API_KEY" in mensajes[0]


def test_clave_rechazada_termina_con_2_sin_crear_carpeta(tmp_path):
    codigo, corrida, mensajes = correr_main(
        tmp_path, verificar=lambda clave: f"Groq rechazó la clave {clave} (401).")
    assert codigo == g.CODIGO_SIN_PROVEEDOR
    assert corrida is None
    assert CLAVE not in "\n".join(mensajes)


@pytest.mark.parametrize("carpeta", ["otros/casos", "eval/casos/../validacion/casos"])
def test_casos_fuera_de_eval_casos_no_corren(tmp_path, carpeta):
    escribir_casos(tmp_path / "eval" / "casos")
    otra = escribir_casos(tmp_path / carpeta)
    codigo, corrida, _ = correr_main(tmp_path, casos_dir=otra)
    assert codigo == g.CODIGO_SIN_PROVEEDOR
    assert corrida is None


def test_no_reanuda_una_corrida_de_ollama(tmp_path):
    previa = tmp_path / "previa"
    previa.mkdir()
    (previa / "config.json").write_text(json.dumps({"modelo": "qwen2.5:7b"}), encoding="utf-8")
    codigo, _, mensajes = correr_main(tmp_path, extra=("--reanudar", str(previa)))
    assert codigo == g.CODIGO_SIN_PROVEEDOR
    assert "no es una corrida de Groq" in mensajes[0]


# --- main: corrida completa con urlopen reemplazado ---


def test_corrida_registra_groq_en_config_y_traza_sin_clave_ni_razonamiento(tmp_path, capturar):
    capturar["respuestas"] = [
        completion(json.dumps(r)) for r in (e.INVESTIGADOR, e.ESTRATEGA, e.REDACTOR)
    ]
    traza_original, config_original = grafo.Traza, evaluar.config_a_dict
    codigo, corrida, _ = correr_main(tmp_path)

    config = json.loads((corrida / "config.json").read_text(encoding="utf-8"))
    assert config["proveedor"] == "groq"
    assert config["modelo"] == "openai/gpt-oss-120b"
    assert config["ollama_host"] is None
    assert config["margen_razonamiento_tokens"] == g.MARGEN_RAZONAMIENTO
    assert config["base_url"] == g.BASE_URL

    resultado = json.loads((corrida / "resultados" / "a-valido.json").read_text(encoding="utf-8"))
    assert resultado["estado"] == "borrador"
    eventos = [json.loads(linea) for linea in
               (corrida / "trazas" / f"{resultado['run_id']}.jsonl").read_text(
                   encoding="utf-8").splitlines()]
    inicio = next(ev for ev in eventos if ev["evento"] == "ejecucion_inicio")
    assert inicio["detalle"]["proveedor"] == "groq"
    llamadas = [ev for ev in eventos if ev["evento"] == "llamada_proveedor"]
    assert len(llamadas) == 3
    assert all(ev["detalle"]["finish_reason"] == "stop" for ev in llamadas)
    assert all(ev["detalle"]["reasoning_tokens"] == 50 for ev in llamadas)

    todo = textos_de(tmp_path / "reportes")
    assert CLAVE not in todo
    assert RAZONAMIENTO not in todo
    assert codigo == evaluar.codigo_de_salida(
        json.loads((corrida / "reporte.json").read_text(encoding="utf-8")))
    # se restauran los reemplazos
    assert grafo.Traza is traza_original
    assert evaluar.config_a_dict is config_original


def test_un_401_en_la_corrida_queda_como_error_sin_la_clave_en_ningun_archivo(
    tmp_path, capturar
):
    capturar["respuestas"] = [error_http(401, f'{{"error": "Invalid API Key {CLAVE}"}}')]
    _, corrida, mensajes = correr_main(tmp_path)
    resultado = json.loads((corrida / "resultados" / "a-valido.json").read_text(encoding="utf-8"))
    assert resultado["estado"] == "error"
    assert "GROQ_API_KEY" in resultado["detalle"]
    assert CLAVE not in textos_de(tmp_path / "reportes")
    assert CLAVE not in "\n".join(map(str, mensajes))


def test_nada_de_src_referencia_al_proveedor_de_groq():
    """Condición 2 de la excepción del principio IV: ni la CLI ni src/ lo ven."""
    paquete = Path(__file__).resolve().parents[2] / "src" / "outreach_agent"
    referencias = [
        p.relative_to(paquete).as_posix()
        for p in paquete.rglob("*.py")
        for marca in ("evaluar_groq", "GroqProvider", "api.groq.com", "GROQ_API_KEY")
        if marca in p.read_text(encoding="utf-8")
    ]
    assert referencias == []
