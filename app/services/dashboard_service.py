from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import enums
from app.models.fichadas import Fichada
from app.models.novedades import Novedad, TipoNovedad
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario
from app.schemas.dashboard import (
    ConteoEntidad,
    ConteoFichadas,
    ConteoNovedades,
    ConteoUsuarios,
    EmpleadoStatus,
    EmpleadoStatusDetalle,
    EmpleadoStatusList,
    ResumenDashboard,
)


def _ahora() -> datetime:
    return datetime.now(tz=timezone.utc)


def _conteo_estado(db: Session, modelo: type, id_empresa: int | None = None) -> ConteoEntidad:
    stmt = select(modelo.estado, func.count()).group_by(modelo.estado)
    if id_empresa is not None and hasattr(modelo, "id_empresa"):
        stmt = stmt.where(modelo.id_empresa == id_empresa)
    rows = db.execute(stmt).all()
    activos = inactivos = 0
    for estado, count in rows:
        valor = estado.value if hasattr(estado, "value") else str(estado)
        if valor == enums.EstadoEntidad.ACTIVO.value:
            activos += count
        elif valor == enums.EstadoEntidad.INACTIVO.value:
            inactivos += count
    return ConteoEntidad(total=activos + inactivos, activos=activos, inactivos=inactivos)


def _empleados_por_atributo(
    db: Session, atributo: str, id_empresa: int | None
) -> dict[str, int]:
    col = getattr(Empleado, atributo)
    stmt = select(col, func.count()).group_by(col)
    if id_empresa is not None:
        stmt = stmt.where(Empleado.id_empresa == id_empresa)
    return {
        (k.value if hasattr(k, "value") else str(k)): v
        for k, v in db.execute(stmt).all()
    }


def _conteo_usuarios(db: Session, id_empresa: int | None) -> ConteoUsuarios:
    stmt = select(Usuario.rol, func.count()).group_by(Usuario.rol)
    if id_empresa is not None:
        stmt = stmt.join(Empleado, Empleado.id_empleado == Usuario.id_empleado).where(
            Empleado.id_empresa == id_empresa
        )
    rows = db.execute(stmt).all()
    por_rol = {(r.value if hasattr(r, "value") else str(r)): c for r, c in rows}
    return ConteoUsuarios(total=sum(por_rol.values()), por_rol=por_rol)


def _conteo_fichadas(db: Session, id_empresa: int | None) -> ConteoFichadas:
    base = select(func.count(Fichada.id_fichada))
    if id_empresa is not None:
        base = base.join(Empleado, Empleado.id_empleado == Fichada.id_empleado).where(
            Empleado.id_empresa == id_empresa
        )
    total = db.execute(base).scalar_one()

    ahora = _ahora()
    hace_7 = ahora - timedelta(days=7)
    hace_30 = ahora - timedelta(days=30)

    def _ventana(desde: datetime) -> int:
        stmt = select(func.count(Fichada.id_fichada)).where(Fichada.fecha_hora >= desde)
        if id_empresa is not None:
            stmt = stmt.join(
                Empleado, Empleado.id_empleado == Fichada.id_empleado
            ).where(Empleado.id_empresa == id_empresa)
        return int(db.execute(stmt).scalar_one() or 0)

    return ConteoFichadas(
        total=int(total or 0),
        ultimos_7_dias=_ventana(hace_7),
        ultimos_30_dias=_ventana(hace_30),
    )


def _conteo_novedades(db: Session, id_empresa: int | None) -> ConteoNovedades:
    stmt = select(Novedad.estado, func.count()).group_by(Novedad.estado)
    if id_empresa is not None:
        stmt = stmt.join(
            Empleado, Empleado.id_empleado == Novedad.id_empleado
        ).where(Empleado.id_empresa == id_empresa)
    rows = db.execute(stmt).all()
    counter: Counter[str] = Counter()
    for estado, count in rows:
        valor = estado.value if hasattr(estado, "value") else str(estado)
        counter[valor] += count
    return ConteoNovedades(
        total=sum(counter.values()),
        pendientes=counter.get(enums.EstadoNovedad.PENDIENTE.value, 0),
        aprobadas=counter.get(enums.EstadoNovedad.APROBADA.value, 0),
        rechazadas=counter.get(enums.EstadoNovedad.RECHAZADA.value, 0),
        anuladas=counter.get(enums.EstadoNovedad.ANULADA.value, 0),
    )


def resumen(
    db: Session, *, id_empresa: int | None, current: Usuario
) -> ResumenDashboard:
    """Resumen global o por empresa.

    Admin: ve todo o filtra por id_empresa.
    ContadorExterno: forzado a su empresa.
    """
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        empleado = current.empleado
        empresa_propia = getattr(empleado, "id_empresa", None) if empleado else None
        if empresa_propia is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Usuario sin empresa asociada"
            )
        if id_empresa is not None and id_empresa != empresa_propia:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "No tiene acceso a esa empresa"
            )
        id_empresa = empresa_propia

    return ResumenDashboard(
        id_empresa=id_empresa,
        empresas=_conteo_estado(db, Empresa, None if id_empresa is None else id_empresa)
        if id_empresa is None
        else _conteo_empresa_unica(db, id_empresa),
        empleados=_conteo_estado(db, Empleado, id_empresa),
        empleados_por_categoria=_empleados_por_atributo(
            db, "categoria_laboral", id_empresa
        ),
        empleados_por_jornada=_empleados_por_atributo(db, "tipo_jornada", id_empresa),
        usuarios=_conteo_usuarios(db, id_empresa),
        fichadas=_conteo_fichadas(db, id_empresa),
        novedades=_conteo_novedades(db, id_empresa),
    )


def _conteo_empresa_unica(db: Session, id_empresa: int) -> ConteoEntidad:
    """Cuenta 1/0 según una empresa específica (para responses scoped)."""
    empresa = db.get(Empresa, id_empresa)
    if empresa is None:
        return ConteoEntidad(total=0, activos=0, inactivos=0)
    activos = 1 if empresa.estado == enums.EstadoEntidad.ACTIVO else 0
    inactivos = 1 - activos
    return ConteoEntidad(total=1, activos=activos, inactivos=inactivos)


# ============================================================
# Por empleado
# ============================================================


def _ultima_fichada(db: Session, id_empleado: int) -> datetime | None:
    stmt = select(func.max(Fichada.fecha_hora)).where(
        Fichada.id_empleado == id_empleado
    )
    return db.execute(stmt).scalar_one_or_none()


def _primera_fichada(db: Session, id_empleado: int) -> datetime | None:
    stmt = select(func.min(Fichada.fecha_hora)).where(
        Fichada.id_empleado == id_empleado
    )
    return db.execute(stmt).scalar_one_or_none()


def _fichadas_count(
    db: Session, id_empleado: int, *, desde: datetime | None = None
) -> int:
    stmt = select(func.count(Fichada.id_fichada)).where(
        Fichada.id_empleado == id_empleado
    )
    if desde is not None:
        stmt = stmt.where(Fichada.fecha_hora >= desde)
    return int(db.execute(stmt).scalar_one() or 0)


def _novedades_pendientes(db: Session, id_empleado: int) -> int:
    stmt = select(func.count(Novedad.id_novedad)).where(
        Novedad.id_empleado == id_empleado,
        Novedad.estado == enums.EstadoNovedad.PENDIENTE,
    )
    return int(db.execute(stmt).scalar_one() or 0)


def _novedades_total(db: Session, id_empleado: int) -> int:
    stmt = select(func.count(Novedad.id_novedad)).where(
        Novedad.id_empleado == id_empleado
    )
    return int(db.execute(stmt).scalar_one() or 0)


def _novedades_por_tipo(db: Session, id_empleado: int) -> dict[str, int]:
    stmt = (
        select(TipoNovedad.nombre_tipo, func.count(Novedad.id_novedad))
        .join(TipoNovedad, TipoNovedad.id_tipo_novedad == Novedad.id_tipo_novedad)
        .where(Novedad.id_empleado == id_empleado)
        .group_by(TipoNovedad.nombre_tipo)
    )
    return {nombre: int(count) for nombre, count in db.execute(stmt).all()}


def _fichadas_por_mes(db: Session, id_empleado: int) -> dict[str, int]:
    stmt = select(Fichada.fecha_hora).where(Fichada.id_empleado == id_empleado)
    counter: Counter[str] = Counter()
    for (fh,) in db.execute(stmt).all():
        if fh is None:
            continue
        clave = fh.strftime("%Y-%m")
        counter[clave] += 1
    return dict(sorted(counter.items()))


def _scope_empresa_para(current: Usuario, id_empresa_target: int | None) -> bool:
    """Verifica si current puede ver datos de la empresa target. Admin: siempre."""
    if current.rol == enums.Rol.ADMINISTRADOR:
        return True
    empleado = current.empleado
    if empleado is None:
        return False
    return empleado.id_empresa == id_empresa_target


def listar_status(
    db: Session,
    *,
    id_empresa: int | None,
    estado: enums.EstadoEntidad | None,
    current: Usuario,
) -> EmpleadoStatusList:
    """Lista empleados con métricas de status. Admin/Contador."""
    if current.rol == enums.Rol.CONTADOR_EXTERNO:
        empleado = current.empleado
        propia = getattr(empleado, "id_empresa", None) if empleado else None
        if propia is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Usuario sin empresa asociada"
            )
        if id_empresa is not None and id_empresa != propia:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "No tiene acceso a esa empresa"
            )
        id_empresa = propia

    stmt = select(Empleado)
    if id_empresa is not None:
        stmt = stmt.where(Empleado.id_empresa == id_empresa)
    if estado is not None:
        stmt = stmt.where(Empleado.estado == estado)
    stmt = stmt.order_by(Empleado.id_empresa, Empleado.legajo)

    empleados = list(db.scalars(stmt).all())
    hace_30 = _ahora() - timedelta(days=30)

    items: list[EmpleadoStatus] = []
    for e in empleados:
        items.append(
            EmpleadoStatus(
                id_empleado=e.id_empleado,
                id_empresa=e.id_empresa,
                legajo=e.legajo,
                nombre=e.nombre,
                apellido=e.apellido,
                estado=e.estado,
                categoria_laboral=e.categoria_laboral,
                tipo_jornada=e.tipo_jornada,
                ultima_fichada=_ultima_fichada(db, e.id_empleado),
                fichadas_ultimos_30_dias=_fichadas_count(
                    db, e.id_empleado, desde=hace_30
                ),
                novedades_pendientes=_novedades_pendientes(db, e.id_empleado),
            )
        )

    return EmpleadoStatusList(total=len(items), items=items)


def detalle_empleado(
    db: Session, *, id_empleado: int, current: Usuario
) -> EmpleadoStatusDetalle:
    """Detalle completo de un empleado. Admin/Contador (mismo empresa) o el propio empleado."""
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empleado no encontrado")

    es_admin = current.rol == enums.Rol.ADMINISTRADOR
    es_contador = current.rol == enums.Rol.CONTADOR_EXTERNO
    es_propio = current.id_empleado == id_empleado

    if not es_admin and not es_propio:
        if es_contador:
            propia = getattr(current.empleado, "id_empresa", None) if current.empleado else None
            if propia != empleado.id_empresa:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, "No tiene acceso a este empleado"
                )
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Permiso insuficiente"
            )

    hace_30 = _ahora() - timedelta(days=30)

    return EmpleadoStatusDetalle(
        id_empleado=empleado.id_empleado,
        id_empresa=empleado.id_empresa,
        legajo=empleado.legajo,
        nombre=empleado.nombre,
        apellido=empleado.apellido,
        estado=empleado.estado,
        categoria_laboral=empleado.categoria_laboral,
        tipo_jornada=empleado.tipo_jornada,
        modalidad_fichada_habilitada=empleado.modalidad_fichada_habilitada,
        ultima_fichada=_ultima_fichada(db, id_empleado),
        primera_fichada=_primera_fichada(db, id_empleado),
        fichadas_total=_fichadas_count(db, id_empleado),
        fichadas_ultimos_30_dias=_fichadas_count(db, id_empleado, desde=hace_30),
        fichadas_por_mes=_fichadas_por_mes(db, id_empleado),
        novedades_total=_novedades_total(db, id_empleado),
        novedades_pendientes=_novedades_pendientes(db, id_empleado),
        novedades_por_tipo=_novedades_por_tipo(db, id_empleado),
    )
