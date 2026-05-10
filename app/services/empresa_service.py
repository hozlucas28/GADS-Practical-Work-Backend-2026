from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.daos.empresa_dao import EmpresaDAO
from app.models.organizacion import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate


class EmpresaService:
    """Lógica de negocio relacionada con empresas."""

    def __init__(self, dao: EmpresaDAO | None = None) -> None:
        self._dao = dao or EmpresaDAO()

    def listar_todos(self, db: Session) -> list[EmpresaResponse]:
        empresas = self._dao.listar_todos(db)
        return [EmpresaResponse.model_validate(e) for e in empresas]

    def obtener(self, db: Session, id_empresa: int) -> EmpresaResponse:
        empresa = self._dao.obtener_por_id(db, id_empresa)
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada",
            )
        return EmpresaResponse.model_validate(empresa)

    def crear(self, db: Session, datos: EmpresaCreate) -> EmpresaResponse:
        if self._dao.obtener_por_cuit(db, datos.cuit) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CUIT ya registrado",
            )
        empresa = Empresa(
            razon_social=datos.razon_social,
            cuit=datos.cuit,
            email_contacto=datos.email_contacto,
            telefono_contacto=datos.telefono_contacto,
            direccion=datos.direccion,
            fecha_alta=datos.fecha_alta,
            estado=datos.estado,
        )
        try:
            self._dao.crear(db, empresa)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en empresa",
            ) from e
        db.refresh(empresa)
        return EmpresaResponse.model_validate(empresa)

    def actualizar_parcial(
        self, db: Session, id_empresa: int, datos: EmpresaUpdate
    ) -> EmpresaResponse:
        empresa = self._dao.obtener_por_id(db, id_empresa)
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada",
            )
        patch = datos.model_dump(exclude_unset=True)
        if not patch:
            return EmpresaResponse.model_validate(empresa)
        for campo, valor in patch.items():
            setattr(empresa, campo, valor)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto de unicidad en empresa",
            ) from e
        db.refresh(empresa)
        return EmpresaResponse.model_validate(empresa)

    def eliminar(self, db: Session, id_empresa: int) -> None:
        empresa = self._dao.obtener_por_id(db, id_empresa)
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada",
            )
        self._dao.eliminar(db, empresa)
        db.commit()
