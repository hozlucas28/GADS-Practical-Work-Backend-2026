from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registra metadatos
from app.api import deps as api_deps
from app.main import app
from app.models.base import Base

# StaticPool: una sola conexión para que :memory: sea compartida entre sesiones
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP con BD en memoria (sin tocar app.db)."""

    def init_test_db() -> None:
        Base.metadata.create_all(bind=test_engine)

    monkeypatch.setattr("app.main.init_db", init_test_db)
    app.dependency_overrides[api_deps.get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
