"""baseline

Revision ID: 20260510_0001
Revises:
Create Date: 2026-05-10 00:00:00

NOTA: Esta baseline es una versión simplificada que delega la creación
del schema a `Base.metadata.create_all` / `drop_all`. Funciona como punto
de partida para entornos nuevos. TODO: regenerar con `alembic revision
--autogenerate` cuando se haga el primer schema change real, para tener
operaciones declarativas explícitas op.create_table(...) y poder evolucionar
el schema de manera versionada.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# Registramos todos los modelos para que Base.metadata los conozca.
import app.models  # noqa: F401
from app.models.base import Base

# revision identifiers, used by Alembic.
revision: str = "20260510_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
