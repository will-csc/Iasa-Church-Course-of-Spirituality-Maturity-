@echo off
cd /d "%~dp0"

REM Preferencia: executavel gerado com PyInstaller
if exist "Iniciar-Curso.exe" (
  echo Iniciando pelo Iniciar-Curso.exe ...
  "Iniciar-Curso.exe"
  exit /b %ERRORLEVEL%
)

REM Fallback: script Python (run.bat)
call "%~dp0run.bat"
