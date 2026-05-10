from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.daos.empleado_dao import EmpleadoDAO
from app.daos.horario_dao import AsignacionHorarioDAO, HorarioDAO
from app.models import enums
from app.models.horarios import AsignacionHorario, Horario
from app.schemas.horario import HorarioCreate, HorarioResponse, HorarioUpdate


def _rangos_solapan(
    a1: date, a2: date | None, b1: date, b2: date | None
) -> bool:
    """Devuelve True si los rangos [a1, a2] y [b1, b2] se solapan.

    `None` en la fecha de fin se trata como ``date.max`` (rango abierto).
    """
    fin_a = a2 if a2 is not None else date.max
    fin_b = b2 if b2 is not None else date.max
    return a1 <= fin_b and b1 <= fin_a


class HorarioService:
    """Lógica de negocio relacionada con horarios y sus asignaciones."""

    def __init__(
        self,
        horario_dao: HorarioDAO | None = None,
        asignacion_dao: AsignacionHorarioDAO | None = None,
        empleado_dao: EmpleadoDAO | None = None,
    ) -> None:
        self._horario_dao = horario_dao or HorarioDAO()
        self._asig_dao = asignacion_dao or AsignacionHorarioDAO()
        self._empleado_dao = empleado_dao or EmpleadoDAO()

    def listar_todos(self, db: Session) -> list[HorarioResponse]:
        horarios = self._horario_dao.listar_todos(db)
        return [HorarioResponse.model_validate(h) for h in horarios]

    def obtener(self, db: Session, id_horario: int) -> HorarioResponse:
        horario = self._horario_dao.obtener_por_id(db, id_horario)
        if horario is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Horario no encontrado")
        return HorarioResponse.model_validate(horario)

    def crear_desde_schema(self, db: Session, datos: HorarioCreate) -> HorarioResponse:
        horario = Horario(
            nombre_horario=datos.nombre_horario,
            tipo_horario=datos.tipo_horario,
            hora_entrada_esperada=datos.hora_entrada_esperada,
            hora_salida_esperada=datos.hora_salida_esperada,
            cantidad_horas_objetivo=datos.cantidad_horas_objetivo,
            banda_horaria_inicio=datos.banda_horaria_inicio,
            banda_horaria_fin=datos.banda_horaria_fin,
            tolerancia_entrada_minutos=datos.tolerancia_entrada_minutos,
            tolerancia_salida_minutos=datos.tolerancia_salida_minutos,
            tiempo_minimo_descanso_minutos=datos.tiempo_minimo_descanso_minutos,
            umbral_horas_extra_minutos=datos.umbral_horas_extra_minutos,
            dias_descanso_semanal=datos.dias_descanso_semanal,
            estado=datos.estado,
        )
        try:
            self._horario_dao.crear(db, horario)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto al crear horario") from e
        db.refresh(horario)
        return HorarioResponse.model_validate(horario)

    def actualizar_parcial(
        self, db: Session, id_horario: int, datos: HorarioUpdate
    ) -> HorarioResponse:
        horario = self._horario_dao.obtener_por_id(db, id_horario)
        if horario is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Horario no encontrado")
        patch = datos.model_dump(exclude_unset=True)
        if not patch:
            return HorarioResponse.model_validate(horario)
        for campo, valor in patch.items():
            setattr(horario, campo, valor)
        db.commit()
        db.refresh(horario)
        return HorarioResponse.model_validate(horario)

    def eliminar(self, db: Session, id_horario: int) -> None:
        horario = self._horario_dao.obtener_por_id(db, id_horario)
        if horario is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Horario no encontrado")
        self._horario_dao.eliminar(db, horario)
        db.commit()

    def crear_horario(self, db: Session, horario: Horario) -> Horario:
        """Persiste un horario nuevo. El caller arma la instancia."""
        try:
            creado = self._horario_dao.crear(db, horario)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto al crear el horario",
            ) from e
        db.refresh(creado)
        return creado

    def asignar(
        self,
        db: Session,
        *,
        id_empleado: int,
        id_horario: int,
        fecha_desde: date,
        fecha_hasta: date | None,
    ) -> AsignacionHorario:
        empleado = self._empleado_dao.obtener_por_id(db, id_empleado)
        if empleado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado",
            )
        horario = self._horario_dao.obtener_por_id(db, id_horario)
        if horario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario no encontrado",
            )
        if fecha_hasta is not None and fecha_hasta < fecha_desde:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecha_hasta no puede ser anterior a fecha_desde",
            )

        existentes = self._asig_dao.listar_activas_por_empleado(db, id_empleado)
        for asig in existentes:
            if _rangos_solapan(
                fecha_desde, fecha_hasta, asig.fecha_desde, asig.fecha_hasta
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Asignación se solapa con una existente",
                )

        nueva = AsignacionHorario(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=enums.EstadoEntidad.ACTIVO,
            id_empleado=id_empleado,
            id_horario=id_horario,
        )
        try:
            self._asig_dao.crear(db, nueva)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflicto al crear la asignación",
            ) from e
        db.refresh(nueva)
        return nueva
