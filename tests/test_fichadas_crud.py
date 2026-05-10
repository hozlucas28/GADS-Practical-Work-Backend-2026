"""Tests HTTP para el CRUD básico de fichadas (POST/GET/PATCH/DELETE)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from time import time as _time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada, OrigenFichada


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _crear_origen(db: Session, nombre: enums.OrigenFichada = enums.OrigenFichada.LOCAL) -> OrigenFichada:
    existente = db.query(OrigenFichada).filter_by(nombre_origen=nombre).first()
    if existente:
        return existente
    o = OrigenFichada(nombre_origen=nombre, descripcion="test")
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def _ts() -> str:
    return datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Tests GET /fichadas
# ──────────────────────────────────────────────────────────────────────────────

def test_listar_fichadas_vacio(auth_client: TestClient) -> None:
    res = auth_client.get("/fichadas")
    assert res.status_code == 200
    assert res.json() == []


def test_listar_fichadas_con_datos(
    auth_client: TestClient, db_session: Session, admin_user: object, empleado_factory: object
) -> None:
    from app.models.seguridad import Usuario as U
    admin: U = admin_user  # type: ignore[assignment]
    origen = _crear_origen(db_session)

    emp = empleado_factory()
    f = Fichada(
        fecha_hora=datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc),
        tipo_fichada=enums.TipoFichada.ENTRADA,
        fue_corregida=False,
        observacion=None,
        id_empleado=emp.id_empleado,
        id_origen_fichada=origen.id_origen_fichada,
        id_usuario_registrador=admin.id_usuario,
    )
    db_session.add(f)
    db_session.commit()

    res = auth_client.get("/fichadas")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["tipo_fichada"] == "entrada"


# ──────────────────────────────────────────────────────────────────────────────
# Tests POST /fichadas
# ──────────────────────────────────────────────────────────────────────────────

def test_crear_fichada_201(
    auth_client: TestClient, db_session: Session, empleado_factory: object
) -> None:
    origen = _crear_origen(db_session)
    emp = empleado_factory()  # type: ignore[call-arg]

    body = {
        "fecha_hora": _ts(),
        "tipo_fichada": "entrada",
        "id_empleado": emp.id_empleado,
        "id_origen_fichada": origen.id_origen_fichada,
    }
    res = auth_client.post("/fichadas", json=body)
    assert res.status_code == 201
    data = res.json()
    assert data["tipo_fichada"] == "entrada"
    assert data["fue_corregida"] is False


def test_crear_fichada_tipo_invalido(auth_client: TestClient, db_session: Session, empleado_factory: object) -> None:
    origen = _crear_origen(db_session)
    emp = empleado_factory()
    body = {
        "fecha_hora": _ts(),
        "tipo_fichada": "invalido",
        "id_empleado": emp.id_empleado,
        "id_origen_fichada": origen.id_origen_fichada,
    }
    res = auth_client.post("/fichadas", json=body)
    assert res.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Tests GET /fichadas/{id}
# ──────────────────────────────────────────────────────────────────────────────

def test_obtener_fichada_200(
    auth_client: TestClient, db_session: Session, admin_user: object, empleado_factory: object
) -> None:
    admin = admin_user  # type: ignore[assignment]
    origen = _crear_origen(db_session)
    emp = empleado_factory()
    f = Fichada(
        fecha_hora=datetime(2026, 4, 2, 9, 0, tzinfo=timezone.utc),
        tipo_fichada=enums.TipoFichada.SALIDA,
        fue_corregida=False,
        id_empleado=emp.id_empleado,
        id_origen_fichada=origen.id_origen_fichada,
        id_usuario_registrador=admin.id_usuario,
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)

    res = auth_client.get(f"/fichadas/{f.id_fichada}")
    assert res.status_code == 200
    assert res.json()["tipo_fichada"] == "salida"


def test_obtener_fichada_404(auth_client: TestClient) -> None:
    res = auth_client.get("/fichadas/999999")
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Tests PATCH /fichadas/{id}
# ──────────────────────────────────────────────────────────────────────────────

def test_patch_fichada_marca_corregida(
    auth_client: TestClient, db_session: Session, admin_user: object, empleado_factory: object
) -> None:
    admin = admin_user  # type: ignore[assignment]
    origen = _crear_origen(db_session)
    emp = empleado_factory()
    f = Fichada(
        fecha_hora=datetime(2026, 4, 3, 8, 0, tzinfo=timezone.utc),
        tipo_fichada=enums.TipoFichada.ENTRADA,
        fue_corregida=False,
        id_empleado=emp.id_empleado,
        id_origen_fichada=origen.id_origen_fichada,
        id_usuario_registrador=admin.id_usuario,
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)

    res = auth_client.patch(
        f"/fichadas/{f.id_fichada}", json={"observacion": "corregida manualmente"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["fue_corregida"] is True
    assert data["observacion"] == "corregida manualmente"


# ──────────────────────────────────────────────────────────────────────────────
# Tests DELETE /fichadas/{id}
# ──────────────────────────────────────────────────────────────────────────────

def test_delete_fichada_204(
    auth_client: TestClient, db_session: Session, admin_user: object, empleado_factory: object
) -> None:
    admin = admin_user  # type: ignore[assignment]
    origen = _crear_origen(db_session)
    emp = empleado_factory()
    f = Fichada(
        fecha_hora=datetime(2026, 4, 4, 8, 0, tzinfo=timezone.utc),
        tipo_fichada=enums.TipoFichada.ENTRADA,
        fue_corregida=False,
        id_empleado=emp.id_empleado,
        id_origen_fichada=origen.id_origen_fichada,
        id_usuario_registrador=admin.id_usuario,
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)

    res = auth_client.delete(f"/fichadas/{f.id_fichada}")
    assert res.status_code == 204

    res2 = auth_client.get(f"/fichadas/{f.id_fichada}")
    assert res2.status_code == 404


def test_delete_fichada_404(auth_client: TestClient) -> None:
    res = auth_client.delete("/fichadas/999999")
    assert res.status_code == 404
