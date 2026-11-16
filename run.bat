@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
echo.
echo Iniciando reuniao online...
".venv\Scripts\python.exe" app.py
pause
