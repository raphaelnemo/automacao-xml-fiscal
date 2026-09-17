@echo off
setlocal EnableExtensions

title OSC Fiscal - Homologacao
color 0A

set "BASE_DIR=%~dp0"
set "PYTHON=%BASE_DIR%.venv\Scripts\python.exe"
set "APP_FILE=%BASE_DIR%app\app.py"
set "PORTA=8501"

cd /d "%BASE_DIR%"

if not exist "%PYTHON%" (
    echo [ERRO] Python do ambiente virtual nao foi encontrado.
    echo %PYTHON%
    pause
    exit /b 1
)

if not exist "%APP_FILE%" (
    echo [ERRO] app.py nao foi encontrado.
    echo %APP_FILE%
    pause
    exit /b 1
)

echo Verificando se a porta %PORTA% esta em uso...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORTA%" ^| findstr "LISTENING"') do (
    echo Encerrando processo anterior: %%P
    taskkill /F /PID %%P >nul 2>&1
)

timeout /t 1 /nobreak >nul

echo.
echo Iniciando OSC Fiscal...
echo Acesse: http://127.0.0.1:%PORTA%/
echo.

"%PYTHON%" -m streamlit run "%APP_FILE%" --server.address 127.0.0.1 --server.port %PORTA% --server.headless true

pause
endlocal
