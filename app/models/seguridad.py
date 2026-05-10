from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums
from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.fichadas import Fichada
    from app.models.novedades import Justificativo, Novedad
    from app.models.organizacion import Empleado
    from app.models.operaciones import Auditoria, CierreMensual, Exportacion


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_usuario: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    rol: Mapped[enums.Rol] = mapped_column(
        SAEnum(enums.Rol, native_enum=False, length=40), nullable=False, index=True
    )
    estado: Mapped[enums.EstadoEntidad] = mapped_column(
        SAEnum(enums.EstadoEntidad, native_enum=False, length=20), nullable=False, index=True
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado"), nullable=False, unique=True, index=True
    )

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
