from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.daos.empleado_dao import EmpleadoDAO
from app.models.organizacion import Empleado, Empresa
from app.schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate


class EmpleadoService:
    def __init__(self, dao: EmpleadoDAO | None = None) -> None:
        self._dao = dao or EmpleadoDAO()

    def listar_todos(self, db: Session) -> list[EmpleadoResponse]:
        empleados = self._dao.listar_todos(db)
        return [EmpleadoResponse.model_validate(e) for e in empleados]

    def obtener(self, db: Session, id_empleado: int) -> EmpleadoResponse:
        empleado = self._dao.obtener_por_id(db, id_empleado)
        if empleado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado",
            )
        return EmpleadoResponse.model_validate(empleado)

    def crear(self, db: Session, datos: EmpleadoCreate) -> EmpleadoResponse:
        empresa = db.execute(
            select(Empresa).where(Empresa.id_empresa == datos.id_empresa)
        ).scalar_one_or_none()
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa asociada no existe",
            )
        if self._dao.obtener_por_legajo(db, datos.id_empresa, datos.legajo) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="legajo ya existe para esta empresa",
            )
        empleado = Empleado(
            legajo=datos.legajo,
            nombre=datos.nombre,
            apellido=datos.apellido,
            dni=datos.dni,
            cuil=datos.cuil,
            fecha_ingreso=datos.fecha_ingreso,
            categoria_laboral=datos.categoria_laboral,
            tipo_jornada=datos.tipo_jornada,
            modalidad_fichada_habilitada=datos.modalidad_fichada_habilitada,
            estado=datos.estado,
            id_empresa=datos.id_empresa,
        )
        try:
            self._dao.crear(db, empleado)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en empleado (dni/cuil/legajo)",
            ) from e
        db.refresh(empleado)
        return EmpleadoResponse.model_validate(empleado)

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
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en empleado",
            ) from e
        db.refresh(empleado)
        return EmpleadoResponse.model_validate(empleado)

    def eliminar(self, db: Session, id_empleado: int) -> None:
        empleado = self._dao.obtener_por_id(db, id_empleado)
        if empleado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado",
            )
        self._dao.eliminar(db, empleado)
        db.commit()
