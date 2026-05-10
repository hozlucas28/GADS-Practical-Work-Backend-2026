from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada, OrigenFichada
from app.models.novedades import Novedad, TipoNovedad
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


# ============================================================
# Helpers
# ============================================================


def _hash() -> str:
    return bcrypt.hashpw(b"secreta123", bcrypt.gensalt()).decode("utf-8")


def _origen_local(db: Session) -> OrigenFichada:
    o = (
        db.query(OrigenFichada)
        .filter(OrigenFichada.nombre_origen == enums.OrigenFichada.LOCAL)
        .one_or_none()
    )
    if o is None:
        o = OrigenFichada(nombre_origen=enums.OrigenFichada.LOCAL)
        db.add(o)
        db.commit()
        db.refresh(o)
    return o


def _crear_fichada(
    db: Session,
    empleado: Empleado,
    cuando: datetime,
    *,
    tipo: enums.TipoFichada = enums.TipoFichada.ENTRADA,
    id_usuario_registrador: int = 1,
) -> Fichada:
    origen = _origen_local(db)
    f = Fichada(
        fecha_hora=cuando,
        tipo_fichada=tipo,
        fue_corregida=False,
        observacion=None,
        id_empleado=empleado.id_empleado,
        id_origen_fichada=origen.id_origen_fichada,
        id_usuario_registrador=id_usuario_registrador,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _crear_novedad(
    db: Session,
    empleado: Empleado,
    *,
    estado: enums.EstadoNovedad = enums.EstadoNovedad.PENDIENTE,
    nombre_tipo: str = "vacaciones",
    id_usuario_creador: int = 1,
) -> Novedad:
    tipo = (
        db.query(TipoNovedad)
        .filter(TipoNovedad.nombre_tipo == nombre_tipo)
        .one_or_none()
    )
    if tipo is None:
        tipo = TipoNovedad(
            nombre_tipo=nombre_tipo,
            unidad_medida=enums.UnidadMedidaTipoNovedad.DIAS,
            requiere_justificativo=False,
            requiere_aprobacion=False,
            impacta_liquidacion=False,
        )
        db.add(tipo)
        db.commit()
        db.refresh(tipo)
    n = Novedad(
        fecha_desde=date.today(),
        fecha_hasta=None,
        cantidad=Decimal("1"),
        estado=estado,
        origen=enums.OrigenNovedad.MANUAL,
        observacion=None,
        id_empleado=empleado.id_empleado,
        id_tipo_novedad=tipo.id_tipo_novedad,
        id_fichada=None,
        id_usuario_creador=id_usuario_creador,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


# ============================================================
# /dashboards/resumen
# ============================================================


def test_resumen_requiere_auth(client: TestClient) -> None:
    """Sin token: 401."""
    res = client.get("/dashboards/resumen")
    assert res.status_code == 401


def test_resumen_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Empleado plano: 403."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/dashboards/resumen", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


def test_resumen_admin_devuelve_metricas(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Admin obtiene 200 con todas las claves."""
    empresa = empresa_factory()
    empleado_factory(empresa=empresa, legajo="DSH-1")
    empleado_factory(empresa=empresa, legajo="DSH-2")

    res = auth_client.get("/dashboards/resumen")
    assert res.status_code == 200
    data = res.json()
    assert {"empresas", "empleados", "usuarios", "fichadas", "novedades"} <= set(data)
    assert data["empleados"]["total"] >= 2
    assert "por_rol" in data["usuarios"]


def test_resumen_filtro_por_empresa(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Filtro por id_empresa scope todo correctamente."""
    e1 = empresa_factory()
    e2 = empresa_factory()
    empleado_factory(empresa=e1, legajo="A-1")
    empleado_factory(empresa=e2, legajo="B-1")
    empleado_factory(empresa=e2, legajo="B-2")

    res = auth_client.get(f"/dashboards/resumen?id_empresa={e2.id_empresa}")
    assert res.status_code == 200
    data = res.json()
    assert data["id_empresa"] == e2.id_empresa
    assert data["empleados"]["total"] == 2
    assert data["empresas"]["total"] == 1


# ============================================================
# /dashboards/empleados/status
# ============================================================


def test_status_requiere_auth(client: TestClient) -> None:
    """Sin token: 401."""
    res = client.get("/dashboards/empleados/status")
    assert res.status_code == 401


def test_status_empleado_plano_forbidden(
    client: TestClient, auth_client: TestClient, db_session: Session
) -> None:
    """Empleado plano: 403 (es endpoint de admin/contador)."""
    from tests.test_usuarios import _login_empleado

    _, token = _login_empleado(client, auth_client, db_session)
    res = client.get(
        "/dashboards/empleados/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_status_admin_lista_empleados(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Admin lista todos los empleados con sus métricas."""
    empresa = empresa_factory()
    e1 = empleado_factory(empresa=empresa, legajo="ST-1")
    empleado_factory(empresa=empresa, legajo="ST-2")
    _crear_fichada(db_session, e1, datetime.now(tz=timezone.utc))

    res = auth_client.get(f"/dashboards/empleados/status?id_empresa={empresa.id_empresa}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    item_e1 = next(i for i in data["items"] if i["legajo"] == "ST-1")
    assert item_e1["fichadas_ultimos_30_dias"] == 1
    assert item_e1["ultima_fichada"] is not None


def test_status_filtro_estado_inactivo(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Filtro ?estado=inactivo solo trae los inactivos."""
    empresa = empresa_factory()
    activo = empleado_factory(empresa=empresa, legajo="ACT-1")
    inactivo = empleado_factory(empresa=empresa, legajo="INA-1")
    inactivo.estado = enums.EstadoEntidad.INACTIVO
    db_session.commit()

    res = auth_client.get(
        f"/dashboards/empleados/status?id_empresa={empresa.id_empresa}&estado=inactivo"
    )
    assert res.status_code == 200
    data = res.json()
    legajos = {i["legajo"] for i in data["items"]}
    assert "INA-1" in legajos
    assert "ACT-1" not in legajos
    _ = activo  # silence linter


# ============================================================
# /dashboards/empleados/{id}
# ============================================================


def test_detalle_requiere_auth(client: TestClient) -> None:
    """Sin token: 401."""
    res = client.get("/dashboards/empleados/1")
    assert res.status_code == 401


def test_detalle_admin_devuelve_metricas_completas(
    auth_client: TestClient, db_session: Session, empresa_factory, empleado_factory
) -> None:
    """Admin: detalle completo con fichadas_por_mes y novedades_por_tipo."""
    empresa = empresa_factory()
    empleado = empleado_factory(empresa=empresa, legajo="DET-1")
    _crear_fichada(db_session, empleado, datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc))
    _crear_fichada(db_session, empleado, datetime(2026, 4, 5, 17, 0, tzinfo=timezone.utc))
    _crear_fichada(db_session, empleado, datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc))
    _crear_novedad(db_session, empleado)

    res = auth_client.get(f"/dashboards/empleados/{empleado.id_empleado}")
    assert res.status_code == 200
    data = res.json()
    assert data["fichadas_total"] == 3
    assert data["fichadas_por_mes"]["2026-04"] == 2
    assert data["fichadas_por_mes"]["2026-05"] == 1
    assert data["novedades_total"] == 1
    assert data["novedades_pendientes"] == 1
    assert data["novedades_por_tipo"]["vacaciones"] == 1


def test_detalle_no_encontrado(auth_client: TestClient) -> None:
    """ID inexistente: 404."""
    res = auth_client.get("/dashboards/empleados/999999")
    assert res.status_code == 404


def test_detalle_empleado_propio_permitido(
    client: TestClient,
    auth_client: TestClient,
    db_session: Session,
) -> None:
    """Un empleado puede ver SU propio detalle (200)."""
    from tests.test_usuarios import _login_empleado

    uid, token = _login_empleado(client, auth_client, db_session)
    usuario = db_session.get(Usuario, uid)
    assert usuario is not None
    id_emp = usuario.id_empleado
    res = client.get(
        f"/dashboards/empleados/{id_emp}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["id_empleado"] == id_emp


def test_detalle_empleado_ajeno_forbidden(
    client: TestClient,
    auth_client: TestClient,
    db_session: Session,
    empresa_factory,
    empleado_factory,
) -> None:
    """Empleado intentando ver detalle de OTRO empleado: 403."""
    from tests.test_usuarios import _login_empleado

    uid, token = _login_empleado(client, auth_client, db_session)
    # crear otro empleado en otra empresa
    otra = empresa_factory()
    otro_emp = empleado_factory(empresa=otra, legajo="OTH-1")
    res = client.get(
        f"/dashboards/empleados/{otro_emp.id_empleado}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    _ = uid
