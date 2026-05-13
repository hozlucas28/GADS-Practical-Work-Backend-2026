from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.api.routers import auth, empleados, usuarios
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.seed import cargar_seed_si_vacio
from app.services import auth_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if settings.seed_demo_data:
            cargar_seed_si_vacio(db)
        auth_service.bootstrap_from_env(db)
    finally:
        db.close()
    yield


app = FastAPI(title="GADS Backend", version="0.1.0", lifespan=lifespan)

cors_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]


def _cors_allow_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if "*" in cors_origins:
        return "*"
    if origin and origin in cors_origins:
        return origin
    return None


@app.middleware("http")
async def force_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    allow_origin = _cors_allow_origin(request)
    if allow_origin is not None:
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            request.headers.get("access-control-request-headers") or "*"
        )
        response.headers["Vary"] = "Origin"

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(empleados.router)

try:
    from app.api.routers import empresas  # type: ignore[attr-defined]

    app.include_router(empresas.router)
except ImportError:
    pass

try:
    from app.api.routers import fichadas  # type: ignore[attr-defined]

    app.include_router(fichadas.router)
except ImportError:
    pass

try:
    from app.api.routers import horarios  # type: ignore[attr-defined]

    app.include_router(horarios.router)
except ImportError:
    pass

try:
    from app.api.routers import dashboards  # type: ignore[attr-defined]

    app.include_router(dashboards.router)
except ImportError:
    pass


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    _ = db
    return {"status": "ok"}


# --- Preview frontend (HTML estático). No es el frontend definitivo. ---
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.is_dir():
    app.mount(
        "/ui",
        StaticFiles(directory=str(_STATIC_DIR), html=True),
        name="ui",
    )

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/ui/")
