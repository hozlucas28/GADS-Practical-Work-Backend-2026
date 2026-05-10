from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import enums


class ConteoEntidad(BaseModel):
    total: int
    activos: int
    inactivos: int


class ConteoUsuarios(BaseModel):
    total: int
    por_rol: dict[str, int]


class ConteoFichadas(BaseModel):
    total: int
    ultimos_7_dias: int
    ultimos_30_dias: int


class ConteoNovedades(BaseModel):
    total: int
    pendientes: int
    aprobadas: int
    rechazadas: int
    anuladas: int


class ResumenDashboard(BaseModel):
    """Métricas globales (Admin) o de una empresa (ContadorExterno / filtro Admin)."""

    id_empresa: int | None = None
    empresas: ConteoEntidad
    empleados: ConteoEntidad
    empleados_por_categoria: dict[str, int]
    empleados_por_jornada: dict[str, int]
    usuarios: ConteoUsuarios
    fichadas: ConteoFichadas
    novedades: ConteoNovedades


class EmpleadoStatus(BaseModel):
    """Estado resumen de un empleado."""

    model_config = ConfigDict(from_attributes=True)

    id_empleado: int
    id_empresa: int
    legajo: str
    nombre: str
    apellido: str
    estado: enums.EstadoEntidad
    categoria_laboral: enums.CategoriaLaboral
    tipo_jornada: enums.TipoJornada
    ultima_fichada: datetime | None
    fichadas_ultimos_30_dias: int
    novedades_pendientes: int


class EmpleadoStatusList(BaseModel):
    total: int
    items: list[EmpleadoStatus]


class EmpleadoStatusDetalle(BaseModel):
    id_empleado: int
    id_empresa: int
    legajo: str
    nombre: str
    apellido: str
    estado: enums.EstadoEntidad
    categoria_laboral: enums.CategoriaLaboral
    tipo_jornada: enums.TipoJornada
    modalidad_fichada_habilitada: enums.ModalidadFichada
    ultima_fichada: datetime | None
    primera_fichada: datetime | None
    fichadas_total: int
    fichadas_ultimos_30_dias: int
    fichadas_por_mes: dict[str, int]
    novedades_total: int
    novedades_pendientes: int
    novedades_por_tipo: dict[str, int]
