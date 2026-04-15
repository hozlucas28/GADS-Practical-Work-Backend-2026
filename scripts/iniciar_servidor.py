#!/usr/bin/env python3
"""
Inicia el servidor HTTP de desarrollo (FastAPI + uvicorn).

Desde la raíz del repositorio, en PowerShell (recomendado):
  .\\venv\\Scripts\\Activate.ps1
  python scripts/iniciar_servidor.py

O en un solo paso:
  .\\iniciar_servidor.ps1

En CMD (usa el Python del venv si existe):
  iniciar_servidor.bat

Opciones:
  --host 0.0.0.0   # escuchar en todas las interfaces
  --port 8080
  --no-reload      # sin recarga automática al cambiar código
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _asegurar_dependencias() -> None:
    """Falla con mensaje claro si falta bcrypt u otra dependencia base."""
    try:
        import bcrypt  # noqa: F401 — usado por la app al cargar rutas
    except ImportError:
        print(
            "No se encuentra el paquete 'bcrypt'. Instalá las dependencias del proyecto:\n"
            "  .\\venv\\Scripts\\Activate.ps1\n"
            "  pip install -r requirements.txt\n"
            "En PowerShell podés arrancar con: .\\iniciar_servidor.ps1\n"
            "O sin activar: .\\venv\\Scripts\\python.exe scripts\\iniciar_servidor.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def main() -> None:
    _asegurar_dependencias()
    parser = argparse.ArgumentParser(description="Inicia GADS Backend (uvicorn)")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Desactiva el reload automático al editar archivos",
    )
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main()
