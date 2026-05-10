from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empresa


class EmpresaDAO:
    """Acceso a datos de empresas."""

    def obtener_por_id(self, db: Session, id_empresa: int) -> Empresa | None:
        stmt = select(Empresa).where(Empresa.id_empresa == id_empresa)
        return db.execute(stmt).scalar_one_or_none()

    def obtener_por_cuit(self, db: Session, cuit: str) -> Empresa | None:
        stmt = select(Empresa).where(Empresa.cuit == cuit)
        return db.execute(stmt).scalar_one_or_none()

    def listar_todos(self, db: Session) -> list[Empresa]:
        stmt = select(Empresa).order_by(Empresa.id_empresa)
        return list(db.scalars(stmt).all())

    def crear(self, db: Session, empresa: Empresa) -> Empresa:
        db.add(empresa)
        db.flush()
        db.refresh(empresa)
        return empresa

    def eliminar(self, db: Session, empresa: Empresa) -> None:
        """Baja lógica: marca la empresa como INACTIVO."""
        empresa.estado = enums.EstadoEntidad.INACTIVO
