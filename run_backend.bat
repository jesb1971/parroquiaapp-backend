@echo off
setlocal enabledelayedexpansion

REM Ir a la carpeta donde está este BAT (backend)
cd /d "%~dp0"

REM 1) Crear venv si no existe (usa py si está, si no python)
if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creando entorno virtual...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)

REM 2) Activar venv
call .venv\Scripts\activate.bat

REM 3) Instalar dependencias solo si falta uvicorn
python -c "import uvicorn" 1>nul 2>nul
if errorlevel 1 (
  echo [setup] Instalando dependencias...
  pip install -r requirements.txt
)

REM 4) Arrancar el servidor (puedes pasar puerto como argumento: run_backend.bat 8001)
set "HOST=127.0.0.1"
set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"

echo [run] Iniciando Uvicorn en http://%HOST%:%PORT%  (Ctrl+C para parar)
python -m uvicorn app.main:app --host %HOST% --port %PORT% --reload

endlocal
