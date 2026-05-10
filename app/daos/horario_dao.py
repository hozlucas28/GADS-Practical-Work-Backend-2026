from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.horarios import AsignacionHorario, Horario


class HorarioDAO:
    """Acceso a datos de horarios."""

    def obtener_por_id(self, db: Session, id_horario: int) -> Horario | None:
        stmt = select(Horario).where(Horario.id_horario == id_horario)
        return db.execute(stmt).scalar_one_or_none()

    def listar_todos(self, db: Session) -> list[Horario]:
        stmt = select(Horario).order_by(Horario.id_horario)
        return list(db.scalars(stmt).all())

    def crear(self, db: Session, horario: Horario) -> Horario:
        db.add(horario)
        db.flush()
        db.refresh(horario)
        return horario

    def eliminar(self, db: Session, horario: Horario) -> None:
        """Baja lógica: hay FK desde AsignacionHorario."""
        horario.estado = enums.EstadoEntidad.INACTIVO


class AsignacionHorarioDAO:
    """Acceso a datos de asignaciones de horario."""

    def crear(self, db: Session, asig: AsignacionHorario) -> AsignacionHorario:
        db.add(asig)
        db.flush()
        db.refresh(asig)
        return asig

    def obtener_por_id(
        self, db: Session, id_asignacion: int
    ) -> AsignacionHorario | None:
        stmt = select(AsignacionHorario).where(
            AsignacionHorario.id_asignacion_horario == id_asignacion
        )
        return db.execute(stmt).scalar_one_or_none()

    def listar_activas_por_empleado(
        self, db: Session, id_empleado: int
    ) -> list[AsignacionHorario]:
        stmt = (
            select(AsignacionHorario)
            .where(
                AsignacionHorario.id_empleado == id_empleado,
                AsignacionHorario.estado == enums.EstadoEntidad.ACTIVO,
            )
            .order_by(AsignacionHorario.fecha_desde)
        )
        return list(db.scalars(stmt).all())
