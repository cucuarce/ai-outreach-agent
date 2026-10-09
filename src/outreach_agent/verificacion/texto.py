"""Utilidades deterministas de texto usadas por las verificaciones (research R2 y R5)."""

import re
import unicodedata

_NUMERO = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
_CIFRA = re.compile(r"[0-9]+(?:[.,][0-9]+)*%?")
_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"'()\[\]]+", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def normalizar_espacios(s: str) -> str:
    return " ".join(s.split())


def normalizar(s: str) -> str:
    """Minúsculas, sin tildes, sin puntuación y con espacios colapsados."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return normalizar_espacios(s)


def contar_palabras(s: str) -> int:
    return len(s.split())


def contiene_literal(texto: str, fragmento: str) -> bool:
    """El fragmento aparece tal cual en el texto, ignorando diferencias de espacios."""
    fragmento = normalizar_espacios(fragmento)
    return bool(fragmento) and fragmento in normalizar_espacios(texto)


def contiene_normalizado(texto: str, fragmento: str) -> bool:
    fragmento = normalizar(fragmento)
    return bool(fragmento) and fragmento in normalizar(texto)


def contiene_palabra(texto: str, fragmento: str) -> bool:
    """El fragmento aparece como palabra(s) completa(s): "IA" no está en "media"."""
    fragmento = normalizar(fragmento)
    if not fragmento:
        return False
    return re.search(r"\b" + re.escape(fragmento) + r"\b", normalizar(texto)) is not None


def es_cifra(s: str) -> bool:
    return _CIFRA.fullmatch(s.strip()) is not None


def reducir_ancla(ancla: str) -> str:
    """Si el ancla es una frase con una cifra suelta, la reduce a esa cifra tal como aparece:
    "1,2 millones de hectáreas" → "1,2". Las palabras que acompañan a la cifra se traducen y
    harían fallar la validación de un borrador en otro idioma (research R5).

    Solo cuenta una cifra que es una palabra completa: "Lote360" o "Sentinel-2" son nombres
    propios con dígitos y quedan igual."""
    if es_cifra(ancla):
        return ancla.strip()
    for palabra in ancla.split():
        palabra = palabra.strip(".,;:()\"'¿?¡!")
        if es_cifra(palabra):
            return palabra
    return ancla


def contiene_ancla(texto: str, ancla: str) -> bool:
    """Una cifra se compara contra los números del texto ("2" no está en "2024"); cualquier
    otra ancla, por palabra completa."""
    if es_cifra(ancla):
        numeros_ancla = extraer_numeros(ancla)
        return bool(numeros_ancla) and set(numeros_ancla) <= set(extraer_numeros(texto))
    return contiene_palabra(texto, ancla)


def extraer_urls_emails(s: str) -> list[str]:
    urls = [u.rstrip(".,;:!?") for u in _URL.findall(s)]
    return urls + _EMAIL.findall(s)


def extraer_numeros(s: str) -> list[str]:
    """Números normalizados a dígitos: "10.000" y "10,000" → "10000"; "3,5" → "3.5";
    "30%" → "30". También extrae números pegados a letras ("ZEBRA-7731" → "7731")."""
    return [_normalizar_numero(token) for token in _NUMERO.findall(s)]


def _normalizar_numero(token: str) -> str:
    puntos, comas = token.count("."), token.count(",")
    if puntos and comas:
        # El separador que aparece último es el decimal; el otro, de miles.
        decimal = "." if token.rfind(".") > token.rfind(",") else ","
        miles = "," if decimal == "." else "."
        entero, _, fraccion = token.rpartition(decimal)
        return entero.replace(miles, "") + "." + fraccion
    if not (puntos or comas):
        return token
    partes = token.split("." if puntos else ",")
    # Varios separadores, o uno seguido de exactamente 3 dígitos: separador de miles.
    if len(partes) > 2 or len(partes[1]) == 3:
        return "".join(partes)
    return partes[0] + "." + partes[1]
