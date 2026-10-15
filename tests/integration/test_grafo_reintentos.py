"""T030: reintento acotado del redactor y resultado inválido (FR-011)."""

import json
from dataclasses import replace
from pathlib import Path

from outreach_agent.config import cargar_config
from outreach_agent.grafo import ejecutar
from outreach_agent.modelos import Entrada, Estado, Motivo
from tests import escenarios as e
from tests import escenarios_r13 as r13
from tests.escenarios import RAIZ
from tests.fakes import FakeProvider

LARGO = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Además" * 68)  # 170 palabras
LARGO_B = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Asimismo" * 68)  # 170 palabras, distinto de LARGO
CON_RELLENO = dict(e.REDACTOR, texto=e.TEXTO_BORRADOR + " Quedo a la espera de su respuesta.")


def correr(redacciones, max_reintentos=2):
    config = replace(cargar_config(env={}), max_reintentos=max_reintentos)
    respuestas = [e.INVESTIGADOR, e.ESTRATEGA, *redacciones]
    provider = FakeProvider([json.dumps(r) for r in respuestas])
    resultado = ejecutar(Entrada(e.TEXTO_EMPRESA, e.PERFIL), provider, config)
    return resultado, provider


def llamadas_al_redactor(provider):
    return [ll for ll in provider.llamadas if "agente redactor" in ll["system"]]


def test_falla_y_luego_valido_da_borrador_en_el_segundo_intento():
    resultado, provider = correr([LARGO, e.REDACTOR])

    assert resultado.estado is Estado.BORRADOR
    redactor = llamadas_al_redactor(provider)
    assert len(redactor) == 2
    assert "longitud" in redactor[1]["user"]
    assert "170 palabras" in redactor[1]["user"]
    assert "longitud" not in redactor[0]["user"].split("Longitud:")[0]


def test_tres_fallos_con_dos_reintentos_da_invalido_con_los_fallos_del_ultimo():
    resultado, provider = correr([LARGO, LARGO_B, CON_RELLENO], max_reintentos=2)

    assert resultado.estado is Estado.INVALIDO
    assert resultado.motivo is Motivo.VALIDACION_FALLIDA
    assert [f.criterio for f in resultado.fallos] == ["relleno"]
    assert resultado.borrador is None
    assert len(llamadas_al_redactor(provider)) == 3


def test_sin_reintentos_hay_un_solo_intento():
    resultado, provider = correr([LARGO], max_reintentos=0)

    assert resultado.estado is Estado.INVALIDO
    assert [f.criterio for f in resultado.fallos] == ["longitud"]
    assert len(llamadas_al_redactor(provider)) == 1


def test_el_reintento_recibe_el_borrador_anterior_y_la_orden_de_mantener_el_resto():
    _, provider = correr([LARGO, e.REDACTOR])
    primero, segundo = llamadas_al_redactor(provider)

    assert LARGO["texto"] in segundo["user"]
    assert "Corregí solo los criterios fallidos y mantené el resto del borrador." in segundo["user"]
    assert "Longitud obligatoria: entre 80 y 150 palabras." in segundo["user"]
    assert "El borrador anterior tenía 170 palabras." in segundo["user"]
    # El primer intento no tiene borrador anterior ni feedback.
    assert "Borrador anterior" not in primero["user"]
    assert "Corregí solo" not in primero["user"]


def test_sin_fallo_de_longitud_no_se_agrega_la_linea_de_longitud():
    _, provider = correr([CON_RELLENO, e.REDACTOR])
    segundo = llamadas_al_redactor(provider)[1]

    assert CON_RELLENO["texto"] in segundo["user"]
    assert "relleno:" in segundo["user"]
    assert "Longitud obligatoria" not in segundo["user"]


def test_borrador_repetido_no_corta_y_el_siguiente_intento_reescribe():
    # Spec 002, research D3 (T011): reemplaza el corte inmediato por repetición de la 001.
    repetido = dict(LARGO, texto=LARGO["texto"].upper())  # igual tras normalizar
    resultado, provider = correr([LARGO, repetido, e.REDACTOR], max_reintentos=2)

    assert resultado.estado is Estado.BORRADOR
    redactor = llamadas_al_redactor(provider)
    assert len(redactor) == 3
    tercero = redactor[2]["user"]
    assert "Borrador anterior:" not in tercero
    assert "Escribí un borrador nuevo" in tercero
    assert "Corregí solo los criterios fallidos" not in tercero


def test_tres_intentos_identicos_terminan_invalido_sin_superar_el_limite():
    # FR-006: la repetición no agrega intentos.
    resultado, provider = correr([LARGO, LARGO, LARGO], max_reintentos=2)

    assert resultado.estado is Estado.INVALIDO
    assert resultado.motivo is Motivo.VALIDACION_FALLIDA
    assert [f.criterio for f in resultado.fallos] == ["longitud"]
    assert len(llamadas_al_redactor(provider)) == 3


# --- Respuestas grabadas de valido-01 (spec 002, research D3, T012) ---

CASO_VALIDO_01 = json.loads(
    (RAIZ / "eval" / "casos" / "valido-01.json").read_text(encoding="utf-8")
)
# El intento 1 de la línea base con "Campo Claro" en la primera oración.
REDACTOR_VALIDO_01_CON_NOMBRE = dict(
    r13.REDACTOR_VALIDO_01_INTENTO_1,
    texto=r13.REDACTOR_VALIDO_01_INTENTO_1["texto"].replace(
        "Soy Ángel, ingeniero", "Soy Ángel y le escribo a Campo Claro como ingeniero", 1
    ),
)


def correr_con_traza(respuestas, texto, perfil, max_reintentos=2):
    config = replace(cargar_config(env={}), max_reintentos=max_reintentos)
    provider = FakeProvider([json.dumps(r) for r in respuestas])
    resultado = ejecutar(Entrada(texto, perfil), provider, config)
    lineas = Path(resultado.rutas_registro["jsonl"]).read_text(encoding="utf-8").splitlines()
    return resultado, provider, [json.loads(linea) for linea in lineas]


def detalles(traza, nodo, campo):
    return [
        ev["detalle"].get(campo, "ausente")
        for ev in traza
        if ev["evento"] == "nodo_fin" and ev["nodo"] == nodo
    ]


def test_valido_01_repite_reescribe_y_entrega_con_el_nombre():
    assert "Campo Claro" in REDACTOR_VALIDO_01_CON_NOMBRE["texto"]
    resultado, provider, traza = correr_con_traza(
        [
            r13.INVESTIGADOR_VALIDO_01,
            r13.ESTRATEGA_VALIDO_01,
            r13.REDACTOR_VALIDO_01_INTENTO_1,
            r13.REDACTOR_VALIDO_01_INTENTO_2,
            REDACTOR_VALIDO_01_CON_NOMBRE,
        ],
        r13.TEXTO_EMPRESA_VALIDO_01,
        CASO_VALIDO_01["perfil"],
    )

    assert resultado.estado is Estado.BORRADOR
    assert "Campo Claro" in resultado.borrador.texto
    assert detalles(traza, "redactor", "modo_correccion") == ["inicial", "conservar", "reescribir"]
    assert detalles(traza, "validar_borrador", "repite_intento") == [None, 1, None]
    tercero = llamadas_al_redactor(provider)[2]["user"]
    assert "Nombrá a Campo Claro en la primera oración." in tercero
    assert "Borrador anterior:" not in tercero


def test_repeticion_no_consecutiva_se_detecta():
    # Intentos A, B y A: el tercero repite el primero.
    _, _, traza = correr_con_traza([e.INVESTIGADOR, e.ESTRATEGA, LARGO, LARGO_B, LARGO],
                                   e.TEXTO_EMPRESA, e.PERFIL)
    assert detalles(traza, "validar_borrador", "repite_intento") == [None, None, 1]
