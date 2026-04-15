"""Modelos ORM (SQLAlchemy) del dominio. Importar este módulo registra todas las tablas en Base.metadata."""

from app.models.base import Base
import app.models.enums as enums

from app.models.enums import (
    AccionAuditoria,
    EstadoCierreMensual,
    TipoDiaEspecial,
    TipoFormatoExportacion,
    UnidadMedidaTipoNovedad,
)
from app.models.mixins import TimestampMixin
from app.models.seguridad import Rol, Usuario
from app.models.organizacion import Empresa, Empleado
from app.models.horarios import Horario, AsignacionHorario
from app.models.fichadas import OrigenFichada, Fichada
from app.models.novedades import Justificativo, Novedad, TipoNovedad
from app.models.operaciones import (
    Auditoria,
    CierreMensual,
    DiasEspeciales,
    Exportacion,
    ResumenMensualEmpleado,
)

__all__ = [
    "Base",
    "enums",
    "UnidadMedidaTipoNovedad",
    "EstadoCierreMensual",
    "TipoFormatoExportacion",
    "TipoDiaEspecial",
    "AccionAuditoria",
    "TimestampMixin",
    "Rol",
    "Usuario",
    "Empresa",
    "Empleado",
    "Horario",
    "AsignacionHorario",
    "OrigenFichada",
    "Fichada",
    "TipoNovedad",
    "Novedad",
    "Justificativo",
    "CierreMensual",
    "ResumenMensualEmpleado",
    "Exportacion",
    "DiasEspeciales",
    "Auditoria",
]
