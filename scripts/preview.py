#!/usr/bin/env python3
"""Levanta el backend GADS con bootstrap automatico y sirve el preview HTML.

Uso:
    python scripts/preview.py

- Borra app.db (preview siempre arranca con BD limpia).
- Setea las env vars de bootstrap (admin/admin1234, empresa "Nero IT").
- Ejecuta uvicorn en http://127.0.0.1:8000.
- El preview HTML queda disponible en http://127.0.0.1:8000/ui/.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    # Resolver el python del venv.
    if os.name == "nt":
        venv_bin = repo_root / "venv" / "Scripts"
        py = venv_bin / "python.exe"
        uvicorn_exe = venv_bin / "uvicorn.exe"
    else:
        venv_bin = repo_root / "venv" / "bin"
        py = venv_bin / "python"
        uvicorn_exe = venv_bin / "uvicorn"

    if not py.exists():
        print("[error] No se encontro ./venv. Crealo asi:")
        print("  python3 -m venv venv")
        print("  ./venv/bin/pip install -r requirements.txt")
        return 1

    # Borrar BD anterior.
    db_file = repo_root / "app.db"
    if db_file.exists():
        db_file.unlink()
        print(f"[preview] BD anterior borrada: {db_file.name}")

    # Borrar dir de migraciones SQLite-only sidecar si existe.
    for stale in ("app.db-journal", "app.db-wal", "app.db-shm"):
        p = repo_root / stale
        if p.exists():
            p.unlink()

    # Env vars de bootstrap.
    env = os.environ.copy()
    env.update({
        "GADS_INITIAL_ADMIN_USER": "admin",
        "GADS_INITIAL_ADMIN_PASSWORD": "admin1234",
        "GADS_INITIAL_ADMIN_EMAIL": "admin@local.dev",
        "GADS_INITIAL_EMPRESA_RAZON_SOCIAL": "Nero IT",
        "GADS_INITIAL_EMPRESA_CUIT": "30-71888999-1",
        "GADS_JWT_SECRET": env.get(
            "GADS_JWT_SECRET", "dev-secret-change-me-32bytes-min!"
        ),
    })

    # Aplicar migraciones (alembic) antes de uvicorn.
    alembic_ini = repo_root / "alembic.ini"
    if alembic_ini.exists():
        print("[preview] Aplicando migraciones (alembic upgrade head)...")
        try:
            subprocess.run(
                [str(py), "-m", "alembic", "upgrade", "head"],
                env=env,
                check=True,
                cwd=str(repo_root),
            )
        except subprocess.CalledProcessError as e:
            print(f"[warning] alembic fallo (codigo {e.returncode}); "
                  "uvicorn intentara crear tablas via metadata en lifespan.")
        except FileNotFoundError:
            print("[warning] alembic no disponible en el venv; saltando.")

    # Banner.
    print()
    print("=" * 66)
    print("  GADS preview  ->  http://127.0.0.1:8000/ui/")
    print("=" * 66)
    print("  Login:        admin / admin1234")
    print("  Swagger:      http://127.0.0.1:8000/docs")
    print("  Health:       http://127.0.0.1:8000/health")
    print()
    print("  CSV de prueba: tests/fixtures/planilla_ejemplo.csv")
    print("    (247 filas, empleados con legajos 14, 10, 12, 13.")
    print("     Crea esos empleados antes de importar.)")
    print()
    print("  Ctrl+C para detener.")
    print("=" * 66)
    print()

    cmd = [
        str(uvicorn_exe) if uvicorn_exe.exists() else str(py),
        *([] if uvicorn_exe.exists() else ["-m", "uvicorn"]),
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]

    try:
        return subprocess.call(cmd, env=env, cwd=str(repo_root))
    except KeyboardInterrupt:
        print("\n[preview] Detenido por el usuario.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
