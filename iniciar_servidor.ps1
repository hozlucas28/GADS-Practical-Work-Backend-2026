# Inicia el servidor de desarrollo usando el venv del proyecto (PowerShell).
# Uso desde la raíz del repo: .\iniciar_servidor.ps1
# Opciones extra se reenvían al script Python, p. ej.: .\iniciar_servidor.ps1 --port 8080

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    . ".\venv\Scripts\Activate.ps1"
} else {
    Write-Warning "No se encontró .\venv\Scripts\Activate.ps1. Creá el venv o usá: python -m venv venv"
}

python "scripts\iniciar_servidor.py" @args
