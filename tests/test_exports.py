from __future__ import annotations

import csv
import io
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _parse_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = list(reader)
    return headers, rows


# ============================================================
# /empresas/export
# ============================================================


def test_export_empresas_requiere_auth(client: TestClient) -> None:
    """Sin token devuelve 401."""
    res = client.get("/empresas/export")
    assert res.status_code == 401


def test_export_empresas_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Rol Empleado no puede exportar (403)."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/empresas/export", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_export_empresas_admin_devuelve_csv(auth_client: TestClient) -> None:
    """Admin obtiene 200 con content-type text/csv y header Content-Disposition."""
    res = auth_client.get("/empresas/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    assert "empresas.csv" in res.headers["content-disposition"]


def test_export_empresas_contenido(auth_client: TestClient) -> None:
    """El CSV tiene los headers esperados y al menos 1 fila (Nero IT del bootstrap)."""
    res = auth_client.get("/empresas/export")
    headers, rows = _parse_csv(res.text)
    assert "id_empresa" in headers
    assert "razon_social" in headers
    assert "cuit" in headers
    assert "estado" in headers
    assert len(rows) >= 1
    assert all(row.get("estado") for row in rows)


# ============================================================
# /empleados/export
# ============================================================


def test_export_empleados_requiere_auth(client: TestClient) -> None:
    """Sin token devuelve 401."""
    res = client.get("/empleados/export")
    assert res.status_code == 401


def test_export_empleados_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Rol Empleado no puede exportar (403)."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/empleados/export", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_export_empleados_admin_devuelve_csv(
    auth_client: TestClient,
    db_session: Session,
    empresa_factory,
    empleado_factory,
) -> None:
    """Admin recibe CSV con datos."""
    empresa = empresa_factory()
    empleado_factory(empresa=empresa, legajo="EXP-1", nombre="Export", apellido="Uno")
    empleado_factory(empresa=empresa, legajo="EXP-2", nombre="Export", apellido="Dos")

    res = auth_client.get("/empleados/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "empleados.csv" in res.headers["content-disposition"]
    headers, rows = _parse_csv(res.text)
    assert "legajo" in headers
    assert "dni" in headers
    legajos = {r["legajo"] for r in rows}
    assert {"EXP-1", "EXP-2"}.issubset(legajos)


def test_export_empleados_enums_serializados(
    auth_client: TestClient, db_session: Session, empresa_factory
) -> None:
    """Los enums salen como string (no como 'EstadoEntidad.ACTIVO')."""
    empresa = empresa_factory()
    empleado = Empleado(
        legajo="ENM-1",
        nombre="Enum",
        apellido="Test",
        dni="99999990",
        cuil="20-99999990-1",
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.ADMINISTRACION,
        tipo_jornada=enums.TipoJornada.PARCIAL,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    db_session.add(empleado)
    db_session.commit()

    res = auth_client.get("/empleados/export")
    _, rows = _parse_csv(res.text)
    fila = next(r for r in rows if r["legajo"] == "ENM-1")
    assert fila["estado"] == "activo"
    assert fila["tipo_jornada"] == "parcial"
    assert fila["categoria_laboral"] == "administracion"


# ============================================================
# /usuarios/export
# ============================================================


def test_export_usuarios_requiere_auth(client: TestClient) -> None:
    """Sin token devuelve 401."""
    res = client.get("/usuarios/export")
    assert res.status_code == 401


def test_export_usuarios_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Rol Empleado no puede exportar (403)."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/usuarios/export", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_export_usuarios_admin_devuelve_csv(auth_client: TestClient) -> None:
    """Admin obtiene 200 con CSV."""
    res = auth_client.get("/usuarios/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "usuarios.csv" in res.headers["content-disposition"]
    headers, rows = _parse_csv(res.text)
    assert "id_usuario" in headers
    assert "nombre_usuario" in headers
    assert "rol" in headers
    assert len(rows) >= 1


def test_export_usuarios_no_filtra_contrasena_hash(auth_client: TestClient) -> None:
    """El CSV NO debe incluir la columna contrasena_hash bajo ninguna circunstancia."""
    res = auth_client.get("/usuarios/export")
    assert "contrasena" not in res.text.lower()
    assert "hash" not in res.text.lower()
    headers, _ = _parse_csv(res.text)
    assert "contrasena_hash" not in headers
    assert "contrasena" not in headers


def test_export_usuarios_rol_admin_presente(auth_client: TestClient) -> None:
    """El admin del bootstrap aparece con rol Administrador."""
    res = auth_client.get("/usuarios/export")
    _, rows = _parse_csv(res.text)
    admin = next((r for r in rows if r["rol"] == enums.Rol.ADMINISTRADOR.value), None)
    assert admin is not None
    assert admin["estado"] == enums.EstadoEntidad.ACTIVO.value


# ============================================================
# Format checks (cross-feature)
# ============================================================


def test_export_csv_es_utf8_valido(auth_client: TestClient) -> None:
    """Los 3 endpoints devuelven UTF-8 parseable sin errores."""
    for path in ("/empresas/export", "/empleados/export", "/usuarios/export"):
        res = auth_client.get(path)
        assert res.status_code == 200
        # decode no debería levantar
        res.content.decode("utf-8")
