from __future__ import annotations

from datetime import date

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums as enums_models
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Rol, Usuario


def test_listar_usuarios_vacio(client: TestClient) -> None:
    response = client.get("/usuarios")
    assert response.status_code == 200
    assert response.json() == []


def test_listar_usuarios_con_un_registro(client: TestClient, db_session: Session) -> None:
    empresa = Empresa(
        razon_social="Test SA",
        cuit="30-11111111-1",
        email_contacto="c@test.com",
        telefono_contacto="123",
        direccion="Calle 1",
        estado="activa",
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()

    rol = Rol(
        nombre_rol=enums_models.Rol.ADMINISTRADOR,
        descripcion="Admin",
    )
    db_session.add(rol)
    db_session.flush()

    empleado = Empleado(
        legajo="E-1",
        nombre="Ana",
        apellido="Test",
        dni="30111222",
        cuil="27-30111222-4",
        fecha_ingreso=date.today(),
        categoria_laboral="general",
        tipo_jornada="completa",
        modalidad_fichada_habilitada="si",
        estado="activo",
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.flush()

    usuario = Usuario(
        nombre_usuario="ana.test",
        contrasena_hash="hash_dummy",
        email="ana@test.com",
        estado="activo",
        ultimo_acceso=None,
        id_rol=rol.id_rol,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()

    response = client.get("/usuarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nombre_usuario"] == "ana.test"
    assert data[0]["email"] == "ana@test.com"
    assert data[0]["estado"] == "activo"
    assert data[0]["nombre_rol"] == "Administrador"
    assert "contrasena_hash" not in data[0]


def test_patch_usuario_actualiza_email(client: TestClient, db_session: Session) -> None:
    empresa = Empresa(
        razon_social="Patch User SA",
        cuit="30-33333333-3",
        email_contacto="c@p.com",
        telefono_contacto="1",
        direccion="X",
        estado="activa",
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()
    rol = Rol(nombre_rol=enums_models.Rol.EMPLEADO, descripcion="Emp")
    db_session.add(rol)
    db_session.flush()
    empleado = Empleado(
        legajo="PU-1",
        nombre="U",
        apellido="Patch",
        dni="50111222",
        cuil="20-50111222-3",
        fecha_ingreso=date.today(),
        categoria_laboral="x",
        tipo_jornada="completa",
        modalidad_fichada_habilitada="habilitada",
        estado="activo",
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.flush()
    usuario = Usuario(
        nombre_usuario="u.patch",
        contrasena_hash="hash",
        email="viejo@test.com",
        estado="activo",
        ultimo_acceso=None,
        id_rol=rol.id_rol,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()

    res = client.patch(
        f"/usuarios/{usuario.id_usuario}",
        json={"email": "nuevo@test.com", "nombre_usuario": "u.nuevo"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "nuevo@test.com"
    assert data["nombre_usuario"] == "u.nuevo"
    assert "contrasena" not in data


def test_patch_usuario_contrasena(client: TestClient, db_session: Session) -> None:
    empresa = Empresa(
        razon_social="Pwd SA",
        cuit="30-44444444-4",
        email_contacto="c@p.com",
        telefono_contacto="1",
        direccion="X",
        estado="activa",
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()
    rol = Rol(nombre_rol=enums_models.Rol.EMPLEADO, descripcion="Emp")
    db_session.add(rol)
    db_session.flush()
    empleado = Empleado(
        legajo="PW-1",
        nombre="P",
        apellido="W",
        dni="51111222",
        cuil="20-51111222-1",
        fecha_ingreso=date.today(),
        categoria_laboral="x",
        tipo_jornada="completa",
        modalidad_fichada_habilitada="habilitada",
        estado="activo",
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.flush()
    hash_ini = bcrypt.hashpw(b"vieja", bcrypt.gensalt()).decode("utf-8")
    usuario = Usuario(
        nombre_usuario="pwd.test",
        contrasena_hash=hash_ini,
        email="pwd@test.com",
        estado="activo",
        ultimo_acceso=None,
        id_rol=rol.id_rol,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()
    uid = usuario.id_usuario

    res = client.patch(f"/usuarios/{uid}", json={"contrasena": "secreta_nueva"})
    assert res.status_code == 200

    db_session.expire_all()
    u2 = db_session.get(Usuario, uid)
    assert u2 is not None
    assert bcrypt.checkpw(b"secreta_nueva", u2.contrasena_hash.encode("utf-8"))


def test_patch_usuario_no_encontrado(client: TestClient) -> None:
    res = client.patch("/usuarios/99999", json={"estado": "inactivo"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Usuario no encontrado"
