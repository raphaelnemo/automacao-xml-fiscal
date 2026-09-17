import datetime as dt
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import bcrypt
except ImportError:
    bcrypt = None

st.set_page_config(page_title="OSC Fiscal", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = Path(__file__).resolve().parent.parent
SEGREDOS_DIR = BASE_DIR / "segredos"
LOGS_DIR = BASE_DIR / "logs"
ARMAZENAMENTO_DIR = BASE_DIR / "armazenamento"
DB_PATH = SEGREDOS_DIR / "osc_sistema.db"
CERT_CONFIG_PATH = SEGREDOS_DIR / "cert_config.json"

MAX_TENTATIVAS = 5
BLOQUEIO_MINUTOS = 15
SESSAO_MINUTOS = 30
VALIDADE_SENHA_DIAS = 90

for pasta in (SEGREDOS_DIR, LOGS_DIR, ARMAZENAMENTO_DIR):
    pasta.mkdir(parents=True, exist_ok=True)


def agora():
    return dt.datetime.now().astimezone()


def agora_iso():
    return agora().isoformat(timespec="seconds")


def apenas_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def validar_cnpj_basico(cnpj):
    return bool(re.fullmatch(r"\d{14}", apenas_digitos(cnpj)))


def gerar_hash_senha(senha):
    if bcrypt:
        return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return "sha256$" + hashlib.sha256(senha.encode("utf-8")).hexdigest()


def verificar_senha(senha, senha_hash):
    if senha_hash.startswith("sha256$"):
        atual = hashlib.sha256(senha.encode("utf-8")).hexdigest()
        return atual == senha_hash.split("$", 1)[1]
    if not bcrypt:
        return False
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


def senha_valida(senha):
    if len(senha) < 12:
        return False, "Use pelo menos 12 caracteres."
    if not re.search(r"[A-Z]", senha):
        return False, "Inclua uma letra maiúscula."
    if not re.search(r"[a-z]", senha):
        return False, "Inclua uma letra minúscula."
    if not re.search(r"\d", senha):
        return False, "Inclua um número."
    if not re.search(r"[^A-Za-z0-9]", senha):
        return False, "Inclua um caractere especial."
    return True, ""


@st.cache_resource
def conectar_banco():
    banco = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20)
    banco.row_factory = sqlite3.Row
    banco.execute("PRAGMA journal_mode=WAL")
    banco.execute("PRAGMA foreign_keys=ON")
    banco.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK(perfil IN ('admin', 'operador')),
            ativo INTEGER NOT NULL DEFAULT 1,
            falhas_login INTEGER NOT NULL DEFAULT 0,
            bloqueado_ate TEXT,
            ultimo_acesso TEXT,
            senha_alterada_em TEXT,
            deve_trocar_senha INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            cnpj TEXT NOT NULL UNIQUE,
            razao_social TEXT NOT NULL,
            procuracao_ativa INTEGER NOT NULL DEFAULT 0,
            pode_consultar INTEGER NOT NULL DEFAULT 0,
            pode_baixar INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            usuario TEXT,
            acao TEXT NOT NULL,
            detalhes TEXT,
            ip_origem TEXT,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS configuracoes_sistema (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
    """)
    colunas = {linha["name"] for linha in banco.execute("PRAGMA table_info(usuarios)").fetchall()}
    if "senha_alterada_em" not in colunas:
        banco.execute("ALTER TABLE usuarios ADD COLUMN senha_alterada_em TEXT")
    if "deve_trocar_senha" not in colunas:
        banco.execute("ALTER TABLE usuarios ADD COLUMN deve_trocar_senha INTEGER NOT NULL DEFAULT 0")
    banco.commit()
    return banco


banco = conectar_banco()


def registrar_auditoria(usuario, acao, detalhes="", status="sucesso"):
    data_hora = agora_iso()
    banco.execute(
        """INSERT INTO auditoria_logs
        (data_hora, usuario, acao, detalhes, ip_origem, status)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (data_hora, usuario, acao, detalhes, "rede_local", status)
    )
    banco.commit()
    linha = {
        "data_hora": data_hora,
        "usuario": usuario,
        "acao": acao,
        "detalhes": detalhes,
        "ip_origem": "rede_local",
        "status": status,
    }
    with (LOGS_DIR / "sistema.log").open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")


def garantir_admin_inicial():
    existe = banco.execute("SELECT id FROM usuarios WHERE username = ?", ("admin",)).fetchone()
    if existe:
        return
    data = agora_iso()
    banco.execute(
        """INSERT INTO usuarios
        (username, senha_hash, perfil, ativo, senha_alterada_em, deve_trocar_senha, criado_em)
        VALUES (?, ?, 'admin', 1, ?, 1, ?)""",
        ("admin", gerar_hash_senha("troque-esta-senha"), data, data)
    )
    banco.commit()


garantir_admin_inicial()


def buscar_usuario(username):
    return banco.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()


def senha_vencida(usuario):
    if usuario["deve_trocar_senha"] or not usuario["senha_alterada_em"]:
        return True
    try:
        data = dt.datetime.fromisoformat(usuario["senha_alterada_em"])
        return agora() >= data + dt.timedelta(days=VALIDADE_SENHA_DIAS)
    except ValueError:
        return True


def autenticar(username, senha):
    usuario = buscar_usuario(username)
    if not usuario or not usuario["ativo"]:
        registrar_auditoria(username, "login", "Usuário inexistente ou inativo", "falha")
        return None, "Usuário ou senha inválidos."
    if usuario["bloqueado_ate"]:
        try:
            if dt.datetime.fromisoformat(usuario["bloqueado_ate"]) > agora():
                registrar_auditoria(username, "login", "Usuário bloqueado", "falha")
                return None, "Usuário temporariamente bloqueado."
        except ValueError:
            pass
    if not verificar_senha(senha, usuario["senha_hash"]):
        falhas = usuario["falhas_login"] + 1
        bloqueado_ate = None
        if falhas >= MAX_TENTATIVAS:
            bloqueado_ate = (agora() + dt.timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat(timespec="seconds")
            falhas = 0
        banco.execute("UPDATE usuarios SET falhas_login = ?, bloqueado_ate = ? WHERE id = ?", (falhas, bloqueado_ate, usuario["id"]))
        banco.commit()
        registrar_auditoria(username, "login", "Senha inválida", "falha")
        return None, "Usuário ou senha inválidos."
    banco.execute("UPDATE usuarios SET falhas_login=0, bloqueado_ate=NULL, ultimo_acesso=? WHERE id=?", (agora_iso(), usuario["id"]))
    banco.commit()
    registrar_auditoria(username, "login", "Login realizado")
    return dict(buscar_usuario(username)), ""


def alterar_senha(usuario_id, username, senha_atual, nova_senha):
    usuario = banco.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if not usuario or not verificar_senha(senha_atual, usuario["senha_hash"]):
        registrar_auditoria(username, "alterar_senha", "Senha atual inválida", "falha")
        return False, "Senha atual inválida."
    valida, mensagem = senha_valida(nova_senha)
    if not valida:
        return False, mensagem
    if verificar_senha(nova_senha, usuario["senha_hash"]):
        return False, "A nova senha deve ser diferente da atual."
    banco.execute(
        """UPDATE usuarios SET senha_hash=?, senha_alterada_em=?, deve_trocar_senha=0,
        falhas_login=0, bloqueado_ate=NULL WHERE id=?""",
        (gerar_hash_senha(nova_senha), agora_iso(), usuario_id)
    )
    banco.commit()
    registrar_auditoria(username, "alterar_senha", "Usuário alterou a própria senha")
    return True, "Senha alterada com sucesso."


def redefinir_senha(admin, alvo_id, nova_senha):
    valida, mensagem = senha_valida(nova_senha)
    if not valida:
        return False, mensagem
    alvo = banco.execute("SELECT username FROM usuarios WHERE id=?", (alvo_id,)).fetchone()
    if not alvo:
        return False, "Usuário não encontrado."
    banco.execute(
        """UPDATE usuarios SET senha_hash=?, senha_alterada_em=?, deve_trocar_senha=1,
        falhas_login=0, bloqueado_ate=NULL WHERE id=?""",
        (gerar_hash_senha(nova_senha), agora_iso(), alvo_id)
    )
    banco.commit()
    registrar_auditoria(admin["username"], "redefinir_senha", f"Senha redefinida para {alvo['username']}")
    return True, "Senha redefinida. O usuário deverá alterá-la no próximo login."


def cliente_autorizado(cliente, acao):
    if not cliente["ativo"] or not cliente["procuracao_ativa"]:
        return False
    return bool(cliente["pode_consultar"] if acao == "consulta" else cliente["pode_baixar"])


def formulario_troca_senha(usuario, obrigatoria=False):
    if obrigatoria:
        st.warning("Sua senha é temporária ou venceu. Altere-a para continuar.")
    with st.form("form_troca_senha"):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        enviar = st.form_submit_button("Alterar senha", use_container_width=True)
    if enviar:
        if nova != confirmar:
            st.error("A confirmação não coincide.")
        else:
            ok, mensagem = alterar_senha(usuario["id"], usuario["username"], atual, nova)
            if ok:
                st.session_state["usuario"] = dict(buscar_usuario(usuario["username"]))
                st.session_state["mostrar_troca_senha"] = False
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)
    st.caption("Mínimo de 12 caracteres: maiúscula, minúscula, número e caractere especial. Validade: 90 dias.")


def renderizar_documentos(usuario):
    st.subheader("Repositório de documentos fiscais")
    clientes = banco.execute("SELECT * FROM clientes WHERE ativo=1 ORDER BY razao_social").fetchall()
    opcoes = {
        f"[{c['codigo']}] {c['razao_social']}": dict(c)
        for c in clientes if cliente_autorizado(c, "consulta")
    }
    if not opcoes:
        st.info("Nenhum cliente autorizado cadastrado. Use a aba Clientes para cadastrar.")
        return
    selecionados = st.multiselect("Clientes autorizados", list(opcoes.keys()))
    busca = st.text_input("Buscar arquivo", placeholder="CNPJ, chave ou nome do XML")
    registros = []
    for nome in selecionados:
        cliente = opcoes[nome]
        pasta = ARMAZENAMENTO_DIR / cliente["cnpj"]
        if not pasta.exists():
            continue
        for arquivo in pasta.rglob("*.xml"):
            if busca and busca.lower() not in str(arquivo).lower():
                continue
            registros.append({
                "Código": cliente["codigo"],
                "Cliente": cliente["razao_social"],
                "CNPJ": cliente["cnpj"],
                "Arquivo": arquivo.name,
                "Emissão/Alteração": dt.datetime.fromtimestamp(arquivo.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "Tamanho (KB)": round(arquivo.stat().st_size / 1024, 2),
                "_caminho": str(arquivo),
            })
    if not registros:
        st.info("Selecione um cliente. Os XMLs aparecerão aqui quando existirem em armazenamento.")
        return
    tabela = pd.DataFrame(registros)
    st.dataframe(tabela.drop(columns=["_caminho"]), use_container_width=True, hide_index=True)
    indices = st.multiselect("Arquivos para download", list(range(len(registros))), format_func=lambda i: registros[i]["Arquivo"])
    if st.button("Preparar ZIP para download", type="primary"):
        if not indices:
            st.warning("Selecione pelo menos um arquivo.")
        else:
            buffer = io.BytesIO()
            incluidos = 0
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for i in indices:
                    reg = registros[i]
                    cliente = next((c for c in clientes if c["cnpj"] == reg["CNPJ"]), None)
                    if cliente and cliente_autorizado(cliente, "download"):
                        zf.write(Path(reg["_caminho"]), arcname=reg["Arquivo"])
                        incluidos += 1
            if incluidos:
                registrar_auditoria(usuario["username"], "download_xml", f"Quantidade: {incluidos}")
                st.download_button("Baixar ZIP", buffer.getvalue(), "xml_selecionados.zip", "application/zip")
            else:
                st.error("Nenhum dos arquivos selecionados possui permissão de download.")


def renderizar_clientes(usuario):
    st.subheader("Gestão de clientes")
    with st.form("form_cliente"):
        codigo = st.text_input("Código")
        cnpj = st.text_input("CNPJ")
        razao = st.text_input("Razão social")
        procuracao = st.checkbox("Procuração ativa")
        consultar = st.checkbox("Permitir consulta", value=True)
        baixar = st.checkbox("Permitir download", value=True)
        salvar = st.form_submit_button("Cadastrar cliente", use_container_width=True)
    if salvar:
        cnpj = apenas_digitos(cnpj)
        if not codigo.strip() or not razao.strip() or not validar_cnpj_basico(cnpj):
            st.error("Informe código, razão social e CNPJ com 14 dígitos.")
        else:
            try:
                data = agora_iso()
                banco.execute(
                    """INSERT INTO clientes
                    (codigo, cnpj, razao_social, procuracao_ativa, pode_consultar, pode_baixar, ativo, criado_em, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                    (codigo.strip(), cnpj, razao.strip(), int(procuracao), int(procuracao and consultar), int(procuracao and baixar), data, data)
                )
                banco.commit()
                registrar_auditoria(usuario["username"], "cadastrar_cliente", f"CNPJ: {cnpj}")
                st.success("Cliente cadastrado.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Código ou CNPJ já cadastrado.")
    st.divider()
    arquivo_csv = st.file_uploader("Importar clientes por CSV", type=["csv"])
    if arquivo_csv is not None:
        try:
            dados_csv = pd.read_csv(arquivo_csv, dtype=str).fillna("")
            obrigatorias = {"codigo", "cnpj", "razao_social", "procuracao_ativa", "pode_consultar", "pode_baixar"}
            faltantes = obrigatorias - set(dados_csv.columns)
            if faltantes:
                st.error("Colunas ausentes: " + ", ".join(sorted(faltantes)))
            else:
                st.dataframe(dados_csv.head(20), use_container_width=True, hide_index=True)
                if st.button("Importar CSV confirmado"):
                    importados = 0
                    erros = 0
                    for _, linha in dados_csv.iterrows():
                        cnpj = apenas_digitos(linha["cnpj"])
                        if not linha["codigo"].strip() or not linha["razao_social"].strip() or not validar_cnpj_basico(cnpj):
                            erros += 1
                            continue
                        def verdadeiro(valor):
                            return str(valor).strip().lower() in {"1", "true", "sim", "s", "yes"}
                        data = agora_iso()
                        banco.execute(
                            """INSERT INTO clientes
                            (codigo, cnpj, razao_social, procuracao_ativa, pode_consultar, pode_baixar, ativo, criado_em, atualizado_em)
                            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                            ON CONFLICT(cnpj) DO UPDATE SET
                                codigo=excluded.codigo,
                                razao_social=excluded.razao_social,
                                procuracao_ativa=excluded.procuracao_ativa,
                                pode_consultar=excluded.pode_consultar,
                                pode_baixar=excluded.pode_baixar,
                                atualizado_em=excluded.atualizado_em""",
                            (linha["codigo"].strip(), cnpj, linha["razao_social"].strip(), int(verdadeiro(linha["procuracao_ativa"])), int(verdadeiro(linha["pode_consultar"])), int(verdadeiro(linha["pode_baixar"])), data, data)
                        )
                        importados += 1
                    banco.commit()
                    registrar_auditoria(usuario["username"], "importar_clientes_csv", f"Importados/atualizados: {importados}; erros: {erros}")
                    st.success(f"Importados/atualizados: {importados}. Linhas rejeitadas: {erros}.")
                    st.rerun()
        except Exception as erro:
            st.error(f"Falha ao ler o CSV: {erro}")
    clientes = banco.execute("SELECT * FROM clientes ORDER BY razao_social").fetchall()
    if clientes:
        df = pd.DataFrame([dict(c) for c in clientes])
        st.dataframe(df, use_container_width=True, hide_index=True)
        opcoes = [{"id": c["id"], "nome": f"[{c['codigo']}] {c['razao_social']}"} for c in clientes]
        alvo = st.selectbox("Cliente para ativar/inativar", opcoes, format_func=lambda x: x["nome"])
        col1, col2 = st.columns(2)
        if col1.button("Ativar cliente"):
            banco.execute("UPDATE clientes SET ativo=1, atualizado_em=? WHERE id=?", (agora_iso(), alvo["id"]))
            banco.commit()
            registrar_auditoria(usuario["username"], "ativar_cliente", f"ID: {alvo['id']}")
            st.rerun()
        if col2.button("Inativar cliente"):
            banco.execute("UPDATE clientes SET ativo=0, atualizado_em=? WHERE id=?", (agora_iso(), alvo["id"]))
            banco.commit()
            registrar_auditoria(usuario["username"], "inativar_cliente", f"ID: {alvo['id']}")
            st.rerun()


def renderizar_usuarios(usuario):
    st.subheader("Gestão de usuários")
    with st.form("form_usuario"):
        username = st.text_input("Novo usuário")
        senha = st.text_input("Senha temporária", type="password")
        perfil = st.selectbox("Perfil", ["operador", "admin"])
        criar = st.form_submit_button("Criar usuário", use_container_width=True)
    if criar:
        valida, mensagem = senha_valida(senha)
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
            st.error("Usuário inválido. Use 3 a 40 caracteres: letras, números, ponto, hífen ou sublinhado.")
        elif not valida:
            st.error(mensagem)
        else:
            try:
                data = agora_iso()
                banco.execute(
                    """INSERT INTO usuarios
                    (username, senha_hash, perfil, ativo, senha_alterada_em, deve_trocar_senha, criado_em)
                    VALUES (?, ?, ?, 1, ?, 1, ?)""",
                    (username, gerar_hash_senha(senha), perfil, data, data)
                )
                banco.commit()
                registrar_auditoria(usuario["username"], "criar_usuario", f"Usuário: {username}; perfil: {perfil}")
                st.success("Usuário criado. Ele deverá trocar a senha no primeiro login.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Esse usuário já existe.")
    usuarios = banco.execute("SELECT id, username, perfil, ativo, ultimo_acesso, senha_alterada_em FROM usuarios ORDER BY username").fetchall()
    opcoes = [dict(u) for u in usuarios]
    st.dataframe(pd.DataFrame(opcoes), use_container_width=True, hide_index=True)
    alvo = st.selectbox("Usuário para administrar", opcoes, format_func=lambda x: f"{x['username']} ({x['perfil']})")
    col1, col2 = st.columns(2)
    if col1.button("Ativar usuário"):
        banco.execute("UPDATE usuarios SET ativo=1 WHERE id=?", (alvo["id"],))
        banco.commit()
        registrar_auditoria(usuario["username"], "ativar_usuario", f"Usuário: {alvo['username']}")
        st.rerun()
    if col2.button("Inativar usuário"):
        if alvo["username"] == usuario["username"]:
            st.error("Você não pode inativar sua própria conta.")
        else:
            admins_ativos = banco.execute("SELECT COUNT(*) AS total FROM usuarios WHERE perfil='admin' AND ativo=1").fetchone()["total"]
            if alvo["perfil"] == "admin" and alvo["ativo"] and admins_ativos <= 1:
                st.error("Não é permitido inativar o último administrador ativo.")
            else:
                banco.execute("UPDATE usuarios SET ativo=0 WHERE id=?", (alvo["id"],))
                banco.commit()
                registrar_auditoria(usuario["username"], "inativar_usuario", f"Usuário: {alvo['username']}")
                st.rerun()
    st.divider()
    st.subheader("Redefinir senha")
    with st.form("form_redefinir_senha"):
        nova = st.text_input("Nova senha temporária", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        redefinir = st.form_submit_button("Redefinir senha", use_container_width=True)
    if redefinir:
        if nova != confirmar:
            st.error("A confirmação não coincide.")
        else:
            ok, mensagem = redefinir_senha(usuario, alvo["id"], nova)
            if ok:
                st.success(mensagem)
            else:
                st.error(mensagem)


def renderizar_auditoria():
    st.subheader("Auditoria")
    logs = banco.execute("SELECT data_hora, usuario, acao, detalhes, ip_origem, status FROM auditoria_logs ORDER BY id DESC LIMIT 1000").fetchall()
    if logs:
        st.dataframe(pd.DataFrame([dict(l) for l in logs]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum evento registrado.")


def renderizar_certificado(usuario):
    st.subheader("Certificado do Windows")
    st.warning("Esta tela guarda somente o thumbprint. Não informe nem armazene PFX ou senha no sistema.")
    atual = {"store": "LocalMachine", "store_name": "My", "thumbprint": "", "ambiente": "homologacao"}
    if CERT_CONFIG_PATH.exists():
        try:
            atual.update(json.loads(CERT_CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    store = st.selectbox("Repositório", ["LocalMachine", "CurrentUser"], index=0 if atual["store"] == "LocalMachine" else 1)
    thumbprint = st.text_input("Thumbprint", value=atual.get("thumbprint", ""))
    if st.button("Salvar configuração do certificado"):
        limpo = re.sub(r"\s+", "", thumbprint).upper()
        if limpo and not re.fullmatch(r"[A-F0-9]{40,128}", limpo):
            st.error("Thumbprint inválido.")
        else:
            config = {"store": store, "store_name": "My", "thumbprint": limpo, "ambiente": "homologacao"}
            CERT_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            registrar_auditoria(usuario["username"], "configurar_certificado", "Thumbprint atualizado")
            st.success("Configuração salva.")
    st.info("A integração real com CryptoAPI/CNG e Sefaz não está implementada nesta homologação. Manifestação fiscal é bloqueada por escopo do sistema.")


if not st.session_state.get("autenticado", False):
    st.title("OSC Assessoria Contábil")
    st.caption("OSC Fiscal — acesso restrito à rede local")
    with st.form("form_login"):
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)
    if entrar:
        usuario, mensagem = autenticar(username.strip(), senha)
        if usuario:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["ultimo_acesso"] = agora()
            st.rerun()
        st.error(mensagem)
    st.info("Primeiro acesso: admin / troque-esta-senha")
    st.stop()

usuario_atual = st.session_state["usuario"]
ultimo_acesso = st.session_state.get("ultimo_acesso", agora())
if agora() - ultimo_acesso > dt.timedelta(minutes=SESSAO_MINUTOS):
    registrar_auditoria(usuario_atual["username"], "sessao_expirada", "Sessão encerrada por inatividade")
    st.session_state.clear()
    st.warning("Sessão expirada. Faça login novamente.")
    st.stop()
st.session_state["ultimo_acesso"] = agora()

if senha_vencida(usuario_atual):
    st.title("Troca obrigatória de senha")
    formulario_troca_senha(usuario_atual, obrigatoria=True)
    st.stop()

with st.sidebar:
    st.title("OSC Fiscal")
    st.caption(f"{usuario_atual['username']} · {usuario_atual['perfil']}")
    if st.button("Alterar minha senha", use_container_width=True):
        st.session_state["mostrar_troca_senha"] = True
    if st.button("Sair", use_container_width=True):
        registrar_auditoria(usuario_atual["username"], "logout", "Logout realizado")
        st.session_state.clear()
        st.rerun()

st.title("OSC Fiscal")
st.caption("Repositório e gestão de documentos fiscais — Homologação local")

if st.session_state.get("mostrar_troca_senha", False):
    with st.expander("Alterar minha senha", expanded=True):
        formulario_troca_senha(usuario_atual)

if usuario_atual["perfil"] == "admin":
    tab_documentos, tab_clientes, tab_usuarios, tab_auditoria, tab_certificado = st.tabs([
        "Documentos", "Clientes", "Usuários", "Auditoria", "Certificado"
    ])
    with tab_documentos:
        renderizar_documentos(usuario_atual)
    with tab_clientes:
        renderizar_clientes(usuario_atual)
    with tab_usuarios:
        renderizar_usuarios(usuario_atual)
    with tab_auditoria:
        renderizar_auditoria()
    with tab_certificado:
        renderizar_certificado(usuario_atual)
else:
    renderizar_documentos(usuario_atual)

st.divider()
st.caption("OSC Fiscal — consultas e downloads somente. Eventos de manifestação fiscal não são implementados.")
