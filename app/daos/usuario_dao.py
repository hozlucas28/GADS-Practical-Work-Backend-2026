from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.seguridad import Usuario


class UsuarioDAO:
    """Acceso a datos de usuarios."""

    def obtener_por_id(self, db: Session, id_usuario: int) -> Usuario | None:
        stmt = (
            select(Usuario)
            .options(joinedload(Usuario.rol))
            .where(Usuario.id_usuario == id_usuario)
        )
        return db.execute(stmt).scalar_one_or_none()

    def listar_todos(self, db: Session) -> list[Usuario]:
        stmt = (
            select(Usuario)
            .options(joinedload(Usuario.rol))
            .order_by(Usuario.id_usuario)
        )
        return list(db.scalars(stmt).unique().all())
