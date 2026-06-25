#!/usr/bin/env python3
"""
Seed de desarrollo: empresa Nero IT y empleados/usuarios indicados.

Uso desde la raíz del proyecto:
  python scripts/crear_usuario_admin_alejandro.py

Recrear tablas (borra todos los datos — usar con precaución en producción):
  python scripts/crear_usuario_admin_alejandro.py --reset-db

Apuntar a una base de datos de Render (u otro PostgreSQL):
  GADS_DATABASE_URL="postgresql+psycopg2://user:pass@host/dbname" \\
    python scripts/crear_usuario_admin_alejandro.py

Credenciales:
  - Alejandro Mabbdet: admin / admin (email admin@local.dev), rol Administrador
  - Alan Mangano y Lucas Hoz: contadores externos (rol ContadorExterno)
  - Resto empleados: primera inicial + apellido en minúsculas (usuario y contraseña iguales)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, init_db
from app.models import enums as enums_models
from app.models.base import Base
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Empresa única
EMPRESA_RAZON_SOCIAL = "Nero IT"
EMPRESA_CUIT = "30-71888999-1"
EMPRESA_EMAIL = "contacto@neroit.local"
EMPRESA_TEL = "011-4000-0000"
EMPRESA_DIR = "Buenos Aires, Argentina"


# (nombre, apellido, nombre_usuario, contraseña, email, rol, legajo, dni, cuil)
# dni/cuil sintéticos únicos por persona
PERSONAS: list[tuple[str, str, str, str, str, enums_models.Rol, str, str, str]] = [
    (
        "Alejandro",
        "Mabbdet",
        "admin",
        "admin",
        "admin@local.dev",
        enums_models.Rol.ADMINISTRADOR,
        "NERO-001",
        "35111222",
        "20-35111222-4",
    ),
    (
        "Alan",
        "Mangano",
        "amangano",
        "amangano",
        "amangano@nero.local.dev",
        enums_models.Rol.CONTADOR_EXTERNO,
        "NERO-002",
        "36222333",
        "20-36222333-1",
    ),
    (
        "Lucas",
        "Hoz",
        "lhoz",
        "lhoz",
        "lhoz@nero.local.dev",
        enums_models.Rol.CONTADOR_EXTERNO,
        "NERO-003",
        "37333444",
        "20-37333444-8",
    ),
    (
        "Leo",
        "De Luca",
        "ldeluca",
        "ldeluca",
        "ldeluca@nero.local.dev",
        enums_models.Rol.EMPLEADO,
        "NERO-004",
        "38444555",
        "20-38444555-5",
    ),
    (
        "Tiago",
        "Giannotti",
        "tgiannotti",
        "tgiannotti",
        "tgiannotti@nero.local.dev",
        enums_models.Rol.EMPLEADO,
        "NERO-005",
        "39555666",
        "20-39555666-2",
    ),
    (
        "Valentin",
        "Massa",
        "vmassa",
        "vmassa",
        "vmassa@nero.local.dev",
        enums_models.Rol.EMPLEADO,
        "NERO-006",
        "40666777",
        "20-40666777-9",
    ),
    (
        "Agustin",
        "Passa",
        "apassa",
        "apassa",
        "apassa@nero.local.dev",
        enums_models.Rol.EMPLEADO,
        "NERO-007",
        "41777888",
        "20-41777888-6",
    ),
]


def _obtener_o_crear_empresa_nero(db: Session) -> Empresa:
    stmt = select(Empresa).where(Empresa.cuit == EMPRESA_CUIT)
    emp = db.execute(stmt).scalar_one_or_none()
    if emp is not None:
        return emp
    emp = Empresa(
        razon_social=EMPRESA_RAZON_SOCIAL,
        cuit=EMPRESA_CUIT,
        email_contacto=EMPRESA_EMAIL,
        telefono_contacto=EMPRESA_TEL,
        direccion=EMPRESA_DIR,
        estado=enums_models.EstadoEntidad.ACTIVO,
        fecha_alta=date.today(),
    )
    db.add(emp)
    db.flush()
    return emp


def _categoria_laboral(rol_enum: enums_models.Rol) -> enums_models.CategoriaLaboral:
    if rol_enum == enums_models.Rol.ADMINISTRADOR:
        return enums_models.CategoriaLaboral.ADMINISTRACION
    if rol_enum == enums_models.Rol.CONTADOR_EXTERNO:
        return enums_models.CategoriaLaboral.CONTADURIA
    return enums_models.CategoriaLaboral.OPERACIONES


def run_seed(*, reset_db: bool = False) -> tuple[int, int]:
    """Ejecuta el seed. Devuelve (creados, omitidos).

    Reutilizable desde tests. Compatible con SQLite (dev) y PostgreSQL (Render).
    """

    import app.models  # noqa: F401 — registra tablas en Base.metadata

    if reset_db:
        Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    creados = 0
    omitidos = 0
    try:
        empresa = _obtener_o_crear_empresa_nero(db)

        for (
            nombre,
            apellido,
            nombre_usuario,
            contrasena,
            email,
            rol_enum,
            legajo,
            dni,
            cuil,
        ) in PERSONAS:
            if db.execute(
                select(Usuario).where(Usuario.email == email)
            ).scalar_one_or_none():
                print(f"  Ya existe usuario con email {email}; se omite.")
                omitidos += 1
                continue
            if db.execute(
                select(Empleado).where(
                    Empleado.id_empresa == empresa.id_empresa,
                    Empleado.legajo == legajo,
                )
            ).scalar_one_or_none():
                print(f"  Ya existe empleado legajo {legajo}; se omite.")
                omitidos += 1
                continue

            empleado = Empleado(
                legajo=legajo,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                cuil=cuil,
                fecha_ingreso=date.today(),
                categoria_laboral=_categoria_laboral(rol_enum),
                tipo_jornada=enums_models.TipoJornada.COMPLETA,
                modalidad_fichada_habilitada=enums_models.ModalidadFichada.HABILITADA,
                estado=enums_models.EstadoEntidad.ACTIVO,
                id_empresa=empresa.id_empresa,
            )
            db.add(empleado)
            db.flush()

            usuario = Usuario(
                nombre_usuario=nombre_usuario,
                contrasena_hash=_hash_password(contrasena),
                email=email,
                rol=rol_enum,
                estado=enums_models.EstadoEntidad.ACTIVO,
                ultimo_acceso=None,
                id_empleado=empleado.id_empleado,
            )
            db.add(usuario)
            creados += 1
            print(f"  Creado: {nombre} {apellido} -> {nombre_usuario}")

        db.commit()
        print(f"Empresa: {EMPRESA_RAZON_SOCIAL} (CUIT {EMPRESA_CUIT})")
        print(f"Usuarios nuevos: {creados}, omitidos (ya existian): {omitidos}")
        return creados, omitidos
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Nero IT + usuarios de desarrollo")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Elimina todas las tablas y las recrea (solo desarrollo; borra todos los datos).",
    )
    args = parser.parse_args()
    run_seed(reset_db=args.reset_db)


if __name__ == "__main__":
    main()
