@echo off
chcp 65001 >nul
TITLE Servidor - OSC Assessoria Contábil

:: Proteção: Verifica se o script está rodando como Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO CRITICO] O servidor precisa de privilegios para configurar o Firewall e ACLs.
    echo Por favor, clique com o botao direito neste arquivo e selecione "Executar como Administrador".
    pause
    exit /b
)

set "BASE_DIR=C:\OSC\automacao_xml_producao"
:: IMPORTANTE: Altere este IP para o IP fixo real do servidor (ex: 192.168.0.10)
set "IP_SERVIDOR=192.168.0.10" 

echo =======================================================
echo   Iniciando Servidor - OSC Assessoria Contábil
echo =======================================================
echo.

echo [1/3] Aplicando Defesa em Profundidade (ACLs) na pasta de Segredos...
:: Remove a herança de rede e garante acesso APENAS aos Administradores e ao Sistema.
icacls "%BASE_DIR%\segredos" /inheritance:r /grant:r "Administradores":(OI)(CI)F /grant:r "SYSTEM":(OI)(CI)F /c /q

echo [2/3] Blindando Firewall (Porta 8501 restrita a Rede Interna)...
netsh advfirewall firewall delete rule name="OSC Assessoria Contabil" >nul 2>&1
netsh advfirewall firewall add rule name="OSC Assessoria Contabil" dir=in action=allow protocol=TCP localport=8501 remoteip=LocalSubnet profile=private,domain >nul 2>&1

echo [3/3] Subindo aplicacao no IP %IP_SERVIDOR%...
cd /d "%BASE_DIR%"
call .venv\Scripts\activate.bat

echo.
echo O ERP estara disponivel para os operadores da rede em: http://%IP_SERVIDOR%:8501
echo.

cd app
python -m streamlit run app.py --server.port 8501 --server.address %IP_SERVIDOR% --server.headless true

pause