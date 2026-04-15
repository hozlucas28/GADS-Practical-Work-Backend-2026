from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UnidadMedidaTipoNovedad
from app.models.fichadas import Fichada
from app.models.seguridad import Usuario

if TYPE_CHECKING:
    from app.models.organizacion import Empleado


class TipoNovedad(Base):
    __tablename__ = "tipos_novedad"

    id_tipo_novedad: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_tipo: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unidad_medida: Mapped[UnidadMedidaTipoNovedad] = mapped_column(
        SAEnum(UnidadMedidaTipoNovedad, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    requiere_justificativo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requiere_aprobacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impacta_liquidacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    novedades: Mapped[list["Novedad"]] = relationship(back_populates="tipo")


class Novedad(Base):
    __tablename__ = "novedades"

    id_novedad: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fecha_hasta: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    origen: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    observacion: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    id_empleado: Mapped[int] = mapped_column(ForeignKey("empleados.id_empleado"), nullable=False, index=True)
    id_tipo_novedad: Mapped[int] = mapped_column(
        ForeignKey("tipos_novedad.id_tipo_novedad"), nullable=False, index=True
    )
    id_fichada: Mapped[int] = mapped_column(ForeignKey("fichadas.id_fichada"), nullable=False, index=True)
    id_usuario_creador: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )

    empleado: Mapped["Empleado"] = relationship(back_populates="novedades")
    tipo: Mapped["TipoNovedad"] = relationship(back_populates="novedades")
    fichada: Mapped["Fichada"] = relationship(back_populates="novedades")
    usuario_creador: Mapped["Usuario"] = relationship(back_populates="novedades_creadas")
    justificativo: Mapped["Justificativo | None"] = relationship(
        back_populates="novedad", uselist=False
    )


class Justificativo(Base):
    __tablename__ = "justificativos"

    id_justificativo: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_justificativo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(1024), nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    id_novedad: Mapped[int] = mapped_column(ForeignKey("novedades.id_novedad"), nullable=False, unique=True, index=True)
    id_usuario_cargador: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )

    novedad: Mapped["Novedad"] = relationship(back_populates="justificativo")
    usuario_cargador: Mapped["Usuario"] = relationship(back_populates="justificativos_cargados")
