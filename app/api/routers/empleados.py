from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_empleado_service
from app.schemas.empleado import EmpleadoResponse, EmpleadoUpdate
from app.services.empleado_service import EmpleadoService

router = APIRouter(prefix="/empleados", tags=["empleados"])


@router.get("", response_model=list[EmpleadoResponse])
def listar_empleados(
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
) -> list[EmpleadoResponse]:
    """Devuelve todos los empleados registrados."""
    return service.listar_todos(db)


@router.patch("/{id_empleado}", response_model=EmpleadoResponse)
def actualizar_empleado(
    id_empleado: int,
    body: EmpleadoUpdate,
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
) -> EmpleadoResponse:
    """Actualiza los campos enviados del empleado (el resto permanece igual)."""
    return service.actualizar_parcial(db, id_empleado, body)
