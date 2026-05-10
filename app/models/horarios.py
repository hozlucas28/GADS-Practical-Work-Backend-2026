from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums
from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.organizacion import Empleado


class Horario(Base, TimestampMixin):
    __tablename__ = "horarios"

    id_horario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_horario: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_horario: Mapped[enums.TipoHorario] = mapped_column(
        SAEnum(enums.TipoHorario, native_enum=False, length=20), nullable=False, index=True
    )
    hora_entrada_esperada: Mapped[time] = mapped_column(Time, nullable=False)
    hora_salida_esperada: Mapped[time] = mapped_column(Time, nullable=False)
    cantidad_horas_objetivo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    banda_horaria_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    banda_horaria_fin: Mapped[time] = mapped_column(Time, nullable=False)
    tolerancia_entrada_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    tolerancia_salida_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    tiempo_minimo_descanso_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    umbral_horas_extra_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_descanso_semanal: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[enums.EstadoEntidad] = mapped_column(
        SAEnum(enums.EstadoEntidad, native_enum=False, length=20), nullable=False, index=True
    )

    asignaciones: Mapped[list["AsignacionHorario"]] = relationship(back_populates="horario")


class AsignacionHorario(Base, TimestampMixin):
    __tablename__ = "asignaciones_horario"

    id_asignacion_horario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fecha_hasta: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    estado: Mapped[enums.EstadoEntidad] = mapped_column(
        SAEnum(enums.EstadoEntidad, native_enum=False, length=20), nullable=False, index=True
    )

    id_empleado: Mapped[int] = mapped_column(ForeignKey("empleados.id_empleado"), nullable=False, index=True)
    id_horario: Mapped[int] = mapped_column(ForeignKey("horarios.id_horario"), nullable=False, index=True)

    empleado: Mapped["Empleado"] = relationship(back_populates="asignaciones_horario")
    horario: Mapped["Horario"] = relationship(back_populates="asignaciones")
