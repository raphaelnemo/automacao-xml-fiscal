import datetime as dt
import json
import re
import sqlite3
import zipfile
import io
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import bcrypt

# Relatório PDF profissional via ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="OSC Assessoria Contábil", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = Path(__file__).resolve().parent.parent
SEGREDOS_DIR = BASE_DIR / "segredos"
LOGS_DIR = BASE_DIR / "logs"
ARMAZENAMENTO_DIR = BASE_DIR / "armazenamento"
DB_PATH = SEGREDOS_DIR / "osc_sistema.db"
CERT_CONFIG_PATH = SEGREDOS_DIR / "cert_config.json"
AMBIENTE_PATH = BASE_DIR / "ambiente.txt"

MAX_TENTATIVAS = 5
BLOQUEIO_MINUTOS = 15
SESSAO_MINUTOS = 30
VALIDADE_SENHA_DIAS = 90

for pasta in (SEGREDOS_DIR, LOGS_DIR, ARMAZENAMENTO_DIR):
    pasta.mkdir(parents=True, exist_ok=True)

# --- FUNÇÕES DE AMBIENTE ---
def obter_ambiente():
    if not AMBIENTE_PATH.exists():
        AMBIENTE_PATH.write_text("HOMOLOGACAO", encoding="utf-8")
    amb = AMBIENTE_PATH.read_text(encoding="utf-8").strip().upper()
    return amb if amb in ("PRODUCAO", "HOMOLOGACAO") else "HOMOLOGACAO"

# --- FUNÇÕES UTILITÁRIAS ---
def agora():
    return dt.datetime.now().astimezone()

def agora_iso():
    return agora().isoformat(timespec="seconds")

def apenas_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))

def validar_cnpj_completo(cnpj):
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    return True

def gerar_hash_senha(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_senha(senha, senha_hash):
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False

def senha_valida(senha):
    if len(senha) < 12: return False, "Use pelo menos 12 caracteres."
    if not re.search(r"[A-Z]", senha): return False, "Inclua uma letra maiúscula."
    if not re.search(r"[a-z]", senha): return False, "Inclua uma letra minúscula."
    if not re.search(r"\d", senha): return False, "Inclua um número."
    if not re.search(r"[^A-Za-z0-9]", senha): return False, "Inclua um caractere especial."
    return True, ""

# --- BANCO DE DADOS ---
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
            uf TEXT,
            municipio TEXT,
            provedor_nfse TEXT,
            fonte_nfse TEXT,
            procuracao_ativa INTEGER NOT NULL DEFAULT 0,
            tipo_autenticacao TEXT DEFAULT 'procuracao',
            thumbprint_proprio TEXT,
            pode_consultar INTEGER NOT NULL DEFAULT 0,
            pode_baixar INTEGER NOT NULL DEFAULT 0,
            outro_sistema_nsu TEXT DEFAULT 'NAO_INFORMADO',
            nfse_nsu_habilitado INTEGER NOT NULL DEFAULT 0,
            nfe_produtos_nsu_habilitado INTEGER NOT NULL DEFAULT 0,
            ultimo_nsu_nfse TEXT,
            ultimo_nsu_nfe TEXT,
            ultima_consulta_nfse_em TEXT,
            ultimo_status_nfse TEXT,
            proxima_consulta_nfse_em TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conectores_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            cobertura TEXT,
            uf TEXT,
            municipio TEXT,
            ambiente TEXT NOT NULL,
            url_base TEXT,
            url_status TEXT,
            url_consulta TEXT,
            versao_leiaute TEXT,
            usa_nsu INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1,
            observacao TEXT,
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
    """)
    banco.commit()
    return banco

banco = conectar_banco()

def exec_db(query, params=(), commit=False, retries=5):
    for tentativa in range(retries):
        try:
            cursor = banco.execute(query, params)
            if commit:
                banco.commit()
            return cursor
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and tentativa < retries - 1:
                time.sleep(0.2 * (2 ** tentativa))
            else:
                if commit: banco.rollback()
                raise

def registrar_auditoria(usuario, acao, detalhes="", status="sucesso"):
    data_hora = agora_iso()
    exec_db("INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes, ip_origem, status) VALUES (?, ?, ?, ?, ?, ?)",
            (data_hora, usuario, acao, detalhes, "rede_local", status), commit=True)
    linha = {"data_hora": data_hora, "usuario": usuario, "acao": acao, "detalhes": detalhes, "ip_origem": "rede_local", "status": status}
    with (LOGS_DIR / "sistema.log").open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")

def garantir_admin_inicial():
    if not banco.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone():
        data = agora_iso()
        exec_db("INSERT INTO usuarios (username, senha_hash, perfil, ativo, senha_alterada_em, deve_trocar_senha, criado_em) VALUES (?, ?, 'admin', 1, ?, 1, ?)",
                ("admin", gerar_hash_senha("troque-esta-senha"), data, data), commit=True)

garantir_admin_inicial()

def buscar_usuario(username):
    return banco.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()

def senha_vencida(usuario):
    if usuario["deve_trocar_senha"] or not usuario["senha_alterada_em"]: return True
    try:
        return agora() >= dt.datetime.fromisoformat(usuario["senha_alterada_em"]) + dt.timedelta(days=VALIDADE_SENHA_DIAS)
    except ValueError: return True

def autenticar(username, senha):
    usuario = buscar_usuario(username)
    if not usuario or not usuario["ativo"]:
        registrar_auditoria(username, "login", "Tentativa de acesso bloqueada (inativo/inexistente).", "falha")
        return None, "Usuário ou senha inválidos."
    if usuario["bloqueado_ate"]:
        try:
            dt_bloqueio = dt.datetime.fromisoformat(usuario["bloqueado_ate"])
            dt_bloqueio_naive = dt_bloqueio.replace(tzinfo=None)
            agora_naive = agora().replace(tzinfo=None) if hasattr(agora(), "replace") else agora()

            if dt_bloqueio_naive > agora_naive:
                registrar_auditoria(username, "login", "Usuário temporariamente bloqueado.", "falha")
                return None, "Usuário temporariamente bloqueado."
        except Exception as e:
            pass
    if not verificar_senha(senha, usuario["senha_hash"]):
        falhas = usuario["falhas_login"] + 1
        bloqueado_ate = (agora() + dt.timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat(timespec="seconds") if falhas >= MAX_TENTATIVAS else None
        exec_db("UPDATE usuarios SET falhas_login = ?, bloqueado_ate = ? WHERE id = ?", (falhas if falhas < MAX_TENTATIVAS else 0, bloqueado_ate, usuario["id"]), commit=True)
        registrar_auditoria(username, "login", "Senha inválida.", "falha")
        return None, "Usuário ou senha inválidos."
    
    exec_db("UPDATE usuarios SET falhas_login=0, bloqueado_ate=NULL, ultimo_acesso=? WHERE id=?", (agora_iso(), usuario["id"]), commit=True)
    registrar_auditoria(username, "login", "Login realizado com sucesso.")
    return dict(usuario), ""

def cliente_autorizado(cliente, acao):
    if not cliente["ativo"]: return False
    if cliente["tipo_autenticacao"] == "procuracao" and not cliente["procuracao_ativa"]: return False
    if cliente["tipo_autenticacao"] == "proprio" and not cliente["thumbprint_proprio"]: return False
    return bool(cliente["pode_consultar"] if acao == "consulta" else cliente["pode_baixar"])

# --- RENDERIZAÇÃO DAS TELAS ---
def formulario_troca_senha(usuario, obrigatoria=False):
    if obrigatoria: st.warning("Sua senha é temporária ou venceu. Altere-a para continuar.")
    with st.form("form_troca_senha"):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        enviar = st.form_submit_button("Alterar senha", use_container_width=True)
    if enviar:
        if nova != confirmar: st.error("A confirmação não coincide.")
        else:
            valida, msg = senha_valida(nova)
            if not valida: st.error(msg)
            elif verificar_senha(nova, usuario["senha_hash"]): st.error("A nova senha deve ser diferente da atual.")
            else:
                exec_db("UPDATE usuarios SET senha_hash=?, senha_alterada_em=?, deve_trocar_senha=0, falhas_login=0, bloqueado_ate=NULL WHERE id=?", (gerar_hash_senha(nova), agora_iso(), usuario["id"]), commit=True)
                registrar_auditoria(usuario["username"], "alterar_senha", "Usuário alterou a própria senha.")
                st.session_state["usuario"] = dict(buscar_usuario(usuario["username"]))
                st.session_state["mostrar_troca_senha"] = False
                st.success("Senha alterada com sucesso!")
                st.rerun()

def gerar_pdf_relatorio(docs_selecionados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('TituloRM', parent=estilos['Heading1'], fontSize=14, textColor=colors.HexColor('#1f2937'), spaceAfter=10)
    estilo_normal = ParagraphStyle('NormalRM', parent=estilos['Normal'], fontSize=9, textColor=colors.HexColor('#374151'))
    
    elementos.append(Paragraph("<b>Relatório de Documentos Fiscais - Repositório RM</b>", estilo_titulo))
    elementos.append(Spacer(1, 10))
    
    cabecalho = ["ID", "CNPJ Cliente", "Tipo", "Chave de Acesso", "Emitente", "Valor (R$)"]
    dados_tabela = [cabecalho]
    
    for d in docs_selecionados:
        dados_tabela.append([
            str(d.get("id", "")),
            str(d.get("cnpj_cliente", "")),
            str(d.get("tipo_doc", "")),
            str(d.get("chave_acesso", "")),
            str(d.get("emitente", ""))[:25],
            f"R$ {float(d.get('valor_total', 0.0)):,.2f}"
        ])
        
    t = Table(dados_tabela, colWidths=[30, 85, 45, 175, 130, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#111827')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('ALIGN', (5,1), (5,-1), 'RIGHT'),
    ]))
    
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

def renderizar_consultas(usuario):
    st.subheader("Painel de Consultas Fiscais (Lote / Múltiplos Clientes)")
    
    banco.execute("""
        CREATE TABLE IF NOT EXISTS documentos_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj_cliente TEXT,
            tipo_doc TEXT,
            chave_acesso TEXT UNIQUE,
            nsu TEXT,
            emitente TEXT,
            valor_total REAL,
            xml_conteudo TEXT,
            data_recebimento TEXT
        )
    """)
    banco.commit()

    registros_clientes = banco.execute("SELECT * FROM clientes WHERE ativo=1 ORDER BY razao_social").fetchall()
    registros_conectores = banco.execute("SELECT * FROM conectores_fiscais WHERE ativo=1").fetchall()
    
    clientes = [dict(c) for c in registros_clientes]
    conectores = [dict(c) for c in registros_conectores]
    
    if not clientes or not conectores:
        st.info("Cadastre clientes autorizados e conectores para prosseguir.")
        return
        
    if "selecionar_todos_clientes" not in st.session_state:
        st.session_state["selecionar_todos_clientes"] = False

    col_bt1, col_bt2 = st.columns([2, 5])
    if col_bt1.button("☑️ Marcar / Desmarcar Todos (Clientes)"):
        st.session_state["selecionar_todos_clientes"] = not st.session_state["selecionar_todos_clientes"]
        st.rerun()

    clientes_padrao = clientes if st.session_state["selecionar_todos_clientes"] else []

    with st.form("form_executar_consulta_lote"):
        clientes_selecionados = st.multiselect(
            "Clientes Alvo da Consulta", 
            options=clientes,
            default=clientes_padrao,
            format_func=lambda x: f"[{x['codigo']}] {x['razao_social']} (CNPJ: {x['cnpj']})"
        )
        
        con_selecionado = st.selectbox(
            "Conector Fiscal", 
            conectores, 
            format_func=lambda x: f"{x['nome']} ({x['ambiente']})"
        )
        
        btn_consultar = st.form_submit_button("Executar Consulta em Lote", type="primary")
        
    if btn_consultar:
        if not clientes_selecionados:
            st.warning("Selecione ao menos um cliente para executar a consulta.")
        else:
            ambiente_atual = obter_ambiente()
            barra_progresso = st.progress(0)
            total_clientes = len(clientes_selecionados)
            
            sucessos, bloqueados, erros_conexao = 0, 0, 0
            
            for i, cli_sel in enumerate(clientes_selecionados):
                erros = []
                if ambiente_atual != con_selecionado["ambiente"]:
                    erros.append("Ambiente incompatível.")
                if not cliente_autorizado(cli_sel, "consulta"):
                    erros.append("Sem permissão.")
                if con_selecionado["usa_nsu"] and cli_sel["outro_sistema_nsu"] in ("SIM", "NAO_INFORMADO"):
                    erros.append("Conflito NSU.")
                    
                if erros:
                    bloqueados += 1
                else:
                    nsu_atual = cli_sel.get("ultimo_nsu_nfse") or "1"
                    url_base = con_selecionado['url_consulta'].strip().rstrip('/')
                    endpoint_completo = f"{url_base}/{cli_sel['cnpj']}/{nsu_atual}"
                    
                    try:
                        resposta = requests.get(endpoint_completo, timeout=5)
                        if resposta.status_code == 200:
                            dados = resposta.json()
                            detalhes = dados.get("detalhes", {})
                            tipo_documento_val = con_selecionado.get("tipo_documento") or "NFS-e"
                            
                            banco.execute("""
                                INSERT INTO documentos_fiscais (
                                    cnpj_cliente, tipo_doc, chave_acesso, nsu, emitente, valor_total, xml_conteudo, data_recebimento
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
                                ON CONFLICT(chave_acesso) DO UPDATE SET data_recebimento = DATETIME('now')
                            """, (
                                cli_sel["cnpj"], tipo_documento_val, detalhes.get("chave"),
                                dados.get("ultNSU"), detalhes.get("emitente"), dados.get("valor"), dados.get("docZip")
                            ))
                            
                            banco.execute("""
                                UPDATE clientes SET ultimo_nsu_nfse = ?, ultima_consulta_nfse_em = ?, ultimo_status_nfse = 'SUCESSO_LOTE'
                                WHERE id = ?
                            """, (dados.get("ultNSU"), agora_iso(), cli_sel["id"]))
                            banco.commit()
                            sucessos += 1
                        elif resposta.status_code == 404:
                            banco.execute("UPDATE clientes SET ultima_consulta_nfse_em = ?, ultimo_status_nfse = 'FILA_FINALIZADA' WHERE id = ?", (agora_iso(), cli_sel["id"]))
                            banco.commit()
                        else:
                            erros_conexao += 1
                    except Exception:
                        erros_conexao += 1
                barra_progresso.progress((i + 1) / total_clientes)

            st.success(f"Consulta finalizada! Sucessos: {sucessos} | Bloqueados: {bloqueados} | Erros: {erros_conexao}")
            st.rerun()

    # --- REPOSITÓRIO COM FILTRO DINÂMICO E TABELA RM ---
    st.divider()
    
    docs_registros = banco.execute("""
        SELECT id, cnpj_cliente, tipo_doc, chave_acesso, nsu, emitente, valor_total, xml_conteudo, data_recebimento 
        FROM documentos_fiscais 
        ORDER BY id DESC LIMIT 250
    """).fetchall()
    
    docs = [dict(d) for d in docs_registros]
    
    if not docs:
        st.subheader("Repositório de Documentos Fiscais")
        st.info("Nenhuma nota fiscal armazenada no banco até o momento.")
        return

    # Cabeçalho da seção com filtros dinâmicos e botões
    col_t, col_filtro, col_xml, col_pdf = st.columns([2.5, 2.5, 1.2, 1.2])
    col_t.markdown("### Repositório Fiscais")
    
    termo_busca = col_filtro.text_input(
        "🔍 Filtrar tabela",
        placeholder="Digite emitente, chave ou CNPJ...",
        label_visibility="collapsed"
    )

    docs_filtrados = docs
    if termo_busca.strip():
        termo = termo_busca.strip().lower()
        docs_filtrados = [
            d for d in docs
            if termo in str(d.get("emitente", "")).lower()
            or termo in str(d.get("chave_acesso", "")).lower()
            or termo in str(d.get("cnpj_cliente", "")).lower()
            or termo in str(d.get("tipo_doc", "")).lower()
        ]

    # Montagem do DataFrame para o st.data_editor com os dados filtrados
    df_dados = pd.DataFrame([{
        "Selecionar": False,
        "ID": d["id"],
        "CNPJ Cliente": d["cnpj_cliente"],
        "Tipo": d["tipo_doc"],
        "Chave de Acesso": d["chave_acesso"],
        "NSU": d["nsu"],
        "Emitente": d["emitente"],
        "Valor (R$)": float(d["valor_total"] or 0.0),
        "Recebimento": d["data_recebimento"]
    } for d in docs_filtrados])

    df_editado = st.data_editor(
        df_dados,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Sel.", default=False, width="small"),
            "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
        },
        disabled=["ID", "CNPJ Cliente", "Tipo", "Chave de Acesso", "NSU", "Emitente", "Valor (R$)", "Recebimento"],
        hide_index=True,
        use_container_width=True,
        key="tabela_rm_docs_filtrada"
    )

    # Identificação dos registros selecionados na tabela interativa
    selecionados_df = df_editado[df_editado["Selecionar"] == True]
    ids_selecionados = selecionados_df["ID"].tolist() if not selecionados_df.empty else []
    docs_selecionados_lista = [d for d in docs if d["id"] in ids_selecionados]

    # Renderização sutil dos botões no topo/direita do repositório
    with col_xml:
        if ids_selecionados:
            zip_xml = io.BytesIO()
            with zipfile.ZipFile(zip_xml, "w", zipfile.ZIP_DEFLATED) as zf:
                for d in docs_selecionados_lista:
                    zf.writestr(f"{d['tipo_doc']}_{d['chave_acesso']}.xml", d["xml_conteudo"] or "")
            zip_xml.seek(0)
            st.download_button(
                label="📥 XML", 
                data=zip_xml, 
                file_name="xmls_selecionados.zip", 
                mime="application/zip", 
                use_container_width=True,
                key="btn_dl_xml_rm"
            )
        else:
            st.button("📥 XML", disabled=True, use_container_width=True, key="btn_dl_xml_rm_dis")

    with col_pdf:
        if ids_selecionados:
            pdf_bytes = gerar_pdf_relatorio(docs_selecionados_lista)
            st.download_button(
                label="📄 PDF", 
                data=pdf_bytes, 
                file_name="relatorio_notas_rm.pdf", 
                mime="application/pdf", 
                use_container_width=True,
                key="btn_dl_pdf_rm"
            )
        else:
            st.button("📄 PDF", disabled=True, use_container_width=True, key="btn_dl_pdf_rm_dis")

def renderizar_edicao_cliente(usuario):
    if usuario["perfil"] != "admin":
        return

    clientes = banco.execute("SELECT * FROM clientes ORDER BY razao_social").fetchall()
    
    if not clientes:
        st.info("Nenhum cliente cadastrado para edição.")
        return

    opcoes_clientes = {f"[{c['codigo']}] {c['razao_social']} ({c['cnpj']})": dict(c) for c in clientes}
    cliente_selecionado = st.selectbox("Selecione o cliente para alterar", list(opcoes_clientes.keys()), key="select_cliente_editar")
    c_dados = opcoes_clientes[cliente_selecionado]
    cid = c_dados["id"]

    with st.form(f"form_editar_cliente_{cid}"):
        e1, e2, e3 = st.columns([1, 2, 3])
        codigo = e1.text_input("Código", value=c_dados["codigo"], key=f"edit_codigo_{cid}")
        cnpj_display = e2.text_input("CNPJ (Somente leitura)", value=c_dados["cnpj"], disabled=True, key=f"edit_cnpj_{cid}")
        razao = e3.text_input("Razão social", value=c_dados["razao_social"], key=f"edit_razao_{cid}")

        e4, e5 = st.columns(2)
        fontes = ["ADN Nacional", "Provedor Municipal", "Ambas"]
        idx_fonte = fontes.index(c_dados["fonte_nfse"]) if c_dados["fonte_nfse"] in fontes else 0
        fonte_nfse = e4.selectbox("Fonte NFS-e Prioritária", fontes, index=idx_fonte, key=f"edit_fonte_{cid}")

        outros = ["NAO_INFORMADO", "SIM", "NAO"]
        idx_outro = outros.index(c_dados["outro_sistema_nsu"]) if c_dados["outro_sistema_nsu"] in outros else 0
        outro_sistema = e5.selectbox("Outro sistema consulta NSU?", outros, index=idx_outro, key=f"edit_outro_{cid}")

        e6, e7 = st.columns(2)
        tipos_auth = ["procuracao", "proprio"]
        idx_auth = tipos_auth.index(c_dados["tipo_autenticacao"]) if c_dados["tipo_autenticacao"] in tipos_auth else 0
        tipo_auth = e6.selectbox("Tipo de Autenticação", tipos_auth, index=idx_auth, key=f"edit_auth_{cid}")
        thumb_proprio = e7.text_input("Thumbprint Próprio", value=c_dados["thumbprint_proprio"] or "", key=f"edit_thumb_{cid}")

        st.write("Permissões e Regras")
        procuracao = st.checkbox("Procuração Ativa no ESCRITÓRIO", value=bool(c_dados["procuracao_ativa"]), key=f"edit_proc_{cid}")
        consultar = st.checkbox("Permitir Consulta", value=bool(c_dados["pode_consultar"]), key=f"edit_cons_{cid}")
        baixar = st.checkbox("Permitir Download", value=bool(c_dados["pode_baixar"]), key=f"edit_baix_{cid}")
        hab_nsu = st.checkbox("Habilitar busca por NSU (NFS-e)", value=bool(c_dados["nfse_nsu_habilitado"]), key=f"edit_nsu_{cid}")
        ativo = st.checkbox("Cadastro Ativo", value=bool(c_dados["ativo"]), key=f"edit_ativo_{cid}")

        if st.form_submit_button("Salvar Alterações"):
            if not codigo.strip() or not razao.strip():
                st.error("Código e Razão Social não podem ficar em branco.")
            elif outro_sistema != "NAO" and hab_nsu:
                st.error("Falha de segurança: Habilitar NSU bloqueado se outro sistema for SIM ou NAO_INFORMADO.")
            else:
                data = agora_iso()
                exec_db("""
                    UPDATE clientes SET
                        codigo = ?,
                        razao_social = ?,
                        fonte_nfse = ?,
                        outro_sistema_nsu = ?,
                        tipo_autenticacao = ?,
                        thumbprint_proprio = ?,
                        procuracao_ativa = ?,
                        pode_consultar = ?,
                        pode_baixar = ?,
                        nfse_nsu_habilitado = ?,
                        ativo = ?,
                        atualizado_em = ?
                    WHERE id = ?
                """, (
                    codigo.strip(),
                    razao.strip(),
                    fonte_nfse,
                    outro_sistema,
                    tipo_auth,
                    thumb_proprio.strip().upper(),
                    int(procuracao),
                    int(consultar),
                    int(baixar),
                    int(hab_nsu),
                    int(ativo),
                    data,
                    cid
                ), commit=True)
                
                registrar_auditoria(usuario["username"], "editar_cliente", f"Cliente ID {cid} ({c_dados['cnpj']}) atualizado.")
                st.success("Dados do cliente atualizados com sucesso!")
                st.rerun()

def renderizar_clientes(usuario):
    if usuario["perfil"] != "admin":
        st.error("Acesso negado: Requer privilégios de administrador.")
        st.stop()
        
    st.subheader("Gestão de Clientes")
    
    with st.expander("Cadastrar Novo Cliente Manualmente", expanded=False):
        with st.form("form_cliente"):
            c1, c2, c3 = st.columns([1, 2, 3])
            codigo = c1.text_input("Código")
            cnpj = c2.text_input("CNPJ (somente números)")
            razao = c3.text_input("Razão social")
            
            c4, c5 = st.columns(2)
            fonte_nfse = c4.selectbox("Fonte NFS-e Prioritária", ["ADN Nacional", "Provedor Municipal", "Ambas"])
            outro_sistema = c5.selectbox("Outro sistema consulta NSU?", ["NAO_INFORMADO", "SIM", "NAO"], help="Regra rígida de bloqueio.")
            
            c6, c7 = st.columns(2)
            tipo_auth = c6.selectbox("Tipo de Autenticação", ["procuracao", "proprio"])
            thumb_proprio = c7.text_input("Thumbprint Próprio (se houver)")
            
            st.write("Permissões")
            procuracao = st.checkbox("Procuração Ativa no ESCRITÓRIO", value=True)
            consultar = st.checkbox("Permitir Consulta", value=True)
            baixar = st.checkbox("Permitir Download", value=True)
            hab_nsu = st.checkbox("Habilitar busca por NSU (NFS-e)", value=False)
            
            if st.form_submit_button("Salvar Cliente"):
                cnpj_limpo = apenas_digitos(cnpj)
                if not codigo.strip() or not razao.strip() or not validar_cnpj_completo(cnpj_limpo): 
                    st.error("Código e Razão Social são obrigatórios. O CNPJ precisa ser válido.")
                elif outro_sistema != "NAO" and hab_nsu: 
                    st.error("Falha de segurança: Habilitar NSU bloqueado se outro sistema é SIM ou NAO_INFORMADO.")
                else:
                    try:
                        data = agora_iso()
                        exec_db("""
                            INSERT INTO clientes 
                            (codigo, cnpj, razao_social, fonte_nfse, tipo_autenticacao, thumbprint_proprio, outro_sistema_nsu, nfse_nsu_habilitado, procuracao_ativa, pode_consultar, pode_baixar, ativo, criado_em, atualizado_em) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """, (codigo.strip(), cnpj_limpo, razao.strip(), fonte_nfse, tipo_auth, thumb_proprio.strip().upper(), outro_sistema, int(hab_nsu), int(procuracao), int(consultar), int(baixar), data, data), commit=True)
                        registrar_auditoria(usuario["username"], "cadastrar_cliente", f"CNPJ: {cnpj_limpo}")
                        st.success("Cliente cadastrado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Código ou CNPJ já cadastrado.")

    st.divider()
    
    with st.expander("Editar Cliente Existente", expanded=False):
        renderizar_edicao_cliente(usuario)

    st.divider()
    
    arquivo_csv = st.file_uploader("Importar clientes em lote (.csv)", type=["csv"])
    if arquivo_csv is not None:
        try:
            try:
                dados_csv = pd.read_csv(arquivo_csv, dtype=str, encoding="utf-8-sig").fillna("")
            except UnicodeDecodeError:
                arquivo_csv.seek(0)
                dados_csv = pd.read_csv(arquivo_csv, dtype=str, encoding="latin1").fillna("")

            dados_csv.columns = [str(col).strip().lower() for col in dados_csv.columns]
            obrigatorias = {"codigo", "cnpj", "razao_social", "fonte_nfse", "outro_sistema_nsu", "tipo_autenticacao"}
            faltantes = obrigatorias - set(dados_csv.columns)
            
            if faltantes:
                st.error("O CSV não contém as colunas obrigatórias: " + ", ".join(sorted(faltantes)))
            else:
                st.dataframe(dados_csv.head(5), use_container_width=True, hide_index=True)
                if st.button("Confirmar Importação de Lote"):
                    importados, erros = 0, 0
                    log_erros = []
                    
                    for idx, linha in dados_csv.iterrows():
                        cnpj_limpo = apenas_digitos(linha.get("cnpj", ""))
                        codigo = str(linha.get("codigo", "")).split(".")[0].strip()
                        razao = str(linha.get("razao_social", "")).strip()
                        
                        if not codigo or not razao or not validar_cnpj_completo(cnpj_limpo):
                            erros += 1
                            log_erros.append(f"Linha {idx+2}: Código/Razão vazios ou CNPJ inválido ({cnpj_limpo}).")
                            continue
                            
                        def verdadeiro(v): return str(v).strip().upper() in {"1", "TRUE", "SIM", "S", "YES"}
                        
                        proc = verdadeiro(linha.get("procuracao_ativa", "1"))
                        cons = verdadeiro(linha.get("pode_consultar", "1"))
                        baix = verdadeiro(linha.get("pode_baixar", "1"))
                        hab_nsu = verdadeiro(linha.get("nfse_nsu_habilitado", "0"))
                        
                        fonte = str(linha.get("fonte_nfse", "ADN Nacional")).strip()
                        outro = str(linha.get("outro_sistema_nsu", "NAO_INFORMADO")).strip().upper()
                        tipo_auth = str(linha.get("tipo_autenticacao", "procuracao")).strip().lower()
                        thumb = str(linha.get("thumbprint_proprio", "")).strip().upper()
                        
                        if outro != "NAO" and hab_nsu:
                            erros += 1
                            log_erros.append(f"Linha {idx+2} ({razao}): Conflito de Regras NSU evitado para segurança da Sefaz.")
                            continue
                            
                        data = agora_iso()
                        try:
                            exec_db("""
                                INSERT INTO clientes 
                                (codigo, cnpj, razao_social, fonte_nfse, procuracao_ativa, tipo_autenticacao, thumbprint_proprio, pode_consultar, pode_baixar, outro_sistema_nsu, nfse_nsu_habilitado, ativo, criado_em, atualizado_em)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                                ON CONFLICT(cnpj) DO UPDATE SET
                                    codigo=excluded.codigo,
                                    razao_social=excluded.razao_social,
                                    fonte_nfse=excluded.fonte_nfse,
                                    procuracao_ativa=excluded.procuracao_ativa,
                                    tipo_autenticacao=excluded.tipo_autenticacao,
                                    thumbprint_proprio=excluded.thumbprint_proprio,
                                    pode_consultar=excluded.pode_consultar,
                                    pode_baixar=excluded.pode_baixar,
                                    outro_sistema_nsu=excluded.outro_sistema_nsu,
                                    nfse_nsu_habilitado=excluded.nfse_nsu_habilitado,
                                    atualizado_em=excluded.atualizado_em
                            """, (codigo, cnpj_limpo, razao, fonte, int(proc), tipo_auth, thumb, int(cons), int(baix), outro, int(hab_nsu), data, data), commit=True)
                            importados += 1
                        except Exception as e:
                            erros += 1
                            log_erros.append(f"Linha {idx+2}: Erro de Gravação Banco ({str(e)}).")
                            
                    registrar_auditoria(usuario["username"], "importacao_csv_lote", f"Processados: {importados}; Rejeitados: {erros}")
                    if erros > 0:
                        st.error(f"Erros encontrados: {erros}. Clientes importados/atualizados com sucesso: {importados}.")
                        with st.expander("Ver Log de Rejeições", expanded=True):
                            for erro_txt in log_erros: st.write(erro_txt)
                    else:
                        st.success(f"Sucesso! {importados} clientes importados/atualizados.")
                        st.rerun()
        except Exception as e:
            st.error(f"Ocorreu um erro estrutural ao ler o CSV: {e}")

    st.divider()
    st.subheader("Lista de Clientes Cadastrados")
    clientes = banco.execute("SELECT * FROM clientes ORDER BY razao_social").fetchall()
    if clientes:
        df = pd.DataFrame([dict(c) for c in clientes])
        st.dataframe(df.drop(columns=["criado_em", "atualizado_em"]), use_container_width=True, hide_index=True)

def renderizar_conectores(usuario):
    if usuario["perfil"] != "admin":
        st.error("Acesso negado: Requer privilégios de administrador.")
        st.stop()
        
    st.subheader("Gestão de Conectores (APIs)")
    
    with st.expander("Cadastrar Novo Conector", expanded=False):
        with st.form("form_conector"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome do Conector (Ex: API Municipal - SP)")
            ambiente = c2.selectbox("Ambiente do Conector", ["PRODUCAO", "HOMOLOGACAO"])
            
            c3, c4, c5 = st.columns([1,1,1])
            tipo_doc = c3.selectbox("Tipo de Documento", ["NFS-e", "NF-e"])
            cobertura = c4.selectbox("Cobertura", ["Nacional", "Municipal", "Estadual"])
            usa_nsu = c5.checkbox("Utiliza Fila/NSU?", value=True)
            
            url_consulta = st.text_input("URL de Consulta (Endpoint REST/SOAP)")
            
            if st.form_submit_button("Cadastrar Conector"):
                if not nome or not url_consulta: 
                    st.error("Nome e URL são obrigatórios.")
                else:
                    data = agora_iso()
                    exec_db("""
                        INSERT INTO conectores_fiscais (nome, tipo_documento, cobertura, ambiente, url_consulta, usa_nsu, ativo, criado_em, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (nome, tipo_doc, cobertura, ambiente, url_consulta, int(usa_nsu), data, data), commit=True)
                    registrar_auditoria(usuario["username"], "cadastrar_conector", f"Nome: {nome}")
                    st.success("Conector ativado com sucesso!")
                    st.rerun()
                
    st.divider()
    st.subheader("Conectores Cadastrados")
    conectores = banco.execute("SELECT * FROM conectores_fiscais").fetchall()
    if conectores:
        st.dataframe(pd.DataFrame([dict(c) for c in conectores]), use_container_width=True, hide_index=True)

def renderizar_configuracoes(usuario):
    if usuario["perfil"] != "admin":
        st.error("Acesso negado: Requer privilégios de administrador.")
        st.stop()
        
    st.subheader("Configurações do Sistema")
    ambiente_atual = obter_ambiente()
    
    st.write(f"**Ambiente de Execução Atual:** `{ambiente_atual}`")
    with st.form("form_ambiente"):
        st.warning("A troca de ambiente exige ação consciente. Ela altera o comportamento de rede e trava conectores de Produção.")
        acao_esperada = "ATIVAR PRODUÇÃO" if ambiente_atual == "HOMOLOGACAO" else "ATIVAR HOMOLOGAÇÃO"
        novo_amb = "PRODUCAO" if ambiente_atual == "HOMOLOGACAO" else "HOMOLOGACAO"
        
        confirmacao = st.text_input(f"Para alterar, digite exatamente: {acao_esperada}")
        if st.form_submit_button("Mudar Ambiente Principal"):
            if confirmacao.strip() == acao_esperada:
                AMBIENTE_PATH.write_text(novo_amb, encoding="utf-8")
                registrar_auditoria(usuario["username"], "alterar_ambiente", f"Para: {novo_amb}")
                st.success(f"O servidor local foi migrado para o modo {novo_amb}.")
                st.rerun()
            else:
                st.error("Texto de confirmação incorreto.")
                
    st.divider()
    st.subheader("Certificado Digital Padrão (Uso do Escritório)")
    atual = {"store": "LocalMachine", "thumbprint": ""}
    if CERT_CONFIG_PATH.exists():
        try:
            atual.update(json.loads(CERT_CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            st.error("O arquivo de configuração do certificado (JSON) possui falhas de formatação.")
            registrar_auditoria(usuario["username"], "erro_leitura", f"JSONDecodeError em cert_config.json: {e}", "falha")
            
    with st.form("form_cert"):
        store = st.selectbox("Repositório", ["LocalMachine", "CurrentUser"], index=0 if atual["store"] == "LocalMachine" else 1)
        thumbprint = st.text_input("Thumbprint Principal", value=atual.get("thumbprint", ""))
        if st.form_submit_button("Salvar Vínculo do Certificado"):
            limpo = re.sub(r"\s+", "", thumbprint).upper()
            if limpo and not re.fullmatch(r"[A-F0-9]{40,128}", limpo): st.error("O Thumbprint inserido é inválido.")
            else:
                config = {"store": store, "store_name": "My", "thumbprint": limpo}
                CERT_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
                registrar_auditoria(usuario["username"], "configurar_certificado", "Thumbprint global alterado")
                st.success("Thumbprint salvo! A senha da chave privada nunca será manipulada pelo ERP.")

def renderizar_usuarios(usuario):
    if usuario["perfil"] != "admin":
        st.error("Acesso negado: Requer privilégios de administrador.")
        st.stop()
        
    st.subheader("Gestão de Usuários")
    
    with st.expander("Cadastrar Novo Usuário", expanded=False):
        with st.form("form_usuario"):
            username = st.text_input("Novo usuário")
            senha = st.text_input("Senha temporária", type="password")
            perfil = st.selectbox("Perfil", ["operador", "admin"])
            criar = st.form_submit_button("Criar usuário", use_container_width=True)
            
        if criar:
            valida, mensagem = senha_valida(senha)
            if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
                st.error("Usuário inválido. Use 3 a 40 caracteres (letras, números, ponto, hífen ou sublinhado).")
            elif not valida:
                st.error(mensagem)
            else:
                try:
                    data = agora_iso()
                    exec_db("INSERT INTO usuarios (username, senha_hash, perfil, ativo, senha_alterada_em, deve_trocar_senha, criado_em) VALUES (?, ?, ?, 1, ?, 1, ?)",
                            (username, gerar_hash_senha(senha), perfil, data, data), commit=True)
                    registrar_auditoria(usuario["username"], "criar_usuario", f"Usuário: {username}; perfil: {perfil}")
                    st.success("Usuário criado com sucesso. Ele deverá trocar a senha no primeiro login.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Esse usuário já existe.")
                
    usuarios = banco.execute("SELECT id, username, perfil, ativo, ultimo_acesso, senha_alterada_em FROM usuarios ORDER BY username").fetchall()
    opcoes = [dict(u) for u in usuarios]
    st.dataframe(pd.DataFrame(opcoes), use_container_width=True, hide_index=True)
    
    alvo = st.selectbox("Usuário para administrar", opcoes, format_func=lambda x: f"{x['username']} ({x['perfil']})")
    c1, c2 = st.columns(2)
    if c1.button("Ativar usuário"):
        exec_db("UPDATE usuarios SET ativo=1 WHERE id=?", (alvo["id"],), commit=True)
        registrar_auditoria(usuario["username"], "ativar_usuario", f"Usuário: {alvo['username']}")
        st.rerun()
    if c2.button("Inativar usuário"):
        if alvo["username"] == usuario["username"]:
            st.error("Você não pode inativar sua própria conta.")
        else:
            admins_ativos = banco.execute("SELECT COUNT(*) AS total FROM usuarios WHERE perfil='admin' AND ativo=1").fetchone()["total"]
            if alvo["perfil"] == "admin" and alvo["ativo"] and admins_ativos <= 1:
                st.error("Não é permitido inativar o último administrador ativo.")
            else:
                exec_db("UPDATE usuarios SET ativo=0 WHERE id=?", (alvo["id"],), commit=True)
                registrar_auditoria(usuario["username"], "inativar_usuario", f"Usuário: {alvo['username']}")
                st.rerun()
                
    st.divider()
    st.subheader("Redefinir senha de usuário")
    with st.form("form_redefinir_senha"):
        nova = st.text_input("Nova senha temporária", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        redefinir = st.form_submit_button("Redefinir senha", use_container_width=True)
    if redefinir:
        if nova != confirmar:
            st.error("A confirmação não coincide.")
        else:
            valida, mensagem = senha_valida(nova)
            if not valida:
                st.error(mensagem)
            else:
                exec_db("UPDATE usuarios SET senha_hash=?, senha_alterada_em=?, deve_trocar_senha=1, falhas_login=0, bloqueado_ate=NULL WHERE id=?", 
                        (gerar_hash_senha(nova), agora_iso(), alvo["id"]), commit=True)
                registrar_auditoria(usuario["username"], "redefinir_senha", f"Senha redefinida para {alvo['username']}")
                st.success("Senha redefinida. O usuário deverá alterá-la no próximo login.")

# --- INICIALIZAÇÃO DA APLICAÇÃO ---
if not st.session_state.get("autenticado", False):
    st.title("OSC Assessoria Contábil")
    st.caption("ERP Fiscal — Acesso Administrativo e Operacional")
    with st.form("form_login"):
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            usuario, mensagem = autenticar(username.strip(), senha)
            if usuario:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario
                st.session_state["ultimo_acesso"] = agora()
                st.rerun()
            st.error(mensagem)
    st.stop()

usuario_atual = st.session_state["usuario"]
ultimo_acesso = st.session_state.get("ultimo_acesso", agora())
if agora() - ultimo_acesso > dt.timedelta(minutes=SESSAO_MINUTOS):
    registrar_auditoria(usuario_atual["username"], "sessao_expirada", "Usuário desconectado por inatividade")
    st.session_state.clear()
    st.warning("Sua sessão expirou. Faça login novamente.")
    st.stop()
st.session_state["ultimo_acesso"] = agora()

if senha_vencida(usuario_atual):
    st.title("Renovação Trimestral Obrigatória")
    formulario_troca_senha(usuario_atual, obrigatoria=True)
    st.stop()

with st.sidebar:
    st.title("OSC Assessoria Contábil")
    st.caption(f"Logado como: **{usuario_atual['username']}** ({usuario_atual['perfil']})")
    st.caption(f"Ambiente: **{obter_ambiente()}**")
    if st.button("Alterar minha senha", use_container_width=True): st.session_state["mostrar_troca_senha"] = True
    if st.button("Sair / Logout", use_container_width=True):
        registrar_auditoria(usuario_atual["username"], "logout", "Logoff manual do painel.")
        st.session_state.clear()
        st.rerun()

if st.session_state.get("mostrar_troca_senha", False):
    with st.expander("Alterar minha senha", expanded=True):
        formulario_troca_senha(usuario_atual)

st.title("OSC Assessoria Contábil")
st.caption(f"Captação Passiva de Documentos — Execução restrita ao ambiente {obter_ambiente()}")

if usuario_atual["perfil"] == "admin":
    tabs = st.tabs(["Consultas Sefaz", "Clientes/Integrações", "Conectores", "Gestão de Usuários", "Configurações Globais", "Trilha de Auditoria"])
    with tabs[0]: renderizar_consultas(usuario_atual)
    with tabs[1]: renderizar_clientes(usuario_atual)
    with tabs[2]: renderizar_conectores(usuario_atual)
    with tabs[3]: renderizar_usuarios(usuario_atual)
    with tabs[4]: renderizar_configuracoes(usuario_atual)
    with tabs[5]: 
        st.dataframe(pd.DataFrame([dict(l) for l in banco.execute("SELECT * FROM auditoria_logs ORDER BY id DESC LIMIT 500").fetchall()]), use_container_width=True)
else:
    tabs = st.tabs(["Consultas Sefaz", "Repositório Visual de XMLs"])
    with tabs[0]: renderizar_consultas(usuario_atual)
    with tabs[1]: st.info("Arquivos disponíveis para download (Visualização Operacional simplificada).")