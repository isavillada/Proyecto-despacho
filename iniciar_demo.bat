@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (python -m venv .venv) else (py -3 -m venv .venv)
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
set "DATABASE_URL=sqlite:///./demo.db"
set "UPLOAD_DIR=./demo_uploads"
echo.
echo DEMOSTRACION LOCAL - no use datos personales reales.
echo Abra http://127.0.0.1:8000. Si es el primer inicio, la clave de admin aparece en la terminal.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
exit /b 0
:fail
echo No se pudo preparar el entorno. Compruebe Python 3.11+ y la conexion para descargar dependencias.
pause
exit /b 1
