from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsuarioResponse(BaseModel):
    """Usuario para listados y consultas (sin datos sensibles)."""

    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre_usuario: str
    email: str
    estado: str
    ultimo_acceso: datetime | None = None
    id_rol: int
    id_empleado: int
    nombre_rol: str = Field(..., description="Valor textual del rol (p. ej. Administrador)")


class UsuarioUpdate(BaseModel):
    """Campos opcionales para actualización parcial (PATCH).

    Si se envía ``contrasena``, se persiste el hash (no se devuelve en respuestas).
    """

    nombre_usuario: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    estado: str | None = Field(default=None, max_length=40)
    ultimo_acceso: datetime | None = None
    id_rol: int | None = None
    id_empleado: int | None = None
    contrasena: str | None = Field(default=None, min_length=1, max_length=255)
