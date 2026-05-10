from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado


class EmpleadoDAO:
    def listar_todos(self, db: Session) -> list[Empleado]:
        stmt = select(Empleado).order_by(Empleado.id_empleado)
        return list(db.scalars(stmt).all())

    def obtener_por_id(self, db: Session, id_empleado: int) -> Empleado | None:
        stmt = select(Empleado).where(Empleado.id_empleado == id_empleado)
        return db.execute(stmt).scalar_one_or_none()

    def obtener_por_legajo(
        self, db: Session, id_empresa: int, legajo: str
    ) -> Empleado | None:
        stmt = select(Empleado).where(
            Empleado.id_empresa == id_empresa,
            Empleado.legajo == legajo,
        )
        return db.execute(stmt).scalar_one_or_none()

    def crear(self, db: Session, empleado: Empleado) -> Empleado:
        db.add(empleado)
        db.flush()
        db.refresh(empleado)
        return empleado

    def eliminar(self, db: Session, empleado: Empleado) -> None:
        empleado.estado = enums.EstadoEntidad.INACTIVO
