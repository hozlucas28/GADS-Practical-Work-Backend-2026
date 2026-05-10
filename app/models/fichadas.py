from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums
from app.models.base import Base
from app.models.mixins import TimestampMixin
from app.models.seguridad import Usuario

if TYPE_CHECKING:
    from app.models.organizacion import Empleado
    from app.models.novedades import Novedad


class OrigenFichada(Base, TimestampMixin):
    __tablename__ = "origenes_fichada"

    id_origen_fichada: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_origen: Mapped[enums.OrigenFichada] = mapped_column(
        SAEnum(enums.OrigenFichada, native_enum=False, length=40),
        unique=True,
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    fichadas: Mapped[list["Fichada"]] = relationship(back_populates="origen")


class Fichada(Base, TimestampMixin):
    __tablename__ = "fichadas"

    id_fichada: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    tipo_fichada: Mapped[enums.TipoFichada] = mapped_column(
        SAEnum(enums.TipoFichada, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    fue_corregida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    id_empleado: Mapped[int] = mapped_column(ForeignKey("empleados.id_empleado"), nullable=False, index=True)
    id_origen_fichada: Mapped[int] = mapped_column(
        ForeignKey("origenes_fichada.id_origen_fichada"), nullable=False, index=True
    )
    id_usuario_registrador: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )

    empleado: Mapped["Empleado"] = relationship(back_populates="fichadas")
    origen: Mapped["OrigenFichada"] = relationship(back_populates="fichadas")
    usuario_registrador: Mapped["Usuario"] = relationship(back_populates="fichadas_registradas")
    novedades: Mapped[list["Novedad"]] = relationship(back_populates="fichada")
