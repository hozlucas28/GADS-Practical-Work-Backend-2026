from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "crear_usuario_admin_alejandro.py"


def _run_seed(
    db_path: Path,
    *,
    reset_db: bool = False,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GADS_DATABASE_URL"] = f"sqlite:///{db_path}"
    if extra_env:
        env.update(extra_env)
    args = [sys.executable, str(SCRIPT)]
    if reset_db:
        args.append("--reset-db")
    return subprocess.run(
        args,
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_seed_reset_crea_usuarios(tmp_path: Path) -> None:
    db_path = tmp_path / "seed_dev.db"
    result = _run_seed(db_path, reset_db=True)
    assert result.returncode == 0, result.stderr or result.stdout

    # Verificamos contando usuarios via la propia BD generada.
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    try:
        import app.models  # noqa: F401

        from app.models.seguridad import Usuario

        with Session(engine) as session:
            usuarios = session.execute(select(Usuario)).scalars().all()
            assert len(usuarios) == 7
    finally:
        engine.dispose()


def test_seed_es_idempotente(tmp_path: Path) -> None:
    db_path = tmp_path / "seed_idem.db"
    primero = _run_seed(db_path, reset_db=True)
    assert primero.returncode == 0, primero.stderr or primero.stdout

    segundo = _run_seed(db_path, reset_db=False)
    assert segundo.returncode == 0, segundo.stderr or segundo.stdout
    # En el segundo run debería omitir todos los usuarios ya existentes.
    assert "Usuarios nuevos: 0" in segundo.stdout
    assert "omitidos (ya existian): 7" in segundo.stdout


def test_seed_run_seed_smoke(tmp_path: Path) -> None:
    """Smoke test del seed completo: tras reset, reporta 7 usuarios creados."""
    db_path = tmp_path / "seed_smoke.db"
    result = _run_seed(db_path, reset_db=True)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Usuarios nuevos: 7" in result.stdout
