@echo off
chcp 65001 >nul
title Gerenciador Unificado - ERP OSC Fiscal

:: Identifica dinamicamente a pasta raiz onde o .bat esta salvo
set "RAIZ=%~dp0"
if "%RAIZ:~-1%"=="\" set "RAIZ=%RAIZ:~0,-1%"
cd /d "%RAIZ%"

:: Caminhos relativos ao ambiente virtual e arquivos
set "PYTHON_VENV=%RAIZ%\.venv\Scripts\python.exe"
set "PYINSTALLER_VENV=%RAIZ%\.venv\Scripts\pyinstaller.exe"
set "DB_RAIZ=%RAIZ%\segredos\osc_sistema.db"
set "DB_DIST=%RAIZ%\dist\run_app\segredos\osc_sistema.db"

:MENU
cls
echo =======================================================
echo          GERENCIADOR MESTRE - ERP FISCAL
echo =======================================================
echo  Diretorio: %RAIZ%
echo =======================================================
echo.
echo  --- ACESSO E MANUTENCAO DE USUARIOS ---
echo  [1] Desbloquear e Reativar "admin" (Zera falhas e inatividade)
echo  [2] Voltar "admin" para Configuracao de Primeiro Acesso (Sem senha)
echo.
echo  --- COMPILACAO E INSTALADOR (.EXE) ---
echo  [3] Compilar Modo PRODUCAO (Janela oculta / Windowed)
echo  [4] Compilar Modo DEBUG (Exibe janela do console)
echo  [5] Gerar Instalador Windows (setup_osc_fiscal.exe via Inno Setup)
echo  [6] Limpar pastas de build temporarias (build e dist)
echo.
echo  --- SISTEMA E PROCESSOS ---
echo  [7] Executar aplicacao compilada (dist\run_app\run_app.exe)
echo  [8] Encerrar todos os processos do app (taskkill)
echo  [9] Sair
echo.
echo =======================================================
set /p opcao="Escolha uma opcao [1-9]: "

if "%opcao%"=="1" goto DESBLOQUEAR
if "%opcao%"=="2" goto RESETAR_PRIMEIRO_ACESSO
if "%opcao%"=="3" goto BUILD_PRODUCAO
if "%opcao%"=="4" goto BUILD_DEBUG
if "%opcao%"=="5" goto GERAR_INSTALADOR
if "%opcao%"=="6" goto LIMPAR
if "%opcao%"=="7" goto EXECUTAR
if "%opcao%"=="8" goto KILL
if "%opcao%"=="9" goto SAIR

echo.
echo Opcao invalida!
pause
goto MENU


:DESBLOQUEAR
cls
echo [1/2] Encerrando executaveis em segundo plano para liberar o banco...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Aplicando desbloqueio e reativacao nos bancos SQLite...
if exist "%DB_RAIZ%" (
    "%PYTHON_VENV%" -c "import sqlite3, datetime; ts = datetime.datetime.now().astimezone().isoformat(timespec='seconds'); conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL, ultimo_acesso = ? WHERE username = ?', (ts, 'admin')); conn.commit(); conn.close(); print('-> Banco Raiz: Admin reativado e desbloqueado!')"
)
if exist "%DB_DIST%" (
    "%PYTHON_VENV%" -c "import sqlite3, datetime; ts = datetime.datetime.now().astimezone().isoformat(timespec='seconds'); conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL, ultimo_acesso = ? WHERE username = ?', (ts, 'admin')); conn.commit(); conn.close(); print('-> Banco Dist: Admin reativado e desbloqueado!')"
)
echo.
echo Processo concluido com sucesso.
pause
goto MENU


:RESETAR_PRIMEIRO_ACESSO
cls
echo [1/2] Encerrando processos antigos...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Redefinindo para exigir configuracao de senha no proximo acesso...
if exist "%DB_RAIZ%" (
    "%PYTHON_VENV%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE perfil = ?', ('', 'admin')); conn.commit(); conn.close(); print('-> Banco Raiz: Pronto para configurar nova senha no primeiro login!')"
)
if exist "%DB_DIST%" (
    "%PYTHON_VENV%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE perfil = ?', ('', 'admin')); conn.commit(); conn.close(); print('-> Banco Dist: Pronto para configurar nova senha no primeiro login!')"
)
echo.
pause
goto MENU


:BUILD_PRODUCAO
cls
echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/3] Compilando com PyInstaller (Modo Producao - Sem Janela)...
"%PYINSTALLER_VENV%" --noconfirm --clean --onedir --windowed --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests run_app.py

echo [3/3] Garantindo estrutura e sincronizando banco de dados...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%RAIZ%\dist\run_app\gerenciador_mestre.bat" >nul

if exist "%DB_RAIZ%" (
    copy /Y "%DB_RAIZ%" "%DB_DIST%" >nul
)

echo.
echo === COMPILACAO DE PRODUCAO CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:BUILD_DEBUG
cls
echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/3] Compilando com PyInstaller (Modo Debug - Com Console)...
"%PYINSTALLER_VENV%" --noconfirm --clean --onedir --console --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests run_app.py

echo [3/3] Garantindo estrutura e sincronizando banco de dados...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%RAIZ%\dist\run_app\gerenciador_mestre.bat" >nul

if exist "%DB_RAIZ%" (
    copy /Y "%DB_RAIZ%" "%DB_DIST%" >nul
)

echo.
echo === COMPILACAO DE DEBUG CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:GERAR_INSTALADOR
cls
if not exist "%RAIZ%\dist\run_app\run_app.exe" (
    echo [AVISO] A pasta dist\run_app ainda nao foi compilada.
    echo Execute primeiro a opcao [3] ou [4] para compilar o executavel.
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


:EXECUTAR
cls
if not exist "%RAIZ%\dist\run_app\run_app.exe" (
    echo [ERRO] O executavel nao foi encontrado. Execute a opcao 3 ou 4 primeiro.
    pause
    goto MENU
)
echo Iniciando aplicacao em dist\run_app\run_app.exe...
start "" "%RAIZ%\dist\run_app\run_app.exe"
goto MENU


:KILL
cls
echo Encerrando todos os processos do executavel...
taskkill /F /IM run_app.exe /T
echo.
pause
goto MENU


:SAIR
exit
