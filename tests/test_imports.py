from __future__ import annotations

import io

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _csv(headers: list[str], rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    buf.write(",".join(headers) + "\n")
    for r in rows:
        buf.write(",".join(r) + "\n")
    return buf.getvalue().encode("utf-8")


# ============================================================
# /empresas/import
# ============================================================


def test_import_empresas_requiere_auth(client: TestClient) -> None:
    """Sin token: 401."""
    csv = _csv(
        ["razon_social", "cuit", "email_contacto", "telefono_contacto", "direccion", "fecha_alta"],
        [["A", "30-1-1", "a@a.com", "1", "X", "2026-01-01"]],
    )
    res = client.post(
        "/empresas/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 401


def test_import_empresas_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Empleado plano: 403."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    csv = _csv(
        ["razon_social", "cuit", "email_contacto", "telefono_contacto", "direccion", "fecha_alta"],
        [["A", "30-2-1", "a@a.com", "1", "X", "2026-01-01"]],
    )
    res = client.post(
        "/empresas/import",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("e.csv", csv, "text/csv")},
    )
    assert res.status_code == 403


def test_import_empresas_admin_crea_y_omite(
    auth_client: TestClient, db_session: Session
) -> None:
    """Admin: crea las nuevas, omite las que ya existen por CUIT."""
    csv = _csv(
        ["razon_social", "cuit", "email_contacto", "telefono_contacto", "direccion", "fecha_alta"],
        [
            ["ACME", "30-99001-1", "rrhh@acme.com", "111", "X", "2026-01-01"],
            ["ACME 2", "30-99002-1", "rrhh@acme2.com", "222", "Y", "2026-01-02"],
            ["ACME dup", "30-99001-1", "x@x.com", "0", "Z", "2026-01-03"],  # omitido
        ],
    )
    res = auth_client.post(
        "/empresas/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_filas"] == 3
    assert data["creados"] == 2
    assert data["omitidos"] == 1
    assert data["errores"] == []
    assert data["dry_run"] is False
    db_session.expire_all()
    assert db_session.query(Empresa).filter_by(cuit="30-99001-1").one().razon_social == "ACME"


def test_import_empresas_dry_run_no_persiste(auth_client: TestClient) -> None:
    """dry_run=true: la respuesta cuenta correctamente pero la BD no cambia (validado via API)."""
    antes_listado = auth_client.get("/empresas").json()
    cuits_antes = {e["cuit"] for e in antes_listado}
    csv = _csv(
        ["razon_social", "cuit", "email_contacto", "telefono_contacto", "direccion", "fecha_alta"],
        [["DryRun", "30-DRY-9999-1", "d@d.com", "1", "X", "2026-01-01"]],
    )
    res = auth_client.post(
        "/empresas/import?dry_run=true",
        files={"file": ("e.csv", csv, "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["creados"] == 1
    assert res.json()["dry_run"] is True
    despues = auth_client.get("/empresas").json()
    cuits_despues = {e["cuit"] for e in despues}
    assert cuits_despues == cuits_antes  # ningún cuit nuevo persistió
    assert "30-DRY-9999-1" not in cuits_despues


def test_import_empresas_headers_faltantes_422(auth_client: TestClient) -> None:
    """Falta una columna obligatoria: 422."""
    csv = _csv(
        ["razon_social", "cuit"],  # faltan varios
        [["A", "30-X-1"]],
    )
    res = auth_client.post(
        "/empresas/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 422


# ============================================================
# /empleados/import
# ============================================================


EMP_HEADERS = [
    "id_empresa",
    "legajo",
    "nombre",
    "apellido",
    "dni",
    "cuil",
    "fecha_ingreso",
    "categoria_laboral",
    "tipo_jornada",
    "modalidad_fichada_habilitada",
]


def test_import_empleados_requiere_auth(client: TestClient) -> None:
    csv = _csv(EMP_HEADERS, [["1", "L1", "A", "B", "1", "1", "2026-01-01", "operaciones", "completa", "habilitada"]])
    res = client.post("/empleados/import", files={"file": ("e.csv", csv, "text/csv")})
    assert res.status_code == 401


def test_import_empleados_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    csv = _csv(EMP_HEADERS, [["1", "L1", "A", "B", "1", "1", "2026-01-01", "operaciones", "completa", "habilitada"]])
    res = client.post(
        "/empleados/import",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("e.csv", csv, "text/csv")},
    )
    assert res.status_code == 403


def test_import_empleados_admin_crea(
    auth_client: TestClient, db_session: Session, empresa_factory
) -> None:
    """Admin importa 2 empleados nuevos contra una empresa existente."""
    empresa = empresa_factory()
    csv = _csv(
        EMP_HEADERS,
        [
            [str(empresa.id_empresa), "IMP-1", "Juan", "Perez", "55001", "20-55001-1",
             "2026-01-01", "operaciones", "completa", "habilitada"],
            [str(empresa.id_empresa), "IMP-2", "Ana", "Gomez", "55002", "20-55002-1",
             "2026-01-02", "administracion", "parcial", "habilitada"],
        ],
    )
    res = auth_client.post(
        "/empleados/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["creados"] == 2
    assert data["errores"] == []
    db_session.expire_all()
    assert db_session.query(Empleado).filter_by(legajo="IMP-1").one().nombre == "Juan"


def test_import_empleados_id_empresa_invalida_da_error_fila(
    auth_client: TestClient, db_session: Session
) -> None:
    """Empresa inexistente: la fila va a errores, batch sigue."""
    csv = _csv(
        EMP_HEADERS,
        [
            ["999999", "BAD-1", "X", "Y", "9991", "20-9991-1", "2026-01-01", "operaciones", "completa", "habilitada"],
        ],
    )
    res = auth_client.post(
        "/empleados/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["creados"] == 0
    assert len(data["errores"]) == 1
    assert "no existe" in data["errores"][0]["motivo"].lower()


def test_import_empleados_enum_invalido(
    auth_client: TestClient, empresa_factory
) -> None:
    """tipo_jornada con valor inválido: error de fila claro."""
    empresa = empresa_factory()
    csv = _csv(
        EMP_HEADERS,
        [
            [str(empresa.id_empresa), "ENM-1", "A", "B", "55003", "20-55003-1",
             "2026-01-01", "operaciones", "INVALIDA", "habilitada"],
        ],
    )
    res = auth_client.post(
        "/empleados/import", files={"file": ("e.csv", csv, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["creados"] == 0
    assert "tipo_jornada" in data["errores"][0]["motivo"]


# ============================================================
# /usuarios/import
# ============================================================


USR_HEADERS = ["nombre_usuario", "contrasena", "email", "rol", "id_empleado"]


def test_import_usuarios_requiere_auth(client: TestClient) -> None:
    csv = _csv(USR_HEADERS, [["u1", "secreta12", "u1@a.com", "Empleado", "1"]])
    res = client.post("/usuarios/import", files={"file": ("u.csv", csv, "text/csv")})
    assert res.status_code == 401


def test_import_usuarios_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    csv = _csv(USR_HEADERS, [["u1", "secreta12", "u1@a.com", "Empleado", "1"]])
    res = client.post(
        "/usuarios/import",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("u.csv", csv, "text/csv")},
    )
    assert res.status_code == 403


def test_import_usuarios_admin_crea_y_hashea(
    auth_client: TestClient,
    db_session: Session,
    empresa_factory,
    empleado_factory,
) -> None:
    """Admin: crea usuarios y la contraseña queda como hash bcrypt verificable."""
    empresa = empresa_factory()
    e1 = empleado_factory(empresa=empresa, legajo="USRIMP-1")
    e2 = empleado_factory(empresa=empresa, legajo="USRIMP-2")
    csv = _csv(
        USR_HEADERS,
        [
            ["uimp1", "passw0rd!", "u1@imp.com", "Empleado", str(e1.id_empleado)],
            ["uimp2", "passw0rd!", "u2@imp.com", "ContadorExterno", str(e2.id_empleado)],
        ],
    )
    res = auth_client.post(
        "/usuarios/import", files={"file": ("u.csv", csv, "text/csv")}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["creados"] == 2
    db_session.expire_all()
    u = db_session.query(Usuario).filter_by(nombre_usuario="uimp1").one()
    assert bcrypt.checkpw(b"passw0rd!", u.contrasena_hash.encode("utf-8"))


def test_import_usuarios_password_corta(
    auth_client: TestClient, empresa_factory, empleado_factory
) -> None:
    """Password < 8 chars: error de fila."""
    empresa = empresa_factory()
    e1 = empleado_factory(empresa=empresa, legajo="USRSHORT-1")
    csv = _csv(
        USR_HEADERS,
        [["short", "1234", "s@x.com", "Empleado", str(e1.id_empleado)]],
    )
    res = auth_client.post(
        "/usuarios/import", files={"file": ("u.csv", csv, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["creados"] == 0
    assert "8 caracteres" in data["errores"][0]["motivo"]


def test_import_usuarios_omite_repetidos(
    auth_client: TestClient,
    db_session: Session,
    empresa_factory,
    empleado_factory,
) -> None:
    """nombre_usuario ya existente: omitido (no error)."""
    empresa = empresa_factory()
    e1 = empleado_factory(empresa=empresa, legajo="USRREP-1")
    e2 = empleado_factory(empresa=empresa, legajo="USRREP-2")
    csv = _csv(
        USR_HEADERS,
        [
            ["urep", "passw0rd!", "u@r.com", "Empleado", str(e1.id_empleado)],
            ["urep", "passw0rd!", "u2@r.com", "Empleado", str(e2.id_empleado)],
        ],
    )
    res = auth_client.post(
        "/usuarios/import", files={"file": ("u.csv", csv, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["creados"] == 1
    assert data["omitidos"] == 1


# ============================================================
# /fichadas/export (round-trip con import)
# ============================================================


def test_export_fichadas_requiere_auth(client: TestClient) -> None:
    res = client.get("/fichadas/export")
    assert res.status_code == 401


def test_export_fichadas_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/fichadas/export", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_export_fichadas_admin_devuelve_csv(auth_client: TestClient) -> None:
    """Admin obtiene 200 con CSV (puede estar vacío) y headers correctos."""
    res = auth_client.get("/fichadas/export?formato=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "fichadas.csv" in res.headers["content-disposition"]
    primera = res.text.splitlines()[0]
    assert primera == "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones"


def test_export_fichadas_round_trip_con_import(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Importa CSV de ejemplo, exporta, valida que el CSV salido sea round-trip-able."""
    empresa = empresa_factory()
    # Empleados con los legajos del fixture.
    for legajo in ("14", "10", "12", "13"):
        empleado_factory(empresa=empresa, legajo=legajo)

    # Importar el CSV real.
    with open("tests/fixtures/planilla_ejemplo.csv", "rb") as f:
        contenido = f.read()
    res = auth_client.post(
        f"/fichadas/import?id_empresa={empresa.id_empresa}",
        files={"file": ("planilla_ejemplo.csv", contenido, "text/csv")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["fichadas_creadas"] == 247

    # Exportar.
    res_export = auth_client.get(f"/fichadas/export?id_empresa={empresa.id_empresa}&formato=csv")
    assert res_export.status_code == 200
    lineas = res_export.text.splitlines()
    assert lineas[0] == "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones"
    assert len(lineas) == 248  # header + 247 fichadas
    # Sample: tiene Local + Manual + entrada/salida + legajos del fixture.
    body = "\n".join(lineas)
    assert ",Local," in body
    assert ",Manual," in body
    assert ",Entrada," in body
    assert ",Salida," in body
    assert ",14,Gabriel Marquez," in body or ",14," in body
