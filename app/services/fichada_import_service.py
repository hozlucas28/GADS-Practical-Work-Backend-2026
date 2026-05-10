from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada, OrigenFichada
from app.models.novedades import Novedad, TipoNovedad
from app.models.organizacion import Empleado
from app.schemas.fichada import FichadaImportError, FichadaImportResponse

REQUIRED_HEADERS = {
    "Fecha",
    "Hora",
    "Forma Registro",
    "Tipo Registro",
    "Legajo",
    "Empleado",
    "Observaciones",
}

_FORMA_REGISTRO_MAP = {
    "local": enums.OrigenFichada.LOCAL,
    "manual": enums.OrigenFichada.MANUAL,
}

_TIPO_FICHADA_MAP = {
    "entrada": enums.TipoFichada.ENTRADA,
    "salida": enums.TipoFichada.SALIDA,
}

_JUSTIFICACION_RE = re.compile(
    r"^\s*JUSTIFICACION\s+(?:Entra|Sale)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def _resolver_origen(db: Session, valor: str) -> OrigenFichada:
    """Resuelve un record `OrigenFichada` por su nombre del CSV (Local/Manual)."""
    clave = (valor or "").strip().lower()
    if clave not in _FORMA_REGISTRO_MAP:
        raise ValueError(f"Forma Registro inválida: '{valor}'")
    enum_value = _FORMA_REGISTRO_MAP[clave]
    record = db.execute(
        select(OrigenFichada).where(OrigenFichada.nombre_origen == enum_value)
    ).scalar_one_or_none()
    if record is None:
        raise ValueError(f"Origen '{enum_value.value}' no inicializado en la base")
    return record


def _resolver_tipo_fichada(valor: str) -> enums.TipoFichada:
    """Resuelve el enum `TipoFichada` desde el CSV (Entrada/Salida)."""
    clave = (valor or "").strip().lower()
    if clave not in _TIPO_FICHADA_MAP:
        raise ValueError(f"Tipo Registro inválido: '{valor}'")
    return _TIPO_FICHADA_MAP[clave]


def _normalizar_nombre_tipo(nombre: str) -> str:
    """Normaliza un nombre de tipo de novedad: trim + lowercase + espacios → '_'."""
    return "_".join(nombre.strip().lower().split())


def _resolver_tipo_novedad(
    db: Session,
    nombre: str,
    cache: dict[str, TipoNovedad],
    creados: list[str],
) -> TipoNovedad:
    """Devuelve el `TipoNovedad` para `nombre` (lookup case-insensitive). Si no existe lo crea."""
    nombre_normalizado = _normalizar_nombre_tipo(nombre)
    if nombre_normalizado in cache:
        return cache[nombre_normalizado]

    existente = db.execute(
        select(TipoNovedad).where(
            func.lower(TipoNovedad.nombre_tipo) == nombre_normalizado
        )
    ).scalar_one_or_none()
    if existente is not None:
        cache[nombre_normalizado] = existente
        return existente

    nuevo = TipoNovedad(
        nombre_tipo=nombre_normalizado,
        descripcion=None,
        unidad_medida=enums.UnidadMedidaTipoNovedad.DIAS,
        requiere_justificativo=False,
        requiere_aprobacion=False,
        impacta_liquidacion=False,
    )
    db.add(nuevo)
    db.flush()
    cache[nombre_normalizado] = nuevo
    creados.append(nombre_normalizado)
    return nuevo


def _parse_justificacion(observacion: str | None) -> str | None:
    """Extrae el tipo de la observación, ej. 'JUSTIFICACION Entra : VACACIONES' → 'VACACIONES'."""
    if not observacion:
        return None
    match = _JUSTIFICACION_RE.match(observacion)
    if match is None:
        return None
    return match.group(1).strip()


def _asegurar_origenes(db: Session) -> dict[enums.OrigenFichada, OrigenFichada]:
    """Crea los records de `OrigenFichada` faltantes y devuelve un cache por enum."""
    existentes = db.execute(select(OrigenFichada)).scalars().all()
    cache: dict[enums.OrigenFichada, OrigenFichada] = {
        record.nombre_origen: record for record in existentes
    }
    for valor in enums.OrigenFichada:
        if valor not in cache:
            record = OrigenFichada(nombre_origen=valor, descripcion=None)
            db.add(record)
            cache[valor] = record
    db.flush()
    return cache


def importar_csv(
    *,
    db: Session,
    archivo_bytes: bytes,
    id_usuario_registrador: int,
    id_empresa_default: int,
    dry_run: bool,
    timezone_name: str,
) -> FichadaImportResponse:
    """Importa fichadas masivas desde un CSV con formato estándar."""
    try:
        contenido = archivo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"CSV no es UTF-8: {e}",
        ) from e

    reader = csv.DictReader(io.StringIO(contenido))
    if reader.fieldnames is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "CSV sin encabezados",
        )
    headers_normalizados = {(h or "").strip() for h in reader.fieldnames}
    faltantes = REQUIRED_HEADERS - headers_normalizados
    if faltantes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Faltan encabezados: {sorted(faltantes)}",
        )

    try:
        tz = ZoneInfo(timezone_name)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Timezone inválida: {timezone_name}",
        ) from e

    origenes_cache = _asegurar_origenes(db)
    origenes_existentes_nombres = [o.value for o in origenes_cache.keys()]

    empleados_cache: dict[tuple[int, str], Empleado] = {}
    tipos_novedad_cache: dict[str, TipoNovedad] = {}
    tipos_creados: list[str] = []

    errores: list[FichadaImportError] = []
    fichadas_creadas = 0
    novedades_creadas = 0
    total_filas = 0

    for indice, raw_row in enumerate(reader, start=2):
        total_filas += 1
        # Strip keys y valores, descartando None.
        row = {
            (k or "").strip(): (v.strip() if isinstance(v, str) else v)
            for k, v in raw_row.items()
            if k is not None
        }
        legajo_raw = row.get("Legajo") or None
        # Usamos un SAVEPOINT por fila para que un error individual no aborte
        # el batch entero (rollback solo de la fila fallada).
        savepoint = db.begin_nested()
        try:
            fecha_str = row.get("Fecha") or ""
            hora_str = row.get("Hora") or ""
            forma_registro = row.get("Forma Registro") or ""
            tipo_registro = row.get("Tipo Registro") or ""
            observacion = row.get("Observaciones") or None

            if not fecha_str or not hora_str:
                raise ValueError("Fecha u Hora vacía")
            try:
                fecha_dt = datetime.strptime(
                    f"{fecha_str} {hora_str}", "%d/%m/%y %H:%M"
                ).replace(tzinfo=tz)
            except ValueError as e:
                raise ValueError(f"Fecha/Hora inválida: {e}") from e

            origen = _resolver_origen(db, forma_registro)
            tipo_fichada = _resolver_tipo_fichada(tipo_registro)

            if not legajo_raw:
                raise ValueError("Legajo vacío")
            cache_key = (id_empresa_default, legajo_raw)
            empleado = empleados_cache.get(cache_key)
            if empleado is None:
                empleado = db.execute(
                    select(Empleado).where(
                        Empleado.id_empresa == id_empresa_default,
                        Empleado.legajo == legajo_raw,
                    )
                ).scalar_one_or_none()
                if empleado is None:
                    raise ValueError(
                        f"Empleado legajo {legajo_raw} no encontrado en empresa {id_empresa_default}"
                    )
                empleados_cache[cache_key] = empleado

            fichada = Fichada(
                fecha_hora=fecha_dt,
                tipo_fichada=tipo_fichada,
                fue_corregida=False,
                observacion=observacion,
                id_empleado=empleado.id_empleado,
                id_origen_fichada=origen.id_origen_fichada,
                id_usuario_registrador=id_usuario_registrador,
            )
            db.add(fichada)

            tipo_justif = _parse_justificacion(observacion)
            if tipo_justif:
                db.flush()  # asegura id_fichada
                tipo_novedad = _resolver_tipo_novedad(
                    db, tipo_justif, tipos_novedad_cache, tipos_creados
                )
                novedad = Novedad(
                    fecha_desde=fecha_dt.date(),
                    fecha_hasta=None,
                    cantidad=Decimal("1"),
                    estado=enums.EstadoNovedad.PENDIENTE,
                    origen=enums.OrigenNovedad.IMPORTACION,
                    observacion=observacion,
                    id_empleado=empleado.id_empleado,
                    id_tipo_novedad=tipo_novedad.id_tipo_novedad,
                    id_fichada=fichada.id_fichada,
                    id_usuario_creador=id_usuario_registrador,
                )
                db.add(novedad)
                novedades_creadas += 1

            savepoint.commit()
            fichadas_creadas += 1
        except Exception as e:  # noqa: BLE001
            # Errores de fila no abortan el batch — rollback al savepoint y seguir.
            savepoint.rollback()
            errores.append(
                FichadaImportError(
                    fila=indice,
                    motivo=str(e),
                    legajo=legajo_raw,
                )
            )

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return FichadaImportResponse(
        total_filas=total_filas,
        fichadas_creadas=fichadas_creadas,
        novedades_creadas=novedades_creadas,
        tipos_novedad_creados=tipos_creados,
        origenes_fichada_existentes=origenes_existentes_nombres,
        errores=errores,
        dry_run=dry_run,
    )


def importar_xlsx(
    *,
    db: Session,
    archivo_bytes: bytes,
    id_usuario_registrador: int,
    id_empresa_default: int,
    dry_run: bool,
    timezone_name: str,
) -> FichadaImportResponse:
    """Importa fichadas desde un .xlsx convirtiendo las filas a CSV dict y reutilizando la lógica."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(archivo_bytes), data_only=True)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Archivo xlsx inválido: {e}",
        ) from e

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Archivo xlsx vacío")

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    faltantes = REQUIRED_HEADERS - set(headers)
    if faltantes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Faltan columnas: {sorted(faltantes)}",
        )

    # Convertir a lista de dicts (mismo formato que csv.DictReader)
    buf_lines = [",".join(headers)]
    for row in rows[1:]:
        valores = [str(v).strip() if v is not None else "" for v in row]
        buf_lines.append(",".join(f'"{v}"' for v in valores))
    csv_bytes = "\n".join(buf_lines).encode("utf-8")

    return importar_csv(
        db=db,
        archivo_bytes=csv_bytes,
        id_usuario_registrador=id_usuario_registrador,
        id_empresa_default=id_empresa_default,
        dry_run=dry_run,
        timezone_name=timezone_name,
    )
