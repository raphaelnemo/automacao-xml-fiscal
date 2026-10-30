@echo off
chcp 65001 >nul
TITLE Instalador - OSC Assessoria Contábil

set "BASE_DIR=%~dp0.."
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"

echo =======================================================
echo   Instalador do Sistema - OSC Assessoria Contábil
echo =======================================================
echo Diretorio alvo: %BASE_DIR%
echo.

echo [1/4] Criando estrutura de pastas blindada...
mkdir "%BASE_DIR%\app" 2>nul
mkdir "%BASE_DIR%\segredos" 2>nul
mkdir "%BASE_DIR%\logs" 2>nul
mkdir "%BASE_DIR%\armazenamento" 2>nul
cd /d "%BASE_DIR%"

echo [2/4] Criando ambiente virtual Python isolado...
if not exist "%BASE_DIR%\.venv\Scripts\python.exe" (
    python -m venv .venv
)

echo [3/4] Instalando dependencias de seguranca, relatorios e dados...
"%BASE_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%BASE_DIR%\.venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [4/4] Definindo arquivo de ambiente padrao...
if not exist "%BASE_DIR%\ambiente.txt" (
    echo HOMOLOGACAO> "%BASE_DIR%\ambiente.txt"
)

echo.
echo Instalacao estrutural concluida com sucesso em: %BASE_DIR%
pause
