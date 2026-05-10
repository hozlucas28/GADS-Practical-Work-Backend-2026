from __future__ import annotations

from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import enums


class HorarioCreate(BaseModel):
    nombre_horario: str = Field(..., min_length=1, max_length=120)
    tipo_horario: enums.TipoHorario
    hora_entrada_esperada: time
    hora_salida_esperada: time
    cantidad_horas_objetivo: Decimal = Field(..., gt=0)
    banda_horaria_inicio: time
    banda_horaria_fin: time
    tolerancia_entrada_minutos: int = Field(..., ge=0)
    tolerancia_salida_minutos: int = Field(..., ge=0)
    tiempo_minimo_descanso_minutos: int = Field(..., ge=0)
    umbral_horas_extra_minutos: int = Field(..., ge=0)
    dias_descanso_semanal: str = Field(..., min_length=1, max_length=255)
    estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO


class HorarioUpdate(BaseModel):
    nombre_horario: str | None = None
    tipo_horario: enums.TipoHorario | None = None
    hora_entrada_esperada: time | None = None
    hora_salida_esperada: time | None = None
    cantidad_horas_objetivo: Decimal | None = None
    banda_horaria_inicio: time | None = None
    banda_horaria_fin: time | None = None
    tolerancia_entrada_minutos: int | None = None
    tolerancia_salida_minutos: int | None = None
    tiempo_minimo_descanso_minutos: int | None = None
    umbral_horas_extra_minutos: int | None = None
    dias_descanso_semanal: str | None = None
    estado: enums.EstadoEntidad | None = None


class HorarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_horario: int
    nombre_horario: str
    tipo_horario: enums.TipoHorario
    hora_entrada_esperada: time
    hora_salida_esperada: time
    cantidad_horas_objetivo: Decimal
    banda_horaria_inicio: time
    banda_horaria_fin: time
    tolerancia_entrada_minutos: int
    tolerancia_salida_minutos: int
    tiempo_minimo_descanso_minutos: int
    umbral_horas_extra_minutos: int
    dias_descanso_semanal: str
    estado: enums.EstadoEntidad
