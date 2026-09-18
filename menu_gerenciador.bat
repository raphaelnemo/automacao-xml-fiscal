@echo off
:: Garante codificacao UTF-8 no Prompt de Comando
chcp 65001 >nul
title Gerenciador do ERP Fiscal

:: Define a pasta onde o BAT está localizado como raiz do projeto
set "RAIZ=%~dp0"
cd /d "%RAIZ%"

:: Define os caminhos relativos baseados na raiz atual
set "PYTHON_VENV=%RAIZ%\.venv\Scripts\python.exe"
set "PYINSTALLER_VENV=%RAIZ%\.venv\Scripts\pyinstaller.exe"
set "DB_RAIZ=%RAIZ%\segredos\osc_sistema.db"
set "DB_DIST=%RAIZ%\dist\run_app\segredos\osc_sistema.db"

:MENU
cls
echo =======================================================
echo         GERENCIADOR DO ERP FISCAL (PORTATIL)
echo =======================================================
echo Pasta Atual: %RAIZ%
echo.
echo  [1] Desbloquear "admin" (Banco da Raiz)
echo  [2] Desbloquear "admin" (Banco do Executavel / DIST)
echo  [3] Resetar senha do "admin" para "admin123"
echo  [4] Recompilar projeto (Modo Console - Debug)
echo  [5] Recompilar projeto (Modo Oculto - Producao)
echo  [6] Testar execucao (dist\run_app\run_app.exe)
echo  [7] Encerrar processos pendentes (taskkill)
echo  [8] Sair
echo.
echo =======================================================
set /p opcao="Escolha uma opcao [1-8]: "

if "%opcao%"=="1" goto DESBLOQUEAR_RAIZ
if "%opcao%"=="2" goto DESBLOQUEAR_DIST
if "%opcao%"=="3" goto RESETAR_SENHA
if "%opcao%"=="4" goto BUILD_CONSOLE
if "%opcao%"=="5" goto BUILD_WINDOWED
if "%opcao%"=="6" goto RODAR_APP
if "%opcao%"=="7" goto KILL_PROCESS
if "%opcao%"=="8" goto SAIR

echo.
echo Opcao invalida! Pressione qualquer tecla para tentar novamente.
pause >nul
goto MENU

:DESBLOQUEAR_RAIZ
cls
echo [1/1] Desbloqueando usuario admin no banco local...
"%PYTHON_VENV%" -c "import sqlite3; conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE username = ?', ('admin',)); conn.commit(); conn.close(); print('-> Usuario admin desbloqueado na RAIZ com sucesso!')"
echo.
pause
goto MENU

:DESBLOQUEAR_DIST
cls
echo [1/1] Desbloqueando usuario admin no banco do executavel...
"%PYTHON_VENV%" -c "import os, shutil, sqlite3; os.makedirs(r'%RAIZ%\dist\run_app\segredos', exist_ok=True); (shutil.copy(r'%DB_RAIZ%', r'%DB_DIST%') if not os.path.exists(r'%DB_DIST%') else None); conn = sqlite3.connect(r'%DB_DIST%'); conn.execute('UPDATE usuarios SET ativo = 1, falhas_login = 0, bloqueado_ate = NULL WHERE username = ?', ('admin',)); conn.commit(); conn.close(); print('-> Usuario admin desbloqueado no DIST com sucesso!')"
echo.
pause
goto MENU

:RESETAR_SENHA
cls
echo [1/1] Resetando senha do usuario admin para "admin123"...
"%PYTHON_VENV%" -c "import sqlite3, bcrypt; hash_pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'); conn = sqlite3.connect(r'%DB_RAIZ%'); conn.execute('UPDATE usuarios SET senha_hash = ? WHERE username = ?', (hash_pw, 'admin')); conn.commit(); conn.close(); print('-> Senha redefinida para admin123 na RAIZ!')"
"%PYTHON_VENV%" -c "import os, sqlite3, bcrypt; (None if not os.path.exists(r'%DB_DIST%') else (hash_pw := bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), conn := sqlite3.connect(r'%DB_DIST%'), conn.execute('UPDATE usuarios SET senha_hash = ? WHERE username = ?', (hash_pw, 'admin')), conn.commit(), conn.close(), print('-> Senha redefinida para admin123 no DIST!')))"
echo.
pause
goto MENU

:BUILD_CONSOLE
cls
echo [1/2] Encerrando executaveis antigos...
taskkill /F /IM run_app.exe /T >nul 2>&1
echo [2/2] Compilando com PyInstaller (Modo Console)...
"%PYINSTALLER_VENV%" --noconfirm --onedir --console --add-data "app;app" --copy-metadata streamlit --collect-all streamlit --collect-all reportlab --collect-all bcrypt run_app.py
echo.
echo Build concluido!
pause
goto MENU

:BUILD_WINDOWED
cls
echo [1/2] Encerrando executaveis antigos...
taskkill /F /IM run_app.exe /T >nul 2>&1
echo [2/2] Compilando com PyInstaller (Modo Oculto - Producao)...
"%PYINSTALLER_VENV%" --noconfirm --onedir --windowed --add-data "app;app" --copy-metadata streamlit --collect-all streamlit --collect-all reportlab --collect-all bcrypt run_app.py
echo.
echo Build para producao concluido!
pause
goto MENU

:RODAR_APP
cls
echo Iniciando executavel compilado...
start "" "%RAIZ%\dist\run_app\run_app.exe"
goto MENU

:KILL_PROCESS
cls
echo Encerrando processos do run_app.exe em execucao...
taskkill /F /IM run_app.exe /T
echo.
pause
goto MENU

:SAIR
exit