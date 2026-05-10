from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.services import auth_service


def _empresa(db_session: Session, *, cuit: str = "30-22222222-2") -> Empresa:
    empresa = Empresa(
        razon_social="Emp Patch",
        cuit=cuit,
        email_contacto="e@patch.com",
        telefono_contacto="123",
        direccion="Calle 2",
        estado=enums.EstadoEntidad.ACTIVO,
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)
    return empresa


def _empleado_minimo(
    db_session: Session,
    *,
    legajo: str = "P-1",
    dni: str = "40111222",
    cuil: str = "20-40111222-1",
    cuit: str = "30-22222222-2",
) -> Empleado:
    empresa = _empresa(db_session, cuit=cuit)
    empleado = Empleado(
        legajo=legajo,
        nombre="Pepe",
        apellido="Prueba",
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


def test_listar_empleados_requiere_auth(client: TestClient) -> None:
    res = client.get("/empleados")
    assert res.status_code == 401


def test_patch_empleado_actualiza_campos(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _empleado_minimo(db_session)
    res = auth_client.patch(
        f"/empleados/{empleado.id_empleado}",
        json={
            "estado": enums.EstadoEntidad.INACTIVO.value,
            "categoria_laboral": enums.CategoriaLaboral.ADMINISTRACION.value,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id_empleado"] == empleado.id_empleado
    assert data["estado"] == enums.EstadoEntidad.INACTIVO.value
    assert data["categoria_laboral"] == enums.CategoriaLaboral.ADMINISTRACION.value


def test_patch_empleado_body_vacio(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _empleado_minimo(db_session)
    res = auth_client.patch(f"/empleados/{empleado.id_empleado}", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["estado"] == enums.EstadoEntidad.ACTIVO.value


def test_patch_empleado_no_encontrado(auth_client: TestClient) -> None:
    res = auth_client.patch("/empleados/99999", json={"estado": enums.EstadoEntidad.INACTIVO.value})
    assert res.status_code == 404


def test_listar_empleados_varios(
    auth_client: TestClient, db_session: Session
) -> None:
    empresa = _empresa(db_session, cuit="30-55555555-5")
    for i, legajo in enumerate(["L-1", "L-2"], start=1):
        e = Empleado(
            legajo=legajo,
            nombre=f"N{i}",
            apellido=f"A{i}",
            dni=f"6011122{i}",
            cuil=f"20-6011122{i}-9",
            fecha_ingreso=date.today(),
            categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
            tipo_jornada=enums.TipoJornada.COMPLETA,
            modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
            estado=enums.EstadoEntidad.ACTIVO,
            id_empresa=empresa.id_empresa,
        )
        db_session.add(e)
    db_session.commit()
    res = auth_client.get("/empleados")
    assert res.status_code == 200
    legajos = {row["legajo"] for row in res.json()}
    assert {"L-1", "L-2"}.issubset(legajos)


def test_post_empleado_admin_crea(
    auth_client: TestClient, db_session: Session
) -> None:
    empresa = _empresa(db_session, cuit="30-66666666-6")
    payload = {
        "legajo": "NEW-1",
        "nombre": "Nuevo",
        "apellido": "Emp",
        "dni": "70000001",
        "cuil": "20-70000001-1",
        "fecha_ingreso": date.today().isoformat(),
        "categoria_laboral": enums.CategoriaLaboral.OPERACIONES.value,
        "tipo_jornada": enums.TipoJornada.COMPLETA.value,
        "id_empresa": empresa.id_empresa,
    }
    res = auth_client.post("/empleados", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["legajo"] == "NEW-1"
    assert data["modalidad_fichada_habilitada"] == enums.ModalidadFichada.HABILITADA.value


def test_post_empleado_empleado_plano_forbidden(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    empresa = _empresa(db_session, cuit="30-77777777-7")
    empleado = Empleado(
        legajo="LOG-1",
        nombre="L",
        apellido="O",
        dni="80000001",
        cuil="20-80000001-1",
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
    user_payload = {
        "nombre_usuario": "noadmin",
        "contrasena": "secreta123",
        "email": "noadmin@test.com",
        "rol": enums.Rol.EMPLEADO.value,
        "id_empleado": empleado.id_empleado,
    }
    auth_client.post("/usuarios", json=user_payload)
    login = client.post(
        "/auth/login",
        json={"nombre_usuario": "noadmin", "contrasena": "secreta123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    payload = {
        "legajo": "X-1",
        "nombre": "X",
        "apellido": "X",
        "dni": "80000002",
        "cuil": "20-80000002-1",
        "fecha_ingreso": date.today().isoformat(),
        "categoria_laboral": enums.CategoriaLaboral.OPERACIONES.value,
        "tipo_jornada": enums.TipoJornada.COMPLETA.value,
        "id_empresa": empresa.id_empresa,
    }
    res = client.post(
        "/empleados", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_post_empleado_dni_duplicado_conflict(
    auth_client: TestClient, db_session: Session
) -> None:
    empresa = _empresa(db_session, cuit="30-88888888-8")
    payload = {
        "legajo": "DUP-1",
        "nombre": "D",
        "apellido": "U",
        "dni": "90000001",
        "cuil": "20-90000001-1",
        "fecha_ingreso": date.today().isoformat(),
        "categoria_laboral": enums.CategoriaLaboral.OPERACIONES.value,
        "tipo_jornada": enums.TipoJornada.COMPLETA.value,
        "id_empresa": empresa.id_empresa,
    }
    res1 = auth_client.post("/empleados", json=payload)
    assert res1.status_code == 201
    payload2 = {**payload, "legajo": "DUP-2", "cuil": "20-90000002-1"}
    res2 = auth_client.post("/empleados", json=payload2)
    assert res2.status_code == 409


def test_delete_empleado_baja_logica(
    auth_client: TestClient, db_session: Session
) -> None:
    empleado = _empleado_minimo(
        db_session, legajo="DEL-E", dni="95000001", cuil="20-95000001-1", cuit="30-99999991-1"
    )
    res = auth_client.delete(f"/empleados/{empleado.id_empleado}")
    assert res.status_code == 204
    db_session.expire_all()
    db_session.refresh(empleado)
    assert empleado.estado == enums.EstadoEntidad.INACTIVO


def _login_empleado_token(
    client: TestClient, db_session: Session, empleado: Empleado
) -> str:
    """Crea un Usuario rol EMPLEADO sobre empleado dado y devuelve token."""
    sufijo = uuid4().hex[:6]
    usuario = Usuario(
        nombre_usuario=f"emp_{sufijo}",
        contrasena_hash=auth_service.hash_password("secreta123"),
        email=f"emp_{sufijo}@test.com",
        rol=enums.Rol.EMPLEADO,
        estado=enums.EstadoEntidad.ACTIVO,
        ultimo_acceso=None,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()
    login = client.post(
        "/auth/login",
        json={"nombre_usuario": usuario.nombre_usuario, "contrasena": "secreta123"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_post_empleado_fecha_invalida_422(
    auth_client: TestClient, db_session: Session
) -> None:
    """fecha_ingreso con formato inválido devuelve 422."""
    empresa = _empresa(db_session, cuit="30-44444411-1")
    payload = {
        "legajo": "F-1",
        "nombre": "F",
        "apellido": "F",
        "dni": "75000001",
        "cuil": "20-75000001-1",
        "fecha_ingreso": "no-es-fecha",
        "categoria_laboral": enums.CategoriaLaboral.OPERACIONES.value,
        "tipo_jornada": enums.TipoJornada.COMPLETA.value,
        "id_empresa": empresa.id_empresa,
    }
    res = auth_client.post("/empleados", json=payload)
    assert res.status_code == 422


def test_get_empleado_por_id_200(
    auth_client: TestClient, db_session: Session
) -> None:
    """Admin obtiene un empleado existente."""
    empleado = _empleado_minimo(
        db_session,
        legajo="G-1",
        dni="76000001",
        cuil="20-76000001-1",
        cuit="30-55444433-2",
    )
    res = auth_client.get(f"/empleados/{empleado.id_empleado}")
    assert res.status_code == 200
    assert res.json()["legajo"] == "G-1"


def test_get_empleado_no_encontrado_404(auth_client: TestClient) -> None:
    """GET de empleado inexistente devuelve 404."""
    res = auth_client.get("/empleados/9999999")
    assert res.status_code == 404


def test_patch_empleado_empleado_plano_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado plano no puede patchear empleados."""
    empresa = _empresa(db_session, cuit="30-33444455-1")
    empleado = Empleado(
        legajo="PE-1",
        nombre="P",
        apellido="E",
        dni="77000001",
        cuil="20-77000001-1",
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
    token = _login_empleado_token(client, db_session, empleado)
    res = client.patch(
        f"/empleados/{empleado.id_empleado}",
        json={"nombre": "Hack"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_patch_empleado_enum_invalido_422(
    auth_client: TestClient, db_session: Session
) -> None:
    """Valor de enum desconocido en PATCH devuelve 422."""
    empleado = _empleado_minimo(
        db_session,
        legajo="EI-1",
        dni="78000001",
        cuil="20-78000001-1",
        cuit="30-22443322-1",
    )
    res = auth_client.patch(
        f"/empleados/{empleado.id_empleado}",
        json={"categoria_laboral": "NO_EXISTE"},
    )
    assert res.status_code == 422


def test_delete_empleado_empleado_plano_403(
    auth_client: TestClient, client: TestClient, db_session: Session
) -> None:
    """Empleado plano no puede borrar empleados."""
    empresa = _empresa(db_session, cuit="30-44551122-1")
    empleado = Empleado(
        legajo="DE-1",
        nombre="D",
        apellido="E",
        dni="79000001",
        cuil="20-79000001-1",
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
    token = _login_empleado_token(client, db_session, empleado)
    res = client.delete(
        f"/empleados/{empleado.id_empleado}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_delete_empleado_no_encontrado_404(auth_client: TestClient) -> None:
    """DELETE de empleado inexistente devuelve 404."""
    res = auth_client.delete("/empleados/9999999")
    assert res.status_code == 404
