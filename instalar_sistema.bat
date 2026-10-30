@echo off
chcp 65001 >nul
title Instalador do Sistema Fiscal - OSC Assessoria Contabil
color 0A

set "RAIZ=%~dp0"
if "%RAIZ:~-1%"=="\" set "RAIZ=%RAIZ:~0,-1%"
cd /d "%RAIZ%"

echo [1/3] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado neste computador! Instale o Python 3.11+ marcando "Add Python to PATH".
    pause
    exit /b 1
)

echo [2/3] Criando e configurando ambiente virtual (.venv)...
if not exist "%RAIZ%\.venv\Scripts\python.exe" (
    python -m venv .venv
)

echo [3/3] Instalando todas as bibliotecas necessarias...
"%RAIZ%\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%RAIZ%\.venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.

(
echo @echo off
echo cd /d "%%~dp0"
echo ".\.venv\Scripts\python.exe" -m streamlit run app/app.py --server.address 0.0.0.0 --server.port 8501
echo pause
) > iniciar_servidor.bat

echo Instalacao concluida com sucesso! De dois cliques em 'iniciar_servidor.bat'.
pause
