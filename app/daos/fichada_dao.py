from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.fichadas import Fichada


class FichadaDAO:
    def obtener_por_id(self, db: Session, id_fichada: int) -> Fichada | None:
        stmt = (
            select(Fichada)
            .options(selectinload(Fichada.empleado), selectinload(Fichada.origen))
            .where(Fichada.id_fichada == id_fichada)
        )
        return db.execute(stmt).scalar_one_or_none()

    def listar_todos(
        self,
        db: Session,
        *,
        id_empleado: int | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Fichada]:
        stmt = (
            select(Fichada)
            .options(selectinload(Fichada.empleado), selectinload(Fichada.origen))
            .order_by(Fichada.fecha_hora)
        )
        if id_empleado is not None:
            stmt = stmt.where(Fichada.id_empleado == id_empleado)
        if desde is not None:
            stmt = stmt.where(Fichada.fecha_hora >= datetime.combine(desde, time.min))
        if hasta is not None:
            stmt = stmt.where(Fichada.fecha_hora <= datetime.combine(hasta, time.max))
        return list(db.scalars(stmt).all())

    def crear(self, db: Session, fichada: Fichada) -> Fichada:
        db.add(fichada)
        db.flush()
        db.refresh(fichada)
        return fichada

    def eliminar(self, db: Session, fichada: Fichada) -> None:
        db.delete(fichada)
        db.flush()
