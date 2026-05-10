from __future__ import annotations

from datetime import date
from uuid import uuid4

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _login_empleado(
    client: TestClient,
    auth_client: TestClient,
    db_session: Session,
    *,
    nombre_usuario: str | None = None,
    dni: str | None = None,
    cuil: str | None = None,
    legajo: str | None = None,
) -> tuple[int, str]:
    """Crea un Usuario rol EMPLEADO y devuelve (id_usuario, access_token)."""
    sufijo = uuid4().hex[:6]
    nombre_usuario = nombre_usuario or f"emp_{sufijo}"
    empleado = _crear_empleado(
        db_session,
        dni=dni or f"60{sufijo}",
        cuil=cuil or f"20-60{sufijo}-1",
        legajo=legajo or f"L-{sufijo}",
    )
    payload = {
        "nombre_usuario": nombre_usuario,
        "contrasena": "secreta123",
        "email": f"{nombre_usuario}@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    create = auth_client.post("/usuarios", json=payload)
    assert create.status_code == 201, create.text
    uid = create.json()["id_usuario"]
    login = client.post(
        "/auth/login",
        json={"nombre_usuario": nombre_usuario, "contrasena": "secreta123"},
    )
    assert login.status_code == 200, login.text
    return uid, login.json()["access_token"]


def _crear_empleado(db_session: Session, *, dni: str = "30111222", cuil: str = "27-30111222-4", legajo: str = "E-1") -> Empleado:
    sufijo = uuid4().hex[:8]
    empresa = Empresa(
        razon_social=f"Test SA {sufijo}",
        cuit=f"30-{sufijo}-1",
        email_contacto="c@test.com",
        telefono_contacto="123",
        direccion="Calle 1",
        estado=enums.EstadoEntidad.ACTIVO,
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()
    empleado = Empleado(
        legajo=legajo,
        nombre="Ana",
        apellido="Test",
        dni=dni,
        cuil=cuil,
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.commit()
    db_session.refresh(empleado)
    return empleado


def test_listar_usuarios_requiere_auth(client: TestClient) -> None:
    res = client.get("/usuarios")
    assert res.status_code == 401


def test_listar_usuarios_con_admin(auth_client: TestClient) -> None:
    res = auth_client.get("/usuarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(u["rol"] == enums.Rol.ADMINISTRADOR.value for u in data)


def test_post_usuario_crea_correctamente(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="40222333", cuil="20-40222333-1", legajo="E-NEW")
    payload = {
        "nombre_usuario": "u.nuevo",
        "contrasena": "secreta123",
        "email": "u.nuevo@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res = auth_client.post("/usuarios", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["nombre_usuario"] == "u.nuevo"
    assert data["rol"] == enums.Rol.EMPLEADO.value
    assert "contrasena" not in data
    assert "contrasena_hash" not in data
    db_session.expire_all()
    u = db_session.query(Usuario).filter_by(nombre_usuario="u.nuevo").one()
    assert bcrypt.checkpw(b"secreta123", u.contrasena_hash.encode("utf-8"))


def test_post_usuario_nombre_repetido_conflict(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="41222333", cuil="20-41222333-1", legajo="E-DUP")
    payload = {
        "nombre_usuario": "duplicado",
        "contrasena": "secreta123",
        "email": "dup1@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res1 = auth_client.post("/usuarios", json=payload)
    assert res1.status_code == 201
    empleado2 = _crear_empleado(db_session, dni="42222333", cuil="20-42222333-1", legajo="E-DUP2")
    payload2 = {**payload, "email": "dup2@test.com", "id_empleado": empleado2.id_empleado}
    res2 = auth_client.post("/usuarios", json=payload2)
    assert res2.status_code == 409


def test_patch_usuario_actualiza_email(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="50111222", cuil="20-50111222-3", legajo="PU-1")
    payload = {
        "nombre_usuario": "u.patch",
        "contrasena": "secreta123",
        "email": "viejo@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    create = auth_client.post("/usuarios", json=payload)
    assert create.status_code == 201
    uid = create.json()["id_usuario"]
    res = auth_client.patch(
        f"/usuarios/{uid}",
        json={"email": "nuevo@test.com", "nombre_usuario": "u.nuevo2"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "nuevo@test.com"
    assert data["nombre_usuario"] == "u.nuevo2"


def test_patch_usuario_contrasena(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="51111222", cuil="20-51111222-1", legajo="PW-1")
    payload = {
        "nombre_usuario": "pwd.test",
        "contrasena": "viejavieja",
        "email": "pwd@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    create = auth_client.post("/usuarios", json=payload)
    assert create.status_code == 201
    uid = create.json()["id_usuario"]
    res = auth_client.patch(f"/usuarios/{uid}", json={"contrasena": "secreta_nueva"})
    assert res.status_code == 200
    db_session.expire_all()
    u2 = db_session.get(Usuario, uid)
    assert u2 is not None
    assert bcrypt.checkpw(b"secreta_nueva", u2.contrasena_hash.encode("utf-8"))


def test_patch_usuario_no_encontrado(auth_client: TestClient) -> None:
    res = auth_client.patch("/usuarios/99999", json={"estado": enums.EstadoEntidad.INACTIVO.value})
    assert res.status_code == 404


def test_patch_rol_por_empleado_forbidden(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="52111222", cuil="20-52111222-1", legajo="EMP-LOG")
    payload = {
        "nombre_usuario": "emp.login",
        "contrasena": "secreta123",
        "email": "emp.login@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    create = auth_client.post("/usuarios", json=payload)
    assert create.status_code == 201
    uid = create.json()["id_usuario"]
    login = client.post(
        "/auth/login",
        json={"nombre_usuario": "emp.login", "contrasena": "secreta123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    res = client.patch(
        f"/usuarios/{uid}",
        json={"rol": enums.Rol.ADMINISTRADOR.value},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_delete_usuario_baja_logica(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _crear_empleado(db_session, dni="53111222", cuil="20-53111222-1", legajo="DEL-1")
    payload = {
        "nombre_usuario": "para.borrar",
        "contrasena": "secreta123",
        "email": "borrar@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    create = auth_client.post("/usuarios", json=payload)
    uid = create.json()["id_usuario"]
    res = auth_client.delete(f"/usuarios/{uid}")
    assert res.status_code == 204
    db_session.expire_all()
    u = db_session.get(Usuario, uid)
    assert u is not None
    assert u.estado == enums.EstadoEntidad.INACTIVO
    get_res = auth_client.get(f"/usuarios/{uid}")
    assert get_res.status_code == 200
    assert get_res.json()["estado"] == enums.EstadoEntidad.INACTIVO.value


# ---------- GET /usuarios listar ----------


def test_listar_usuarios_no_incluye_contrasena_hash(
    auth_client: TestClient,
) -> None:
    """La respuesta del listado no expone contrasena_hash."""
    res = auth_client.get("/usuarios")
    assert res.status_code == 200
    for u in res.json():
        assert "contrasena_hash" not in u
        assert "contrasena" not in u


def test_listar_usuarios_items_tienen_campos_clave(
    auth_client: TestClient,
) -> None:
    """Cada usuario listado expone rol, estado, id_empleado."""
    res = auth_client.get("/usuarios")
    assert res.status_code == 200
    data = res.json()
    assert data
    for u in data:
        assert "rol" in u
        assert "estado" in u
        assert "id_empleado" in u


def test_listar_usuarios_empleado_plano_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado plano no puede listar usuarios."""
    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/usuarios", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


# ---------- POST /usuarios ----------


def test_post_usuario_sin_auth_401(client: TestClient) -> None:
    """POST sin token devuelve 401."""
    res = client.post(
        "/usuarios",
        json={
            "nombre_usuario": "x",
            "contrasena": "12345678",
            "email": "x@test.com",
            "rol": enums.Rol.EMPLEADO.value,
            "id_empleado": 1,
        },
    )
    assert res.status_code == 401


def test_post_usuario_empleado_plano_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado plano no puede crear usuarios."""
    _, token = _login_empleado(client, auth_client, db_session)
    empleado = _crear_empleado(
        db_session, dni="71000001", cuil="20-71000001-1", legajo="EX-1"
    )
    payload = {
        "nombre_usuario": "nuevo_x",
        "contrasena": "secreta123",
        "email": "nx@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res = client.post(
        "/usuarios", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_post_usuario_password_corta_422(
    auth_client: TestClient, db_session: Session
) -> None:
    """Password con menos de 8 caracteres devuelve 422."""
    empleado = _crear_empleado(
        db_session, dni="72000001", cuil="20-72000001-1", legajo="PW-S"
    )
    payload = {
        "nombre_usuario": "corta",
        "contrasena": "1234",  # < 8
        "email": "corta@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    res = auth_client.post("/usuarios", json=payload)
    assert res.status_code == 422


def test_post_usuario_empleado_inexistente_404(
    auth_client: TestClient,
) -> None:
    """id_empleado inexistente devuelve 404."""
    payload = {
        "nombre_usuario": "sin_emp",
        "contrasena": "secreta123",
        "email": "sinemp@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": 9_999_999,
    }
    res = auth_client.post("/usuarios", json=payload)
    assert res.status_code in (400, 404)


# ---------- GET /usuarios/{id} ----------


def test_get_usuario_sin_auth_401(client: TestClient) -> None:
    """GET /usuarios/{id} sin token devuelve 401."""
    res = client.get("/usuarios/1")
    assert res.status_code == 401


def test_get_usuario_admin_ve_a_otro(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Admin puede ver a cualquier usuario."""
    uid, _ = _login_empleado(client, auth_client, db_session)
    res = auth_client.get(f"/usuarios/{uid}")
    assert res.status_code == 200
    assert res.json()["id_usuario"] == uid


def test_get_usuario_empleado_se_obtiene_a_si_mismo(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado puede leerse a sí mismo."""
    uid, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        f"/usuarios/{uid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["id_usuario"] == uid


def test_get_usuario_empleado_a_otro_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado pidiendo otro usuario recibe 403."""
    uid1, token = _login_empleado(client, auth_client, db_session)
    uid2, _ = _login_empleado(
        client, auth_client, db_session, nombre_usuario=f"otro_{uuid4().hex[:4]}"
    )
    assert uid1 != uid2
    res = client.get(
        f"/usuarios/{uid2}", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_get_usuario_inexistente_404(auth_client: TestClient) -> None:
    """ID inexistente devuelve 404."""
    res = auth_client.get("/usuarios/9999999")
    assert res.status_code == 404


# ---------- PATCH /usuarios/{id} (faltantes) ----------


def test_patch_usuario_sin_auth_401(client: TestClient) -> None:
    """PATCH sin token devuelve 401."""
    res = client.patch("/usuarios/1", json={"email": "x@y.com"})
    assert res.status_code == 401


def test_patch_empleado_cambia_email_de_otro_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado intentando modificar a otro empleado recibe 403."""
    uid1, token = _login_empleado(client, auth_client, db_session)
    uid2, _ = _login_empleado(
        client,
        auth_client,
        db_session,
        nombre_usuario=f"victima_{uuid4().hex[:4]}",
    )
    res = client.patch(
        f"/usuarios/{uid2}",
        json={"email": "hack@test.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert uid1 != uid2


def test_patch_empleado_cambia_su_propio_email_200(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado puede cambiar su propio email."""
    uid, token = _login_empleado(client, auth_client, db_session)
    res = client.patch(
        f"/usuarios/{uid}",
        json={"email": "miNuevo@test.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "miNuevo@test.com"


def test_patch_admin_cambia_rol_de_otro_200(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Admin puede cambiar el rol de otro usuario."""
    uid, _ = _login_empleado(client, auth_client, db_session)
    res = auth_client.patch(
        f"/usuarios/{uid}",
        json={"rol": enums.Rol.ADMINISTRADOR.value},
    )
    assert res.status_code == 200
    assert res.json()["rol"] == enums.Rol.ADMINISTRADOR.value


# ---------- DELETE /usuarios/{id} ----------


def test_delete_usuario_sin_auth_401(client: TestClient) -> None:
    """DELETE sin token devuelve 401."""
    res = client.delete("/usuarios/1")
    assert res.status_code == 401


def test_delete_usuario_empleado_plano_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado plano no puede borrar usuarios."""
    uid, token = _login_empleado(client, auth_client, db_session)
    res = client.delete(
        f"/usuarios/{uid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_delete_usuario_inexistente_404(auth_client: TestClient) -> None:
    """DELETE de un ID inexistente devuelve 404."""
    res = auth_client.delete("/usuarios/9999999")
    assert res.status_code == 404
