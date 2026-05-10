from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empresa
from app.models.seguridad import Usuario


def test_login_ok(client: TestClient, admin_user: Usuario) -> None:
    res = client.post(
        "/auth/login",
        json={"nombre_usuario": admin_user.nombre_usuario, "contrasena": "admin1234"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_password_invalida(client: TestClient, admin_user: Usuario) -> None:
    res = client.post(
        "/auth/login",
        json={"nombre_usuario": admin_user.nombre_usuario, "contrasena": "mala"},
    )
    assert res.status_code == 401


def test_login_usuario_inexistente(client: TestClient, db_session: Session) -> None:
    res = client.post(
        "/auth/login",
        json={"nombre_usuario": "nadie", "contrasena": "x"},
    )
    assert res.status_code == 401


def test_login_usuario_inactivo(
    client: TestClient, admin_user: Usuario, db_session: Session
) -> None:
    admin_user.estado = enums.EstadoEntidad.INACTIVO
    db_session.commit()
    res = client.post(
        "/auth/login",
        json={"nombre_usuario": admin_user.nombre_usuario, "contrasena": "admin1234"},
    )
    assert res.status_code == 401


def test_me_sin_token(client: TestClient) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_con_token(auth_client: TestClient, admin_user: Usuario) -> None:
    res = auth_client.get("/auth/me")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id_usuario"] == admin_user.id_usuario
    assert data["nombre_usuario"] == admin_user.nombre_usuario
    assert data["rol"] == enums.Rol.ADMINISTRADOR.value
    assert data["estado"] == enums.EstadoEntidad.ACTIVO.value


def test_register_first_admin_ok(client: TestClient) -> None:
    payload = {
        "nombre_usuario": "primer_admin",
        "contrasena": "supersecret",
        "email": "admin@example.com",
        "nombre": "Primer",
        "apellido": "Admin",
        "dni": "12345678",
        "cuil": "20-12345678-9",
        "legajo": "ADM-001",
        "empresa_razon_social": "Empresa Inicial",
        "empresa_cuit": "30-99999999-9",
        "empresa_email": "empresa@example.com",
        "empresa_telefono": "1122334455",
        "empresa_direccion": "Av Siempre Viva 742",
    }
    res = client.post("/auth/register-first-admin", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["nombre_usuario"] == "primer_admin"
    assert data["rol"] == enums.Rol.ADMINISTRADOR.value


def test_register_first_admin_conflict_si_ya_existe(
    client: TestClient, admin_user: Usuario
) -> None:
    payload = {
        "nombre_usuario": "otro_admin",
        "contrasena": "supersecret",
        "email": "otro@example.com",
        "nombre": "Otro",
        "apellido": "Admin",
        "dni": "87654321",
        "cuil": "20-87654321-9",
        "legajo": "ADM-002",
        "empresa_razon_social": "Empresa B",
        "empresa_cuit": "30-88888888-8",
        "empresa_email": "b@example.com",
        "empresa_telefono": "1100000000",
        "empresa_direccion": "Calle 123",
    }
    res = client.post("/auth/register-first-admin", json=payload)
    assert res.status_code == 409


def test_login_body_invalido_422(client: TestClient) -> None:
    """Login sin campos requeridos devuelve 422."""
    res = client.post("/auth/login", json={"nombre_usuario": "x"})
    assert res.status_code == 422


def test_me_token_invalido_401(client: TestClient) -> None:
    """Token random no decodificable devuelve 401."""
    res = client.get(
        "/auth/me", headers={"Authorization": "Bearer no-es-un-jwt-valido"}
    )
    assert res.status_code == 401


def test_me_usuario_inactivado_401(
    client: TestClient, admin_user: Usuario, db_session: Session
) -> None:
    """Si tras login el usuario pasa a INACTIVO, /me debe responder 401."""
    res = client.post(
        "/auth/login",
        json={"nombre_usuario": admin_user.nombre_usuario, "contrasena": "admin1234"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    admin_user.estado = enums.EstadoEntidad.INACTIVO
    db_session.commit()
    res2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 401


def test_register_first_admin_body_invalido_422(client: TestClient) -> None:
    """Email malformado y password corta devuelven 422."""
    payload = {
        "nombre_usuario": "admin_x",
        "contrasena": "corta",  # < 8 chars
        "email": "no-es-email",
        "nombre": "X",
        "apellido": "X",
        "dni": "1",
        "cuil": "20-1-1",
        "legajo": "ADM-X",
        "empresa_razon_social": "X",
        "empresa_cuit": "30-1-1",
        "empresa_email": "tampoco-es-email",
        "empresa_telefono": "1",
        "empresa_direccion": "X",
    }
    res = client.post("/auth/register-first-admin", json=payload)
    assert res.status_code == 422


def test_register_first_admin_crea_empresa_asociada(
    client: TestClient, db_session: Session
) -> None:
    """Tras register-first-admin la Empresa enviada queda persistida."""
    payload = {
        "nombre_usuario": "admin_con_emp",
        "contrasena": "supersecret",
        "email": "admin_emp@example.com",
        "nombre": "Adm",
        "apellido": "Inicial",
        "dni": "11111111",
        "cuil": "20-11111111-9",
        "legajo": "ADM-EMP-001",
        "empresa_razon_social": "Empresa Asociada SA",
        "empresa_cuit": "30-55555555-5",
        "empresa_email": "empresa.asociada@example.com",
        "empresa_telefono": "1100000000",
        "empresa_direccion": "Calle Falsa 123",
    }
    res = client.post("/auth/register-first-admin", json=payload)
    assert res.status_code == 201, res.text
    stmt = select(Empresa).where(Empresa.cuit == "30-55555555-5")
    empresa = db_session.execute(stmt).scalar_one()
    assert empresa.razon_social == "Empresa Asociada SA"
    assert empresa.estado == enums.EstadoEntidad.ACTIVO
