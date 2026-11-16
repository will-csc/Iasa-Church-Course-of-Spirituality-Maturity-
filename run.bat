@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Curso de Maturidade Espiritual - IASA
echo ========================================
echo.

REM --- Localiza Python (python ou py -3) ---
set "PYEXE="
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  for /f "delims=" %%i in ('where python') do (
    set "PYEXE=%%i"
    goto :py_found
  )
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
    set "PYEXE=%%i"
    goto :py_found
  )
)

echo [ERRO] Python nao encontrado neste computador.
echo.
echo Instale o Python 3.10+ em:
echo   https://www.python.org/downloads/
echo.
echo Na instalacao, marque a opcao:
echo   "Add python.exe to PATH"
echo.
pause
exit /b 1

:py_found
echo Usando Python: %PYEXE%
"%PYEXE%" --version
if errorlevel 1 (
  echo [ERRO] Falha ao executar o Python.
  pause
  exit /b 1
)
echo.

REM --- Cria config.ini se nao existir ---
if not exist "config.ini" (
  if exist "config.ini.example" (
    echo Criando config.ini a partir do exemplo...
    copy /Y "config.ini.example" "config.ini" >nul
  ) else (
    echo [ERRO] Faltam config.ini e config.ini.example
    pause
    exit /b 1
  )
)

REM --- Ambiente virtual ---
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual (.venv)...
  "%PYEXE%" -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar o .venv
    echo Tente: "%PYEXE%" -m pip install --upgrade pip virtualenv
    pause
    exit /b 1
  )
  echo.
  echo Instalando dependencias (pode demorar na primeira vez)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar requirements.txt
    echo Verifique a internet e tente de novo.
    pause
    exit /b 1
  )
  echo.
) else (
  REM Garante dependencias mesmo se o venv ja existir
  ".venv\Scripts\python.exe" -c "import flask, flask_socketio" >nul 2>&1
  if errorlevel 1 (
    echo Reinstalando dependencias faltantes...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
      echo [ERRO] Falha ao instalar dependencias.
      pause
      exit /b 1
    )
  )
)

REM --- PDF padrao ---
if not exist "data\784656217-CURSO-DE-MATURIDADE-NO-ESPIRITO-1.pdf" (
  echo [AVISO] PDF padrao nao encontrado em data\
  echo O app sobe, mas o material so aparece depois de colocar o PDF.
  echo.
)

echo Iniciando servidor...
echo Nao feche esta janela enquanto a reuniao estiver ativa.
echo.
".venv\Scripts\python.exe" -u app.py
set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" (
  echo [ERRO] O servidor encerrou com codigo %EXITCODE%.
)
pause
exit /b %EXITCODE%
