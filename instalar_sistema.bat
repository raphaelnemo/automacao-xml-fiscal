@echo off
title Instalador do Sistema Fiscal - OSC Assessoria Contabil
color 0A

echo [1/2] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado neste computador!
    pause
    exit
)

echo [2/2] Instalando todas as bibliotecas necessarias...
python -m pip install --upgrade pip
python -m pip install requests flask streamlit pandas xlsxwriter reportlab streamlit-aggrid
echo.

echo (
echo @echo off
echo cd /d "%%~dp0"
echo python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
echo pause
) > iniciar_servidor.bat

echo Instalacao concluida! De dois cliques em 'iniciar_servidor.bat'.
pause