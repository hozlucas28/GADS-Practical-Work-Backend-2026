"""Carga inicial idempotente de datos demo.

Corre al arrancar si la DB está vacía. Datos basados en el CSV de fichadas real
de la empresa "Nero IT" (empleados legajo 10, 12 y 14).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada, OrigenFichada
from app.models.horarios import Horario
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario

_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def cargar_seed_si_vacio(db: Session) -> None:
    """No hace nada si ya hay datos (idempotente)."""
    try:
        if db.execute(select(Empresa).limit(1)).scalar_one_or_none() is not None:
            return
    except Exception:  # noqa: BLE001 — tabla aún no existe (test env sin init_db)
        return

    # --- Empresa ---
    empresa = Empresa(
        razon_social="Nero IT",
        cuit="30-71888999-1",
        email_contacto="contacto@neroit.local",
        telefono_contacto="011-4000-0000",
        direccion="Buenos Aires, Argentina",
        estado=enums.EstadoEntidad.ACTIVO,
        fecha_alta=date(2024, 1, 1),
    )
    db.add(empresa)
    db.flush()

    # --- Orígenes de fichada ---
    origenes: dict[enums.OrigenFichada, OrigenFichada] = {}
    for valor, desc in [
        (enums.OrigenFichada.LOCAL, "Terminal local in-situ"),
        (enums.OrigenFichada.MANUAL, "Carga manual por operador"),
        (enums.OrigenFichada.EXCEL, "Importación desde Excel/CSV"),
    ]:
        origen = OrigenFichada(nombre_origen=valor, descripcion=desc)
        db.add(origen)
        origenes[valor] = origen
    db.flush()

    # --- Empleados (del CSV) ---
    empleados_data = [
        ("10", "Azucena", "Picaflor", "40100010", "27-40100010-5"),
        ("12", "Cachito", "Bellavista", "40100012", "20-40100012-1"),
        ("14", "Gabriel", "Marquez", "40100014", "20-40100014-8"),
    ]
    empleados: list[Empleado] = []
    for legajo, nombre, apellido, dni, cuil in empleados_data:
        emp = Empleado(
            legajo=legajo,
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            cuil=cuil,
            fecha_ingreso=date(2024, 1, 1),
            categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
            tipo_jornada=enums.TipoJornada.COMPLETA,
            modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
            estado=enums.EstadoEntidad.ACTIVO,
            id_empresa=empresa.id_empresa,
        )
        db.add(emp)
        empleados.append(emp)
    db.flush()

    # --- Usuarios ---
    users_data = [
        ("apicaflor", "apicaflor@nero.local.dev"),
        ("cbellavista", "cbellavista@nero.local.dev"),
        ("gmarquez", "gmarquez@nero.local.dev"),
    ]
    usuarios: list[Usuario] = []
    for (username, email), emp in zip(users_data, empleados):
        u = Usuario(
            nombre_usuario=username,
            contrasena_hash=_hash(username),
            email=email,
            rol=enums.Rol.EMPLEADO,
            estado=enums.EstadoEntidad.ACTIVO,
            ultimo_acceso=None,
            id_empleado=emp.id_empleado,
        )
        db.add(u)
        usuarios.append(u)
    db.flush()

    # --- Horarios ---
    horarios_data = [
        ("Mañana 8-14", enums.TipoHorario.FIJO, (8, 0), (14, 0), Decimal("6.00"), "sabado,domingo"),
        ("Tarde 14-18", enums.TipoHorario.FIJO, (14, 0), (18, 0), Decimal("4.00"), "sabado,domingo"),
        ("Completo 8-17", enums.TipoHorario.FIJO, (8, 0), (17, 0), Decimal("9.00"), "sabado,domingo"),
    ]
    from datetime import time
    for nombre, tipo, entrada, salida, horas, descanso in horarios_data:
        h = Horario(
            nombre_horario=nombre,
            tipo_horario=tipo,
            hora_entrada_esperada=time(*entrada),
            hora_salida_esperada=time(*salida),
            cantidad_horas_objetivo=horas,
            banda_horaria_inicio=time(entrada[0] - 1 if entrada[0] > 0 else 0, 0),
            banda_horaria_fin=time(salida[0] + 1 if salida[0] < 23 else 23, 0),
            tolerancia_entrada_minutos=15,
            tolerancia_salida_minutos=10,
            tiempo_minimo_descanso_minutos=30,
            umbral_horas_extra_minutos=15,
            dias_descanso_semanal=descanso,
            estado=enums.EstadoEntidad.ACTIVO,
        )
        db.add(h)
    db.flush()

    # --- Fichadas reales del CSV (primeras 3 entradas de Azucena Picaflor legajo 10) ---
    fichadas_data = [
        (datetime(2026, 4, 1, 7, 59, tzinfo=_TZ), enums.TipoFichada.ENTRADA),
        (datetime(2026, 4, 1, 14, 0, tzinfo=_TZ), enums.TipoFichada.SALIDA),
        (datetime(2026, 4, 1, 15, 7, tzinfo=_TZ), enums.TipoFichada.ENTRADA),
    ]
    id_usuario_reg = usuarios[0].id_usuario
    id_empleado_azucena = empleados[0].id_empleado
    id_origen_local = origenes[enums.OrigenFichada.LOCAL].id_origen_fichada
    for ts, tipo in fichadas_data:
        f = Fichada(
            fecha_hora=ts,
            tipo_fichada=tipo,
            fue_corregida=False,
            observacion=None,
            id_empleado=id_empleado_azucena,
            id_origen_fichada=id_origen_local,
            id_usuario_registrador=id_usuario_reg,
        )
        db.add(f)

    db.commit()
