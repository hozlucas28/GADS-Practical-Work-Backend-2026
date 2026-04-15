from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    AccionAuditoria,
    EstadoCierreMensual,
    TipoDiaEspecial,
    TipoFormatoExportacion,
)
from app.models.seguridad import Usuario

if TYPE_CHECKING:
    from app.models.organizacion import Empleado, Empresa


class Exportacion(Base):
    __tablename__ = "exportaciones"

    id_exportacion: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_formato: Mapped[TipoFormatoExportacion] = mapped_column(
        SAEnum(TipoFormatoExportacion, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(1024), nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    version_formato: Mapped[str] = mapped_column(String(40), nullable=False)

    id_usuario_generador: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )

    usuario_generador: Mapped["Usuario"] = relationship(back_populates="exportaciones")
    cierres_mensuales: Mapped[list["CierreMensual"]] = relationship(back_populates="exportacion")


class CierreMensual(Base):
    __tablename__ = "cierres_mensuales"
    __table_args__ = (
        UniqueConstraint("id_empresa", "anio", "mes", name="uq_cierre_empresa_periodo"),
    )

    id_cierre_mensual: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_cierre: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estado: Mapped[EstadoCierreMensual] = mapped_column(
        SAEnum(EstadoCierreMensual, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    observaciones: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    id_usuario_cierre: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresas.id_empresa"), nullable=False, index=True)
    id_exportacion: Mapped[int] = mapped_column(
        ForeignKey("exportaciones.id_exportacion"), nullable=False, index=True
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="cierres_mensuales")
    usuario_cierre: Mapped["Usuario"] = relationship(back_populates="cierres_mensuales_realizados")
    exportacion: Mapped["Exportacion"] = relationship(back_populates="cierres_mensuales")
    resumenes_mensuales_empleado: Mapped[list["ResumenMensualEmpleado"]] = relationship(
        back_populates="cierre_mensual"
    )


class ResumenMensualEmpleado(Base):
    """Consolidado mensual por empleado dentro de un cierre de período.

    Fichada = dato crudo; Novedad = evento interpretado; este resumen agrega métricas del
    empleado para el período del :class:`CierreMensual` (cierre global de la empresa).
    """

    __tablename__ = "resumenes_mensuales_empleado"
    __table_args__ = (
        UniqueConstraint(
            "id_empleado",
            "id_cierre_mensual",
            name="uq_resumen_mensual_empleado_cierre",
        ),
    )

    id_resumen_mensual_empleado: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dias_trabajados: Mapped[int] = mapped_column(Integer, nullable=False)
    ausencias_justificadas: Mapped[int] = mapped_column(Integer, nullable=False)
    ausencias_injustificadas: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_tardanzas: Mapped[int] = mapped_column(Integer, nullable=False)
    horas_trabajadas: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    horas_extra_50: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    horas_extra_100: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    dias_licencia: Mapped[int] = mapped_column(Integer, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    id_empleado: Mapped[int] = mapped_column(ForeignKey("empleados.id_empleado"), nullable=False, index=True)
    id_cierre_mensual: Mapped[int] = mapped_column(
        ForeignKey("cierres_mensuales.id_cierre_mensual"), nullable=False, index=True
    )

    empleado: Mapped["Empleado"] = relationship(back_populates="resumenes_mensuales_empleado")
    cierre_mensual: Mapped["CierreMensual"] = relationship(back_populates="resumenes_mensuales_empleado")


class DiasEspeciales(Base):
    __tablename__ = "dias_especiales"

    id_dia_especial: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_dia_especial: Mapped[TipoDiaEspecial] = mapped_column(
        SAEnum(TipoDiaEspecial, native_enum=False, length=40),
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    es_laborable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entidad_afectada: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    id_registro_afectado: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accion: Mapped[AccionAuditoria] = mapped_column(
        SAEnum(AccionAuditoria, native_enum=False, length=40),
        nullable=False,
        index=True,
    )
    valor_anterior: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False, index=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="auditorias")
