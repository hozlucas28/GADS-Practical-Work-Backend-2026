from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import enums
from app.models.base import Base
from app.models.fichadas import Fichada
from app.models.novedades import Novedad, TipoNovedad
from app.models.operaciones import (
    Auditoria,
    CierreMensual,
    DiasEspeciales,
    Exportacion,
)
from app.models.organizacion import Empleado, Empresa
from app.models.seguridad import Usuario


def _hash() -> str:
    return "$2b$12$abcdefghijklmnopqrstuv"


def _crear_usuario(
    db: Session,
    empleado: Empleado,
    *,
    nombre_usuario: str = "user1",
    email: str = "user1@test.com",
) -> Usuario:
    usuario = Usuario(
        nombre_usuario=nombre_usuario,
        contrasena_hash=_hash(),
        email=email,
        rol=enums.Rol.EMPLEADO,
        estado=enums.EstadoEntidad.ACTIVO,
        ultimo_acceso=None,
        id_empleado=empleado.id_empleado,
    )
    db.add(usuario)
    db.flush()
    return usuario


def test_usuario_nombre_unico(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    emp1 = empleado_factory()
    emp2 = empleado_factory()
    _crear_usuario(
        db_session, emp1, nombre_usuario="repetido", email="r1@test.com"
    )
    db_session.commit()
    with pytest.raises(IntegrityError):
        _crear_usuario(
            db_session, emp2, nombre_usuario="repetido", email="r2@test.com"
        )
    db_session.rollback()


def test_empleado_dni_unico(
    db_session: Session,
    empresa_factory: Callable[..., Empresa],
) -> None:
    empresa = empresa_factory()
    emp1 = Empleado(
        legajo="A-1",
        nombre="A",
        apellido="A",
        dni="DUP-DNI",
        cuil="20-100-1",
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    emp2 = Empleado(
        legajo="A-2",
        nombre="B",
        apellido="B",
        dni="DUP-DNI",
        cuil="20-200-1",
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    db_session.add(emp1)
    db_session.commit()
    db_session.add(emp2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_empleado_cuil_unico(
    db_session: Session,
    empresa_factory: Callable[..., Empresa],
) -> None:
    empresa = empresa_factory()
    emp1 = Empleado(
        legajo="C-1",
        nombre="A",
        apellido="A",
        dni="DNI-1",
        cuil="20-DUP-1",
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    emp2 = Empleado(
        legajo="C-2",
        nombre="B",
        apellido="B",
        dni="DNI-2",
        cuil="20-DUP-1",
        fecha_ingreso=date.today(),
        categoria_laboral=enums.CategoriaLaboral.OPERACIONES,
        tipo_jornada=enums.TipoJornada.COMPLETA,
        modalidad_fichada_habilitada=enums.ModalidadFichada.HABILITADA,
        estado=enums.EstadoEntidad.ACTIVO,
        id_empresa=empresa.id_empresa,
    )
    db_session.add(emp1)
    db_session.commit()
    db_session.add(emp2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_dias_especiales_unico_fecha_tipo(db_session: Session) -> None:
    d1 = DiasEspeciales(
        fecha=date(2026, 1, 1),
        tipo_dia_especial=enums.TipoDiaEspecial.FERIADO,
        descripcion="Año nuevo",
        es_laborable=False,
    )
    d2 = DiasEspeciales(
        fecha=date(2026, 1, 1),
        tipo_dia_especial=enums.TipoDiaEspecial.FERIADO,
        descripcion="Duplicado",
        es_laborable=False,
    )
    db_session.add(d1)
    db_session.commit()
    db_session.add(d2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def _setup_cierre_dependencias(
    db_session: Session,
    empleado_factory: Callable[..., Empleado],
) -> tuple[Empresa, Usuario, Exportacion]:
    empleado = empleado_factory()
    db_session.refresh(empleado)
    usuario = _crear_usuario(
        db_session,
        empleado,
        nombre_usuario="cierre_user",
        email="cierre@test.com",
    )
    exportacion = Exportacion(
        tipo_formato=enums.TipoFormatoExportacion.CSV,
        nombre_archivo="x.csv",
        ruta_archivo="/tmp/x.csv",
        estado=enums.EstadoExportacion.GENERADA,
        version_formato="v1",
        id_usuario_generador=usuario.id_usuario,
    )
    db_session.add(exportacion)
    db_session.commit()
    return empleado.empresa, usuario, exportacion


def test_cierre_mensual_mes_invalido(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empresa, usuario, exportacion = _setup_cierre_dependencias(
        db_session, empleado_factory
    )
    cierre = CierreMensual(
        anio=2026,
        mes=13,
        estado=enums.EstadoCierreMensual.BORRADOR,
        observaciones=None,
        id_usuario_cierre=usuario.id_usuario,
        id_empresa=empresa.id_empresa,
        id_exportacion=exportacion.id_exportacion,
    )
    db_session.add(cierre)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cierre_mensual_anio_invalido(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empresa, usuario, exportacion = _setup_cierre_dependencias(
        db_session, empleado_factory
    )
    cierre = CierreMensual(
        anio=1999,
        mes=6,
        estado=enums.EstadoCierreMensual.BORRADOR,
        observaciones=None,
        id_usuario_cierre=usuario.id_usuario,
        id_empresa=empresa.id_empresa,
        id_exportacion=exportacion.id_exportacion,
    )
    db_session.add(cierre)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_novedad_sin_fichada_permitida(
    db_session: Session, empleado_factory: Callable[..., Empleado]
) -> None:
    empleado = empleado_factory()
    usuario = _crear_usuario(
        db_session,
        empleado,
        nombre_usuario="novedad_user",
        email="novedad@test.com",
    )
    tipo = TipoNovedad(
        nombre_tipo="Inasistencia",
        descripcion=None,
        unidad_medida=enums.UnidadMedidaTipoNovedad.HORAS,
        requiere_justificativo=False,
        requiere_aprobacion=False,
        impacta_liquidacion=False,
    )
    db_session.add(tipo)
    db_session.commit()

    novedad = Novedad(
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 1),
        cantidad=Decimal("8.0"),
        estado=enums.EstadoNovedad.PENDIENTE,
        origen=enums.OrigenNovedad.MANUAL,
        observacion=None,
        id_empleado=empleado.id_empleado,
        id_tipo_novedad=tipo.id_tipo_novedad,
        id_fichada=None,
        id_usuario_creador=usuario.id_usuario,
    )
    db_session.add(novedad)
    db_session.commit()
    db_session.refresh(novedad)
    assert novedad.id_fichada is None
    assert novedad.id_novedad is not None


def test_tabla_auditorias_existe() -> None:
    tablas = Base.metadata.tables
    assert "auditorias" in tablas
    auditoria_tabla = tablas["auditorias"]
    columnas = {c.name for c in auditoria_tabla.columns}
    assert "id_auditoria" in columnas
    assert "entidad_afectada" in columnas
    assert "accion" in columnas
    # silenciar warning de imports no usados
    _ = Auditoria
    _ = Fichada
    _ = datetime
