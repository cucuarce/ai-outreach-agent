import pytest

from outreach_agent.modelos import Borrador, Entrada, Hecho
from outreach_agent.verificacion.borrador import validar_borrador
from tests import escenarios

TEXTO = escenarios.TEXTO_BORRADOR  # 102 palabras, válido


def validar(texto=TEXTO, hechos_usados=("H1", "H2"), puntos_usados=("P1", "P2"), **extra):
    estado = {
        "entrada": Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL),
        "idioma_objetivo": "es",
        "hechos": escenarios.hechos(),
        "estrategia": escenarios.estrategia(),
        "borrador": Borrador(texto, list(hechos_usados), list(puntos_usados)),
    }
    estado.update(extra)
    return validar_borrador(estado)


def criterios(resultado):
    return [f.criterio for f in resultado.fallos]


def test_borrador_valido():
    resultado = validar()
    assert resultado.ok
    assert resultado.fallos == []


@pytest.mark.parametrize(
    "texto, criterio",
    [
        (" ".join(["palabra"] * 79), "longitud"),
        (TEXTO + " Además" * 60, "longitud"),
        (TEXTO + " Quedo a la espera de su respuesta.", "relleno"),
    ],
)
def test_un_criterio_por_caso(texto, criterio):
    assert criterio in criterios(validar(texto))


def test_longitud_detalla_palabras_y_rango():
    resultado = validar(TEXTO + " Además" * 60)
    assert resultado.fallos[0].detalle == "162 palabras; rango 80–150"


def test_idioma_distinto_del_objetivo():
    assert criterios(validar(idioma_objetivo="en")) == ["idioma"]


def test_hechos_con_menos_de_dos_anclas():
    resultado = validar(hechos_usados=["H1"])
    assert criterios(resultado) == ["hechos"]
    assert "1 de 2" in resultado.fallos[0].detalle


def test_hecho_declarado_inexistente_no_cuenta():
    assert criterios(validar(hechos_usados=["H1", "H9"])) == ["hechos"]


def test_ancla_cifra_no_coincide_dentro_de_otro_numero():
    hechos = [
        Hecho("H1", "d", "procesa 2 millones de transacciones al mes", "2"),
        Hecho("H2", "d", "Migramos toda la infraestructura a Kubernetes en 2024", "Kubernetes"),
    ]
    texto = TEXTO.replace("2 millones", "muchas")  # queda "2024" pero no "2"
    resultado = validar(texto, hechos=hechos)
    assert criterios(resultado) == ["hechos"]
    assert 'H1 (ancla "2")' in resultado.fallos[0].detalle


def test_ancla_ia_no_coincide_dentro_de_media():
    hechos = [
        Hecho("H1", "d", "procesa 2 millones de transacciones al mes", "2"),
        Hecho("H2", "d", "equipo de IA para fraude", "IA"),
    ]
    texto = TEXTO + " Trabajé en media y publicidad."
    resultado = validar(texto, hechos=hechos)
    assert criterios(resultado) == ["hechos"]
    assert 'H2 (ancla "IA")' in resultado.fallos[0].detalle


def test_perfil_declarado_sin_ancla_en_el_texto():
    texto = TEXTO.replace("Kubernetes", "la nube").replace("un 30%", "bastante")
    resultado = validar(texto, hechos_usados=["H1", "H3"], puntos_usados=["P1", "P2"])
    assert "perfil" in criterios(resultado)
    detalle = next(f.detalle for f in resultado.fallos if f.criterio == "perfil")
    assert 'P1 (ancla "Kubernetes")' in detalle


def test_falla_varios_criterios_a_la_vez():
    texto = " ".join(["word"] * 60) + " I look forward to hearing from you."
    resultado = validar(texto, idioma_objetivo="es")
    assert set(criterios(resultado)) == {"longitud", "relleno", "idioma", "hechos", "perfil"}


# --- Criterio empresa (T033f, FR-019) ---


def test_empresa_presente_no_falla():
    assert validar(nombre_empresa="Nubeluz").ok


def test_empresa_ausente_falla():
    texto = TEXTO.replace("Nubeluz", "Pagosur")
    resultado = validar(texto, nombre_empresa="Nubeluz")
    assert criterios(resultado) == ["empresa"]
    assert resultado.fallos[0].detalle == 'el borrador no menciona a "Nubeluz"'


def test_sin_nombre_el_criterio_no_aplica():
    assert validar(TEXTO.replace("Nubeluz", "Pagosur")).ok


def test_nombre_dentro_de_otra_palabra_no_cuenta():
    texto = TEXTO.replace("Nubeluz", "Nubeluzia")
    assert criterios(validar(texto, nombre_empresa="Nubeluz")) == ["empresa"]


def test_numeros_permitidos_por_nombre_solo_si_lo_indico_el_usuario():
    from outreach_agent.verificacion.borrador import numeros_permitidos_por_nombre

    usuario = {"nombre_empresa": "Grupo 3M", "origen_nombre_empresa": "usuario"}
    texto = {"nombre_empresa": "ZEBRA-7731", "origen_nombre_empresa": "texto"}
    assert numeros_permitidos_por_nombre(usuario) == {"3"}
    assert numeros_permitidos_por_nombre(texto) == set()
    assert numeros_permitidos_por_nombre({}) == set()
