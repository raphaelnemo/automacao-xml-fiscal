import json
import os
import shutil
import xml.etree.ElementTree as ET
import requests

URL_SERVIDOR = "http://127.0.0.1:5000/sefaz/download"

def baixar_e_organizar(cnpj, chave_acesso, razao_social):
    url_requisicao = f"{URL_SERVIDOR}/{cnpj}/{chave_acesso}"
    print(f"\n[+] Processando: {razao_social} (CNPJ: {cnpj})")
    print(f"    Solicitando XML à Sefaz...")
    
    resposta = requests.get(url_requisicao)
    
    if resposta.status_code == 200:
        temp_file = "temp_download.xml"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(resposta.text)
            
        # Extrai CNPJ e Data de dentro do XML recebido
        tree = ET.parse(temp_file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        cnpj_xml = root.find('.//nfe:emit/nfe:CNPJ', ns).text
        data_emissao = root.find('.//nfe:ide/nfe:dhEmi', ns).text  # Ex: 2026-09-05...
        ano_mes = data_emissao[:7]
        
        # Cria a hierarquia: armazenamento/CNPJ/ANO-MES/
        pasta_destino = os.path.join("armazenamento", cnpj_xml, ano_mes)
        os.makedirs(pasta_destino, exist_ok=True)
        
        caminho_final = os.path.join(pasta_destino, f"{chave_acesso}.xml")
        shutil.move(temp_file, caminho_final)
        
        print(f"    -> OK: Salvo em '{caminho_final}'")
    else:
        print(f"    -> ERRO: Falha ao conectar (Código {resposta.status_code})")

def processar_todas_empresas():
    # 1. Carrega a lista de empresas do JSON
    with open("empresas.json", "r", encoding="utf-8") as f:
        empresas = json.load(f)
    
    print("=" * 60)
    print(f"INICIANDO PROCESSAMENTO EM LOTE ({len(empresas)} EMPRESAS)")
    print("=" * 60)
    
    # 2. Percorre cada empresa da lista
    for cnpj, dados in empresas.items():
        # Chave fictícia gerada para o teste
        chave_simulada = f"312609{cnpj}650010000001011000001010"
        
        # Baixa e organiza
        baixar_e_organizar(
            cnpj=cnpj, 
            chave_acesso=chave_simulada, 
            razao_social=dados["razao_social"]
        )

    print("\n" + "=" * 60)
    print("TODAS AS EMPRESAS FORAM PROCESSADAS COM SUCESSO!")
    print("=" * 60)

# --- EXECUÇÃO DO LOTE ---
processar_todas_empresas()