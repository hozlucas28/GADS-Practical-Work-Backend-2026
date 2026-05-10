from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada
from app.models.novedades import Novedad, TipoNovedad
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.services import auth_service

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "planilla_ejemplo.csv"


def _crear_empleados_planilla(
    db_session: Session,
    empleado_factory: Callable[..., Empleado],
    empresa: Empresa,
) -> dict[str, Empleado]:
    """Crea los empleados con legajos referenciados por el CSV de fixture."""
    legajos_nombres = {
        "14": ("Gabriel", "Marquez"),
        "10": ("Azucena", "Picaflor"),
        "12": ("Cachito", "Bellavista"),
        "13": ("Esteban", "Silvestre"),
    }
    creados: dict[str, Empleado] = {}
    for legajo, (nombre, apellido) in legajos_nombres.items():
        creados[legajo] = empleado_factory(
            empresa=empresa,
            legajo=legajo,
            nombre=nombre,
            apellido=apellido,
        )
    return creados


def test_import_csv_planilla_ejemplo_caso_feliz(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """Importa el CSV de fixture; espera 2 novedades VACACIONES y todas las fichadas creadas."""
    # Empresa del admin (su empleado vive en ella).
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None

    _crear_empleados_planilla(db_session, empleado_factory, empresa)

    contenido = FIXTURE_PATH.read_bytes()
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa},
        files={"file": ("planilla_ejemplo.csv", contenido, "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["dry_run"] is False
    assert data["errores"] == []
    # 247 filas de datos en el CSV.
    assert data["total_filas"] == 247
    assert data["fichadas_creadas"] == 247
    assert data["novedades_creadas"] == 2
    assert "vacaciones" in data["tipos_novedad_creados"]

    # Verificamos en BD.
    assert db_session.query(Fichada).count() == 247
    assert db_session.query(Novedad).count() == 2
    tipos = {t.nombre_tipo for t in db_session.query(TipoNovedad).all()}
    assert "vacaciones" in tipos


def test_import_empleado_inexistente_genera_error_de_fila(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """Un legajo desconocido produce un error de fila pero no aborta el batch."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None
    # Sólo creamos legajo 14.
    empleado_factory(empresa=empresa, legajo="14", nombre="Gabriel", apellido="Marquez")

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Local,Entrada,14,Gabriel Marquez,\n"
        "01/04/26,08:05,Local,Entrada,99,Desconocido Sin Empresa,\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_filas"] == 2
    assert data["fichadas_creadas"] == 1
    assert len(data["errores"]) == 1
    assert data["errores"][0]["fila"] == 3
    assert data["errores"][0]["legajo"] == "99"


def test_import_dry_run_no_persiste(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """Con dry_run=true no debe quedar nada en BD."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None
    empleado_factory(empresa=empresa, legajo="14", nombre="Gabriel", apellido="Marquez")

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Local,Entrada,14,Gabriel Marquez,\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa, "dry_run": True},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["dry_run"] is True
    assert data["fichadas_creadas"] == 1
    # Nada persistido.
    db_session.expire_all()
    assert db_session.query(Fichada).count() == 0


def test_import_encabezados_faltantes_devuelve_422(
    auth_client: TestClient,
    db_session: Session,
    admin_user: Usuario,
) -> None:
    """Si faltan headers requeridos, responde 422."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    csv = "Fecha,Hora,Legajo\n01/04/26,08:00,14\n"
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empleado_admin.id_empresa},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 422, res.text


def test_import_auth_empleado_plano_403(
    client: TestClient,
    db_session: Session,
    empleado_factory,
) -> None:
    """Un usuario con rol Empleado no puede importar."""
    empleado = empleado_factory()
    sufijo = uuid4().hex[:6]
    usuario = Usuario(
        nombre_usuario=f"emp_{sufijo}",
        contrasena_hash=auth_service.hash_password("emp12345"),
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
        json={"nombre_usuario": usuario.nombre_usuario, "contrasena": "emp12345"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Local,Entrada,14,Gabriel,\n"
    )
    res = client.post(
        "/fichadas/import",
        params={"id_empresa": empleado.id_empresa},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 403, res.text


def test_import_forma_registro_invalida_genera_error_de_fila(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """Forma Registro fuera de Local/Manual genera error de fila (no aborta)."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None
    empleado_factory(empresa=empresa, legajo="14", nombre="Gabriel", apellido="Marquez")

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Marciano,Entrada,14,Gabriel Marquez,\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["fichadas_creadas"] == 0
    assert len(data["errores"]) == 1
    assert "Marciano" in data["errores"][0]["motivo"]


def test_import_parser_justificacion_crea_tipo_novedad_normalizado(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """'JUSTIFICACION Entra : Licencia Medica' debe crear tipo 'licencia_medica'."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None
    empleado_factory(empresa=empresa, legajo="14", nombre="Gabriel", apellido="Marquez")

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Manual,Entrada,14,Gabriel Marquez,JUSTIFICACION Entra : Licencia Medica\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa},
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["fichadas_creadas"] == 1
    assert data["novedades_creadas"] == 1
    assert "licencia_medica" in data["tipos_novedad_creados"]

    tipos = {t.nombre_tipo for t in db_session.query(TipoNovedad).all()}
    assert "licencia_medica" in tipos
    novedad = db_session.query(Novedad).one()
    tipo = db_session.get(TipoNovedad, novedad.id_tipo_novedad)
    assert tipo is not None
    assert tipo.nombre_tipo == "licencia_medica"


def test_import_admin_sin_id_empresa_400(
    auth_client: TestClient,
    db_session: Session,
    admin_user: Usuario,
) -> None:
    """Admin debe enviar id_empresa explícitamente; sin él, 400."""
    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Local,Entrada,14,Gabriel,\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 400, res.text


def test_import_contador_externo_infiere_empresa(
    auth_client: TestClient,
    client: TestClient,
    db_session: Session,
    empleado_factory: Callable[..., Empleado],
) -> None:
    """Un ContadorExterno no envía id_empresa: se infiere de su empleado."""
    empleado = empleado_factory()
    sufijo = uuid4().hex[:6]
    usuario = Usuario(
        nombre_usuario=f"contador_{sufijo}",
        contrasena_hash=auth_service.hash_password("contador1"),
        email=f"contador_{sufijo}@test.com",
        rol=enums.Rol.CONTADOR_EXTERNO,
        estado=enums.EstadoEntidad.ACTIVO,
        ultimo_acceso=None,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()

    # Aseguramos que exista el legajo 14 EN LA MISMA empresa del contador.
    empleado_factory(
        empresa=db_session.get(Empresa, empleado.id_empresa),
        legajo="14",
        nombre="Gabriel",
        apellido="Marquez",
    )

    login = client.post(
        "/auth/login",
        json={"nombre_usuario": usuario.nombre_usuario, "contrasena": "contador1"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Local,Entrada,14,Gabriel Marquez,\n"
    )
    res = client.post(
        "/fichadas/import",
        files={"file": ("p.csv", csv.encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["fichadas_creadas"] == 1
    assert data["errores"] == []


def test_import_csv_solo_headers_sin_filas(
    auth_client: TestClient,
    db_session: Session,
    admin_user: Usuario,
) -> None:
    """CSV con solo headers debe procesarse sin fichadas ni errores."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    csv = "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empleado_admin.id_empresa},
        files={"file": ("vacio.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_filas"] == 0
    assert data["fichadas_creadas"] == 0
    assert data["errores"] == []
    assert db_session.query(Fichada).count() == 0


def test_import_vacaciones_crea_novedad_normalizada(
    auth_client: TestClient,
    db_session: Session,
    empleado_factory,
    admin_user: Usuario,
) -> None:
    """'JUSTIFICACION Entra : VACACIONES' debe crear tipo 'vacaciones'."""
    empleado_admin = db_session.get(Empleado, admin_user.id_empleado)
    assert empleado_admin is not None
    empresa = db_session.get(Empresa, empleado_admin.id_empresa)
    assert empresa is not None
    empleado_factory(empresa=empresa, legajo="14", nombre="Gabriel", apellido="Marquez")

    csv = (
        "Fecha,Hora,Forma Registro,Tipo Registro,Legajo,Empleado,Observaciones\n"
        "01/04/26,08:00,Manual,Entrada,14,Gabriel Marquez,JUSTIFICACION Entra : VACACIONES\n"
    )
    res = auth_client.post(
        "/fichadas/import",
        params={"id_empresa": empresa.id_empresa},
        files={"file": ("v.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["novedades_creadas"] == 1
    assert "vacaciones" in data["tipos_novedad_creados"]
    tipos = {t.nombre_tipo for t in db_session.query(TipoNovedad).all()}
    assert "vacaciones" in tipos
