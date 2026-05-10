from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums
from app.models.base import Base
from app.models.mixins import TimestampMixin
from app.models.seguridad import Usuario

if TYPE_CHECKING:
    from app.models.horarios import AsignacionHorario
    from app.models.fichadas import Fichada
    from app.models.novedades import Novedad
    from app.models.operaciones import CierreMensual, ResumenMensualEmpleado


class Empresa(Base, TimestampMixin):
    __tablename__ = "empresas"

    id_empresa: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    cuit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email_contacto: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono_contacto: Mapped[str] = mapped_column(String(50), nullable=False)
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[enums.EstadoEntidad] = mapped_column(
        SAEnum(enums.EstadoEntidad, native_enum=False, length=20), nullable=False, index=True
    )
    fecha_alta: Mapped[date] = mapped_column(Date, nullable=False)

    empleados: Mapped[list["Empleado"]] = relationship(back_populates="empresa")
    cierres_mensuales: Mapped[list["CierreMensual"]] = relationship(back_populates="empresa")


class Empleado(Base, TimestampMixin):
    __tablename__ = "empleados"
    __table_args__ = (UniqueConstraint("id_empresa", "legajo", name="uq_empleado_empresa_legajo"),)

    id_empleado: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    legajo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido: Mapped[str] = mapped_column(String(120), nullable=False)
    dni: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    cuil: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)
    categoria_laboral: Mapped[enums.CategoriaLaboral] = mapped_column(
        SAEnum(enums.CategoriaLaboral, native_enum=False, length=40), nullable=False
    )
    tipo_jornada: Mapped[enums.TipoJornada] = mapped_column(
        SAEnum(enums.TipoJornada, native_enum=False, length=20), nullable=False
    )
    modalidad_fichada_habilitada: Mapped[enums.ModalidadFichada] = mapped_column(
        SAEnum(enums.ModalidadFichada, native_enum=False, length=20), nullable=False
    )
    estado: Mapped[enums.EstadoEntidad] = mapped_column(
        SAEnum(enums.EstadoEntidad, native_enum=False, length=20), nullable=False, index=True
    )

    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresas.id_empresa"), nullable=False, index=True)

    empresa: Mapped["Empresa"] = relationship(back_populates="empleados")
    usuario: Mapped["Usuario | None"] = relationship(back_populates="empleado", uselist=False)

    asignaciones_horario: Mapped[list["AsignacionHorario"]] = relationship(
        back_populates="empleado"
    )
    fichadas: Mapped[list["Fichada"]] = relationship(back_populates="empleado")
    novedades: Mapped[list["Novedad"]] = relationship(back_populates="empleado")
    resumenes_mensuales_empleado: Mapped[list["ResumenMensualEmpleado"]] = relationship(
        back_populates="empleado"
    )
