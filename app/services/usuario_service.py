from __future__ import annotations

from enum import Enum

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.daos.usuario_dao import UsuarioDAO
from app.models.seguridad import Usuario
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class UsuarioService:
    """Lógica de negocio relacionada con usuarios."""

    def __init__(self, dao: UsuarioDAO | None = None) -> None:
        self._dao = dao or UsuarioDAO()

    def listar_todos(self, db: Session) -> list[UsuarioResponse]:
        usuarios = self._dao.listar_todos(db)
        return [self._a_respuesta(u) for u in usuarios]

    def actualizar_parcial(
        self, db: Session, id_usuario: int, datos: UsuarioUpdate
    ) -> UsuarioResponse:
        usuario = self._dao.obtener_por_id(db, id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        patch = datos.model_dump(exclude_unset=True)
        nueva_contrasena = patch.pop("contrasena", None)
        if nueva_contrasena is not None:
            usuario.contrasena_hash = _hash_password(nueva_contrasena)
        if not patch and nueva_contrasena is None:
            return self._a_respuesta(usuario)
        for campo, valor in patch.items():
            setattr(usuario, campo, valor)
        db.commit()
        db.refresh(usuario)
        return self._a_respuesta(usuario)

    @staticmethod
    def _a_respuesta(usuario: Usuario) -> UsuarioResponse:
        nr = usuario.rol.nombre_rol
        nombre_rol = nr.value if isinstance(nr, Enum) else str(nr)
        return UsuarioResponse(
            id_usuario=usuario.id_usuario,
            nombre_usuario=usuario.nombre_usuario,
            email=usuario.email,
            estado=usuario.estado,
            ultimo_acceso=usuario.ultimo_acceso,
            id_rol=usuario.id_rol,
            id_empleado=usuario.id_empleado,
            nombre_rol=nombre_rol,
        )
