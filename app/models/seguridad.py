from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums as enums_models
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.fichadas import Fichada
    from app.models.novedades import Justificativo, Novedad
    from app.models.organizacion import Empleado
    from app.models.operaciones import Auditoria, CierreMensual, Exportacion


class Rol(Base):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_rol: Mapped[enums_models.Rol] = mapped_column(
        SAEnum(enums_models.Rol, native_enum=False, length=40),
        unique=True,
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_usuario: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    id_rol: Mapped[int] = mapped_column(ForeignKey("roles.id_rol"), nullable=False, index=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado"), nullable=False, unique=True, index=True
    )

    rol: Mapped["Rol"] = relationship(back_populates="usuarios")
    empleado: Mapped["Empleado"] = relationship(back_populates="usuario")

    exportaciones: Mapped[list["Exportacion"]] = relationship(back_populates="usuario_generador")
    fichadas_registradas: Mapped[list["Fichada"]] = relationship(back_populates="usuario_registrador")
    novedades_creadas: Mapped[list["Novedad"]] = relationship(back_populates="usuario_creador")
    justificativos_cargados: Mapped[list["Justificativo"]] = relationship(
        back_populates="usuario_cargador"
    )
    cierres_mensuales_realizados: Mapped[list["CierreMensual"]] = relationship(
        back_populates="usuario_cierre"
    )
    auditorias: Mapped[list["Auditoria"]] = relationship(back_populates="usuario")
