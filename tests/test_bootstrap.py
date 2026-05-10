from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import enums
from app.models.organizacion import Empresa
from app.models.seguridad import Usuario
from app.services import auth_service


def _contar_admins(db: Session) -> int:
    stmt = select(Usuario).where(Usuario.rol == enums.Rol.ADMINISTRADOR)
    return len(db.execute(stmt).scalars().all())


def test_bootstrap_from_env_crea_admin(
    db_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "initial_admin_user", "boot_admin")
    monkeypatch.setattr(settings, "initial_admin_password", "boot_secret")
    monkeypatch.setattr(settings, "initial_admin_email", "boot@test.com")
    monkeypatch.setattr(settings, "initial_empresa_razon_social", "Boot SA")
    monkeypatch.setattr(settings, "initial_empresa_cuit", "30-77777777-7")

    assert _contar_admins(db_session) == 0
    auth_service.bootstrap_from_env(db_session)
    assert _contar_admins(db_session) == 1

    stmt = select(Usuario).where(Usuario.nombre_usuario == "boot_admin")
    creado = db_session.execute(stmt).scalar_one()
    assert creado.rol == enums.Rol.ADMINISTRADOR
    assert creado.estado == enums.EstadoEntidad.ACTIVO


def test_bootstrap_from_env_no_duplica(
    db_session: Session, admin_user: Usuario, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "initial_admin_user", "otro_boot")
    monkeypatch.setattr(settings, "initial_admin_password", "boot_secret")
    monkeypatch.setattr(settings, "initial_admin_email", "boot2@test.com")
    monkeypatch.setattr(settings, "initial_empresa_razon_social", "Boot SA")
    monkeypatch.setattr(settings, "initial_empresa_cuit", "30-66666666-6")

    antes = _contar_admins(db_session)
    auth_service.bootstrap_from_env(db_session)
    assert _contar_admins(db_session) == antes


def test_bootstrap_from_env_silencioso_sin_envs(
    db_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "initial_admin_user", None)
    monkeypatch.setattr(settings, "initial_admin_password", None)
    monkeypatch.setattr(settings, "initial_admin_email", None)
    monkeypatch.setattr(settings, "initial_empresa_razon_social", None)
    monkeypatch.setattr(settings, "initial_empresa_cuit", None)

    auth_service.bootstrap_from_env(db_session)
    assert _contar_admins(db_session) == 0


def test_bootstrap_from_env_empresa_coherente(
    db_session: Session, monkeypatch
) -> None:
    """La empresa creada en bootstrap usa los datos del env."""
    monkeypatch.setattr(settings, "initial_admin_user", "boot_admin_e")
    monkeypatch.setattr(settings, "initial_admin_password", "boot_secret")
    monkeypatch.setattr(settings, "initial_admin_email", "boot_e@test.com")
    monkeypatch.setattr(
        settings, "initial_empresa_razon_social", "Empresa BootEnv SA"
    )
    monkeypatch.setattr(settings, "initial_empresa_cuit", "30-12121212-1")

    auth_service.bootstrap_from_env(db_session)
    stmt = select(Empresa).where(Empresa.cuit == "30-12121212-1")
    empresa = db_session.execute(stmt).scalar_one()
    assert empresa.razon_social == "Empresa BootEnv SA"


def test_bootstrap_from_env_silencioso_si_falta_uno(
    db_session: Session, monkeypatch
) -> None:
    """Si UNO de los envs falta, no crea ni admin ni empresa."""
    monkeypatch.setattr(settings, "initial_admin_user", "boot_admin_x")
    monkeypatch.setattr(settings, "initial_admin_password", "boot_secret")
    monkeypatch.setattr(settings, "initial_admin_email", "boot_x@test.com")
    monkeypatch.setattr(
        settings, "initial_empresa_razon_social", "Empresa X"
    )
    # falta initial_empresa_cuit
    monkeypatch.setattr(settings, "initial_empresa_cuit", None)

    auth_service.bootstrap_from_env(db_session)
    assert _contar_admins(db_session) == 0
    assert (
        db_session.execute(select(Empresa)).scalars().first() is None
    )
