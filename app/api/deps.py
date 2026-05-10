from __future__ import annotations

from collections.abc import Generator
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.daos.empleado_dao import EmpleadoDAO
from app.daos.usuario_dao import UsuarioDAO
from app.database import get_db as _get_db
from app.models import enums
from app.models.seguridad import Usuario
from app.services import auth_service
from app.services.empleado_service import EmpleadoService
from app.services.usuario_service import UsuarioService


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_usuario_service() -> UsuarioService:
    return UsuarioService(UsuarioDAO())


def get_empleado_service() -> EmpleadoService:
    return EmpleadoService(EmpleadoDAO())


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token")
    try:
        claims = auth_service.decode_access_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    try:
        id_usuario = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sin sub válido") from e
    usuario = db.get(Usuario, id_usuario)
    if usuario is None or usuario.estado != enums.EstadoEntidad.ACTIVO:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario inactivo o inexistente"
        )
    return usuario


def require_rol(*roles: enums.Rol) -> Callable[[Usuario], Usuario]:
    def _checker(current: Usuario = Depends(get_current_user)) -> Usuario:
        if current.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
        return current

    return _checker
