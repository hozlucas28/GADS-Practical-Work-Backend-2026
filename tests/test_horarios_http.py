"""Tests HTTP para el CRUD de horarios (POST/GET/PATCH/DELETE)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import enums


_HORARIO_BASE = {
    "nombre_horario": "Test Mañana",
    "tipo_horario": "fijo",
    "hora_entrada_esperada": "08:00:00",
    "hora_salida_esperada": "14:00:00",
    "cantidad_horas_objetivo": "6.00",
    "banda_horaria_inicio": "07:00:00",
    "banda_horaria_fin": "15:00:00",
    "tolerancia_entrada_minutos": 10,
    "tolerancia_salida_minutos": 10,
    "tiempo_minimo_descanso_minutos": 30,
    "umbral_horas_extra_minutos": 15,
    "dias_descanso_semanal": "sabado,domingo",
}


def test_listar_horarios_vacio(auth_client: TestClient) -> None:
    res = auth_client.get("/horarios")
    assert res.status_code == 200
    assert res.json() == []


def test_crear_horario_201(auth_client: TestClient) -> None:
    res = auth_client.post("/horarios", json=_HORARIO_BASE)
    assert res.status_code == 201
    data = res.json()
    assert data["nombre_horario"] == "Test Mañana"
    assert data["estado"] == "activo"


def test_crear_y_listar(auth_client: TestClient) -> None:
    auth_client.post("/horarios", json=_HORARIO_BASE)
    res = auth_client.get("/horarios")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_obtener_por_id_200(auth_client: TestClient) -> None:
    created = auth_client.post("/horarios", json=_HORARIO_BASE).json()
    res = auth_client.get(f"/horarios/{created['id_horario']}")
    assert res.status_code == 200
    assert res.json()["id_horario"] == created["id_horario"]


def test_obtener_por_id_404(auth_client: TestClient) -> None:
    res = auth_client.get("/horarios/999999")
    assert res.status_code == 404


def test_patch_horario(auth_client: TestClient) -> None:
    created = auth_client.post("/horarios", json=_HORARIO_BASE).json()
    res = auth_client.patch(
        f"/horarios/{created['id_horario']}",
        json={"nombre_horario": "Mañana Actualizado"},
    )
    assert res.status_code == 200
    assert res.json()["nombre_horario"] == "Mañana Actualizado"


def test_delete_horario_soft(auth_client: TestClient) -> None:
    created = auth_client.post("/horarios", json=_HORARIO_BASE).json()
    res = auth_client.delete(f"/horarios/{created['id_horario']}")
    assert res.status_code == 204

    # Sigue existiendo pero inactivo (soft delete).
    res2 = auth_client.get(f"/horarios/{created['id_horario']}")
    assert res2.status_code == 200
    assert res2.json()["estado"] == "inactivo"


def test_delete_horario_404(auth_client: TestClient) -> None:
    res = auth_client.delete("/horarios/999999")
    assert res.status_code == 404
