@echo off
setlocal EnableExtensions

title Instalador OSC Fiscal - Homologacao
color 0A

set "BASE_DIR=%~dp0"
set "APP_DIR=%BASE_DIR%app"
set "VENV_DIR=%BASE_DIR%.venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS=%BASE_DIR%requirements.txt"
set "APP_FILE=%APP_DIR%\app.py"

cd /d "%BASE_DIR%"

cls
echo ============================================================
echo                  INSTALADOR OSC FISCAL
 echo ============================================================
echo.
echo Este instalador prepara o ambiente de HOMOLOGACAO LOCAL.
echo Ele nao acessa Sefaz, Receita Federal ou certificado digital.
echo.

echo [1/7] Criando estrutura de pastas...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%BASE_DIR%segredos" mkdir "%BASE_DIR%segredos"
if not exist "%BASE_DIR%logs" mkdir "%BASE_DIR%logs"
if not exist "%BASE_DIR%armazenamento" mkdir "%BASE_DIR%armazenamento"

echo [2/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao foi encontrado.
    echo Instale Python 3.11 ou superior e marque Add Python to PATH.
    pause
    exit /b 1
)
python --version

echo [3/7] Criando ambiente virtual...
if not exist "%PYTHON%" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo [4/7] Atualizando pip...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERRO] Falha ao atualizar o pip.
    pause
    exit /b 1
)

echo [5/7] Criando requirements.txt...
(
    echo streamlit
    echo pandas
    echo bcrypt
) > "%REQUIREMENTS%"

echo [6/7] Instalando dependencias...
"%PYTHON%" -m pip install -r "%REQUIREMENTS%"
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo [7/7] Validando app.py...
if not exist "%APP_FILE%" (
    echo.
    echo [ERRO] app.py nao encontrado em:
    echo %APP_FILE%
    echo.
    echo Baixe o arquivo app.py enviado e coloque dentro da pasta app.
    pause
    exit /b 1
)

"%PYTHON%" -m py_compile "%APP_FILE%"
if errorlevel 1 (
    echo.
    echo [ERRO] O app.py possui erro de sintaxe.
    echo Corrija o arquivo antes de iniciar.
    pause
    exit /b 1
)

(
    echo @echo off
    echo setlocal EnableExtensions
    echo title OSC Fiscal - Homologacao
    echo set "BASE_DIR=%%~dp0"
    echo set "PYTHON=%%BASE_DIR%%.venv\Scripts\python.exe"
    echo set "APP_FILE=%%BASE_DIR%%app\app.py"
    echo cd /d "%%BASE_DIR%%"
    echo for /f "tokens=5" %%%%P in ^('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"'^) do taskkill /PID %%%%P /F ^>nul 2^>^&1
    echo timeout /t 1 /nobreak ^>nul
    echo "%%PYTHON%%" -m streamlit run "%%APP_FILE%%" --server.address 127.0.0.1 --server.port 8501 --server.headless true
    echo pause
    echo endlocal
) > "%BASE_DIR%iniciar_osc_fiscal.bat"

if not exist "%BASE_DIR%ambiente.txt" echo HOMOLOGACAO> "%BASE_DIR%ambiente.txt"
if not exist "%BASE_DIR%logs\sistema.log" type nul > "%BASE_DIR%logs\sistema.log"
if not exist "%BASE_DIR%segredos\cert_config.json" (
    (
        echo {
        echo   "store": "LocalMachine",
        echo   "store_name": "My",
        echo   "thumbprint": "",
        echo   "ambiente": "homologacao"
        echo }
    ) > "%BASE_DIR%segredos\cert_config.json"
)

echo.
echo ============================================================
echo INSTALACAO CONCLUIDA COM SUCESSO
 echo ============================================================
echo.
echo Agora execute: iniciar_osc_fiscal.bat
echo Depois abra: http://127.0.0.1:8501/
echo.
echo Primeiro acesso: admin
echo Senha inicial: troque-esta-senha
echo.
pause
endlocal
