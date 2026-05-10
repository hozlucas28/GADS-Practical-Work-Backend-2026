from __future__ import annotations

from collections.abc import Callable
from datetime import date, time
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.daos.horario_dao import HorarioDAO
from app.models import enums
from app.models.horarios import Horario
from app.models.organizacion import Empleado
from app.services.horario_service import HorarioService


def _crear_horario(db: Session, nombre: str = "Mañana") -> Horario:
    horario = Horario(
        nombre_horario=nombre,
        tipo_horario=enums.TipoHorario.FIJO,
        hora_entrada_esperada=time(9, 0),
        hora_salida_esperada=time(18, 0),
        cantidad_horas_objetivo=Decimal("8.00"),
        banda_horaria_inicio=time(8, 0),
        banda_horaria_fin=time(19, 0),
        tolerancia_entrada_minutos=10,
        tolerancia_salida_minutos=10,
        tiempo_minimo_descanso_minutos=30,
        umbral_horas_extra_minutos=15,
        dias_descanso_semanal="sabado,domingo",
        estado=enums.EstadoEntidad.ACTIVO,
    )
    return HorarioDAO().crear(db, horario)


def test_asignar_horario_crea_exitoso(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    horario = _crear_horario(db_session)
    db_session.commit()

    service = HorarioService()
    asig = service.asignar(
        db_session,
        id_empleado=empleado.id_empleado,
        id_horario=horario.id_horario,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 6, 30),
    )
    assert asig.id_asignacion_horario is not None
    assert asig.estado == enums.EstadoEntidad.ACTIVO


def test_asignar_horario_rechaza_solapamiento(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    horario = _crear_horario(db_session)
    db_session.commit()

    service = HorarioService()
    service.asignar(
        db_session,
        id_empleado=empleado.id_empleado,
        id_horario=horario.id_horario,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 6, 30),
    )

    with pytest.raises(HTTPException) as excinfo:
        service.asignar(
            db_session,
            id_empleado=empleado.id_empleado,
            id_horario=horario.id_horario,
            fecha_desde=date(2026, 6, 15),
            fecha_hasta=date(2026, 12, 31),
        )
    assert excinfo.value.status_code == 409


def test_asignar_contigua_sin_overlap_ok(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    horario = _crear_horario(db_session)
    db_session.commit()

    service = HorarioService()
    service.asignar(
        db_session,
        id_empleado=empleado.id_empleado,
        id_horario=horario.id_horario,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 6, 30),
    )
    asig2 = service.asignar(
        db_session,
        id_empleado=empleado.id_empleado,
        id_horario=horario.id_horario,
        fecha_desde=date(2026, 7, 1),
        fecha_hasta=date(2026, 12, 31),
    )
    assert asig2.id_asignacion_horario is not None


def test_asignar_con_fecha_hasta_none_bloquea_futuras(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    horario = _crear_horario(db_session)
    db_session.commit()

    service = HorarioService()
    service.asignar(
        db_session,
        id_empleado=empleado.id_empleado,
        id_horario=horario.id_horario,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=None,
    )
    with pytest.raises(HTTPException) as excinfo:
        service.asignar(
            db_session,
            id_empleado=empleado.id_empleado,
            id_horario=horario.id_horario,
            fecha_desde=date(2027, 1, 1),
            fecha_hasta=date(2027, 12, 31),
        )
    assert excinfo.value.status_code == 409


def test_asignar_empleado_inexistente_404(
    db_session: Session,
) -> None:
    horario = _crear_horario(db_session)
    db_session.commit()

    service = HorarioService()
    with pytest.raises(HTTPException) as excinfo:
        service.asignar(
            db_session,
            id_empleado=999999,
            id_horario=horario.id_horario,
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 6, 30),
        )
    assert excinfo.value.status_code == 404


def test_asignar_horario_inexistente_404(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    db_session.commit()

    service = HorarioService()
    with pytest.raises(HTTPException) as excinfo:
        service.asignar(
            db_session,
            id_empleado=empleado.id_empleado,
            id_horario=999999,
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 6, 30),
        )
    assert excinfo.value.status_code == 404
