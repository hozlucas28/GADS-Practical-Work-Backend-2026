from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_rol
from app.daos.horario_dao import HorarioDAO
from app.models import enums
from app.models.seguridad import Usuario
from app.schemas.horario import HorarioCreate, HorarioResponse, HorarioUpdate
from app.services.horario_service import HorarioService

router = APIRouter(prefix="/horarios", tags=["horarios"])


def get_horario_service() -> HorarioService:
    return HorarioService(HorarioDAO())


@router.get("", response_model=list[HorarioResponse])
def listar_horarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)),
    service: HorarioService = Depends(get_horario_service),
) -> list[HorarioResponse]:
    return service.listar_todos(db)


@router.post("", response_model=HorarioResponse, status_code=status.HTTP_201_CREATED)
def crear_horario(
    body: HorarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: HorarioService = Depends(get_horario_service),
) -> HorarioResponse:
    return service.crear_desde_schema(db, body)


@router.get("/{id_horario}", response_model=HorarioResponse)
def obtener_horario(
    id_horario: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR, enums.Rol.CONTADOR_EXTERNO)),
    service: HorarioService = Depends(get_horario_service),
) -> HorarioResponse:
    return service.obtener(db, id_horario)


@router.patch("/{id_horario}", response_model=HorarioResponse)
def actualizar_horario(
    id_horario: int,
    body: HorarioUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: HorarioService = Depends(get_horario_service),
) -> HorarioResponse:
    return service.actualizar_parcial(db, id_horario, body)


@router.delete("/{id_horario}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_horario(
    id_horario: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_rol(enums.Rol.ADMINISTRADOR)),
    service: HorarioService = Depends(get_horario_service),
) -> None:
    service.eliminar(db, id_horario)
