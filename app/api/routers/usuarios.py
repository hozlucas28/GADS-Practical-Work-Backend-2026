from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_usuario_service
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
) -> list[UsuarioResponse]:
    """Devuelve todos los usuarios registrados (sin contraseña)."""
    return service.listar_todos(db)


@router.patch("/{id_usuario}", response_model=UsuarioResponse)
def actualizar_usuario(
    id_usuario: int,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    service: UsuarioService = Depends(get_usuario_service),
) -> UsuarioResponse:
    """Actualiza los campos enviados del usuario (``contrasena`` se guarda hasheada)."""
    return service.actualizar_parcial(db, id_usuario, body)
