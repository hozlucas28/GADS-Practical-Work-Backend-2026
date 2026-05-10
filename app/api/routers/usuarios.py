from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_usuario_service,
    require_rol,
)
from app.daos.usuario_dao import UsuarioDAO
from app.models import enums
from app.models.seguridad import Usuario
from app.schemas.import_csv import ImportSummary
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services import export_service, import_service
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> list[UsuarioResponse]:
    return service.listar_todos(db)


@router.post("/import", response_model=ImportSummary)
async def importar_usuarios_csv(
    file: UploadFile = File(...),
    dry_run: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> ImportSummary:
    """Importa usuarios masivos desde un CSV. La columna ``contrasena`` es texto plano (>= 8 chars), se hashea con bcrypt."""
    contenido = await file.read()
    return import_service.importar_usuarios(
        db=db, archivo_bytes=contenido, dry_run=dry_run
    )


@router.get("/export", response_class=Response)
def exportar_usuarios_csv(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> Response:
    """Exporta todos los usuarios como CSV (sin contrasena_hash)."""
    usuarios = UsuarioDAO().listar_todos(db)
    csv_text = export_service.exportar_usuarios(usuarios)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="usuarios.csv"'},
    )


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> UsuarioResponse:
    return service.crear(db, body)


@router.get("/{id_usuario}", response_model=UsuarioResponse)
def obtener_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
    current: Usuario = Depends(get_current_user),
) -> UsuarioResponse:
    if current.rol != enums.Rol.ADMINISTRADOR and current.id_usuario != id_usuario:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
    return service.obtener(db, id_usuario)


@router.patch("/{id_usuario}", response_model=UsuarioResponse)
def actualizar_usuario(
    id_usuario: int,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
    current: Usuario = Depends(get_current_user),
) -> UsuarioResponse:
    es_admin = current.rol == enums.Rol.ADMINISTRADOR
    if not es_admin and current.id_usuario != id_usuario:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
    patch = body.model_dump(exclude_unset=True)
    if "rol" in patch and not es_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo Admin puede modificar el rol"
        )
    return service.actualizar_parcial(db, id_usuario, body)


@router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> None:
    service.eliminar(db, id_usuario)
