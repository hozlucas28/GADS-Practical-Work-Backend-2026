from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import enums


class OrigenFichadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_origen_fichada: int
    nombre_origen: enums.OrigenFichada
    descripcion: str | None = None


class FichadaImportError(BaseModel):
    fila: int
    motivo: str
    legajo: str | None = None


class FichadaImportResponse(BaseModel):
    total_filas: int
    fichadas_creadas: int
    novedades_creadas: int
    tipos_novedad_creados: list[str]
    origenes_fichada_existentes: list[str]
    errores: list[FichadaImportError]
    dry_run: bool


class FichadaCreate(BaseModel):
    fecha_hora: datetime
    tipo_fichada: enums.TipoFichada
    observacion: str | None = None
    id_empleado: int
    id_origen_fichada: int


class FichadaUpdate(BaseModel):
    fecha_hora: datetime | None = None
    tipo_fichada: enums.TipoFichada | None = None
    observacion: str | None = None
    fue_corregida: bool | None = None
    id_origen_fichada: int | None = None


class FichadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_fichada: int
    fecha_hora: datetime
    tipo_fichada: enums.TipoFichada
    fue_corregida: bool
    observacion: str | None = None
    id_empleado: int
    id_origen_fichada: int
    id_usuario_registrador: int
