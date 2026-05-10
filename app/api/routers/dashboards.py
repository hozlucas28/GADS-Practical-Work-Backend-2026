from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_rol
from app.models import enums
from app.models.seguridad import Usuario
from app.schemas.dashboard import (
    EmpleadoStatusDetalle,
    EmpleadoStatusList,
    ResumenDashboard,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/resumen", response_model=ResumenDashboard)
def resumen(
    id_empresa: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
) -> ResumenDashboard:
    """Métricas globales (Admin) o de la empresa propia (ContadorExterno).

    Admin: ``id_empresa`` opcional para filtrar; sin él, ve todo.
    ContadorExterno: ``id_empresa`` se ignora y se fuerza la propia.
    """
    return dashboard_service.resumen(db, id_empresa=id_empresa, current=current)


@router.get("/empleados/status", response_model=EmpleadoStatusList)
def empleados_status(
    id_empresa: int | None = Query(default=None),
    estado: enums.EstadoEntidad | None = Query(default=None),
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
) -> EmpleadoStatusList:
    """Listado de empleados con métricas resumidas (última fichada, fichadas 30d, novedades pendientes)."""
    return dashboard_service.listar_status(
        db, id_empresa=id_empresa, estado=estado, current=current
    )


@router.get("/empleados/{id_empleado}", response_model=EmpleadoStatusDetalle)
def empleado_detalle(
    id_empleado: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
) -> EmpleadoStatusDetalle:
    """Detalle del empleado: fichadas por mes, novedades por tipo, etc.

    Admin: cualquier empleado. ContadorExterno: empleados de su empresa. Empleado: solo a sí mismo.
    """
    return dashboard_service.detalle_empleado(
        db, id_empleado=id_empleado, current=current
    )
