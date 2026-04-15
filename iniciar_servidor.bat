@echo off
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "scripts\iniciar_servidor.py" %*
) else (
  python "scripts\iniciar_servidor.py" %*
)
