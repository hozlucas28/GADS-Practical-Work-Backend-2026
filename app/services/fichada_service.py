from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.daos.fichada_dao import FichadaDAO
from app.models.fichadas import Fichada
from app.schemas.fichada import FichadaCreate, FichadaResponse, FichadaUpdate


class FichadaService:
    def __init__(self, dao: FichadaDAO | None = None) -> None:
        self._dao = dao or FichadaDAO()

    def listar_todos(
        self,
        db: Session,
        *,
        id_empleado: int | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[FichadaResponse]:
        fichadas = self._dao.listar_todos(
            db, id_empleado=id_empleado, desde=desde, hasta=hasta
        )
        return [FichadaResponse.model_validate(f) for f in fichadas]

    def obtener(self, db: Session, id_fichada: int) -> FichadaResponse:
        f = self._dao.obtener_por_id(db, id_fichada)
        if f is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichada no encontrada")
        return FichadaResponse.model_validate(f)

    def crear(
        self, db: Session, datos: FichadaCreate, id_usuario_registrador: int
    ) -> FichadaResponse:
        fichada = Fichada(
            fecha_hora=datos.fecha_hora,
            tipo_fichada=datos.tipo_fichada,
            fue_corregida=False,
            observacion=datos.observacion,
            id_empleado=datos.id_empleado,
            id_origen_fichada=datos.id_origen_fichada,
            id_usuario_registrador=id_usuario_registrador,
        )
        try:
            self._dao.crear(db, fichada)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Conflicto al crear fichada"
            ) from e
        db.refresh(fichada)
        return FichadaResponse.model_validate(fichada)

    def actualizar_parcial(
        self, db: Session, id_fichada: int, datos: FichadaUpdate
    ) -> FichadaResponse:
        fichada = self._dao.obtener_por_id(db, id_fichada)
        if fichada is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichada no encontrada")
        patch = datos.model_dump(exclude_unset=True)
        if not patch:
            return FichadaResponse.model_validate(fichada)
        for campo, valor in patch.items():
            setattr(fichada, campo, valor)
        fichada.fue_corregida = True
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Conflicto al actualizar fichada"
            ) from e
        db.refresh(fichada)
        return FichadaResponse.model_validate(fichada)

    def eliminar(self, db: Session, id_fichada: int) -> None:
        fichada = self._dao.obtener_por_id(db, id_fichada)
        if fichada is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichada no encontrada")
        try:
            self._dao.eliminar(db, fichada)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Fichada tiene novedades asociadas"
            ) from e
