from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any

import openpyxl

from app.models import enums
from app.models.fichadas import Fichada
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _fmt(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def _to_csv(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_fmt(v) for v in row])
    return buf.getvalue()


EMPRESAS_HEADERS = (
    "id_empresa",
    "razon_social",
    "cuit",
    "email_contacto",
    "telefono_contacto",
    "direccion",
    "fecha_alta",
    "estado",
    "creado_en",
    "actualizado_en",
)

EMPLEADOS_HEADERS = (
    "id_empleado",
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
    "estado",
    "creado_en",
    "actualizado_en",
)

USUARIOS_HEADERS = (
    "id_usuario",
    "nombre_usuario",
    "email",
    "rol",
    "estado",
    "ultimo_acceso",
    "id_empleado",
    "creado_en",
    "actualizado_en",
)


def exportar_empresas(empresas: Iterable[Empresa]) -> str:
    rows = (
        (
            e.id_empresa,
            e.razon_social,
            e.cuit,
            e.email_contacto,
            e.telefono_contacto,
            e.direccion,
            e.fecha_alta,
            e.estado,
            e.creado_en,
            e.actualizado_en,
        )
        for e in empresas
    )
    return _to_csv(EMPRESAS_HEADERS, rows)


def exportar_empleados(empleados: Iterable[Empleado]) -> str:
    rows = (
        (
            e.id_empleado,
            e.id_empresa,
            e.legajo,
            e.nombre,
            e.apellido,
            e.dni,
            e.cuil,
            e.fecha_ingreso,
            e.categoria_laboral,
            e.tipo_jornada,
            e.modalidad_fichada_habilitada,
            e.estado,
            e.creado_en,
            e.actualizado_en,
        )
        for e in empleados
    )
    return _to_csv(EMPLEADOS_HEADERS, rows)


def exportar_usuarios(usuarios: Iterable[Usuario]) -> str:
    """Export sin contrasena_hash."""
    rows = (
        (
            u.id_usuario,
            u.nombre_usuario,
            u.email,
            u.rol,
            u.estado,
            u.ultimo_acceso,
            u.id_empleado,
            u.creado_en,
            u.actualizado_en,
        )
        for u in usuarios
    )
    return _to_csv(USUARIOS_HEADERS, rows)


# Headers del CSV de fichadas espejan el formato del import (round-trip).
FICHADAS_HEADERS = (
    "Fecha",
    "Hora",
    "Forma Registro",
    "Tipo Registro",
    "Legajo",
    "Empleado",
    "Observaciones",
)


_FORMA_REGISTRO_LABEL = {
    enums.OrigenFichada.LOCAL: "Local",
    enums.OrigenFichada.MANUAL: "Manual",
    enums.OrigenFichada.BIOMETRICO: "Biometrico",
    enums.OrigenFichada.QR: "QR",
    enums.OrigenFichada.API: "API",
    enums.OrigenFichada.EXCEL: "Excel",
}

_TIPO_REGISTRO_LABEL = {
    enums.TipoFichada.ENTRADA: "Entrada",
    enums.TipoFichada.SALIDA: "Salida",
}


def exportar_fichadas_xlsx(fichadas: Iterable[Fichada]) -> bytes:
    """Exporta fichadas al formato xlsx (mismas columnas que el CSV de import)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fichadas"
    ws.append(list(FICHADAS_HEADERS))
    for f in fichadas:
        empleado = f.empleado
        origen = f.origen
        forma = _FORMA_REGISTRO_LABEL.get(
            origen.nombre_origen if origen else None, ""
        )
        tipo_label = _TIPO_REGISTRO_LABEL.get(f.tipo_fichada, "")
        ws.append([
            f.fecha_hora.strftime("%d/%m/%y") if f.fecha_hora else "",
            f.fecha_hora.strftime("%H:%M") if f.fecha_hora else "",
            forma,
            tipo_label,
            empleado.legajo if empleado else "",
            f"{empleado.nombre} {empleado.apellido}" if empleado else "",
            f.observacion or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def exportar_fichadas(fichadas: Iterable[Fichada]) -> str:
    """Exporta fichadas al mismo formato que el import (round-trip).

    Asume que los relationships ``empleado`` y ``origen`` están cargados (eager-load
    en el DAO o lazy con la sesión activa). Cada Fichada produce 1 fila.
    """

    def _filas() -> Iterable[Sequence[Any]]:
        for f in fichadas:
            empleado = f.empleado
            origen = f.origen
            forma = _FORMA_REGISTRO_LABEL.get(
                origen.nombre_origen if origen else None, ""
            )
            tipo_label = _TIPO_REGISTRO_LABEL.get(f.tipo_fichada, "")
            yield (
                f.fecha_hora.strftime("%d/%m/%y") if f.fecha_hora else "",
                f.fecha_hora.strftime("%H:%M") if f.fecha_hora else "",
                forma,
                tipo_label,
                empleado.legajo if empleado else "",
                f"{empleado.nombre} {empleado.apellido}" if empleado else "",
                f.observacion or "",
            )

    return _to_csv(FICHADAS_HEADERS, _filas())
