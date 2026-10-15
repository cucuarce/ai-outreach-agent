"""Tipos del dominio (specs/001-outreach-draft/data-model.md).

Las reglas de cada campo se verifican en los nodos de `verificacion/`, no al construir los
objetos: los candidatos que devuelve un agente pueden ser inválidos y deben poder representarse
para descartarlos y registrarlo en la traza.
"""

from dataclasses import asdict, dataclass, field
from enum import StrEnum

IDIOMAS_SOPORTADOS = ("es", "en", "pt", "fr", "de", "it")

MAX_DESCRIPCION = 200
MAX_CITA = 300


class Estado(StrEnum):
    BORRADOR = "borrador"
    INSUFICIENTE = "insuficiente"
    INVALIDO = "invalido"
    ERROR = "error"


class Motivo(StrEnum):
    EMPRESA_VACIA = "empresa_vacia"
    PERFIL_VACIO = "perfil_vacio"
    IDIOMA_INDETERMINADO = "idioma_indeterminado"
    HECHOS_INSUFICIENTES = "hechos_insuficientes"
    PERFIL_SIN_PUNTOS = "perfil_sin_puntos"
    SIN_CONEXION_PERFIL = "sin_conexion_perfil"
    VALIDACION_FALLIDA = "validacion_fallida"
    RESPUESTA_INVALIDA_LLM = "respuesta_invalida_llm"
    PROVEEDOR_NO_DISPONIBLE = "proveedor_no_disponible"
    CONTEXTO_EXCEDIDO = "contexto_excedido"


@dataclass(frozen=True)
class Entrada:
    texto_empresa: str  # contenido no confiable
    perfil: str
    idioma_solicitado: str | None = None  # uno de IDIOMAS_SOPORTADOS
    # --nombre-empresa: tiene prioridad sobre el nombre extraído del texto y no se verifica
    # contra él (research R12).
    nombre_empresa_solicitado: str | None = None


@dataclass(frozen=True)
class Hecho:
    """Dato concreto de la empresa.

    - `descripcion` ≤ 200 caracteres. Solo para la traza y la salida al usuario; MUST NOT
      enviarse al estratega ni al redactor.
    - `cita` … ≤ 300 caracteres. MUST aparecer en el texto (espacios normalizados).
    - `ancla`: elemento que no se traduce (nombre propio, cifra o término técnico) que MUST
      aparecer en `cita`.
    - `ancla_original`: el ancla que devolvió el investigador, solo si `verificar_hechos` le
      quitó una fórmula de búsqueda (spec 002, research D1); si no, None.
    """

    id: str
    descripcion: str
    cita: str
    ancla: str
    ancla_original: str | None = None


@dataclass(frozen=True)
class PuntoPerfil:
    """Punto concreto del perfil. `cita` MUST aparecer en el perfil; `ancla` sigue la misma
    regla que en Hecho, respecto de la cita del perfil."""

    id: str
    descripcion: str
    cita: str
    ancla: str


@dataclass(frozen=True)
class ElementoUsado:
    """Dato de la empresa o punto del perfil tal como se informa al usuario: solo lo verificado
    (cita literal y ancla). La `descripcion` escrita por el modelo queda solo en la traza."""

    id: str
    cita: str
    ancla: str

    @classmethod
    def de(cls, elemento: "Hecho | PuntoPerfil") -> "ElementoUsado":
        return cls(id=elemento.id, cita=elemento.cita, ancla=elemento.ancla)


@dataclass(frozen=True)
class Conexion:
    hecho_id: str
    punto_id: str
    razon: str


@dataclass(frozen=True)
class Estrategia:
    angulo: str
    hechos_elegidos: list[str]
    puntos_perfil: list[PuntoPerfil]
    conexiones: list[Conexion]


@dataclass(frozen=True)
class Borrador:
    texto: str
    hechos_usados: list[str]
    puntos_usados: list[str]


@dataclass(frozen=True)
class Fallo:
    criterio: str  # longitud | relleno | idioma | hechos | perfil | numeros | enlaces | empresa
    detalle: str


@dataclass(frozen=True)
class ResultadoValidacion:
    ok: bool
    fallos: list[Fallo] = field(default_factory=list)


@dataclass(frozen=True)
class Resultado:
    estado: Estado
    run_id: str
    idioma: str | None = None
    nombre_empresa: str | None = None
    origen_nombre_empresa: str | None = None  # "usuario" | "texto" | None
    borrador: Borrador | None = None
    hechos_usados: list[ElementoUsado] = field(default_factory=list)
    puntos_usados: list[ElementoUsado] = field(default_factory=list)
    motivo: Motivo | None = None
    detalle: str | None = None
    fallos: list[Fallo] = field(default_factory=list)
    rutas_registro: dict[str, str] | None = None  # {"jsonl": ..., "md": ...}

    def a_dict(self) -> dict:
        """Serializa con claves en español y los enums como sus valores de texto."""
        datos = asdict(self)
        datos["estado"] = self.estado.value
        datos["motivo"] = self.motivo.value if self.motivo else None
        return datos
