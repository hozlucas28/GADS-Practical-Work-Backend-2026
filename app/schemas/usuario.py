from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import enums


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre_usuario: str
    email: str
    estado: enums.EstadoEntidad
    ultimo_acceso: datetime | None = None
    id_empleado: int
    rol: enums.Rol = Field(..., description="Valor del enum Rol (Administrador/Empleado/ContadorExterno).")


class UsuarioCreate(BaseModel):
    nombre_usuario: str = Field(..., min_length=1, max_length=120)
    contrasena: str = Field(..., min_length=8, max_length=255)
    email: str = Field(..., max_length=255)
    rol: enums.Rol
    id_empleado: int
    estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO


class UsuarioUpdate(BaseModel):
    nombre_usuario: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    estado: enums.EstadoEntidad | None = None
    ultimo_acceso: datetime | None = None
    rol: enums.Rol | None = None
    contrasena: str | None = Field(default=None, min_length=8, max_length=255)
