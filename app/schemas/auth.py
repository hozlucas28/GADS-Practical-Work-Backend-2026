from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

try:
    from pydantic import EmailStr  # type: ignore[attr-defined]

    _EMAIL_TYPE = EmailStr
except ImportError:  # pragma: no cover - fallback si email-validator no está
    _EMAIL_TYPE = str  # type: ignore[assignment,misc]

from app.models import enums


class LoginRequest(BaseModel):
    nombre_usuario: str = Field(..., min_length=1, max_length=120)
    contrasena: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre_usuario: str
    email: str
    rol: enums.Rol
    estado: enums.EstadoEntidad
    id_empleado: int


class RegisterFirstAdminRequest(BaseModel):
    nombre_usuario: str = Field(..., min_length=1, max_length=120)
    contrasena: str = Field(..., min_length=8, max_length=255)
    email: _EMAIL_TYPE  # type: ignore[valid-type]
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    dni: str = Field(..., min_length=1, max_length=32)
    cuil: str = Field(..., min_length=1, max_length=20)
    legajo: str = Field(..., min_length=1, max_length=50)
    empresa_razon_social: str = Field(..., min_length=1, max_length=255)
    empresa_cuit: str = Field(..., min_length=1, max_length=20)
    empresa_email: _EMAIL_TYPE  # type: ignore[valid-type]
    empresa_telefono: str = Field(..., min_length=1, max_length=50)
    empresa_direccion: str = Field(..., min_length=1)
