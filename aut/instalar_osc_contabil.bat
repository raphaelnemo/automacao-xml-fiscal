@echo off
chcp 65001 >nul
TITLE Instalador - OSC Assessoria Contábil

set "BASE_DIR=C:\OSC\automacao_xml_producao"

echo =======================================================
echo   Instalador do Sistema - OSC Assessoria Contábil
echo =======================================================
echo.

echo [1/4] Criando estrutura de pastas blindada...
mkdir "%BASE_DIR%\app" 2>nul
mkdir "%BASE_DIR%\segredos" 2>nul
mkdir "%BASE_DIR%\logs" 2>nul
mkdir "%BASE_DIR%\armazenamento" 2>nul
cd /d "%BASE_DIR%"

echo [2/4] Criando ambiente virtual Python isolado...
python -m venv .venv

echo [3/4] Instalando dependencias de seguranca e dados...
call .venv\Scripts\activate.bat
pip install streamlit pandas bcrypt

echo [4/4] Definindo arquivo de ambiente...
echo PRODUCAO> ambiente.txt

echo.
echo Instalacao estrutural concluida em: %BASE_DIR%
echo Coloque seu codigo "app.py" dentro da pasta "app" antes de iniciar.
pause