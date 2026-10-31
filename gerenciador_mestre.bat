@echo off
chcp 65001 >nul
title Gerenciador Mestre - ERP OSC Fiscal

:: Identifica dinamicamente a pasta raiz onde o .bat esta salvo
set "RAIZ=%~dp0"
if "%RAIZ:~-1%"=="\" set "RAIZ=%RAIZ:~0,-1%"
cd /d "%RAIZ%"

:: Detecta Python (usa .venv se existir, senao usa python global do sistema)
if exist "%RAIZ%\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%RAIZ%\.venv\Scripts\python.exe"
    set "PYINSTALLER_CMD=%RAIZ%\.venv\Scripts\pyinstaller.exe"
) else (
    set "PYTHON_CMD=python"
    set "PYINSTALLER_CMD=pyinstaller"
)

set "DB_RAIZ=%RAIZ%\segredos\osc_sistema.db"
set "DB_DIST=%RAIZ%\dist\run_app\segredos\osc_sistema.db"
set "PORTA_FILE=%RAIZ%\porta.txt"

:MENU
cls
:: Leitura dinamica de Porta e Ambiente para exibir no cabecalho
set "PORTA_ATUAL=8501"
if exist "%PORTA_FILE%" (
    set /p PORTA_ATUAL=<"%PORTA_FILE%"
)
set "AMB_ATUAL=HOMOLOGACAO"
if exist "%RAIZ%\ambiente.txt" (
    set /p AMB_ATUAL=<"%RAIZ%\ambiente.txt"
)

echo ======================================================================
echo                 GERENCIADOR MESTRE - ERP OSC FISCAL
echo ======================================================================
echo  Diretorio : %RAIZ%
echo  Ambiente  : %AMB_ATUAL%   ^|   Porta Streamlit: %PORTA_ATUAL%
echo ======================================================================
echo.
echo  --- EXECUCAO E SERVICOS (MODO DESENVOLVIMENTO / SERVIDOR) ---
echo  [1] Iniciar Painel ERP no navegador (Porta %PORTA_ATUAL%)
echo  [2] Iniciar Motor Agendador de Consultas (agendador.py)
echo  [3] Iniciar Servidor Mock Sefaz/ADN na porta 5000 (Testes)
echo  [4] Alterar Porta do Streamlit (Atual: %PORTA_ATUAL%)
echo.
echo  --- ACESSO, SEGURANCA E BANCO DE DADOS ---
echo  [5] Desbloquear e Reativar "admin" (Zera falhas e inatividade)
echo  [6] Voltar "admin" para Configuracao de Primeiro Acesso (Sem senha)
echo  [7] Fazer Backup Instantaneo do Banco de Dados (segredos\backups)
echo.
echo  --- COMPILACAO E INSTALADOR (.EXE) ---
echo  [8] Compilar Executavel PRODUCAO (Janela oculta / Windowed)
echo  [9] Compilar Executavel DEBUG (Exibe console de diagnostico)
echo  [10] Gerar Instalador Windows (setup_osc_fiscal.exe via Inno Setup)
echo  [11] Limpar pastas temporarias de compilacao (build e dist)
echo.
echo  --- EXECUTAVEL E PROCESSOS ---
echo  [12] Executar aplicacao compilada (run_app.exe)
echo  [13] Encerrar todos os processos ativos (taskkill)
echo  [0] Sair
echo.
echo ======================================================================
set "opcao="
set /p opcao="Escolha uma opcao [0-13]: "

if "%opcao%"=="1" goto INICIAR_ERP
if "%opcao%"=="2" goto INICIAR_AGENDADOR
if "%opcao%"=="3" goto INICIAR_MOCK
if "%opcao%"=="4" goto ALTERAR_PORTA
if "%opcao%"=="5" goto DESBLOQUEAR
if "%opcao%"=="6" goto RESETAR_PRIMEIRO_ACESSO
if "%opcao%"=="7" goto BACKUP_DB
if "%opcao%"=="8" goto BUILD_PRODUCAO
if "%opcao%"=="9" goto BUILD_DEBUG
if "%opcao%"=="10" goto GERAR_INSTALADOR
if "%opcao%"=="11" goto LIMPAR
if "%opcao%"=="12" goto EXECUTAR_EXE
if "%opcao%"=="13" goto KILL
if "%opcao%"=="0" goto SAIR

echo.
echo [AVISO] Opcao invalida!
timeout /t 2 >nul
goto MENU


:INICIAR_ERP
cls
if not exist "%RAIZ%\app\app.py" (
    echo [AVISO] Codigo-fonte app\app.py nao encontrado nesta pasta.
    echo Tentando iniciar pelo executavel compilado...
    goto EXECUTAR_EXE
)
echo Iniciando Painel ERP na porta %PORTA_ATUAL%...
start "Painel ERP - OSC Fiscal (Porta %PORTA_ATUAL%)" "%PYTHON_CMD%" -m streamlit run "%RAIZ%\app\app.py" --server.port %PORTA_ATUAL% --server.address 0.0.0.0
echo.
echo Servidor iniciado em nova janela! Acesse: http://localhost:%PORTA_ATUAL%
pause
goto MENU


:INICIAR_AGENDADOR
cls
if not exist "%RAIZ%\agendador.py" (
    echo [ERRO] O arquivo agendador.py nao foi encontrado em %RAIZ%.
    pause
    goto MENU
)
echo Iniciando Motor de Agendamento em segundo plano...
start "Agendador Fiscal - OSC" "%PYTHON_CMD%" "%RAIZ%\agendador.py"
echo Agendador iniciado em nova janela!
pause
goto MENU


:INICIAR_MOCK
cls
if not exist "%RAIZ%\mock_sefaz_server.py" (
    echo [ERRO] O arquivo mock_sefaz_server.py nao foi encontrado em %RAIZ%.
    pause
    goto MENU
)
echo Iniciando Servidor Mock Sefaz/ADN na porta 5000...
start "Mock Sefaz Server (Porta 5000)" "%PYTHON_CMD%" "%RAIZ%\mock_sefaz_server.py"
echo Servidor Mock iniciado em: http://localhost:5000/status
pause
goto MENU


:ALTERAR_PORTA
cls
echo ======================================================================
echo                  ALTERAR PORTA DO SERVIDOR STREAMLIT
echo ======================================================================
echo Porta atual configurada: %PORTA_ATUAL%
echo (Portas comuns recomendadas: 8501, 8502, 8080, 8090)
echo.
set "NOVA_PORTA="
set /p NOVA_PORTA="Digite a nova porta (entre 1024 e 65535) ou ENTER para cancelar: "
if "%NOVA_PORTA%"=="" goto MENU

:: Valida e grava usando Python para atualizar tanto porta.txt quanto .streamlit\config.toml
"%PYTHON_CMD%" -c "import sys, pathlib, re; p = sys.argv[1].strip(); sys.exit(0 if (p.isdigit() and 1024 <= int(p) <= 65535) else 1)" "%NOVA_PORTA%"
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Porta invalida! Informe apenas numeros entre 1024 e 65535.
    pause
    goto MENU
)

echo %NOVA_PORTA%> "%PORTA_FILE%"
if exist "%RAIZ%\dist\run_app" (
    echo %NOVA_PORTA%> "%RAIZ%\dist\run_app\porta.txt"
)

if exist "%RAIZ%\.streamlit\config.toml" (
    "%PYTHON_CMD%" -c "import pathlib, re; p = pathlib.Path(r'%RAIZ%\.streamlit\config.toml'); txt = p.read_text(encoding='utf-8'); txt = re.sub(r'port\s*=\s*\d+', 'port=' + '%NOVA_PORTA%', txt) if 'port' in txt else txt + '\n[server]\nport=%NOVA_PORTA%\n'; p.write_text(txt, encoding='utf-8')"
)

echo.
echo [SUCESSO] Porta alterada para %NOVA_PORTA%!
echo Reinicie o painel ERP caso ele ja esteja aberto.
pause
goto MENU


:DESBLOQUEAR
cls
echo [1/2] Encerrando executaveis em segundo plano para liberar o banco...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Aplicando desbloqueio e reativacao nos bancos SQLite...
if exist "%DB_RAIZ%" (
    "%PYTHON_CMD%" -c "import sqlite3, datetime; ts = datetime.datetime.now().astimezone().isoformat(timespec='seconds'); conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL, ultimo_acesso = ? WHERE username = ?', (ts, 'admin')); conn.commit(); conn.close(); print('-> Banco Principal: Admin reativado e desbloqueado!')"
) else (
    echo [AVISO] Banco principal ainda nao existe em: %DB_RAIZ%
)
if exist "%DB_DIST%" (
    "%PYTHON_CMD%" -c "import sqlite3, datetime; ts = datetime.datetime.now().astimezone().isoformat(timespec='seconds'); conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL, ultimo_acesso = ? WHERE username = ?', (ts, 'admin')); conn.commit(); conn.close(); print('-> Banco Dist: Admin reativado e desbloqueado!')"
)
echo.
pause
goto MENU


:RESETAR_PRIMEIRO_ACESSO
cls
echo [1/2] Encerrando processos antigos...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Redefinindo para exigir configuracao de senha no proximo acesso...
if exist "%DB_RAIZ%" (
    "%PYTHON_CMD%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE perfil = ?', ('', 'admin')); conn.execute('DELETE FROM sessoes_ativas'); conn.commit(); conn.close(); print('-> Banco Principal: Pronto para configurar nova senha no primeiro login!')"
) else (
    echo [AVISO] Banco principal ainda nao existe em: %DB_RAIZ%
)
if exist "%DB_DIST%" (
    "%PYTHON_CMD%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE perfil = ?', ('', 'admin')); conn.execute('DELETE FROM sessoes_ativas'); conn.commit(); conn.close(); print('-> Banco Dist: Pronto para configurar nova senha no primeiro login!')"
)
echo.
pause
goto MENU


:BACKUP_DB
cls
if not exist "%DB_RAIZ%" (
    echo [ERRO] Banco de dados nao encontrado em: %DB_RAIZ%
    pause
    goto MENU
)
if not exist "%RAIZ%\segredos\backups" mkdir "%RAIZ%\segredos\backups"
"%PYTHON_CMD%" -c "import sqlite3, datetime, pathlib; ts = datetime.datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'); dest = pathlib.Path(r'%RAIZ%\segredos\backups') / f'osc_sistema_backup_{ts}.db'; src_conn = sqlite3.connect(r'%DB_RAIZ%'); dst_conn = sqlite3.connect(dest); src_conn.backup(dst_conn); dst_conn.close(); src_conn.close(); print(f'[SUCESSO] Backup seguro gravado em:\n -> {dest}')"
echo.
pause
goto MENU


:BUILD_PRODUCAO
cls
echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/3] Compilando com PyInstaller (Modo Producao - Sem Janela)...
"%PYINSTALLER_CMD%" --noconfirm --clean --onedir --windowed --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests run_app.py

echo [3/3] Garantindo estrutura e sincronizando arquivos...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%RAIZ%\dist\run_app\gerenciador_mestre.bat" >nul
if exist "%PORTA_FILE%" copy /Y "%PORTA_FILE%" "%RAIZ%\dist\run_app\porta.txt" >nul
if exist "%DB_RAIZ%" copy /Y "%DB_RAIZ%" "%DB_DIST%" >nul

echo.
echo === COMPILACAO DE PRODUCAO CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:BUILD_DEBUG
cls
echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/3] Compilando com PyInstaller (Modo Debug - Com Console)...
"%PYINSTALLER_CMD%" --noconfirm --clean --onedir --console --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests run_app.py

echo [3/3] Garantindo estrutura e sincronizando arquivos...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%RAIZ%\dist\run_app\gerenciador_mestre.bat" >nul
if exist "%PORTA_FILE%" copy /Y "%PORTA_FILE%" "%RAIZ%\dist\run_app\porta.txt" >nul
if exist "%DB_RAIZ%" copy /Y "%DB_RAIZ%" "%DB_DIST%" >nul

echo.
echo === COMPILACAO DE DEBUG CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:GERAR_INSTALADOR
cls
if not exist "%RAIZ%\dist\run_app\run_app.exe" (
    echo [AVISO] A pasta dist\run_app ainda nao foi compilada.
    echo Execute primeiro a opcao [8] ou [9] para compilar o executavel.
    pause
    goto MENU
)

set "ISCC_CMD="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC_CMD%"=="" (
    echo [ERRO] Inno Setup 6 nao foi encontrado no computador.
    echo Para instalar automaticamente pelo terminal, execute:
    echo   winget install JRSoftware.InnoSetup
    echo Ou baixe em: https://jrsoftware.org/isdl.php
    pause
    goto MENU
)

echo Compilando instalador setup_osc_fiscal.exe com Inno Setup...
"%ISCC_CMD%" "%RAIZ%\setup.iss"
echo.
echo === INSTALADOR GERADO EM: %RAIZ%\installer_output\setup_osc_fiscal.exe ===
pause
goto MENU


:LIMPAR
cls
echo [1/2] Fechando executaveis ativos...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Apagando pastas de build temporarias...
if exist "%RAIZ%\build" rmdir /s /q "%RAIZ%\build"
if exist "%RAIZ%\dist" rmdir /s /q "%RAIZ%\dist"
echo Limpeza concluida!
pause
goto MENU


:EXECUTAR_EXE
cls
if exist "%RAIZ%\run_app.exe" (
    echo Iniciando aplicacao local run_app.exe na porta %PORTA_ATUAL%...
    start "" "%RAIZ%\run_app.exe"
    goto MENU
)
if exist "%RAIZ%\dist\run_app\run_app.exe" (
    echo Iniciando aplicacao em dist\run_app\run_app.exe na porta %PORTA_ATUAL%...
    start "" "%RAIZ%\dist\run_app\run_app.exe"
    goto MENU
)
echo [ERRO] O executavel run_app.exe nao foi encontrado. Execute a opcao [8] ou [9] primeiro.
pause
goto MENU


:KILL
cls
echo Encerrando processos do executavel run_app.exe...
taskkill /F /IM run_app.exe /T >nul 2>&1
echo Processos encerrados.
pause
goto MENU


:SAIR
exit
