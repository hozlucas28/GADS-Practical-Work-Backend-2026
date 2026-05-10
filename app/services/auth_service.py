from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.schemas.auth import RegisterFirstAdminRequest


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(*, id_usuario: int, rol: str) -> tuple[str, int]:
    expires_minutes = int(settings.jwt_expire_minutes)
    expires_in_seconds = expires_minutes * 60
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(id_usuario),
        "rol": rol,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if isinstance(token, bytes):  # pyjwt<2 fallback
        token = token.decode("utf-8")
    return token, expires_in_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise ValueError("Token expirado") from e
    except jwt.InvalidTokenError as e:
        raise ValueError("Token inválido") from e
    return claims


def autenticar(db: Session, nombre_usuario: str, contrasena: str) -> Usuario:
    stmt = select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    usuario = db.execute(stmt).scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if not verify_password(contrasena, usuario.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if usuario.estado != enums.EstadoEntidad.ACTIVO:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )
    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario)
    return usuario


def _existe_admin(db: Session) -> bool:
    stmt = select(Usuario).where(Usuario.rol == enums.Rol.ADMINISTRADOR).limit(1)
    return db.execute(stmt).scalar_one_or_none() is not None


def bootstrap_first_admin(db: Session, datos: RegisterFirstAdminRequest) -> Usuario:
    if _existe_admin(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un administrador",
        )
    hoy = date.today()
    empresa = db.execute(
        select(Empresa).where(Empresa.cuit == datos.empresa_cuit)
    ).scalar_one_or_none()
    if empresa is None:
        empresa = Empresa(
            razon_social=datos.empresa_razon_social,
            cuit=datos.empresa_cuit,
            email_contacto=str(datos.empresa_email),
            telefono_contacto=datos.empresa_telefono,
            direccion=datos.empresa_direccion,
            estado=enums.EstadoEntidad.ACTIVO,
            fecha_alta=hoy,
        )
        db.add(empresa)
        db.flush()

    empleado = Empleado(
        legajo=datos.legajo,
        nombre=datos.nombre,
        apellido=datos.apellido,
        dni=datos.dni,
        cuil=datos.cuil,
        fecha_ingreso=hoy,
        categoria_laboral=enums.CategoriaLaboral.ADMINISTRACION,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    db.add(empleado)
    db.flush()

    usuario = Usuario(
        nombre_usuario=datos.nombre_usuario,
        contrasena_hash=hash_password(datos.contrasena),
        email=str(datos.email),
        rol=enums.Rol.ADMINISTRADOR,
        estado=enums.EstadoEntidad.ACTIVO,
        ultimo_acceso=None,
        id_empleado=empleado.id_empleado,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def bootstrap_from_env(db: Session) -> None:
    requeridos = (
        settings.initial_admin_user,
        settings.initial_admin_password,
        settings.initial_admin_email,
        settings.initial_empresa_razon_social,
        settings.initial_empresa_cuit,
    )
    if any(v is None or v == "" for v in requeridos):
        return
    if _existe_admin(db):
        return
    datos = RegisterFirstAdminRequest(
        nombre_usuario=str(settings.initial_admin_user),
        contrasena=str(settings.initial_admin_password),
        email=str(settings.initial_admin_email),
        nombre="Admin",
        apellido="Inicial",
        dni="00000000",
        cuil="20-00000000-0",
        legajo="ADM-0001",
        empresa_razon_social=str(settings.initial_empresa_razon_social),
        empresa_cuit=str(settings.initial_empresa_cuit),
        empresa_email=str(settings.initial_admin_email),
        empresa_telefono="00000000",
        empresa_direccion="—",
    )
    try:
        bootstrap_first_admin(db, datos)
    except HTTPException:
        return
