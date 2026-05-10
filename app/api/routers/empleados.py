from __future__ import annotations

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_empleado_service,
    require_rol,
)
from app.daos.empleado_dao import EmpleadoDAO
from app.models import enums
from app.models.seguridad import Usuario
from app.schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from app.schemas.import_csv import ImportSummary
from app.services import export_service, import_service
from app.services.empleado_service import EmpleadoService

router = APIRouter(prefix="/empleados", tags=["empleados"])


@router.get("", response_model=list[EmpleadoResponse])
def listar_empleados(
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
    _: Usuario = Depends(get_current_user),
) -> list[EmpleadoResponse]:
    return service.listar_todos(db)


@router.post("/import", response_model=ImportSummary)
async def importar_empleados_csv(
    file: UploadFile = File(...),
    dry_run: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> ImportSummary:
    """Importa empleados masivos desde un CSV. Mismo formato que el export."""
    contenido = await file.read()
    return import_service.importar_empleados(
        db=db, archivo_bytes=contenido, dry_run=dry_run
    )


@router.get("/export", response_class=Response)
def exportar_empleados_csv(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> Response:
    """Exporta todos los empleados como CSV (UTF-8)."""
    empleados = EmpleadoDAO().listar_todos(db)
    csv_text = export_service.exportar_empleados(empleados)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="empleados.csv"'},
    )


@router.post("", response_model=EmpleadoResponse, status_code=status.HTTP_201_CREATED)
def crear_empleado(
    body: EmpleadoCreate,
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> EmpleadoResponse:
    return service.crear(db, body)


@router.get("/{id_empleado}", response_model=EmpleadoResponse)
def obtener_empleado(
    id_empleado: int,
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
    _: Usuario = Depends(get_current_user),
) -> EmpleadoResponse:
    return service.obtener(db, id_empleado)


@router.patch("/{id_empleado}", response_model=EmpleadoResponse)
def actualizar_empleado(
    id_empleado: int,
    body: EmpleadoUpdate,
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> EmpleadoResponse:
    return service.actualizar_parcial(db, id_empleado, body)


@router.delete("/{id_empleado}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_empleado(
    id_empleado: int,
    db: Session = Depends(get_db),
    service: EmpleadoService = Depends(get_empleado_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> None:
    service.eliminar(db, id_empleado)
