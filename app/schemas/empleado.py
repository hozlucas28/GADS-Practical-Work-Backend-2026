from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import enums


class EmpleadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_empleado: int
    id_empresa: int
    legajo: str = Field(..., max_length=50)
    nombre: str = Field(..., max_length=120)
    apellido: str = Field(..., max_length=120)
    dni: str = Field(..., max_length=32)
    cuil: str = Field(..., max_length=20)
    fecha_ingreso: date
    categoria_laboral: enums.CategoriaLaboral
    tipo_jornada: enums.TipoJornada
    modalidad_fichada_habilitada: enums.ModalidadFichada
    estado: enums.EstadoEntidad


class EmpleadoCreate(BaseModel):
    legajo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    dni: str = Field(..., min_length=1, max_length=32)
    cuil: str = Field(..., min_length=1, max_length=20)
    fecha_ingreso: date
    categoria_laboral: enums.CategoriaLaboral
    tipo_jornada: enums.TipoJornada
    modalidad_fichada_habilitada: enums.ModalidadFichada = enums.ModalidadFichada.HABILITADA
    id_empresa: int
    estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO


class EmpleadoUpdate(BaseModel):
    legajo: str | None = Field(default=None, max_length=50)
    nombre: str | None = Field(default=None, max_length=120)
    apellido: str | None = Field(default=None, max_length=120)
    dni: str | None = Field(default=None, max_length=32)
    cuil: str | None = Field(default=None, max_length=20)
    fecha_ingreso: date | None = None
    categoria_laboral: enums.CategoriaLaboral | None = None
    tipo_jornada: enums.TipoJornada | None = None
    modalidad_fichada_habilitada: enums.ModalidadFichada | None = None
    estado: enums.EstadoEntidad | None = None
