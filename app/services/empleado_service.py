from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.daos.empleado_dao import EmpleadoDAO
from app.schemas.empleado import EmpleadoResponse, EmpleadoUpdate


class EmpleadoService:
    """Lógica de negocio relacionada con empleados."""

    def __init__(self, dao: EmpleadoDAO | None = None) -> None:
        self._dao = dao or EmpleadoDAO()

    def listar_todos(self, db: Session) -> list[EmpleadoResponse]:
        empleados = self._dao.listar_todos(db)
        return [EmpleadoResponse.model_validate(e) for e in empleados]

    def actualizar_parcial(
        self, db: Session, id_empleado: int, datos: EmpleadoUpdate
    ) -> EmpleadoResponse:
        empleado = self._dao.obtener_por_id(db, id_empleado)
        if empleado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado",
            )
        patch = datos.model_dump(exclude_unset=True)
        if not patch:
            return EmpleadoResponse.model_validate(empleado)
        for campo, valor in patch.items():
            setattr(empleado, campo, valor)
        db.commit()
        db.refresh(empleado)
        return EmpleadoResponse.model_validate(empleado)
