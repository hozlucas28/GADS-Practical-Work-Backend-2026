from __future__ import annotations

from enum import Enum


class Rol(str, Enum):
    """Valores de ejemplo permitidos para el nombre de un rol."""

    ADMINISTRADOR = "Administrador"
    EMPLEADO = "Empleado"
    CONTADOR_EXTERNO = "ContadorExterno"


class OrigenFichada(str, Enum):
    """Origen de una fichada. `LOCAL` representa reloj/terminal in-situ (CSV "Local")."""

    BIOMETRICO = "biometrico"
    MANUAL = "manual"
    QR = "qr"
    API = "api"
    EXCEL = "excel"
    LOCAL = "local"


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


class EstadoEntidad(str, Enum):
    """Estado de entidades con baja lógica (usuarios, empresas, empleados, horarios, asignaciones)."""

    ACTIVO = "activo"
    INACTIVO = "inactivo"


class EstadoNovedad(str, Enum):
    """Ciclo de vida de una novedad."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    ANULADA = "anulada"


class OrigenNovedad(str, Enum):
    """Cómo se creó la novedad."""

    MANUAL = "manual"
    IMPORTACION = "importacion"
    AUTOMATICA = "automatica"


class EstadoJustificativo(str, Enum):
    """Estado de un justificativo cargado contra una novedad."""

    CARGADO = "cargado"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class EstadoExportacion(str, Enum):
    """Resultado de una exportación generada."""

    GENERADA = "generada"
    FALLIDA = "fallida"


class TipoFichada(str, Enum):
    """Tipo de marcado de la fichada. Mapea desde CSV `Entrada`/`Salida`."""

    ENTRADA = "entrada"
    SALIDA = "salida"


class TipoJornada(str, Enum):
    """Modalidad de jornada laboral del empleado."""

    COMPLETA = "completa"
    PARCIAL = "parcial"
    TURNOS = "turnos"


class ModalidadFichada(str, Enum):
    """Indica si el empleado puede fichar."""

    HABILITADA = "habilitada"
    DESHABILITADA = "deshabilitada"


class CategoriaLaboral(str, Enum):
    """Categoría laboral del empleado, usada para reglas de liquidación y reporting."""

    OPERACIONES = "operaciones"
    ADMINISTRACION = "administracion"
    CONTADURIA = "contaduria"


class TipoHorario(str, Enum):
    """Tipo de definición de horario."""

    FIJO = "fijo"
    ROTATIVO = "rotativo"
    FLEXIBLE = "flexible"


class TipoJustificativo(str, Enum):
    """Categoría del justificativo asociado a una novedad."""

    VACACIONES = "vacaciones"
    LICENCIA_MEDICA = "licencia_medica"
    OTROS = "otros"
