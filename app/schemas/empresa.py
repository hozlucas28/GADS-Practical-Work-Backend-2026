from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import enums


class EmpresaCreate(BaseModel):
    razon_social: str = Field(..., min_length=1, max_length=255)
    cuit: str = Field(..., min_length=1, max_length=20)
    email_contacto: str = Field(..., max_length=255)
    telefono_contacto: str = Field(..., max_length=50)
    direccion: str = Field(..., min_length=1)
    fecha_alta: date
    estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO


class EmpresaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_empresa: int
    razon_social: str
    cuit: str
    email_contacto: str
    telefono_contacto: str
    direccion: str
    fecha_alta: date
    estado: enums.EstadoEntidad


class EmpresaUpdate(BaseModel):
    razon_social: str | None = None
    cuit: str | None = None
    email_contacto: str | None = None
    telefono_contacto: str | None = None
    direccion: str | None = None
    estado: enums.EstadoEntidad | None = None
