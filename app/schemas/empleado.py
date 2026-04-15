from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EmpleadoResponse(BaseModel):
    """Empleado para consultas y respuestas de escritura."""

    model_config = ConfigDict(from_attributes=True)

    id_empleado: int
    id_empresa: int
    legajo: str = Field(..., max_length=50)
    nombre: str = Field(..., max_length=120)
    apellido: str = Field(..., max_length=120)
    dni: str = Field(..., max_length=32)
    cuil: str = Field(..., max_length=20)
    fecha_ingreso: date
    categoria_laboral: str = Field(..., max_length=120)
    tipo_jornada: str = Field(..., max_length=80)
    modalidad_fichada_habilitada: str = Field(..., max_length=80)
    estado: str = Field(..., max_length=40)


class EmpleadoUpdate(BaseModel):
    """Campos opcionales para actualización parcial (PATCH)."""

    legajo: str | None = Field(default=None, max_length=50)
    nombre: str | None = Field(default=None, max_length=120)
    apellido: str | None = Field(default=None, max_length=120)
    dni: str | None = Field(default=None, max_length=32)
    cuil: str | None = Field(default=None, max_length=20)
    fecha_ingreso: date | None = None
    categoria_laboral: str | None = Field(default=None, max_length=120)
    tipo_jornada: str | None = Field(default=None, max_length=80)
    modalidad_fichada_habilitada: str | None = Field(default=None, max_length=80)
    estado: str | None = Field(default=None, max_length=40)
    id_empresa: int | None = None
