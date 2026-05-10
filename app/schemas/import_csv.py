from __future__ import annotations

from pydantic import BaseModel


class ImportRowError(BaseModel):
    fila: int
    motivo: str


class ImportSummary(BaseModel):
    total_filas: int
    creados: int
    omitidos: int
    errores: list[ImportRowError]
    dry_run: bool
