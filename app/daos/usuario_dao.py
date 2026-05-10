from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.seguridad import Usuario


class UsuarioDAO:
    def obtener_por_id(self, db: Session, id_usuario: int) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.id_usuario == id_usuario)
        return db.execute(stmt).scalar_one_or_none()

    def listar_todos(self, db: Session) -> list[Usuario]:
        stmt = select(Usuario).order_by(Usuario.id_usuario)
        return list(db.scalars(stmt).all())

    def obtener_por_nombre_usuario(self, db: Session, nombre: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.nombre_usuario == nombre)
        return db.execute(stmt).scalar_one_or_none()

    def obtener_por_email(self, db: Session, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def crear(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        db.refresh(usuario)
        return usuario

    def eliminar(self, db: Session, usuario: Usuario) -> None:
        usuario.estado = enums.EstadoEntidad.INACTIVO
