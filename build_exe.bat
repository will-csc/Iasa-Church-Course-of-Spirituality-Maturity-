@echo off
setlocal
cd /d "%~dp0"

echo Gerando Iniciar-Curso.exe ...
if not exist ".venv\Scripts\python.exe" (
  echo Crie o ambiente antes com run.bat
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q pyinstaller
".venv\Scripts\pyinstaller.exe" --noconfirm --clean "curso.spec"

if exist "dist\Iniciar-Curso.exe" (
  copy /Y "dist\Iniciar-Curso.exe" "Iniciar-Curso.exe" >nul
  echo.
  echo OK: Iniciar-Curso.exe criado na pasta do projeto.
) else (
  echo [ERRO] Falha ao gerar o executavel.
  pause
  exit /b 1
)
pause
