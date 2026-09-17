@echo off
chcp 65001 >nul
TITLE Recuperacao de Emergencia - OSC Assessoria Contabil

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

cd /d "%BASE_DIR%"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERRO] Ambiente virtual .venv nao encontrado nesta pasta!
    pause
    exit /b
)

echo =======================================================
echo   Redefinicao Administrativa - OSC Assessoria Contabil
echo =======================================================
echo.

:: Script Python inline sem caracteres especiais conflitantes
(
echo import sqlite3, bcrypt, sys, re, datetime
echo from pathlib import Path
echo db_path = Path(r"%BASE_DIR%\segredos\osc_sistema.db"^)
echo if not db_path.exists(^):
echo     print("Erro: Banco de dados nao encontrado em:"^)
echo     print(db_path^)
echo     sys.exit(1^)
echo print("A nova senha exige: 12 caracteres, maiuscula, minuscula, numero e caractere especial."^)
echo nova_senha = input("Digite a nova senha para o usuario 'admin': "^)
echo if len(nova_senha^) ^< 12 or not re.search(r"[A-Z]", nova_senha^) or not re.search(r"[a-z]", nova_senha^) or not re.search(r"\d", nova_senha^) or not re.search(r"[^A-Za-z0-9]", nova_senha^):
echo     print("ERRO DE SEGURANCA: A senha nao atende a politica de complexidade."^)
echo     sys.exit(1^)
echo hash_senha = bcrypt.hashpw(nova_senha.encode('utf-8'^), bcrypt.gensalt(^)^).decode('utf-8'^)
echo data_iso = datetime.datetime.now(^).astimezone(^).isoformat(timespec="seconds"^)
echo conn = sqlite3.connect(db_path^)
echo cursor = conn.cursor(^)
echo cursor.execute("UPDATE usuarios SET senha_hash=?, deve_trocar_senha=1, falhas_login=0, bloqueado_ate=NULL, ativo=1 WHERE username='admin'", (hash_senha,^)^)
echo if cursor.rowcount == 0:
echo     print("Usuario 'admin' nao existe no banco!"^)
echo else:
echo     cursor.execute("INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes, ip_origem, status) VALUES (?, ?, ?, ?, ?, ?)", (data_iso, 'SISTEMA', 'recuperacao_emergencia', 'Senha do admin restaurada por terminal local', 'localhost', 'sucesso'^)^)
echo     conn.commit(^)
echo     print("\nSucesso! Senha alterada. A troca sera exigida no proximo login."^)
echo conn.close(^)
) > reset_admin.py

python reset_admin.py
if exist reset_admin.py del reset_admin.py

echo.
pause