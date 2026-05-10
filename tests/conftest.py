from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registra metadatos
from app.api import deps as api_deps
from app.main import app
from app.models import enums
from app.models.base import Base
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.services import auth_service

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[api_deps.get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


ADMIN_PASSWORD_DEFAULT = "admin1234"


@pytest.fixture
def empresa_factory(db_session: Session) -> Callable[..., Empresa]:
    def _make(
        *,
        razon_social: str | None = None,
        cuit: str | None = None,
        email_contacto: str = "empresa@test.com",
        telefono_contacto: str = "00000000",
        direccion: str = "Calle 1",
        estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO,
        fecha_alta: date | None = None,
    ) -> Empresa:
        sufijo = uuid4().hex[:8]
        empresa = Empresa(
            razon_social=razon_social or f"Empresa {sufijo}",
            cuit=cuit or f"30-{sufijo}-1",
            email_contacto=email_contacto,
            telefono_contacto=telefono_contacto,
            direccion=direccion,
            estado=estado,
            fecha_alta=fecha_alta or date.today(),
        )
        db_session.add(empresa)
        db_session.commit()
        db_session.refresh(empresa)
        return empresa

    return _make


@pytest.fixture
def empleado_factory(
    db_session: Session, empresa_factory: Callable[..., Empresa]
) -> Callable[..., Empleado]:
    def _make(
        *,
        empresa: Empresa | None = None,
        legajo: str | None = None,
        nombre: str = "Nombre",
        apellido: str = "Apellido",
        dni: str | None = None,
        cuil: str | None = None,
        fecha_ingreso: date | None = None,
        categoria_laboral: enums.CategoriaLaboral = enums.CategoriaLaboral.ADMINISTRACION,
        tipo_jornada: enums.TipoJornada = enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada: enums.ModalidadFichada = enums.ModalidadFichada.HABILITADA,
        estado: enums.EstadoEntidad = enums.EstadoEntidad.ACTIVO,
    ) -> Empleado:
        emp = empresa or empresa_factory()
        sufijo = uuid4().hex[:8]
        empleado = Empleado(
            legajo=legajo or f"L-{sufijo}",
            nombre=nombre,
            apellido=apellido,
            dni=dni or sufijo,
            cuil=cuil or f"20-{sufijo}-1",
            fecha_ingreso=fecha_ingreso or date.today(),
            categoria_laboral=categoria_laboral,
            tipo_jornada=tipo_jornada,
            modalidad_fichada_habilitada=modalidad_fichada_habilitada,
            estado=estado,
            id_empresa=emp.id_empresa,
        )
        db_session.add(empleado)
        db_session.commit()
        db_session.refresh(empleado)
        return empleado

    return _make


@pytest.fixture
def admin_user(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> Usuario:
    empleado = empleado_factory()
    sufijo = uuid4().hex[:6]
    usuario = Usuario(
        nombre_usuario=f"admin_{sufijo}",
        contrasena_hash=auth_service.hash_password(ADMIN_PASSWORD_DEFAULT),
        email=f"admin_{sufijo}@test.com",
        rol=enums.Rol.ADMINISTRADOR,
        estado=enums.EstadoEntidad.ACTIVO,
        ultimo_acceso=None,
        id_empleado=empleado.id_empleado,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def auth_client(client: TestClient, admin_user: Usuario) -> TestClient:
    res = client.post(
        "/auth/login",
        json={
            "nombre_usuario": admin_user.nombre_usuario,
            "contrasena": ADMIN_PASSWORD_DEFAULT,
        },
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
