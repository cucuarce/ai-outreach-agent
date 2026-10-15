import pytest

from outreach_agent.modelos import Borrador, Entrada, Estado, Hecho, Motivo
from outreach_agent.verificacion.borrador import (
    nodo_validar_borrador,
    resumidor,
    validar_borrador,
)
from outreach_agent.verificacion.texto import normalizar
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
        # Habilita el "2024" del borrador para el criterio numeros; no se usa como hecho.
        Hecho("H3", "d", "Migramos toda la infraestructura a Kubernetes en 2024", "Kubernetes"),
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


# --- Criterios numeros y enlaces (T046) ---


def test_numero_del_perfil_y_de_citas_verificadas_se_aceptan():
    assert validar().ok  # 2 y 2024 de las citas; 40, 30 y 5 del perfil


def test_numero_que_no_esta_en_citas_ni_perfil_falla():
    resultado = validar(TEXTO + " Somos 999 personas.")
    assert criterios(resultado) == ["numeros"]
    assert "999" in resultado.fallos[0].detalle


def test_numero_del_texto_de_la_empresa_fuera_de_las_citas_falla():
    # "2019" está en el texto de la empresa pero en ninguna cita verificada.
    resultado = validar(TEXTO + " Fundada en 2019.")
    assert criterios(resultado) == ["numeros"]


def test_digitos_del_nombre_indicado_por_el_usuario_se_aceptan():
    texto = TEXTO.replace("Nubeluz", "Grupo 3M")
    resultado = validar(texto, nombre_empresa="Grupo 3M", origen_nombre_empresa="usuario")
    assert resultado.ok


def test_digitos_del_nombre_tomado_del_texto_no_se_aceptan():
    texto = TEXTO.replace("Nubeluz", "Grupo 3M")
    resultado = validar(texto, nombre_empresa="Grupo 3M", origen_nombre_empresa="texto")
    assert criterios(resultado) == ["numeros"]


def test_enlace_que_no_esta_en_el_perfil_falla():
    resultado = validar(TEXTO + " Más en https://evil.example.")
    assert criterios(resultado) == ["enlaces"]
    assert "https://evil.example" in resultado.fallos[0].detalle


def test_enlace_del_perfil_se_acepta():
    from outreach_agent.modelos import Entrada

    perfil = escenarios.PERFIL + " Portfolio: https://ana.dev"
    resultado = validar(
        TEXTO + " Mi portfolio: https://ana.dev.",
        entrada=Entrada(escenarios.TEXTO_EMPRESA, perfil),
    )
    assert resultado.ok


# --- Borrador repetido (research R2 de la 001; spec 002, research D3, T010) ---

LARGO = TEXTO + " Además" * 68  # 170 palabras: falla longitud
LARGO_B = TEXTO + " Asimismo" * 68  # 170 palabras, distinto de LARGO


def estado_nodo(texto, anteriores):
    """Estado de validar_borrador en el intento len(anteriores) + 1. `textos_borradores` tiene los
    textos normalizados de todos los intentos, incluido el actual (lo agrega el redactor)."""
    return {
        "run_id": "prueba",
        "entrada": Entrada(escenarios.TEXTO_EMPRESA, escenarios.PERFIL),
        "idioma_objetivo": "es",
        "hechos": escenarios.hechos(),
        "estrategia": escenarios.estrategia(),
        "borrador": Borrador(texto, ["H1", "H2"], ["P1", "P2"]),
        "textos_borradores": [normalizar(t) for t in [*anteriores, texto]],
        "intento": len(anteriores) + 1,
    }


def nodo(texto, anteriores):
    return nodo_validar_borrador(estado_nodo(texto, anteriores))


def test_borrador_repetido_que_falla_no_corta_y_marca_repeticion():
    actualizacion = nodo(LARGO, [LARGO])
    assert "resultado" not in actualizacion
    assert [f.criterio for f in actualizacion["validacion"].fallos] == ["longitud"]
    assert actualizacion["repite_intento"] == 1
    assert actualizacion["modo_correccion"] == "reescribir"


def test_la_comparacion_ignora_mayusculas_tildes_puntuacion_y_espacios():
    anterior = LARGO.upper().replace(".", "").replace(" ", "  \n")
    assert nodo(LARGO, [anterior])["repite_intento"] == 1


def test_borradores_que_difieren_solo_en_espacios_o_mayusculas_cuentan_como_repetidos():
    anterior = "  " + LARGO.upper().replace(" ", "   ") + "\n"
    assert anterior != LARGO
    actualizacion = nodo(LARGO, [anterior])
    assert actualizacion["repite_intento"] == 1
    assert actualizacion["modo_correccion"] == "reescribir"


def test_borrador_distinto_no_repite_y_conserva():
    actualizacion = nodo(LARGO, [LARGO + " También"])
    assert "resultado" not in actualizacion
    assert actualizacion["repite_intento"] is None
    assert actualizacion["modo_correccion"] == "conservar"


def test_primer_intento_no_repite():
    actualizacion = nodo(LARGO, [])
    assert "resultado" not in actualizacion
    assert actualizacion["repite_intento"] is None
    assert actualizacion["modo_correccion"] == "conservar"


def test_repeticion_no_consecutiva_marca_el_intento_repetido():
    # Intentos A, B y A: el tercero repite el primero.
    actualizacion = nodo(LARGO, [LARGO, LARGO_B])
    assert actualizacion["repite_intento"] == 1
    assert actualizacion["modo_correccion"] == "reescribir"


def test_borrador_repetido_valido_no_corta():
    actualizacion = nodo(TEXTO, [TEXTO])
    assert actualizacion["validacion"].ok
    assert "resultado" not in actualizacion


def test_la_traza_registra_repite_intento_y_el_proximo_paso():
    resumir = resumidor(max_reintentos=2)
    estado = estado_nodo(LARGO, [LARGO])
    _, detalle = resumir(estado, nodo_validar_borrador(estado))
    assert detalle["repite_intento"] == 1
    assert detalle["proximo_paso"] == "reintento (reescribir)"

    estado = estado_nodo(LARGO, [LARGO_B])
    _, detalle = resumir(estado, nodo_validar_borrador(estado))
    assert detalle["repite_intento"] is None
    assert detalle["proximo_paso"] == "reintento"

    estado = estado_nodo(LARGO, [LARGO, LARGO])  # intento 3, sin reintentos restantes
    _, detalle = resumir(estado, nodo_validar_borrador(estado))
    assert detalle["repite_intento"] == 1
    assert detalle["proximo_paso"] == "inválido"


# --- Criterio empresa con símbolos de marca (spec 002, research D2, T013) ---


@pytest.mark.parametrize("simbolo", ["®", "™", "©"])
def test_empresa_con_simbolo_de_marca_se_cumple_con_el_nombre_sin_simbolo(simbolo):
    assert "Nubeluz" in TEXTO and simbolo not in TEXTO
    assert validar(nombre_empresa=f"Nubeluz{simbolo}").ok
