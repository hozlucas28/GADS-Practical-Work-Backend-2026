from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.daos.empleado_dao import EmpleadoDAO
from app.daos.usuario_dao import UsuarioDAO
from app.models.seguridad import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services.auth_service import hash_password


class UsuarioService:
    def __init__(
        self,
        dao: UsuarioDAO | None = None,
        empleado_dao: EmpleadoDAO | None = None,
    ) -> None:
        self._dao = dao or UsuarioDAO()
        self._empleado_dao = empleado_dao or EmpleadoDAO()

    def listar_todos(self, db: Session) -> list[UsuarioResponse]:
        usuarios = self._dao.listar_todos(db)
        return [self._a_respuesta(u) for u in usuarios]

    def obtener(self, db: Session, id_usuario: int) -> UsuarioResponse:
        usuario = self._dao.obtener_por_id(db, id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        return self._a_respuesta(usuario)

    def crear(self, db: Session, datos: UsuarioCreate) -> UsuarioResponse:
        empleado = self._empleado_dao.obtener_por_id(db, datos.id_empleado)
        if empleado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado asociado no existe",
            )
        if self._dao.obtener_por_nombre_usuario(db, datos.nombre_usuario) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="nombre_usuario ya existe",
            )
        if self._dao.obtener_por_email(db, datos.email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email ya existe",
            )
        usuario = Usuario(
            nombre_usuario=datos.nombre_usuario,
            contrasena_hash=hash_password(datos.contrasena),
            email=datos.email,
            rol=datos.rol,
            estado=datos.estado,
            ultimo_acceso=None,
            id_empleado=datos.id_empleado,
        )
        try:
            self._dao.crear(db, usuario)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en usuario",
            ) from e
        db.refresh(usuario)
        return self._a_respuesta(usuario)

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
            usuario.contrasena_hash = hash_password(nueva_contrasena)
        if not patch and nueva_contrasena is None:
            return self._a_respuesta(usuario)
        for campo, valor in patch.items():
            setattr(usuario, campo, valor)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en usuario",
            ) from e
        db.refresh(usuario)
        return self._a_respuesta(usuario)

    def eliminar(self, db: Session, id_usuario: int) -> None:
        usuario = self._dao.obtener_por_id(db, id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        self._dao.eliminar(db, usuario)
        db.commit()

    @staticmethod
    def _a_respuesta(usuario: Usuario) -> UsuarioResponse:
        return UsuarioResponse(
            id_usuario=usuario.id_usuario,
            nombre_usuario=usuario.nombre_usuario,
            email=usuario.email,
            estado=usuario.estado,
            ultimo_acceso=usuario.ultimo_acceso,
            id_empleado=usuario.id_empleado,
            rol=usuario.rol,
        )
