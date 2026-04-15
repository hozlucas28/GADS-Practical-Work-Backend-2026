from __future__ import annotations

from enum import Enum


class Rol(str, Enum):
    """Valores de ejemplo permitidos para el nombre de un rol."""

    ADMINISTRADOR = "Administrador"
    EMPLEADO = "Empleado"
    CONTADOR_EXTERNO = "ContadorExterno"


class OrigenFichada(str, Enum):
    """Valores de ejemplo para el nombre del origen de fichada."""

    BIOMETRICO = "biometrico"
    MANUAL = "manual"
    QR = "qr"
    API = "api"
    EXCEL = "excel"


class UnidadMedidaTipoNovedad(str, Enum):
    """Valores de ejemplo para la unidad de medida de un tipo de novedad."""

    MINUTOS = "minutos"
    HORAS = "horas"
    DIAS = "dias"


class EstadoCierreMensual(str, Enum):
    """Estados posibles de un cierre mensual."""

    BORRADOR = "borrador"
    CERRADO = "cerrado"


class TipoFormatoExportacion(str, Enum):
    """Formatos posibles de una exportación."""

    EXCEL = "Excel"
    CSV = "CSV"
    PDF = "PDF"


class TipoDiaEspecial(str, Enum):
    """Ejemplos de tipo de día especial."""

    FERIADO = "feriado"
    VACACIONES = "vacaciones"
    DESCANSO_EXTRAORDINARIO = "descanso extraordinario"


class AccionAuditoria(str, Enum):
    """Ejemplos de acción en registros de auditoría."""

    ALTA = "alta"
    MODIFICACION = "modificacion"
    BAJA_LOGICA = "bajaLogica"
