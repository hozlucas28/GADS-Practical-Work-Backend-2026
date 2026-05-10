"""Imports masivos via CSV para Empresa, Empleado y Usuario.

Cada fila se procesa en su propio SAVEPOINT: errores aislados no abortan el batch.
Al final, ``commit`` o ``rollback`` global según ``dry_run``.
"""
from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import enums
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.schemas.import_csv import ImportRowError, ImportSummary
from app.services.auth_service import hash_password


def _read_dict_rows(archivo_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Decodifica UTF-8 (con BOM tolerado), strip de keys/values, devuelve headers + filas."""
    texto = archivo_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(texto))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    filas: list[dict[str, str]] = []
    for row in reader:
        clean = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
        filas.append(clean)
    return headers, filas


def _ensure_headers(actuales: list[str], requeridos: set[str]) -> None:
    faltan = requeridos - set(actuales)
    if faltan:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Encabezados faltantes: {sorted(faltan)}",
        )


def _parse_date(valor: str, campo: str) -> date:
    try:
        # ISO primero (formato del export); fallback a formato d/m/Y.
        try:
            return date.fromisoformat(valor)
        except ValueError:
            return datetime.strptime(valor, "%d/%m/%Y").date()
    except Exception as e:
        raise ValueError(f"{campo} con formato inválido: '{valor}'") from e


def _parse_enum(valor: str, enum_cls: type, campo: str) -> Any:
    if not valor:
        raise ValueError(f"{campo} vacío")
    for member in enum_cls:
        if member.value == valor:
            return member
    raise ValueError(
        f"{campo}='{valor}' inválido. Valores permitidos: {[m.value for m in enum_cls]}"
    )


def _ejecutar_import(
    db: Session,
    filas: list[dict[str, str]],
    procesar: Callable[[Session, dict[str, str]], bool],
    *,
    dry_run: bool,
) -> ImportSummary:
    """Recorre filas, llama ``procesar`` por fila dentro de SAVEPOINT.

    ``procesar`` devuelve ``True`` si creó algo, ``False`` si omitió (ya existe).
    Levanta ``ValueError`` con motivo claro o ``IntegrityError``.

    Importante: abrimos una transacción explícita afuera. Si solo usáramos
    ``begin_nested`` sin ``begin``, en SA 2.0 al RELEASE-ar el savepoint la
    transacción autobegun queda en un estado donde ``rollback()`` no deshace los
    INSERT. Con ``begin()`` explícito el ``rollback`` final sí los deshace.
    """
    creados = 0
    omitidos = 0
    errores: list[ImportRowError] = []

    if not db.in_transaction():
        db.begin()

    for idx, fila in enumerate(filas, start=2):  # 1 es header
        try:
            with db.begin_nested():
                creado = procesar(db, fila)
            if creado:
                creados += 1
            else:
                omitidos += 1
        except (ValueError, IntegrityError) as e:
            motivo = str(e.__cause__ or e) if isinstance(e, IntegrityError) else str(e)
            errores.append(ImportRowError(fila=idx, motivo=motivo))
        except Exception as e:  # noqa: BLE001
            errores.append(ImportRowError(fila=idx, motivo=f"error inesperado: {e}"))

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return ImportSummary(
        total_filas=len(filas),
        creados=creados,
        omitidos=omitidos,
        errores=errores,
        dry_run=dry_run,
    )


# ============================================================
# Empresas
# ============================================================

EMPRESAS_REQ = {
    "razon_social",
    "cuit",
    "email_contacto",
    "telefono_contacto",
    "direccion",
    "fecha_alta",
}


def _procesar_empresa(db: Session, fila: dict[str, str]) -> bool:
    cuit = fila.get("cuit") or ""
    if not cuit:
        raise ValueError("cuit vacío")
    existente = db.execute(
        select(Empresa).where(Empresa.cuit == cuit)
    ).scalar_one_or_none()
    if existente is not None:
        return False  # omitido
    empresa = Empresa(
        razon_social=fila.get("razon_social") or "",
        cuit=cuit,
        email_contacto=fila.get("email_contacto") or "",
        telefono_contacto=fila.get("telefono_contacto") or "",
        direccion=fila.get("direccion") or "",
        fecha_alta=_parse_date(fila.get("fecha_alta") or "", "fecha_alta"),
        estado=_parse_enum(
            fila.get("estado") or enums.EstadoEntidad.ACTIVO.value,
            enums.EstadoEntidad,
            "estado",
        ),
    )
    db.add(empresa)
    return True


def importar_empresas(
    *, db: Session, archivo_bytes: bytes, dry_run: bool
) -> ImportSummary:
    headers, filas = _read_dict_rows(archivo_bytes)
    _ensure_headers(headers, EMPRESAS_REQ)
    return _ejecutar_import(db, filas, _procesar_empresa, dry_run=dry_run)


# ============================================================
# Empleados
# ============================================================

EMPLEADOS_REQ = {
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
}


def _procesar_empleado(db: Session, fila: dict[str, str]) -> bool:
    id_empresa_str = fila.get("id_empresa") or ""
    if not id_empresa_str:
        raise ValueError("id_empresa vacío")
    try:
        id_empresa = int(id_empresa_str)
    except ValueError as e:
        raise ValueError(f"id_empresa inválido: '{id_empresa_str}'") from e

    if db.get(Empresa, id_empresa) is None:
        raise ValueError(f"id_empresa={id_empresa} no existe")

    legajo = fila.get("legajo") or ""
    if not legajo:
        raise ValueError("legajo vacío")

    existente = db.execute(
        select(Empleado).where(
            Empleado.id_empresa == id_empresa, Empleado.legajo == legajo
        )
    ).scalar_one_or_none()
    if existente is not None:
        return False  # omitido

    empleado = Empleado(
        legajo=legajo,
        nombre=fila.get("nombre") or "",
        apellido=fila.get("apellido") or "",
        dni=fila.get("dni") or "",
        cuil=fila.get("cuil") or "",
        fecha_ingreso=_parse_date(fila.get("fecha_ingreso") or "", "fecha_ingreso"),
        categoria_laboral=_parse_enum(
            fila.get("categoria_laboral") or "",
            enums.CategoriaLaboral,
            "categoria_laboral",
        ),
        tipo_jornada=_parse_enum(
            fila.get("tipo_jornada") or "", enums.TipoJornada, "tipo_jornada"
        ),
        modalidad_fichada_habilitada=_parse_enum(
            fila.get("modalidad_fichada_habilitada") or "",
            enums.ModalidadFichada,
            "modalidad_fichada_habilitada",
        ),
        estado=_parse_enum(
            fila.get("estado") or enums.EstadoEntidad.ACTIVO.value,
            enums.EstadoEntidad,
            "estado",
        ),
        id_empresa=id_empresa,
    )
    db.add(empleado)
    return True


def importar_empleados(
    *, db: Session, archivo_bytes: bytes, dry_run: bool
) -> ImportSummary:
    headers, filas = _read_dict_rows(archivo_bytes)
    _ensure_headers(headers, EMPLEADOS_REQ)
    return _ejecutar_import(db, filas, _procesar_empleado, dry_run=dry_run)


# ============================================================
# Usuarios
# ============================================================

USUARIOS_REQ = {"nombre_usuario", "contrasena", "email", "rol", "id_empleado"}


def _procesar_usuario(db: Session, fila: dict[str, str]) -> bool:
    nombre_usuario = fila.get("nombre_usuario") or ""
    if not nombre_usuario:
        raise ValueError("nombre_usuario vacío")
    contrasena = fila.get("contrasena") or ""
    if len(contrasena) < 8:
        raise ValueError("contrasena debe tener al menos 8 caracteres")

    id_empleado_str = fila.get("id_empleado") or ""
    if not id_empleado_str:
        raise ValueError("id_empleado vacío")
    try:
        id_empleado = int(id_empleado_str)
    except ValueError as e:
        raise ValueError(f"id_empleado inválido: '{id_empleado_str}'") from e

    if db.get(Empleado, id_empleado) is None:
        raise ValueError(f"id_empleado={id_empleado} no existe")

    existente = db.execute(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    ).scalar_one_or_none()
    if existente is not None:
        return False  # omitido

    usuario = Usuario(
        nombre_usuario=nombre_usuario,
        contrasena_hash=hash_password(contrasena),
        email=fila.get("email") or "",
        rol=_parse_enum(fila.get("rol") or "", enums.Rol, "rol"),
        estado=_parse_enum(
            fila.get("estado") or enums.EstadoEntidad.ACTIVO.value,
            enums.EstadoEntidad,
            "estado",
        ),
        id_empleado=id_empleado,
    )
    db.add(usuario)
    return True


def importar_usuarios(
    *, db: Session, archivo_bytes: bytes, dry_run: bool
) -> ImportSummary:
    headers, filas = _read_dict_rows(archivo_bytes)
    _ensure_headers(headers, USUARIOS_REQ)
    return _ejecutar_import(db, filas, _procesar_usuario, dry_run=dry_run)
