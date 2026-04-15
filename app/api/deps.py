from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import get_db as _get_db
from app.daos.empleado_dao import EmpleadoDAO
from app.daos.usuario_dao import UsuarioDAO
from app.services.empleado_service import EmpleadoService
from app.services.usuario_service import UsuarioService


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_usuario_service() -> UsuarioService:
    return UsuarioService(UsuarioDAO())


def get_empleado_service() -> EmpleadoService:
    return EmpleadoService(EmpleadoDAO())
