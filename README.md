# GADS Backend

Backend de **Gestión de Asistencia / Fichadas / Novedades** para empresas. Modela empleados, horarios, fichadas, novedades (vacaciones, licencias), justificativos y cierres mensuales.

**Stack**: FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT (PyJWT) · bcrypt · SQLite (dev) / Postgres (prod) · Alembic.

---

## Tabla de contenidos

1. [Setup](#setup)
2. [Configuración (env vars)](#configuración-env-vars)
3. [Bootstrap del primer admin](#bootstrap-del-primer-admin)
4. [Cómo correrlo](#cómo-correrlo)
5. [Preview con frontend mínimo](#preview-con-frontend-mínimo)
6. [Endpoints — referencia completa](#endpoints--referencia-completa)
7. [Modelo de dominio](#modelo-de-dominio)
8. [Tests y calidad](#tests-y-calidad)
9. [Estructura del proyecto](#estructura-del-proyecto)
10. [Limitaciones conocidas](#limitaciones-conocidas)

---

## Setup

Requiere **Python 3.11+**.

```bash
python3.11 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # editar valores
alembic upgrade head                # crea esquema (o se crea solo en preview)
```

Dependencias clave: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic[email]`, `pydantic-settings`, `bcrypt`, `pyjwt`, `python-multipart`, `alembic`. Ver [requirements.txt](requirements.txt).

---

## Configuración (env vars)

Todas las variables usan prefijo `GADS_`. Cargadas desde `.env` (ver [.env.example](.env.example)).

| Variable | Default | Descripción |
|---|---|---|
| `GADS_DATABASE_URL` | `sqlite:///./app.db` | URL SQLAlchemy. En prod: `postgresql+psycopg://user:pass@host/db`. |
| `GADS_JWT_SECRET` | `dev-secret-change-me` | **Cambiar en prod**. Mínimo 32 bytes recomendado (HS256). |
| `GADS_JWT_ALGORITHM` | `HS256` | Algoritmo JWT. |
| `GADS_JWT_EXPIRE_MINUTES` | `60` | Vida del access token. |
| `GADS_DEFAULT_TIMEZONE` | `America/Argentina/Buenos_Aires` | Zona horaria para parsear CSVs sin tzinfo. |
| `GADS_INITIAL_ADMIN_USER` | — | Bootstrap: nombre de usuario admin si BD vacía. |
| `GADS_INITIAL_ADMIN_PASSWORD` | — | Bootstrap: contraseña inicial. |
| `GADS_INITIAL_ADMIN_EMAIL` | — | Bootstrap: email del admin. |
| `GADS_INITIAL_EMPRESA_RAZON_SOCIAL` | — | Bootstrap: razón social de la primera empresa. |
| `GADS_INITIAL_EMPRESA_CUIT` | — | Bootstrap: CUIT de la primera empresa. |

---

## Bootstrap del primer admin

Dos caminos:

### a) Automático con env vars

Setea las 5 env vars `GADS_INITIAL_*` antes de arrancar. Si la BD no tiene admin, el `lifespan` crea Empresa + Empleado mínimo + Usuario admin al iniciar.

### b) Manual con endpoint

Con la BD vacía:

```bash
curl -X POST http://localhost:8000/auth/register-first-admin \
  -H 'Content-Type: application/json' \
  -d '{
    "nombre_usuario": "admin",
    "contrasena": "admin1234",
    "email": "admin@local.dev",
    "nombre": "Admin",
    "apellido": "Inicial",
    "dni": "11111111",
    "cuil": "20-11111111-1",
    "legajo": "ADM-001",
    "empresa_razon_social": "Mi Empresa",
    "empresa_cuit": "30-12345678-9",
    "empresa_email": "contacto@miempresa.com",
    "empresa_telefono": "011-1234-5678",
    "empresa_direccion": "Av. Siempreviva 742"
  }'
```

Después del primer admin, este endpoint devuelve **409**.

### c) Seed dev (Nero IT)

Solo contra SQLite:

```bash
python scripts/crear_usuario_admin_alejandro.py --reset-db
# Crea 1 empresa (Nero IT) + 7 empleados/usuarios. Idempotente.
```

---

## Cómo correrlo

```bash
python scripts/iniciar_servidor.py        # arranque normal con --reload
# o:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Después: `http://localhost:8000/docs` para Swagger UI.

---

## Preview con frontend mínimo

Hay un frontend HTML/CSS/JS plano en `app/static/` para probar end-to-end **sin** depender del frontend definitivo (ese vive en otro repo).

```bash
python scripts/preview.py
# abrí http://127.0.0.1:8000/ui/  ·  login: admin / admin1234
```

El script borra `app.db`, setea env vars de bootstrap y levanta uvicorn.

---

## Endpoints — referencia completa

Convención de auth:
- 🔓 **público** — sin autenticación.
- 🔑 **autenticado** — bearer JWT.
- 👑 **admin** — `rol == Administrador`.
- 🧮 **admin/contador** — `rol in {Administrador, ContadorExterno}`.
- 🪪 **propio o admin** — `current.id_usuario == :id` o admin.

Todos los endpoints autenticados esperan: `Authorization: Bearer <access_token>`.

---

### Health

#### `GET /health` 🔓

Liveness probe.

**Response 200**:
```json
{"status": "ok"}
```

---

### Auth

#### `POST /auth/login` 🔓

**Body**:
```json
{"nombre_usuario": "admin", "contrasena": "admin1234"}
```

**Response 200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errores**: `401` (credenciales inválidas o usuario inactivo), `422` (body inválido).

---

#### `GET /auth/me` 🔑

Devuelve el usuario autenticado.

**Response 200**:
```json
{
  "id_usuario": 1,
  "nombre_usuario": "admin",
  "email": "admin@local.dev",
  "rol": "Administrador",
  "estado": "activo",
  "id_empleado": 1
}
```

**Errores**: `401` (sin token, token inválido o expirado, usuario eliminado).

---

#### `POST /auth/register-first-admin` 🔓

Bootstrap inicial. Solo permitido si **no existe** ningún admin.

**Body**: ver [Bootstrap manual](#b-manual-con-endpoint).

**Response 201**: mismo formato que `GET /auth/me`.

**Errores**: `409` (ya hay admin), `422` (body inválido — email malformado, password < 8 chars, etc.).

---

### Empresas

#### `GET /empresas` 🔑

Admin: lista todas. ContadorExterno/Empleado: solo la propia.

**Response 200**:
```json
[
  {
    "id_empresa": 1,
    "razon_social": "Nero IT",
    "cuit": "30-71888999-1",
    "email_contacto": "contacto@neroit.local",
    "telefono_contacto": "011-4000-0000",
    "direccion": "Buenos Aires, Argentina",
    "fecha_alta": "2026-05-10",
    "estado": "activo"
  }
]
```

---

#### `GET /empresas/export` 👑

Devuelve un CSV (UTF-8, separador coma) con todas las empresas. Header `Content-Disposition: attachment; filename="empresas.csv"`. Columnas: `id_empresa, razon_social, cuit, email_contacto, telefono_contacto, direccion, fecha_alta, estado, creado_en, actualizado_en`. Ver muestra real en [exports/empresas.csv](exports/empresas.csv).

---

#### `POST /empresas` 👑

**Body**:
```json
{
  "razon_social": "ACME SA",
  "cuit": "30-99999999-1",
  "email_contacto": "rrhh@acme.com",
  "telefono_contacto": "011-5555-5555",
  "direccion": "Av. Corrientes 1234",
  "fecha_alta": "2026-05-10",
  "estado": "activo"
}
```

**Response 201**: misma forma que el item de `GET /empresas` con el `id_empresa` asignado.

**Errores**: `409` (CUIT duplicado), `403` (no admin), `422`.

---

#### `GET /empresas/{id_empresa}` 🔑

Admin: cualquiera. No-admin: solo la propia (`current.empleado.id_empresa`), sino **403**.

**Response 200**: forma `EmpresaResponse`. **404** si no existe.

---

#### `PATCH /empresas/{id_empresa}` 👑

Body parcial (solo los campos a cambiar):
```json
{"estado": "inactivo", "telefono_contacto": "011-9999-9999"}
```

**Response 200**: empresa actualizada. **404** si no existe.

---

#### `DELETE /empresas/{id_empresa}` 👑

**Baja lógica**: pasa `estado` a `inactivo`. La empresa sigue accesible vía GET.

**Response 204** (sin body). **404** si no existe.

---

### Empleados

#### `GET /empleados` 🔑

Lista todos los empleados.

**Response 200**:
```json
[
  {
    "id_empleado": 1,
    "id_empresa": 1,
    "legajo": "NERO-001",
    "nombre": "Alejandro",
    "apellido": "Mabbdet",
    "dni": "35111222",
    "cuil": "20-35111222-4",
    "fecha_ingreso": "2026-05-10",
    "categoria_laboral": "administracion",
    "tipo_jornada": "completa",
    "modalidad_fichada_habilitada": "habilitada",
    "estado": "activo"
  }
]
```

---

#### `GET /empleados/export` 👑

CSV con todos los empleados. Columnas: `id_empleado, id_empresa, legajo, nombre, apellido, dni, cuil, fecha_ingreso, categoria_laboral, tipo_jornada, modalidad_fichada_habilitada, estado, creado_en, actualizado_en`. Muestra: [exports/empleados.csv](exports/empleados.csv).

---

#### `POST /empleados` 👑

**Body**:
```json
{
  "legajo": "EMP-100",
  "nombre": "Juan",
  "apellido": "Pérez",
  "dni": "30111222",
  "cuil": "20-30111222-3",
  "fecha_ingreso": "2026-05-10",
  "categoria_laboral": "operaciones",
  "tipo_jornada": "completa",
  "modalidad_fichada_habilitada": "habilitada",
  "id_empresa": 1,
  "estado": "activo"
}
```

Enums válidos:
- `categoria_laboral`: `operaciones | administracion | contaduria`
- `tipo_jornada`: `completa | parcial | turnos`
- `modalidad_fichada_habilitada`: `habilitada | deshabilitada`
- `estado`: `activo | inactivo`

**Errores**: `404` (`id_empresa` inexistente), `409` (`dni`/`cuil` duplicado o `(id_empresa, legajo)` duplicado), `422`.

---

#### `GET /empleados/{id_empleado}` 🔑

**Response 200**: `EmpleadoResponse`. **404** si no existe.

---

#### `PATCH /empleados/{id_empleado}` 👑

`id_empresa` **NO** es modificable (excluido del schema). Body parcial:
```json
{"estado": "inactivo", "categoria_laboral": "administracion"}
```

---

#### `DELETE /empleados/{id_empleado}` 👑

Baja lógica. **204** sin body.

---

### Usuarios

#### `GET /usuarios` 👑

**Response 200**: lista sin `contrasena_hash`.
```json
[
  {
    "id_usuario": 1,
    "nombre_usuario": "admin",
    "email": "admin@local.dev",
    "estado": "activo",
    "ultimo_acceso": "2026-05-10T20:58:54.530602",
    "rol": "Administrador",
    "id_empleado": 1
  }
]
```

---

#### `GET /usuarios/export` 👑

CSV sin `contrasena_hash`. Columnas: `id_usuario, nombre_usuario, email, rol, estado, ultimo_acceso, id_empleado, creado_en, actualizado_en`. Muestra: [exports/usuarios.csv](exports/usuarios.csv).

---

#### `POST /usuarios` 👑

**Body**:
```json
{
  "nombre_usuario": "jperez",
  "contrasena": "secreta12",
  "email": "jperez@empresa.com",
  "rol": "Empleado",
  "id_empleado": 5,
  "estado": "activo"
}
```

`rol`: `Administrador | ContadorExterno | Empleado`. La contraseña se hashea con bcrypt antes de persistir.

**Errores**: `409` (`nombre_usuario`/`email` duplicado), `404` (`id_empleado` inexistente), `403` (no admin), `422` (password < 8 chars).

---

#### `GET /usuarios/{id_usuario}` 🪪

Admin: cualquiera. No-admin: solo a sí mismo (`current.id_usuario == :id`), sino **403**.

---

#### `PATCH /usuarios/{id_usuario}` 🪪

Reglas:
- `current.id_usuario == :id` o admin → puede editar `email`, `nombre_usuario`, `contrasena`, `estado`.
- Solo **admin** puede modificar `rol` (sino **403**).
- `id_rol` y `id_empleado` **NO** son modificables.

Body ejemplo:
```json
{"email": "nuevo@empresa.com", "contrasena": "nueva-pass-123"}
```

---

#### `DELETE /usuarios/{id_usuario}` 👑

Baja lógica. **204**.

---

### Fichadas

#### `POST /fichadas/import` 🧮

Import masivo de fichadas desde CSV.

**Multipart**:
- `file`: CSV UTF-8 (encoding `utf-8-sig` tolerado para BOM de Excel).

**Query params**:
- `dry_run` (`bool`, default `false`) — si `true`, valida pero hace `rollback`.
- `id_empresa` (`int`, opcional) — admin **debe** indicarla. ContadorExterno la infiere de su empleado.

**Headers esperados del CSV**:
```
Fecha, Hora, Forma Registro, Tipo Registro, Legajo, Empleado, Observaciones
```

Mapeos:
- `Forma Registro`: `Local` → `OrigenFichada.LOCAL`, `Manual` → `OrigenFichada.MANUAL`. Otros valores → error de fila.
- `Tipo Registro`: `Entrada` → `TipoFichada.ENTRADA`, `Salida` → `TipoFichada.SALIDA`.
- Empleado: buscado por `(id_empresa, legajo)`.
- `Observaciones`: si matchea `^JUSTIFICACION\s+(Entra|Sale)\s*:\s*(.+)$` (case-insensitive), se crea **automáticamente** una `Novedad` con `TipoNovedad` (auto-creado si no existe).

Comportamiento de transacción: cada fila usa SAVEPOINT. Errores de fila se acumulan **sin abortar** el batch.

**Curl**:
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/planilla_ejemplo.csv" \
  "http://localhost:8000/fichadas/import?id_empresa=1"
```

**Response 200**:
```json
{
  "total_filas": 247,
  "fichadas_creadas": 247,
  "novedades_creadas": 2,
  "tipos_novedad_creados": ["vacaciones"],
  "origenes_fichada_existentes": ["biometrico", "manual", "qr", "api", "excel", "local"],
  "errores": [],
  "dry_run": false
}
```

**Errores típicos en `errores[]`** (no abortan):
```json
{"fila": 17, "motivo": "Empleado legajo 99 no encontrado en empresa 1", "legajo": "99"}
```

**Errores HTTP**: `422` (headers faltantes, file vacío), `400` (admin sin `id_empresa`), `403` (rol Empleado plano).

---

### Dashboards

Métricas agregadas para tableros de status. Auth: admin o contador (excepto `/empleados/{id}`, que también permite al propio empleado).

#### `GET /dashboards/resumen` 🧮

Métricas globales (admin) o de la empresa propia (contador).

**Query params** (opcionales):
- `id_empresa` (`int`) — admin filtra; contador siempre ve la propia (se ignora si se pasa otra).

**Response 200**:
```json
{
  "id_empresa": null,
  "empresas": {"total": 1, "activos": 1, "inactivos": 0},
  "empleados": {"total": 7, "activos": 7, "inactivos": 0},
  "empleados_por_categoria": {"administracion": 1, "contaduria": 2, "operaciones": 4},
  "empleados_por_jornada": {"completa": 7},
  "usuarios": {"total": 7, "por_rol": {"Administrador": 1, "ContadorExterno": 2, "Empleado": 4}},
  "fichadas": {"total": 247, "ultimos_7_dias": 0, "ultimos_30_dias": 0},
  "novedades": {"total": 2, "pendientes": 2, "aprobadas": 0, "rechazadas": 0, "anuladas": 0}
}
```

**Errores**: `403` (rol Empleado plano).

---

#### `GET /dashboards/empleados/status` 🧮

Listado de empleados con métricas resumidas (última fichada, fichadas de los últimos 30 días, novedades pendientes).

**Query params** (opcionales):
- `id_empresa` (`int`) — admin filtra; contador forzado a la propia.
- `estado` — `activo` | `inactivo`.

**Response 200**:
```json
{
  "total": 7,
  "items": [
    {
      "id_empleado": 1,
      "id_empresa": 1,
      "legajo": "NERO-001",
      "nombre": "Alejandro",
      "apellido": "Mabbdet",
      "estado": "activo",
      "categoria_laboral": "administracion",
      "tipo_jornada": "completa",
      "ultima_fichada": "2026-04-17T17:43:00-03:00",
      "fichadas_ultimos_30_dias": 12,
      "novedades_pendientes": 0
    }
  ]
}
```

---

#### `GET /dashboards/empleados/{id_empleado}` 🪪

Detalle completo del empleado: fichadas por mes, novedades agrupadas por tipo, primera/última fichada.

Auth: **admin** (cualquier empleado), **contador** (solo empleados de su empresa), **el propio empleado** (`current.id_empleado == :id`).

**Response 200**:
```json
{
  "id_empleado": 1,
  "id_empresa": 1,
  "legajo": "NERO-001",
  "nombre": "Alejandro",
  "apellido": "Mabbdet",
  "estado": "activo",
  "categoria_laboral": "administracion",
  "tipo_jornada": "completa",
  "modalidad_fichada_habilitada": "habilitada",
  "ultima_fichada": "2026-04-17T17:43:00-03:00",
  "primera_fichada": "2026-04-01T08:00:00-03:00",
  "fichadas_total": 22,
  "fichadas_ultimos_30_dias": 22,
  "fichadas_por_mes": {"2026-04": 22},
  "novedades_total": 2,
  "novedades_pendientes": 2,
  "novedades_por_tipo": {"vacaciones": 2}
}
```

**Errores**: `403` (otro empleado sin permiso), `404` (id inexistente).

---

### Frontend preview

#### `GET /` 🔓

Redirige `307` → `/ui/`.

#### `GET /ui/` 🔓

Sirve `index.html` (login). Después del login, dashboard estático en `/ui/dashboard.html`.

---

## Modelo de dominio

### Diagrama relacional (resumen)

```
Empresa 1───* Empleado 1───? Usuario
              │                │
              ├───* Asignacion ─── Horario
              ├───* Fichada ──── OrigenFichada
              └───* Novedad ──── TipoNovedad
                       │
                       └───? Justificativo

CierreMensual ─── Empresa
              ├── ResumenMensualEmpleado *── Empleado
              └── Exportacion

DiasEspeciales (independiente)
Auditoria      (genérica, registra cualquier entidad)
```

### Tablas (14)

| Tabla | Notas |
|---|---|
| `usuarios` | `nombre_usuario` único, `rol` SAEnum, `estado` SAEnum, hash bcrypt. |
| `empresas` | `cuit` único, baja lógica. |
| `empleados` | `dni` y `cuil` únicos globales, `(id_empresa, legajo)` único compuesto. |
| `horarios` | Banda, tolerancias, días descanso. |
| `asignaciones_horario` | Validación servicio: rango sin solapamientos por empleado. |
| `fichadas` | `fecha_hora` aware, `tipo_fichada` enum (entrada/salida). |
| `origenes_fichada` | Catálogo: biometrico, manual, qr, api, excel, **local**. |
| `tipos_novedad` | `nombre_tipo` único. |
| `novedades` | `id_fichada` nullable (vacaciones planificadas no tienen fichada). |
| `justificativos` | 1:1 con novedad, archivo asociado. |
| `cierres_mensuales` | CHECK `mes BETWEEN 1 AND 12`, CHECK `anio BETWEEN 2000 AND 2100`. |
| `resumenes_mensuales_empleado` | Métricas por empleado-cierre. |
| `dias_especiales` | UniqueConstraint `(fecha, tipo_dia_especial)`. |
| `auditorias` | Genérica. Index compuesto `(entidad_afectada, id_registro_afectado)`. |

Casi todas las tablas heredan `TimestampMixin` (`creado_en` / `actualizado_en`).

### Enums (Python)

`Rol`, `OrigenFichada`, `TipoFichada`, `EstadoEntidad`, `EstadoNovedad`, `OrigenNovedad`, `EstadoJustificativo`, `EstadoExportacion`, `TipoJornada`, `ModalidadFichada`, `CategoriaLaboral`, `TipoHorario`, `TipoJustificativo`, `UnidadMedidaTipoNovedad`, `EstadoCierreMensual`, `TipoFormatoExportacion`, `TipoDiaEspecial`, `AccionAuditoria`. Ver [app/models/enums.py](app/models/enums.py).

---

## Tests y calidad

```bash
pytest                       # 124 tests verdes
pytest --cov=app             # con cobertura
ruff check .                 # lint
mypy app                     # types strict
```

Cobertura por archivo:

| Archivo | Tests |
|---|---|
| `test_health.py` | 4 |
| `test_auth.py` | 13 |
| `test_bootstrap.py` | 5 |
| `test_usuarios.py` | 28 |
| `test_empleados.py` | 16 |
| `test_empresas.py` | 15 |
| `test_exports.py` | 14 |
| `test_dashboards.py` | 13 |
| `test_fichadas_import.py` | 11 |
| `test_horarios.py` | 6 |
| `test_modelos_constraints.py` | 8 |
| `test_seed.py` | 4 |
| **Total** | **137** |

---

## Estructura del proyecto

```
GADS/
├── app/
│   ├── api/
│   │   ├── deps.py                # get_db, get_current_user, require_rol
│   │   └── routers/
│   │       ├── auth.py            # /auth/*
│   │       ├── empresas.py        # /empresas/* (CRUD + /export)
│   │       ├── empleados.py       # /empleados/* (CRUD + /export)
│   │       ├── usuarios.py        # /usuarios/* (CRUD + /export)
│   │       ├── fichadas.py        # /fichadas/import
│   │       └── dashboards.py      # /dashboards/resumen, /empleados/status, /empleados/{id}
│   ├── daos/                      # acceso a datos (sin commit)
│   ├── services/                  # lógica + commit + manejo de IntegrityError
│   │   ├── auth_service.py        # login, JWT, bootstrap
│   │   ├── usuario_service.py
│   │   ├── empleado_service.py
│   │   ├── empresa_service.py
│   │   ├── horario_service.py     # validación de no-solapamiento
│   │   ├── fichada_import_service.py  # parser CSV + auto-novedades
│   │   ├── export_service.py      # CSVs (empresas/empleados/usuarios)
│   │   └── dashboard_service.py   # métricas agregadas
│   ├── models/                    # ORM SQLAlchemy 2.0
│   ├── schemas/                   # Pydantic v2
│   ├── static/                    # frontend preview HTML/CSS/JS
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── database.py                # engine, SessionLocal, get_db, init_db
│   └── main.py                    # FastAPI app + lifespan + bootstrap
├── exports/                       # muestras de export CSV
│   ├── empresas.csv
│   ├── empleados.csv
│   └── usuarios.csv
├── migrations/                    # Alembic
├── scripts/
│   ├── iniciar_servidor.py
│   ├── preview.py                 # uvicorn + bootstrap env vars
│   └── crear_usuario_admin_alejandro.py  # seed dev
├── tests/
│   ├── fixtures/planilla_ejemplo.csv  # 247 filas, 4 empleados, 2 vacaciones
│   └── test_*.py                  # 124 tests
├── pyproject.toml                 # ruff + mypy
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Limitaciones conocidas

| Limitación | Estado / workaround |
|---|---|
| Sin CRUD de horarios desde API (servicio existe). | Pendiente router. |
| Sin CRUD de novedades (solo se crean por import CSV). | Pendiente router. |
| Sin endpoints de cierre mensual / resumen. | Modelo listo, lógica no implementada. |
| Sin upload de adjuntos de justificativos. | — |
| Sin reportes / exportación de fichadas (solo empresas/empleados/usuarios). | Extender `export_service`. |
| Sin recuperación de contraseña. | Admin puede resetear via `PATCH /usuarios/{id}`. |
| Sin CORS configurado. | Sumar `CORSMiddleware` cuando frontend definitivo viva en otro dominio. |
| Sin CSP / HSTS / headers de seguridad. | Configurar en proxy reverso (nginx/Caddy). |
| JWT en `localStorage` del preview. | Vulnerable a XSS — para prod usar cookie httpOnly + CSRF. |
| Alembic baseline simplificada (`Base.metadata.create_all`). | Regenerar con `alembic revision --autogenerate` al primer schema change. |
| Frontend preview sin paginación / filtros / búsqueda. | UI mínima de demostración. |
| `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning (Starlette). | Cambiar a `HTTP_422_UNPROCESSABLE_CONTENT`. |

---

## Licencia

Ver [LICENSE](LICENSE).
