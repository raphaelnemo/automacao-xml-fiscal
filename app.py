import streamlit as st
import json
import io
import os
import glob
import zipfile
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import subprocess

# Bibliotecas do ReportLab para geração de PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Biblioteca para Data Grid Estilo ERP (TOTVS)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

# Configuração da página e tema visual
st.set_page_config(
    page_title="OSC Assessoria Contábil", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS Minimalista e Limpeza de Cabeçalhos Padrão
st.markdown("""
    <style>
        /* Remove o menu superior do Streamlit e sobe o app */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important;}
        
        /* Cabeçalho do App Limpo */
        .header-box { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #CBD5E1; padding-bottom: 10px; margin-bottom: 15px;}
        .app-title { color: #0F2C59; font-size: 24px; font-weight: 700; margin: 0; padding: 0; line-height: 1; }
        .app-subtitle { color: #64748B; font-size: 12px; margin: 0; padding: 0;}
        .user-info { font-size: 12px; color: #334155; font-weight: 500;}
        
        /* Botões super compactos (estilo barra de ferramentas ERP) */
        .stButton>button {
            background-color: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1; 
            border-radius: 2px; padding: 0px 8px !important; font-size: 11px !important;
            font-weight: 500; min-height: 24px !important; height: 24px !important;
        }
        .stButton>button:hover { background-color: #E2E8F0; border-color: #94A3B8; }
        
        /* Mensagem Sefaz */
        .sefaz-notice { background-color: #FFFBEB; border: 1px solid #FDE68A; padding: 6px 10px; margin-bottom: 10px; font-size: 11px; color: #92400E; }
    </style>
""", unsafe_allow_html=True)

# --- CONTROLE DE SESSÃO ---
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = 1

# --- DATAS DINÂMICAS GLOBAIS ---
hoje = datetime.date.today()
primeiro_dia_mes = hoje.replace(day=1)

# --- FUNÇÕES DE SUPORTE (SEGURANÇA E BACKEND) ---

def carregar_configuracao_completa():
    try:
        with open("empresas.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "certificado_escritorio": {"cnpj_escritorio": "00123456000199", "caminho_cert_pfx": "certificados/osc.pfx", "senha_cert": "osc2026"},
            "clientes": {
                "12345678000199": {"codigo": "001", "razao_social": "Mercado Exemplo Ltda", "procuracao_ativa": True},
                "98765432000111": {"codigo": "002", "razao_social": "Padaria Silva Ltda", "procuracao_ativa": True}
            }
        }

@st.cache_data
def carregar_empresas():
    return carregar_configuracao_completa().get("clientes", {})

def carregar_usuarios():
    try:
        with open("usuarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": "osc2026"}

def registrar_log(usuario, acao, tipo="INFO"):
    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs_sistema.log", "a", encoding="utf-8") as f:
        f.write(f"[{data_hora}] [{tipo}] [{usuario}] - {acao}\n")

def atualizar_data_ultima_consulta(usuario):
    agora = datetime.datetime.now()
    data_hora_str = agora.strftime("%d/%m/%Y às %H:%M:%S")
    with open("ultima_consulta.txt", "w", encoding="utf-8") as f:
        f.write(f"{agora.isoformat()}|{data_hora_str} (por {usuario})")

def obter_data_obj_ultima_consulta():
    if os.path.exists("ultima_consulta.txt"):
        try:
            with open("ultima_consulta.txt", "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if "|" in conteudo:
                    iso_str = conteudo.split("|")[0]
                    return datetime.datetime.fromisoformat(iso_str).date()
        except Exception:
            pass
    return primeiro_dia_mes

def verificar_trava_consulta_sefaz(intervalo_minutos=60):
    if not os.path.exists("ultima_consulta.txt"):
        return True, ""
    try:
        with open("ultima_consulta.txt", "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if "|" in conteudo:
                iso_str = conteudo.split("|")[0]
                dt_ultima = datetime.datetime.fromisoformat(iso_str)
                agora = datetime.datetime.now()
                diferenca = agora - dt_ultima
                
                if diferenca < datetime.timedelta(minutes=intervalo_minutos):
                    restante = datetime.timedelta(minutes=intervalo_minutos) - diferenca
                    minutos_restantes = int(restante.total_seconds() // 60)
                    segundos_restantes = int(restante.total_seconds() % 60)
                    return False, f"Aguarde {minutos_restantes}m e {segundos_restantes}s (Limite de 1 varredura/hora)."
    except Exception:
        pass
    return True, ""

def gerar_pdf_danfe(tipo, cnpj, razao, codigo, data, chave, valor):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = [Paragraph(f"<b>DANFSE / DANFE (Cód {codigo})</b>", getSampleStyleSheet()['Heading1']), Spacer(1, 10)]
    doc.build(story)
    return buffer.getvalue()

def formatar_cnpj(cnpj):
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

def ler_xmls_salvos_localmente(empresas_dict=None):
    pasta_base = "armazenamento"
    notas_locais = []
    if not os.path.exists(pasta_base): return notas_locais

    arquivos_xml = glob.glob(os.path.join(pasta_base, "**", "*.xml"), recursive=True)
    
    for caminho_xml in arquivos_xml:
        try:
            chave = os.path.splitext(os.path.basename(caminho_xml))[0].replace("NFe_", "").replace("NFSe_", "")
            cnpj_pasta = os.path.basename(os.path.dirname(os.path.dirname(caminho_xml)))
            
            with open(caminho_xml, "r", encoding="utf-8") as f_xml:
                conteudo_xml = f_xml.read()
            
            tipo_doc = "Serviço" if "NFSe" in caminho_xml or "vServ" in conteudo_xml else "Produto"
            info_emp = empresas_dict.get(cnpj_pasta, {})
            codigo_cli = info_emp.get("codigo", "N/A")
            razao_cli = info_emp.get("razao_social", "Desconhecido")
            
            # Determinismo simples de Entrada/Saída baseado no primeiro dígito da chave 
            # (Na vida real, baseia-se no CNPJ do XML)
            is_saida = int(chave[0]) % 2 == 0 if chave[0].isdigit() else True
            operacao = "Saída" if is_saida else "Entrada"
            
            # Alerta Visual
            pendente = False
            if operacao == "Entrada" and tipo_doc == "Produto":
                pendente = int(chave[1]) % 3 == 0 if len(chave) > 1 and chave[1].isdigit() else False

            try:
                tree = ET.parse(caminho_xml)
                root = tree.getroot()
                ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                node_data = root.find('.//nfe:ide/nfe:dhEmi', ns)
                data_emi_str = node_data.text[:10] if node_data is not None else hoje.strftime("%Y-%m-%d")
            except:
                data_emi_str = hoje.strftime("%Y-%m-%d")
                
            # Formata data para a tela (DD/MM/YYYY)
            data_emi_fmt = datetime.datetime.strptime(data_emi_str, "%Y-%m-%d").strftime("%d/%m/%Y")

            notas_locais.append({
                "Cód": codigo_cli,
                "Cliente": razao_cli,
                "Op": "ENT" if operacao == "Entrada" else "SAÍ",
                "Tipo": "NF-e" if tipo_doc == "Produto" else "NFS-e",
                "CNPJ": formatar_cnpj(cnpj_pasta),
                "Emissão": data_emi_fmt,
                "Emissao_raw": data_emi_str, # Usado para filtro
                "Chave": chave, # Sem formatação (solicitação)
                "Valor": round(float(len(chave) * 15.5), 2),
                "Pendente": "Sim" if pendente else "Não",
                "Operacao_Completa": operacao,
                "xml_raw": conteudo_xml,
                "nome_arquivo": os.path.basename(caminho_xml)
            })
        except Exception:
            continue
    return notas_locais

# --- CONTROLE DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.write("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown('<p class="app-title" style="text-align: center;">OSC Assessoria Contábil</p>', unsafe_allow_html=True)
        st.markdown('<p class="app-subtitle" style="text-align: center; margin-bottom: 20px;">Acesso ao Repositório Fiscal</p>', unsafe_allow_html=True)
        with st.form("form_login_osc"):
            user_input = st.text_input("Usuário:")
            pass_input = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                usuarios = carregar_usuarios()
                if user_input in usuarios and usuarios[user_input] == pass_input:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_atual"] = user_input
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

# --- PAINEL PRINCIPAL (CABEÇALHO HTML PURO) ---

st.markdown(f"""
    <div class="header-box">
        <div>
            <p class="app-title">Repositório Fiscal</p>
            <p class="app-subtitle">Gestão de Documentos Eletrônicos (XML/PDF)</p>
        </div>
        <div class="user-info">
            👤 Usuário: <b>{st.session_state['usuario_atual']}</b>
        </div>
    </div>
""", unsafe_allow_html=True)

col_logout, _ = st.columns([1, 8])
with col_logout:
    if st.button("Sair (Logout)"):
        st.session_state["autenticado"] = False
        st.rerun()

empresas = carregar_empresas()
opcoes_empresas = {f"[{v.get('codigo', 'N/A')}] {v['razao_social']}": k for k, v in empresas.items()}
notas_armazenadas = ler_xmls_salvos_localmente(empresas_dict=empresas)

# --- AVISO REGRA SEFAZ (Discreto) ---
st.markdown("""<div class="sefaz-notice">ℹ️ <b>Ciência da Operação:</b> Notas de Entrada com pendência podem conter apenas o XML resumido até que o destinatário realize a manifestação no ERP.</div>""", unsafe_allow_html=True)

# --- FILTROS OCULTÁVEIS ---
with st.expander("⚙️ Filtros da Tabela", expanded=False):
    f_c1, f_c2, f_c3, f_c4, f_c5 = st.columns([1.5, 1, 1, 1, 1.5])
    with f_c1:
        f_emp = st.multiselect("Filtrar Cliente:", options=list(opcoes_empresas.keys()), placeholder="Todos")
    with f_c2:
        f_tp = st.selectbox("Documento:", ["Todos", "NF-e", "NFS-e"])
    with f_c3:
        f_op = st.selectbox("Operação:", ["Todas", "Entrada", "Saída"])
    with f_c4:
        dt_ini_grid = st.date_input("De:", value=primeiro_dia_mes, format="DD/MM/YYYY")
        dt_fim_grid = st.date_input("Até:", value=hoje, format="DD/MM/YYYY")
    with f_c5:
        f_busca = st.text_input("Chave/CNPJ:", placeholder="Digite...")

# APLICAÇÃO DE FILTROS DO GRID
cnpjs_selecionados = [opcoes_empresas[e] for e in f_emp] if f_emp else None
notas_filtradas = []
for n in notas_armazenadas:
    if cnpjs_selecionados and n["CNPJ"] not in [formatar_cnpj(c) for c in cnpjs_selecionados]: continue
    if f_tp != "Todos" and n["Tipo"] != f_tp: continue
    if f_op != "Todas" and n["Operacao_Completa"] != f_op: continue
    if f_busca and f_busca not in n["Chave"] and f_busca not in n["CNPJ"]: continue
    try:
        data_n = datetime.datetime.strptime(n["Emissao_raw"], "%Y-%m-%d").date()
        if not (dt_ini_grid <= data_n <= dt_fim_grid):
            continue
    except Exception:
        pass
    notas_filtradas.append(n)

df_grid = pd.DataFrame(notas_filtradas)

# ==============================================================================
# DATA GRID (AGGRID) - VISUAL TOTVS RM / ERP
# ==============================================================================

if df_grid.empty:
    st.info("Nenhuma nota armazenada localmente atende aos filtros de data/cliente.")
else:
    # Remove as colunas de "sistema" do dataframe visual
    df_visual = df_grid.drop(columns=["Emissao_raw", "Operacao_Completa", "xml_raw", "nome_arquivo"])
    
    # Barra superior da Tabela (Métricas e Download em Lote)
    tb_c1, tb_c2 = st.columns([4, 1])
    with tb_c1:
        st.write(f"Registros visíveis: **{len(df_grid)}** | Soma (R$): **{df_grid['Valor'].sum():,.2f}**")
    with tb_c2:
        excel_data = io.BytesIO()
        with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
            df_visual.to_excel(writer, index=False)
        st.download_button("📥 Exportar Relatório Base", data=excel_data.getvalue(), file_name="Relatorio.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

    # Configuração do AgGrid
    gb = GridOptionsBuilder.from_dataframe(df_visual)
    
    # Checkbox e Agrupamento
    gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
    gb.configure_grid_options(rowGroupPanelShow='always') # Mostra a barra "Arraste aqui para agrupar"
    
    # Formatação e Largura de Colunas Individuais
    gb.configure_column("Cód", width=80)
    gb.configure_column("Cliente", width=250)
    gb.configure_column("Op", width=90)
    gb.configure_column("Tipo", width=90)
    gb.configure_column("Emissão", width=110)
    gb.configure_column("CNPJ", width=160)
    gb.configure_column("Valor", type=["numericColumn","numberColumnFilter"], valueFormatter="x.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})", width=120)
    gb.configure_column("Pendente", width=110)
    
    # A Chave de acesso limpa, com largura grande
    gb.configure_column("Chave", width=380, headerTooltip="Chave de Acesso sem formatação")
    
    gridOptions = gb.build()

    # Renderiza a Grade na Tela
    response = AgGrid(
        df_visual,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED, 
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False, # Permite scroll horizontal
        theme='balham', # Tema nativo super denso e com bordas (estilo ERP clássico)
        height=400,     # Altura fixa do grid
        allow_unsafe_jscode=True
    )
    
    # BOTÕES DE DOWNLOAD PARA OS ITENS SELECIONADOS NA TABELA
    linhas_selecionadas = response['selected_rows']
    
    # Verifica se há algo selecionado (Tratamento para DataFrame ou Lista)
    if linhas_selecionadas is not None and len(linhas_selecionadas) > 0:
        
        # Extrai as chaves de forma segura, independente de como o AgGrid retornou os dados
        if isinstance(linhas_selecionadas, pd.DataFrame):
            chaves_selecionadas = linhas_selecionadas['Chave'].tolist()
        else:
            chaves_selecionadas = [row['Chave'] for row in linhas_selecionadas if isinstance(row, dict)]
            
        if chaves_selecionadas:
            st.write(f"**Ações para {len(chaves_selecionadas)} nota(s) selecionada(s):**")
            btn_c1, btn_c2, _ = st.columns([1.5, 1.5, 4])
            
            # Recupera os dados brutos (XML e PDF) cruzando com as chaves selecionadas
            dados_raw_selecionados = [n for n in notas_filtradas if n['Chave'] in chaves_selecionadas]
            
            with btn_c1:
                buffer_zip_xml = io.BytesIO()
                with zipfile.ZipFile(buffer_zip_xml, "w") as zf:
                    for n in dados_raw_selecionados:
                        zf.writestr(n['nome_arquivo'], n['xml_raw'])
                buffer_zip_xml.seek(0)
                st.download_button(
                    label="📥 Baixar XMLs (ZIP)", 
                    data=buffer_zip_xml, 
                    file_name="XMLs_Selecionados.zip", 
                    mime="application/zip",
                    use_container_width=True
                )
                
            with btn_c2:
                buffer_zip_pdf = io.BytesIO()
                with zipfile.ZipFile(buffer_zip_pdf, "w") as zf:
                    for n in dados_raw_selecionados:
                        pdf_bin = gerar_pdf_danfe(n['Tipo'], n['CNPJ'], n['Cliente'], n['Cód'], n['Emissao_raw'], n['Chave'], n['Valor'])
                        zf.writestr(f"DANFE_{n['Chave']}.pdf", pdf_bin)
                buffer_zip_pdf.seek(0)
                st.download_button(
                    label="📥 Baixar PDFs (ZIP)", 
                    data=buffer_zip_pdf, 
                    file_name="PDFs_Selecionados.zip", 
                    mime="application/zip",
                    use_container_width=True
                )

# ==============================================================================
# PAINEL DA SEFAZ E AGENDAMENTO
# ==============================================================================
st.divider()

col_sefaz, col_robo = st.columns(2)

# --- BUSCA MANUAL SEFAZ ---
with col_sefaz:
    st.markdown("**🌐 Sincronização Sefaz (Busca Manual)**")
    
    # Atualiza trava de imediato para prevenir dupla execução
    pode_consultar, msg_trava = verificar_trava_consulta_sefaz(intervalo_minutos=60)
    
    if not pode_consultar:
        st.warning(f"⏳ {msg_trava}")
    else:
        with st.form("form_sefaz"):
            data_ultima = obter_data_obj_ultima_consulta()
            cs1, cs2 = st.columns(2)
            with cs1:
                clientes_sefaz = st.multiselect("Clientes:", options=list(opcoes_empresas.keys()), placeholder="Selecione...")
            with cs2:
                data_ini_sefaz = st.date_input("Início:", value=data_ultima, format="DD/MM/YYYY")
            
            submit_sefaz = st.form_submit_button("Buscar Novas Notas")
            if submit_sefaz:
                if not clientes_sefaz:
                    st.error("Selecione ao menos um cliente.")
                else:
                    atualizar_data_ultima_consulta(st.session_state['usuario_atual']) # Grava log imediatamente (previne corrida)
                    registrar_log(st.session_state['usuario_atual'], f"Sincronização manual Sefaz (a partir de {data_ini_sefaz}).")
                    # Simulação de Busca
                    for emp_nome in clientes_sefaz:
                        cnpj_emp = opcoes_empresas[emp_nome]
                        chave_tmp = f"312608{cnpj_emp}0001"
                        xml_tmp = f"""<?xml version="1.0"?><nfeProc><NFe><infNFe><ide><dhEmi>{hoje.strftime("%Y-%m-%d")}</dhEmi></ide><emit><CNPJ>{cnpj_emp}</CNPJ><xNome>{emp_nome}</xNome></emit><vNF>1250.00</vNF></infNFe></NFe></nfeProc>"""
                        pasta_dest = os.path.join("armazenamento", cnpj_emp, data_ini_sefaz.strftime("%Y-%m"))
                        os.makedirs(pasta_dest, exist_ok=True)
                        with open(os.path.join(pasta_dest, f"NFe_{chave_tmp}.xml"), "w", encoding="utf-8") as f_out:
                            f_out.write(xml_tmp)
                    st.success("✅ Busca concluída com sucesso!")
                    st.rerun()

# --- AGENDADOR ---
with col_robo:
    st.markdown("**⏰ Agendador de Varredura (Robô)**")
    with st.form("form_robo"):
        hora_exec = st.time_input("Executar busca diária automaticamente às:", value=datetime.time(18, 0))
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.form_submit_button("Salvar no Windows"):
                cmd = f'schtasks /create /tn "OSC_Varredura" /tr "python executar_varredura.py" /sc DAILY /st {hora_exec.strftime("%H:%M")} /f'
                subprocess.run(cmd, shell=True, capture_output=True)
                registrar_log(st.session_state['usuario_atual'], f"Agendamento automático alterado para {hora_exec.strftime('%H:%M')}.")
                st.success("Agendamento criado/atualizado!")
        with c_btn2:
            if st.form_submit_button("Remover"):
                subprocess.run('schtasks /delete /tn "OSC_Varredura" /f', shell=True, capture_output=True)
                st.info("Agendamento removido.")

st.caption("OSC Assessoria Contábil © 2026 — Desenvolvido para simplificar a rotina contábil.")