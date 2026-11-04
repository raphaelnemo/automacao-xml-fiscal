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
    set "PYINSTALLER_CMD=%RAIZ%\.venv\Scripts\python.exe -m PyInstaller"
) else (
    set "PYTHON_CMD=python"
    set "PYINSTALLER_CMD=python -m PyInstaller"
)

set "DB_RAIZ=%RAIZ%\segredos\osc_sistema.db"
set "DB_DIST=%RAIZ%\dist\run_app\segredos\osc_sistema.db"
set "PORTA_FILE=%RAIZ%\porta.txt"

if not exist "%RAIZ%\app\app.py" if exist "%RAIZ%\run_app.exe" goto MENU_INSTALADO

:MENU_INSTALADO
if exist "%RAIZ%\app\app.py" goto MENU
if not exist "%RAIZ%\run_app.exe" goto MENU
cls
set "PORTA_ATUAL=8501"
if exist "%PORTA_FILE%" set /p PORTA_ATUAL=<"%PORTA_FILE%"
echo ============================================================
echo                 OSC ERP FISCAL - INSTALADO
echo ============================================================
echo  Porta do ERP: %PORTA_ATUAL%
echo.
echo  [1] Abrir painel do ERP
echo  [2] Iniciar motor agendador
echo  [3] Encerrar ERP e agendador
echo  [0] Sair
echo.
set "opcao="
set /p opcao="Escolha uma opcao [0-3]: "
if "%opcao%"=="1" (
    start "" "%RAIZ%\run_app.exe"
    goto MENU_INSTALADO
)
if "%opcao%"=="2" (
    if not exist "%RAIZ%\agendador.exe" (
        echo [ERRO] O agendador nao foi incluido nesta instalacao. Recompile e gere um novo instalador.
        pause
        goto MENU_INSTALADO
    )
    start "Agendador Fiscal - OSC" "%RAIZ%\agendador.exe"
    echo Agendador iniciado em uma nova janela.
    pause
    goto MENU_INSTALADO
)
if "%opcao%"=="3" (
    taskkill /F /IM run_app.exe /T >nul 2>&1
    taskkill /F /IM agendador.exe /T >nul 2>&1
    echo Processos encerrados.
    pause
    goto MENU_INSTALADO
)
if "%opcao%"=="0" exit /b 0
echo Opcao invalida.
timeout /t 2 >nul
goto MENU_INSTALADO

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
call :ESCOLHER_PASTA_SAIDA
if errorlevel 1 goto MENU
set "BUILD_APP_DIR=%BUILD_OUTPUT_DIR%\run_app"

echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

set "BUILD_WORKPATH=%TEMP%\osc_pyinstaller_producao_%RANDOM%_%RANDOM%"
echo [2/3] Compilando com PyInstaller (Modo Producao - Sem Janela)...
%PYINSTALLER_CMD% --noconfirm --clean --onedir --workpath "%BUILD_WORKPATH%" --distpath "%BUILD_OUTPUT_DIR%" --windowed --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests --hidden-import pandas run_app.py
set "BUILD_EXIT_CODE=%ERRORLEVEL%"
if not "%BUILD_EXIT_CODE%"=="0" (
    echo.
    echo [ERRO] PyInstaller falhou no modo Producao. Codigo de saida: %BUILD_EXIT_CODE%
    echo A sincronizacao pos-compilacao foi interrompida.
    echo Arquivos temporarios: %BUILD_WORKPATH%
    pause
    goto MENU
)
if not exist "%BUILD_APP_DIR%\run_app.exe" (
    echo.
    echo [ERRO] PyInstaller terminou sem gerar "%BUILD_APP_DIR%\run_app.exe".
    echo A sincronizacao foi interrompida.
    pause
    goto MENU
)

echo [3/3] Garantindo estrutura e sincronizando arquivos...
if not exist "%BUILD_APP_DIR%\segredos" mkdir "%BUILD_APP_DIR%\segredos"
if not exist "%BUILD_APP_DIR%\armazenamento" mkdir "%BUILD_APP_DIR%\armazenamento"
if not exist "%BUILD_APP_DIR%\logs" mkdir "%BUILD_APP_DIR%\logs"
if not exist "%BUILD_APP_DIR%\.streamlit" mkdir "%BUILD_APP_DIR%\.streamlit"
if exist "%RAIZ%\.streamlit\config.toml" copy /Y "%RAIZ%\.streamlit\config.toml" "%BUILD_APP_DIR%\.streamlit\config.toml" >nul
if exist "%RAIZ%\ambiente.txt" copy /Y "%RAIZ%\ambiente.txt" "%BUILD_APP_DIR%\ambiente.txt" >nul
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%BUILD_APP_DIR%\gerenciador_mestre.bat" >nul
if exist "%PORTA_FILE%" copy /Y "%PORTA_FILE%" "%BUILD_APP_DIR%\porta.txt" >nul
if exist "%DB_RAIZ%" copy /Y "%DB_RAIZ%" "%BUILD_APP_DIR%\segredos\osc_sistema.db" >nul
call :COMPILAR_AGENDADOR
if errorlevel 1 goto MENU
if /I not "%BUILD_APP_DIR%"=="%RAIZ%\dist\run_app" (
    xcopy /E /H /I /Y /Q "%BUILD_APP_DIR%\*" "%RAIZ%\dist\run_app\" >nul
    if errorlevel 1 (
        echo.
        echo [ERRO] Nao foi possivel sincronizar a compilacao para dist\run_app.
        pause
        goto MENU
    )
)

echo.
echo Executavel salvo em: "%BUILD_APP_DIR%"
echo === COMPILACAO DE PRODUCAO CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:BUILD_DEBUG
cls
call :ESCOLHER_PASTA_SAIDA
if errorlevel 1 goto MENU
set "BUILD_APP_DIR=%BUILD_OUTPUT_DIR%\run_app"

echo [1/3] Encerrando aplicacao em execucao...
taskkill /F /IM run_app.exe /T >nul 2>&1

set "BUILD_WORKPATH=%TEMP%\osc_pyinstaller_debug_%RANDOM%_%RANDOM%"
echo [2/3] Compilando com PyInstaller (Modo Debug - Com Console)...
%PYINSTALLER_CMD% --noconfirm --clean --onedir --workpath "%BUILD_WORKPATH%" --distpath "%BUILD_OUTPUT_DIR%" --console --add-data "app;app" --add-data ".streamlit;.streamlit" --copy-metadata streamlit --copy-metadata reportlab --copy-metadata bcrypt --copy-metadata altair --copy-metadata pandas --copy-metadata pyarrow --collect-all streamlit --collect-all reportlab --collect-all bcrypt --hidden-import sqlite3 --hidden-import requests --hidden-import pandas run_app.py
set "BUILD_EXIT_CODE=%ERRORLEVEL%"
if not "%BUILD_EXIT_CODE%"=="0" (
    echo.
    echo [ERRO] PyInstaller falhou no modo Debug. Codigo de saida: %BUILD_EXIT_CODE%
    echo A sincronizacao pos-compilacao foi interrompida.
    echo Arquivos temporarios: %BUILD_WORKPATH%
    pause
    goto MENU
)
if not exist "%BUILD_APP_DIR%\run_app.exe" (
    echo.
    echo [ERRO] PyInstaller terminou sem gerar "%BUILD_APP_DIR%\run_app.exe".
    echo A sincronizacao foi interrompida.
    pause
    goto MENU
)

echo [3/3] Garantindo estrutura e sincronizando arquivos...
if not exist "%BUILD_APP_DIR%\segredos" mkdir "%BUILD_APP_DIR%\segredos"
if not exist "%BUILD_APP_DIR%\armazenamento" mkdir "%BUILD_APP_DIR%\armazenamento"
if not exist "%BUILD_APP_DIR%\logs" mkdir "%BUILD_APP_DIR%\logs"
if not exist "%BUILD_APP_DIR%\.streamlit" mkdir "%BUILD_APP_DIR%\.streamlit"
if exist "%RAIZ%\.streamlit\config.toml" copy /Y "%RAIZ%\.streamlit\config.toml" "%BUILD_APP_DIR%\.streamlit\config.toml" >nul
if exist "%RAIZ%\ambiente.txt" copy /Y "%RAIZ%\ambiente.txt" "%BUILD_APP_DIR%\ambiente.txt" >nul
copy /Y "%RAIZ%\gerenciador_mestre.bat" "%BUILD_APP_DIR%\gerenciador_mestre.bat" >nul
if exist "%PORTA_FILE%" copy /Y "%PORTA_FILE%" "%BUILD_APP_DIR%\porta.txt" >nul
if exist "%DB_RAIZ%" copy /Y "%DB_RAIZ%" "%BUILD_APP_DIR%\segredos\osc_sistema.db" >nul
call :COMPILAR_AGENDADOR
if errorlevel 1 goto MENU
if /I not "%BUILD_APP_DIR%"=="%RAIZ%\dist\run_app" (
    xcopy /E /H /I /Y /Q "%BUILD_APP_DIR%\*" "%RAIZ%\dist\run_app\" >nul
    if errorlevel 1 (
        echo.
        echo [ERRO] Nao foi possivel sincronizar a compilacao para dist\run_app.
        pause
        goto MENU
    )
)

echo.
echo Executavel salvo em: "%BUILD_APP_DIR%"
echo === COMPILACAO DE DEBUG CONCLUIDA COM SUCESSO! ===
pause
goto MENU


:COMPILAR_AGENDADOR
if not exist "%RAIZ%\agendador.py" (
    echo.
    echo [ERRO] O arquivo agendador.py nao foi encontrado em "%RAIZ%".
    pause
    exit /b 1
)
echo Compilando agendador.exe para incluir no instalador...
%PYINSTALLER_CMD% --noconfirm --clean --onefile --console --workpath "%BUILD_WORKPATH%\agendador" --distpath "%BUILD_APP_DIR%" --name agendador --hidden-import sqlite3 --hidden-import requests "%RAIZ%\agendador.py"
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel compilar agendador.exe.
    pause
    exit /b 1
)
if not exist "%BUILD_APP_DIR%\agendador.exe" (
    echo.
    echo [ERRO] O PyInstaller terminou sem gerar agendador.exe.
    pause
    exit /b 1
)
exit /b 0


:GERAR_INSTALADOR
cls
if not exist "%RAIZ%\dist\run_app\run_app.exe" (
    echo [AVISO] A pasta dist\run_app ainda nao foi compilada.
    echo Execute primeiro a opcao [8] ou [9] para compilar o executavel.
    pause
    goto MENU
)
if not exist "%RAIZ%\dist\run_app\agendador.exe" (
    echo [AVISO] O agendador empacotado nao foi encontrado em dist\run_app.
    echo Execute a opcao [8] ou [9] novamente para compilar ambos os executaveis.
    pause
    goto MENU
)

set "SIGN_CERT_THUMBPRINT="
for /f "usebackq delims=" %%C in (`powershell.exe -NoProfile -Command "$now = Get-Date; $best = $null; foreach ($cert in Get-ChildItem Cert:\CurrentUser\My) { if ($cert.Subject -eq 'CN=MeuCertificadoDev' -and $cert.HasPrivateKey -and $cert.NotBefore -le $now -and $cert.NotAfter -gt $now -and $cert.Thumbprint -match '^[0-9A-Fa-f]{40}$' -and ($null -eq $best -or $cert.NotAfter -gt $best.NotAfter)) { $best = $cert } }; if ($best) { $best.Thumbprint }"`) do set "SIGN_CERT_THUMBPRINT=%%C"
if "%SIGN_CERT_THUMBPRINT%"=="" (
    echo [ERRO] Nao foi encontrado certificado CN=MeuCertificadoDev valido, com chave privada e thumbprint correto, em CurrentUser\My.
    echo Verifique a validade e a instalacao do certificado no repositorio Pessoal deste usuario.
    pause
    goto MENU
)
set "SIGN_CERT_THUMBPRINT=%SIGN_CERT_THUMBPRINT: =%"
echo Certificado selecionado - SHA1: %SIGN_CERT_THUMBPRINT%

set "SIGNTOOL_CMD="
for /f "delims=" %%S in ('where signtool.exe 2^>nul') do if not defined SIGNTOOL_CMD set "SIGNTOOL_CMD=%%~fS"
if "%SIGNTOOL_CMD%"=="" (
    for /d %%V in ("%ProgramFiles(x86)%\Windows Kits\10\bin\*") do if exist "%%~fV\x64\signtool.exe" set "SIGNTOOL_CMD=%%~fV\x64\signtool.exe"
)
if not exist "%SIGNTOOL_CMD%" (
    echo [ERRO] SignTool nao encontrado. Instale o Windows SDK com a ferramenta SignTool.
    echo No Visual Studio Installer, selecione Windows 10/11 SDK.
    echo Caminho localizado: "%SIGNTOOL_CMD%"
    pause
    goto MENU
)
echo SignTool localizado: "%SIGNTOOL_CMD%"

set "ISCC_CMD="
where iscc.exe >nul 2>&1 && set "ISCC_CMD=iscc.exe"
if "%ISCC_CMD%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if "%ISCC_CMD%"=="" if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if "%ISCC_CMD%"=="" if exist "C:\Inno Setup 6\ISCC.exe" set "ISCC_CMD=C:\Inno Setup 6\ISCC.exe"

if "%ISCC_CMD%"=="" (
    echo [ERRO] Inno Setup 6 nao foi encontrado no computador.
    echo Para instalar automaticamente pelo terminal, execute:
    echo   winget install JRSoftware.InnoSetup
    echo Ou baixe em: https://jrsoftware.org/isdl.php
    pause
    goto MENU
)

echo Assinando executavel principal com o certificado CN=MeuCertificadoDev...
"%SIGNTOOL_CMD%" sign /sha1 "%SIGN_CERT_THUMBPRINT%" /s My /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "OSC ERP Fiscal" "%RAIZ%\dist\run_app\run_app.exe"
if errorlevel 1 (
    echo [ERRO] Nao foi possivel assinar dist\run_app\run_app.exe.
    pause
    goto MENU
)
"%SIGNTOOL_CMD%" verify /pa /v "%RAIZ%\dist\run_app\run_app.exe"
if errorlevel 1 (
    echo [ERRO] A assinatura do executavel nao foi validada. Instalador nao sera gerado.
    pause
    goto MENU
)

echo Assinando agendador.exe com o certificado CN=MeuCertificadoDev...
"%SIGNTOOL_CMD%" sign /sha1 "%SIGN_CERT_THUMBPRINT%" /s My /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "OSC ERP Fiscal - Agendador" "%RAIZ%\dist\run_app\agendador.exe"
if errorlevel 1 (
    echo [ERRO] Nao foi possivel assinar dist\run_app\agendador.exe.
    pause
    goto MENU
)
"%SIGNTOOL_CMD%" verify /pa /v "%RAIZ%\dist\run_app\agendador.exe"
if errorlevel 1 (
    echo [ERRO] A assinatura de agendador.exe nao foi validada. Instalador nao sera gerado.
    pause
    goto MENU
)

echo Compilando instalador setup_osc_fiscal.exe com Inno Setup...
"%ISCC_CMD%" "%RAIZ%\setup.iss"
if errorlevel 1 (
    echo [ERRO] O Inno Setup falhou ao gerar o instalador.
    pause
    goto MENU
)
if not exist "%RAIZ%\installer_output\setup_osc_fiscal.exe" (
    echo [ERRO] O instalador nao foi encontrado em installer_output.
    pause
    goto MENU
)

echo Assinando instalador com o certificado CN=MeuCertificadoDev...
"%SIGNTOOL_CMD%" sign /sha1 "%SIGN_CERT_THUMBPRINT%" /s My /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "OSC ERP Fiscal" "%RAIZ%\installer_output\setup_osc_fiscal.exe"
if errorlevel 1 (
    echo [ERRO] Nao foi possivel assinar o instalador.
    pause
    goto MENU
)
"%SIGNTOOL_CMD%" verify /pa /v "%RAIZ%\installer_output\setup_osc_fiscal.exe"
if errorlevel 1 (
    echo [ERRO] A assinatura do instalador nao foi validada.
    pause
    goto MENU
)

echo.
echo === INSTALADOR ASSINADO E VALIDADO: %RAIZ%\installer_output\setup_osc_fiscal.exe ===
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


:ESCOLHER_PASTA_SAIDA
set "BUILD_OUTPUT_DIR="
set "PICKER_FILE=%TEMP%\osc_saida_%RANDOM%_%RANDOM%.txt"
powershell.exe -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $dialog = New-Object System.Windows.Forms.FolderBrowserDialog; $dialog.Description = 'Selecione a pasta para salvar a compilacao'; $dialog.ShowNewFolderButton = $true; if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [System.IO.File]::WriteAllText($env:PICKER_FILE, $dialog.SelectedPath) }"
if errorlevel 1 (
    del /Q "%PICKER_FILE%" >nul 2>&1
    echo [ERRO] Nao foi possivel abrir o seletor de pastas do Windows.
    pause
    exit /b 1
)
if not exist "%PICKER_FILE%" (
    echo Selecao cancelada. Nenhuma compilacao foi iniciada.
    exit /b 1
)
set /p "BUILD_OUTPUT_DIR="<"%PICKER_FILE%"
del /Q "%PICKER_FILE%" >nul 2>&1
if "%BUILD_OUTPUT_DIR%"=="" (
    echo [ERRO] A pasta de saida selecionada esta vazia.
    pause
    exit /b 1
)
exit /b 0


:SAIR
exit
