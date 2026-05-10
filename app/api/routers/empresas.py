from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_rol
from app.daos.empresa_dao import EmpresaDAO
from app.models import enums
from app.models.seguridad import Usuario
from app.schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate
from app.schemas.import_csv import ImportSummary
from app.services import export_service, import_service
from app.services.empresa_service import EmpresaService

router = APIRouter(prefix="/empresas", tags=["empresas"])


def get_empresa_service() -> EmpresaService:
    return EmpresaService(EmpresaDAO())


def _id_empresa_de(usuario: Usuario) -> int | None:
    empleado = getattr(usuario, "empleado", None)
    if empleado is None:
        return None
    return getattr(empleado, "id_empresa", None)


@router.get("", response_model=list[EmpresaResponse])
def listar_empresas(
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
    service: EmpresaService = Depends(get_empresa_service),
) -> list[EmpresaResponse]:
    """Admin lista todas; otros roles solo ven su propia empresa."""
    if current.rol == enums.Rol.ADMINISTRADOR:
        return service.listar_todos(db)
    id_emp = _id_empresa_de(current)
    if id_emp is None:
        return []
    return [service.obtener(db, id_emp)]


@router.post("/import", response_model=ImportSummary)
async def importar_empresas_csv(
    file: UploadFile = File(...),
    dry_run: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> ImportSummary:
    """Importa empresas masivas desde un CSV. Mismo formato que el export."""
    contenido = await file.read()
    return import_service.importar_empresas(
        db=db, archivo_bytes=contenido, dry_run=dry_run
    )


@router.get("/export", response_class=Response)
def exportar_empresas_csv(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
) -> Response:
    """Exporta todas las empresas como CSV (UTF-8)."""
    dao = EmpresaDAO()
    empresas = dao.listar_todos(db)
    csv_text = export_service.exportar_empresas(empresas)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="empresas.csv"'},
    )


@router.post(
    "",
    response_model=EmpresaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_empresa(
    body: EmpresaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: EmpresaService = Depends(get_empresa_service),
) -> EmpresaResponse:
    return service.crear(db, body)


@router.get("/{id_empresa}", response_model=EmpresaResponse)
def obtener_empresa(
    id_empresa: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
    service: EmpresaService = Depends(get_empresa_service),
) -> EmpresaResponse:
    if current.rol != enums.Rol.ADMINISTRADOR:
        id_emp_user = _id_empresa_de(current)
        if id_emp_user != id_empresa:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta empresa",
            )
    return service.obtener(db, id_empresa)


@router.patch("/{id_empresa}", response_model=EmpresaResponse)
def actualizar_empresa(
    id_empresa: int,
    body: EmpresaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: EmpresaService = Depends(get_empresa_service),
) -> EmpresaResponse:
    return service.actualizar_parcial(db, id_empresa, body)


@router.delete("/{id_empresa}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_empresa(
    id_empresa: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: EmpresaService = Depends(get_empresa_service),
) -> None:
    service.eliminar(db, id_empresa)
