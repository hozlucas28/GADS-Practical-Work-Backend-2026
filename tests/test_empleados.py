from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organizacion import Empleado, Empresa


def _empleado_minimo(db_session: Session) -> Empleado:
    empresa = Empresa(
        razon_social="Emp Patch",
        cuit="30-22222222-2",
        email_contacto="e@patch.com",
        telefono_contacto="123",
        direccion="Calle 2",
        estado="activa",
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()
    empleado = Empleado(
        legajo="P-1",
        nombre="Pepe",
        apellido="Prueba",
        dni="40111222",
        cuil="20-40111222-1",
        fecha_ingreso=date.today(),
        categoria_laboral="general",
        tipo_jornada="completa",
        modalidad_fichada_habilitada="habilitada",
        estado="activo",
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.commit()
    db_session.refresh(empleado)
    return empleado


def test_patch_empleado_actualiza_campos(client: TestClient, db_session: Session) -> None:
    empleado = _empleado_minimo(db_session)
    res = client.patch(
        f"/empleados/{empleado.id_empleado}",
        json={"estado": "inactivo", "categoria_laboral": "Sistemas"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id_empleado"] == empleado.id_empleado
    assert data["estado"] == "inactivo"
    assert data["categoria_laboral"] == "Sistemas"
    assert data["nombre"] == "Pepe"


def test_patch_empleado_body_vacio(client: TestClient, db_session: Session) -> None:
    empleado = _empleado_minimo(db_session)
    res = client.patch(f"/empleados/{empleado.id_empleado}", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["estado"] == "activo"
    assert data["legajo"] == "P-1"


def test_patch_empleado_no_encontrado(client: TestClient) -> None:
    res = client.patch("/empleados/99999", json={"estado": "inactivo"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Empleado no encontrado"


def test_listar_empleados_vacio(client: TestClient) -> None:
    res = client.get("/empleados")
    assert res.status_code == 200
    assert res.json() == []


def test_listar_empleados_varios(client: TestClient, db_session: Session) -> None:
    empresa = Empresa(
        razon_social="List SA",
        cuit="30-55555555-5",
        email_contacto="l@list.com",
        telefono_contacto="1",
        direccion="Y",
        estado="activa",
        fecha_alta=date.today(),
    )
    db_session.add(empresa)
    db_session.flush()
    for i, legajo in enumerate(["L-1", "L-2"], start=1):
        e = Empleado(
            legajo=legajo,
            nombre=f"N{i}",
            apellido=f"A{i}",
            dni=f"6011122{i}",
            cuil=f"20-6011122{i}-9",
            fecha_ingreso=date.today(),
            categoria_laboral="c",
            tipo_jornada="completa",
            modalidad_fichada_habilitada="habilitada",
            estado="activo",
            id_empresa=empresa.id_empresa,
        )
        db_session.add(e)
    db_session.commit()

    res = client.get("/empleados")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert {row["legajo"] for row in data} == {"L-1", "L-2"}
