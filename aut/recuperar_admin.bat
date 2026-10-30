@echo off
chcp 65001 >nul
TITLE Recuperacao de Emergencia - OSC Assessoria Contábil

set "BASE_DIR=%~dp0.."
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"
cd /d "%BASE_DIR%"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo =======================================================
echo   Redefinicao Administrativa - OSC Assessoria Contábil
echo =======================================================
echo.

echo import sqlite3, bcrypt, sys, re, datetime > reset_admin.py
echo from pathlib import Path >> reset_admin.py
echo db_path = Path(r"%BASE_DIR%\segredos\osc_sistema.db") >> reset_admin.py
echo if not db_path.exists(): >> reset_admin.py
echo     print("Erro: Banco de dados nao encontrado.") >> reset_admin.py
echo     sys.exit(1) >> reset_admin.py
echo print("A nova senha exige: 12 caracteres, maiuscula, minuscula, numero e caractere especial.") >> reset_admin.py
echo nova_senha = input("Digite a nova senha para o usuario 'admin' (ou deixe em branco para reconfigurar pela web): ").strip() >> reset_admin.py
echo data_iso = datetime.datetime.now().astimezone().isoformat(timespec="seconds") >> reset_admin.py
echo conn = sqlite3.connect(db_path) >> reset_admin.py
echo cursor = conn.cursor() >> reset_admin.py
echo if not nova_senha: >> reset_admin.py
echo     cursor.execute("UPDATE usuarios SET senha_hash='', deve_trocar_senha=0, falhas_login=0, bloqueado_ate=NULL, ativo=1, ultimo_acesso=? WHERE username='admin'", (data_iso,)) >> reset_admin.py
echo     conn.commit() >> reset_admin.py
echo     print("\nSucesso! Acesse o painel no navegador para definir a nova senha no primeiro login.") >> reset_admin.py
echo     conn.close() >> reset_admin.py
echo     sys.exit(0) >> reset_admin.py
echo if len(nova_senha) ^< 12 or not re.search(r"[A-Z]", nova_senha) or not re.search(r"[a-z]", nova_senha) or not re.search(r"\d", nova_senha) or not re.search(r"[^A-Za-z0-9]", nova_senha): >> reset_admin.py
echo     print("ERRO DE SEGURANCA: A senha nao atende a politica de complexidade.") >> reset_admin.py
echo     sys.exit(1) >> reset_admin.py
echo hash_senha = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') >> reset_admin.py
echo cursor.execute("UPDATE usuarios SET senha_hash=?, senha_alterada_em=?, ultimo_acesso=?, deve_trocar_senha=1, falhas_login=0, bloqueado_ate=NULL, ativo=1 WHERE username='admin'", (hash_senha, data_iso, data_iso)) >> reset_admin.py
echo if cursor.rowcount == 0: >> reset_admin.py
echo     print("Usuario 'admin' nao existe no banco!") >> reset_admin.py
echo else: >> reset_admin.py
echo     cursor.execute("INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes, ip_origem, status) VALUES (?, ?, ?, ?, ?, ?)", (data_iso, 'SISTEMA', 'recuperacao_emergencia', 'Senha do admin restaurada por terminal local', 'localhost', 'sucesso')) >> reset_admin.py
echo     conn.commit() >> reset_admin.py
echo     print("\nSucesso! Use a nova senha. Voce sera forcado a troca-la novamente no primeiro login.") >> reset_admin.py
echo conn.close() >> reset_admin.py

python reset_admin.py
del reset_admin.py

echo.
pause
