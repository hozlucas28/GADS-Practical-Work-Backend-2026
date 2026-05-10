from __future__ import annotations

from collections.abc import Callable
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa


def _payload_empresa(**overrides: object) -> dict[str, object]:
    sufijo = uuid4().hex[:8]
    base: dict[str, object] = {
        "razon_social": f"Empresa {sufijo}",
        "cuit": f"30-{sufijo}-1",
        "email_contacto": f"contacto+{sufijo}@empresa.test",
        "telefono_contacto": "011-0000",
        "direccion": "Av. Siempre Viva 1",
        "fecha_alta": date.today().isoformat(),
        "estado": enums.EstadoEntidad.ACTIVO.value,
    }
    base.update(overrides)
    return base


def test_post_empresa_admin_201(auth_client: TestClient) -> None:
    res = auth_client.post("/empresas", json=_payload_empresa())
    assert res.status_code == 201, res.text
    data = res.json()
    assert "id_empresa" in data
    assert data["estado"] == enums.EstadoEntidad.ACTIVO.value


def test_post_empresa_empleado_plano_403(
    auth_client: TestClient,
    client: TestClient,
    db_session: Session,
    empleado_factory: Callable[..., Empleado],
) -> None:
    empleado = empleado_factory()
    sufijo = uuid4().hex[:6]
    user_payload = {
        "nombre_usuario": f"plano_{sufijo}",
        "contrasena": "secreta123",
        "email": f"plano_{sufijo}@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res_user = auth_client.post("/usuarios", json=user_payload)
    assert res_user.status_code in (200, 201), res_user.text

    login = client.post(
        "/auth/login",
        json={
            "nombre_usuario": user_payload["nombre_usuario"],
            "contrasena": "secreta123",
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    res = client.post(
        "/empresas",
        json=_payload_empresa(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_post_empresa_cuit_duplicado_409(auth_client: TestClient) -> None:
    payload = _payload_empresa()
    r1 = auth_client.post("/empresas", json=payload)
    assert r1.status_code == 201, r1.text
    payload2 = _payload_empresa(cuit=payload["cuit"])
    r2 = auth_client.post("/empresas", json=payload2)
    assert r2.status_code == 409


def test_get_empresas_admin_lista_todas(
    auth_client: TestClient,
    empresa_factory: Callable[..., Empresa],
) -> None:
    e1 = empresa_factory()
    e2 = empresa_factory()
    res = auth_client.get("/empresas")
    assert res.status_code == 200
    ids = {row["id_empresa"] for row in res.json()}
    assert e1.id_empresa in ids
    assert e2.id_empresa in ids


def test_get_empresa_por_id_admin_ok(
    auth_client: TestClient,
    empresa_factory: Callable[..., Empresa],
) -> None:
    emp = empresa_factory()
    res = auth_client.get(f"/empresas/{emp.id_empresa}")
    assert res.status_code == 200
    assert res.json()["id_empresa"] == emp.id_empresa


def _login_empleado_plano(
    auth_client: TestClient,
    client: TestClient,
    empleado: Empleado,
) -> str:
    sufijo = uuid4().hex[:6]
    user_payload = {
        "nombre_usuario": f"emp_{sufijo}",
        "contrasena": "secreta123",
        "email": f"emp_{sufijo}@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res_user = auth_client.post("/usuarios", json=user_payload)
    assert res_user.status_code in (200, 201), res_user.text
    login = client.post(
        "/auth/login",
        json={
            "nombre_usuario": user_payload["nombre_usuario"],
            "contrasena": "secreta123",
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_get_empresa_propio_empleado_200(
    auth_client: TestClient,
    client: TestClient,
    empresa_factory: Callable[..., Empresa],
    empleado_factory: Callable[..., Empleado],
) -> None:
    empresa = empresa_factory()
    empleado = empleado_factory(empresa=empresa)
    token = _login_empleado_plano(auth_client, client, empleado)
    res = client.get(
        f"/empresas/{empresa.id_empresa}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["id_empresa"] == empresa.id_empresa


def test_get_empresa_de_otra_empresa_403(
    auth_client: TestClient,
    client: TestClient,
    empresa_factory: Callable[..., Empresa],
    empleado_factory: Callable[..., Empleado],
) -> None:
    empresa_a = empresa_factory()
    empresa_b = empresa_factory()
    empleado = empleado_factory(empresa=empresa_a)
    token = _login_empleado_plano(auth_client, client, empleado)
    res = client.get(
        f"/empresas/{empresa_b.id_empresa}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_patch_empresa_admin_200(
    auth_client: TestClient,
    empresa_factory: Callable[..., Empresa],
) -> None:
    empresa = empresa_factory()
    res = auth_client.patch(
        f"/empresas/{empresa.id_empresa}",
        json={"razon_social": "Nuevo Nombre SA"},
    )
    assert res.status_code == 200
    assert res.json()["razon_social"] == "Nuevo Nombre SA"


def test_delete_empresa_baja_logica(
    auth_client: TestClient,
    db_session: Session,
    empresa_factory: Callable[..., Empresa],
) -> None:
    empresa = empresa_factory()
    res = auth_client.delete(f"/empresas/{empresa.id_empresa}")
    assert res.status_code == 204
    db_session.expire_all()
    db_session.refresh(empresa)
    assert empresa.estado == enums.EstadoEntidad.INACTIVO

    res_list = auth_client.get("/empresas")
    assert res_list.status_code == 200
    ids = {row["id_empresa"] for row in res_list.json()}
    assert empresa.id_empresa in ids


def test_listar_empresas_sin_auth_401(client: TestClient) -> None:
    """GET /empresas sin token devuelve 401."""
    res = client.get("/empresas")
    assert res.status_code == 401


def test_listar_empresas_empleado_solo_la_propia(
    auth_client: TestClient,
    client: TestClient,
    empresa_factory: Callable[..., Empresa],
    empleado_factory: Callable[..., Empleado],
) -> None:
    """Empleado plano lista únicamente su empresa."""
    empresa_a = empresa_factory()
    empresa_b = empresa_factory()
    empleado = empleado_factory(empresa=empresa_a)
    token = _login_empleado_plano(auth_client, client, empleado)
    res = client.get(
        "/empresas", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    ids = {row["id_empresa"] for row in res.json()}
    assert empresa_a.id_empresa in ids
    assert empresa_b.id_empresa not in ids


def test_get_empresa_inexistente_404(auth_client: TestClient) -> None:
    """Admin obteniendo empresa inexistente recibe 404."""
    res = auth_client.get("/empresas/9999999")
    assert res.status_code == 404


def test_patch_empresa_empleado_plano_403(
    auth_client: TestClient,
    client: TestClient,
    empresa_factory: Callable[..., Empresa],
    empleado_factory: Callable[..., Empleado],
) -> None:
    """Empleado plano no puede patchear empresas."""
    empresa = empresa_factory()
    empleado = empleado_factory(empresa=empresa)
    token = _login_empleado_plano(auth_client, client, empleado)
    res = client.patch(
        f"/empresas/{empresa.id_empresa}",
        json={"razon_social": "Hack SA"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_delete_empresa_empleado_plano_403(
    auth_client: TestClient,
    client: TestClient,
    empresa_factory: Callable[..., Empresa],
    empleado_factory: Callable[..., Empleado],
) -> None:
    """Empleado plano no puede borrar empresas."""
    empresa = empresa_factory()
    empleado = empleado_factory(empresa=empresa)
    token = _login_empleado_plano(auth_client, client, empleado)
    res = client.delete(
        f"/empresas/{empresa.id_empresa}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_post_empresa_body_invalido_422(auth_client: TestClient) -> None:
    """POST /empresas con body incompleto devuelve 422."""
    res = auth_client.post(
        "/empresas",
        json={"razon_social": "Solo Esto"},
    )
    assert res.status_code == 422
