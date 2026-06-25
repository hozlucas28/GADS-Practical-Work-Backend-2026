from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db, require_rol
from app.config import settings
from app.daos.fichada_dao import FichadaDAO
from app.models import enums
from app.models.fichadas import Fichada, OrigenFichada
from app.models.organizacion import Empleado
from app.models.seguridad import Usuario
from app.schemas.fichada import (
    FichadaCreate,
    FichadaImportResponse,
    FichadaResponse,
    FichadaUpdate,
    OrigenFichadaResponse,
)
from app.services import export_service
from app.services.fichada_import_service import importar_csv, importar_xlsx
from app.services.fichada_service import FichadaService

router = APIRouter(prefix="/fichadas", tags=["fichadas"])


def get_fichada_service() -> FichadaService:
    return FichadaService(FichadaDAO())


def _id_empresa_de(usuario: Usuario) -> int | None:
    empleado = getattr(usuario, "empleado", None)
    return getattr(empleado, "id_empresa", None) if empleado else None


@router.get("/origenes", response_model=list[OrigenFichadaResponse])
def listar_origenes_fichada(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)),
) -> list[OrigenFichadaResponse]:
    """Devuelve los orígenes de fichada disponibles para usar al crear una fichada."""
    origenes = db.execute(select(OrigenFichada).order_by(OrigenFichada.id_origen_fichada)).scalars().all()
    return [OrigenFichadaResponse.model_validate(o) for o in origenes]


@router.get("", response_model=list[FichadaResponse])
def listar_fichadas(
    id_empleado: int | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
    service: FichadaService = Depends(get_fichada_service),
) -> list[FichadaResponse]:
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        id_emp = _id_empresa_de(current)
        if id_empleado is not None:
            emp = db.get(Empleado, id_empleado)
            if emp is None or emp.id_empresa != id_emp:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Empleado fuera de su empresa")
    return service.listar_todos(db, id_empleado=id_empleado, desde=desde, hasta=hasta)


@router.post("", response_model=FichadaResponse, status_code=status.HTTP_201_CREATED)
def crear_fichada(
    body: FichadaCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
    service: FichadaService = Depends(get_fichada_service),
) -> FichadaResponse:
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        id_emp = _id_empresa_de(current)
        emp = db.get(Empleado, body.id_empleado)
        if emp is None or emp.id_empresa != id_emp:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Empleado fuera de su empresa")
    return service.crear(db, body, current.id_usuario)


@router.get("/export", response_class=Response)
def exportar_fichadas(
    formato: Literal["xlsx", "csv"] = Query(default="xlsx"),
    id_empresa: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
) -> Response:
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        empleado_vinculado = (
            db.get(Empleado, current.id_empleado) if current.id_empleado else None
        )
        if empleado_vinculado is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Usuario sin empleado vinculado para inferir empresa",
            )
        id_empresa = empleado_vinculado.id_empresa

    stmt = (
        select(Fichada)
        .options(selectinload(Fichada.empleado), selectinload(Fichada.origen))
        .order_by(Fichada.fecha_hora)
    )
    if id_empresa is not None:
        stmt = stmt.join(Empleado, Empleado.id_empleado == Fichada.id_empleado).where(
            Empleado.id_empresa == id_empresa
        )

    fichadas = list(db.scalars(stmt).all())

    if formato == "xlsx":
        content = export_service.exportar_fichadas_xlsx(fichadas)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="fichadas.xlsx"'},
        )
    csv_text = export_service.exportar_fichadas(fichadas)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="fichadas.csv"'},
    )


@router.post("/import", response_model=FichadaImportResponse)
async def importar_fichadas(
    file: UploadFile = File(...),
    dry_run: bool = False,
    id_empresa: int | None = None,
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
) -> FichadaImportResponse:
    if current.rol == enums.Rol.ADMINISTRADOR:
        if id_empresa is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Administrador debe indicar id_empresa",
            )
        id_empresa_default = id_empresa
    else:
        empleado_vinculado: Empleado | None = (
            db.get(Empleado, current.id_empleado) if current.id_empleado else None
        )
        if empleado_vinculado is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Usuario sin empleado vinculado para inferir empresa",
            )
        id_empresa_default = empleado_vinculado.id_empresa

    contenido = await file.read()
    nombre = (file.filename or "").lower()

    if nombre.endswith(".xlsx"):
        return importar_xlsx(
            db=db,
            archivo_bytes=contenido,
            id_usuario_registrador=current.id_usuario,
            id_empresa_default=id_empresa_default,
            dry_run=dry_run,
            timezone_name=settings.default_timezone,
        )

    return importar_csv(
        db=db,
        archivo_bytes=contenido,
        id_usuario_registrador=current.id_usuario,
        id_empresa_default=id_empresa_default,
        dry_run=dry_run,
        timezone_name=settings.default_timezone,
    )


@router.get("/{id_fichada}", response_model=FichadaResponse)
def obtener_fichada(
    id_fichada: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
    service: FichadaService = Depends(get_fichada_service),
) -> FichadaResponse:
    resp = service.obtener(db, id_fichada)
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        id_emp = _id_empresa_de(current)
        emp = db.get(Empleado, resp.id_empleado)
        if emp is None or emp.id_empresa != id_emp:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado")
    return resp


@router.patch("/{id_fichada}", response_model=FichadaResponse)
def actualizar_fichada(
    id_fichada: int,
    body: FichadaUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(
        require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)
    ),
    service: FichadaService = Depends(get_fichada_service),
) -> FichadaResponse:
    return service.actualizar_parcial(db, id_fichada, body)


@router.delete("/{id_fichada}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_fichada(
    id_fichada: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: FichadaService = Depends(get_fichada_service),
) -> None:
    service.eliminar(db, id_fichada)
