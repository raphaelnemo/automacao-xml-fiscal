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
echo  [1] Desbloquear "admin" (Zera falhas e libera acesso)
echo  [2] Resetar senha do "admin" para "admin123"
echo.
echo  --- COMPILACAO E EMPACOTAMENTO ---
echo  [3] Compilar Modo PRODUCAO (Janela oculta / Windowed)
echo  [4] Compilar Modo DEBUG (Exibe janela do console)
echo  [5] Limpar pastas de build temporarias (build e dist)
echo.
echo  --- SISTEMA E PROCESSOS ---
echo  [6] Executar aplicacao compilada (dist\run_app\run_app.exe)
echo  [7] Encerrar todos os processos do app (taskkill)
echo  [8] Sair
echo.
echo =======================================================
set /p opcao="Escolha uma opcao [1-8]: "

if "%opcao%"=="1" goto DESBLOQUEAR
if "%opcao%"=="2" goto RESETAR_SENHA
if "%opcao%"=="3" goto BUILD_PRODUCAO
if "%opcao%"=="4" goto BUILD_DEBUG
if "%opcao%"=="5" goto LIMPAR
if "%opcao%"=="6" goto EXECUTAR
if "%opcao%"=="7" goto KILL
if "%opcao%"=="8" goto SAIR

echo.
echo Opcao invalida!
pause
goto MENU


:DESBLOQUEAR
cls
echo [1/2] Encerrando executaveis em segundo plano para liberar o banco...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Aplicando desbloqueio nos bancos SQLite...
if exist "%DB_RAIZ%" (
    "%PYTHON_VENV%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = ? WHERE username = ?', ('1970-01-01 00:00:00', 'admin')); conn.commit(); conn.close(); print('-> Banco Raiz: Admin liberado!')"
)
if exist "%DB_DIST%" (
    "%PYTHON_VENV%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = ? WHERE username = ?', ('1970-01-01 00:00:00', 'admin')); conn.commit(); conn.close(); print('-> Banco Dist: Admin liberado!')"
)
echo.
echo Processo concluido com sucesso.
pause
goto MENU


:RESETAR_SENHA
cls
echo [1/2] Encerrando processos antigos...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/2] Redefinindo senha do usuario admin para 'admin123'...
if exist "%DB_RAIZ%" (
    "%PYTHON_VENV%" -c "import sqlite3, bcrypt; hash_pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'); conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0 WHERE username = ?', (hash_pw, 'admin')); conn.commit(); conn.close(); print('-> Banco Raiz: Senha alterada para admin123!')"
)
if exist "%DB_DIST%" (
    "%PYTHON_VENV%" -c "import sqlite3, bcrypt; hash_pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'); conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET senha_hash = ?, ativo = 1, falhas_login = 0 WHERE username = ?', (hash_pw, 'admin')); conn.commit(); conn.close(); print('-> Banco Dist: Senha alterada para admin123!')"
)
echo.
pause
goto MENU


:BUILD_PRODUCAO
cls
echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

echo [2/3] Compilando com PyInstaller (Modo Producao - Sem Janela)...
"%PYINSTALLER_VENV%" --noconfirm --onedir --windowed --add-data "app;app" --copy-metadata streamlit --collect-all streamlit --collect-all reportlab --collect-all bcrypt run_app.py

echo [3/3] Garantindo estrutura e sincronizando banco de dados...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"

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
"%PYINSTALLER_VENV%" --noconfirm --onedir --console --add-data "app;app" --copy-metadata streamlit --collect-all streamlit --collect-all reportlab --collect-all bcrypt run_app.py

echo [3/3] Garantindo estrutura e sincronizando banco de dados...
if not exist "%RAIZ%\dist\run_app\segredos" mkdir "%RAIZ%\dist\run_app\segredos"
if not exist "%RAIZ%\dist\run_app\armazenamento" mkdir "%RAIZ%\dist\run_app\armazenamento"
if not exist "%RAIZ%\dist\run_app\logs" mkdir "%RAIZ%\dist\run_app\logs"

if exist "%DB_RAIZ%" (
    copy /Y "%DB_RAIZ%" "%DB_DIST%" >nul
)

echo.
echo === COMPILACAO DE DEBUG CONCLUIDA COM SUCESSO! ===
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
echo Iniciando aplicação em dist\run_app\run_app.exe...
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