from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.api.routers import empleados, usuarios
from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="GADS Backend", version="0.1.0", lifespan=lifespan)

app.include_router(usuarios.router)
app.include_router(empleados.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    _ = db  # sesión disponible para rutas que persistan datos
    return {"status": "ok"}
