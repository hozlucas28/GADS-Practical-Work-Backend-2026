"""Tests del módulo app.seed (idempotencia y carga mínima)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fichadas import Fichada, OrigenFichada
from app.models.horarios import Horario
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.seed import cargar_seed_si_vacio


def test_seed_carga_datos_minimos(db_session: Session) -> None:
    cargar_seed_si_vacio(db_session)

    assert db_session.execute(select(Empresa)).scalar_one_or_none() is not None
    assert len(db_session.execute(select(Empleado)).scalars().all()) == 3
    assert len(db_session.execute(select(Usuario)).scalars().all()) == 3
    assert len(db_session.execute(select(OrigenFichada)).scalars().all()) == 3
    assert len(db_session.execute(select(Horario)).scalars().all()) == 3
    assert len(db_session.execute(select(Fichada)).scalars().all()) == 3


def test_seed_es_idempotente(db_session: Session) -> None:
    cargar_seed_si_vacio(db_session)
    cargar_seed_si_vacio(db_session)  # segunda llamada no duplica

    assert len(db_session.execute(select(Empleado)).scalars().all()) == 3
    assert len(db_session.execute(select(Fichada)).scalars().all()) == 3
