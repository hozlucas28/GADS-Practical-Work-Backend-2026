from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    """GET /health responde 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_body_exacto(client: TestClient) -> None:
    """Body es exactamente {status: ok}, sin más claves."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    assert set(response.json().keys()) == {"status"}


def test_health_sin_auth_publico(client: TestClient) -> None:
    """/health no requiere token (público)."""
    # Aseguramos que no haya header de auth
    client.headers.pop("Authorization", None)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_metodo_incorrecto(client: TestClient) -> None:
    """POST /health responde 405 (método no permitido)."""
    response = client.post("/health")
    assert response.status_code == 405
