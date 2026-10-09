"""T021: contrato del CLI (contracts/cli.md), parte de la Historia 1."""

import argparse
import io
import json
import sys

import pytest

from outreach_agent import cli
from tests import escenarios
from tests.fakes import FakeProvider


@pytest.fixture
def archivos(tmp_path):
    empresa = tmp_path / "empresa.txt"
    perfil = tmp_path / "perfil.txt"
    empresa.write_text(escenarios.TEXTO_EMPRESA, encoding="utf-8")
    perfil.write_text(escenarios.PERFIL, encoding="utf-8")
    return empresa, perfil


@pytest.fixture
def proveedor_falso(monkeypatch):
    """Reemplaza la fábrica de proveedores y guarda la configuración que recibió."""
    creados = {}

    def crear(config):
        creados["config"] = config
        creados["provider"] = FakeProvider(escenarios.respuestas_flujo_valido())
        return creados["provider"]

    monkeypatch.setattr(cli, "crear_proveedor", crear)
    return creados


def generar(*args):
    return cli.main(["generar", *map(str, args)])


@pytest.mark.parametrize("falta", ["--empresa", "--perfil"])
def test_falta_una_entrada(archivos, proveedor_falso, capsys, falta):
    empresa, perfil = archivos
    args = {"--empresa": empresa, "--perfil": perfil}
    del args[falta]
    codigo = generar(*[x for par in args.items() for x in par])

    assert codigo == 2
    assert falta in capsys.readouterr().err
    assert proveedor_falso == {}  # no se ejecutó nada


def test_archivo_inexistente(archivos, proveedor_falso, capsys, tmp_path):
    _, perfil = archivos
    codigo = generar("--empresa", tmp_path / "no-existe.txt", "--perfil", perfil)
    assert codigo == 2
    assert "no-existe.txt" in capsys.readouterr().err


def test_idioma_no_soportado(archivos, proveedor_falso):
    empresa, perfil = archivos
    with pytest.raises(SystemExit) as salida:
        generar("--empresa", empresa, "--perfil", perfil, "--idioma", "xx")
    assert salida.value.code == 2


def test_exito_imprime_borrador_datos_y_aviso(archivos, proveedor_falso, capsys):
    empresa, perfil = archivos
    codigo = generar("--empresa", empresa, "--perfil", perfil)
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "=== Borrador (es, " in salida
    assert escenarios.TEXTO_BORRADOR in salida
    assert "=== Datos de la empresa usados ===" in salida
    assert '[H1] Procesa 2 millones de transacciones por mes  —  "procesa 2 millones' in salida
    assert "=== Puntos de tu perfil usados ===" in salida
    assert "[P1] " in salida
    assert "Este programa no envía nada." in salida


def test_empresa_desde_stdin(archivos, proveedor_falso, monkeypatch):
    _, perfil = archivos
    monkeypatch.setattr(sys, "stdin", io.StringIO(escenarios.TEXTO_EMPRESA))
    assert generar("--empresa", "-", "--perfil", perfil) == 0
    assert escenarios.TEXTO_EMPRESA in proveedor_falso["provider"].llamadas[0]["user"]


def test_salida_json(archivos, proveedor_falso, capsys):
    empresa, perfil = archivos
    assert generar("--empresa", empresa, "--perfil", perfil, "--json") == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["estado"] == "borrador"
    assert datos["borrador"]["texto"] == escenarios.TEXTO_BORRADOR


def test_num_ctx_llega_al_proveedor(archivos, proveedor_falso):
    empresa, perfil = archivos
    generar("--empresa", empresa, "--perfil", perfil, "--num-ctx", 32768)
    assert proveedor_falso["config"].num_ctx == 32768


def test_ayuda_no_ofrece_enviar_ni_bedrock(capsys):
    for argv in (["--help"], ["generar", "--help"]):
        with pytest.raises(SystemExit) as salida:
            cli.main(argv)
        assert salida.value.code == 0
        ayuda = capsys.readouterr().out.lower()
        for prohibida in ("enviar", "send", "bedrock"):
            assert prohibida not in ayuda


def test_unico_subcomando_es_generar():
    parser = cli.construir_parser()
    subcomandos = [
        accion for accion in parser._actions if isinstance(accion, argparse._SubParsersAction)
    ]
    assert len(subcomandos) == 1
    assert set(subcomandos[0].choices) == {"generar"}


# --- Nombre de la empresa (T033g, FR-019) ---


def test_linea_empresa_tomada_del_texto(archivos, proveedor_falso, capsys):
    empresa, perfil = archivos
    assert generar("--empresa", empresa, "--perfil", perfil) == 0
    assert "Empresa: Nubeluz (tomado del texto)" in capsys.readouterr().out


def test_nombre_empresa_llega_a_la_entrada_y_se_imprime(archivos, monkeypatch, capsys):
    import json as jsonlib

    texto = escenarios.TEXTO_BORRADOR.replace("Nubeluz", "Campo Claro")
    respuestas = escenarios.respuestas_flujo_valido()
    respuestas[2] = jsonlib.dumps(dict(escenarios.REDACTOR, texto=texto))
    provider = FakeProvider(respuestas)
    monkeypatch.setattr(cli, "crear_proveedor", lambda config: provider)

    empresa, perfil = archivos
    codigo = generar("--empresa", empresa, "--perfil", perfil, "--nombre-empresa", " Campo Claro ")

    assert codigo == 0
    assert "Empresa: Campo Claro (indicado por vos)" in capsys.readouterr().out
    assert "dirigido a Campo Claro" in provider.llamadas[2]["user"]


def test_linea_empresa_no_identificada(archivos, monkeypatch, capsys):
    import json as jsonlib

    respuestas = escenarios.respuestas_flujo_valido()
    respuestas[0] = jsonlib.dumps(dict(escenarios.INVESTIGADOR, nombre_empresa=None))
    monkeypatch.setattr(cli, "crear_proveedor", lambda config: FakeProvider(respuestas))

    empresa, perfil = archivos
    assert generar("--empresa", empresa, "--perfil", perfil) == 0
    salida = capsys.readouterr().out
    assert "Empresa: no identificada; el borrador no nombra ninguna empresa" in salida


def test_temp_redactor_llega_al_proveedor(archivos, proveedor_falso):
    empresa, perfil = archivos
    generar("--empresa", empresa, "--perfil", perfil, "--temp-redactor", 0.1)
    assert proveedor_falso["config"].temperatura_redactor == 0.1
    assert proveedor_falso["provider"].llamadas[2]["temperatura"] == 0.1


# --- Historia 2 (T035) ---


def test_insuficiente_sale_con_3_y_explica_en_stderr(tmp_path, monkeypatch, capsys):
    empresa = tmp_path / "vacia.txt"
    perfil = tmp_path / "perfil.txt"
    empresa.write_text("   \n", encoding="utf-8")
    perfil.write_text(escenarios.PERFIL, encoding="utf-8")
    monkeypatch.setattr(cli, "crear_proveedor", lambda config: FakeProvider([]))

    codigo = generar("--empresa", empresa, "--perfil", perfil)
    salida = capsys.readouterr()

    assert codigo == 3
    assert "Motivo: empresa_vacia" in salida.err
    assert "Pegá el texto" in salida.err  # sugerencia de cómo corregir la entrada
    assert "=== Borrador" not in salida.out
    assert salida.out == ""
