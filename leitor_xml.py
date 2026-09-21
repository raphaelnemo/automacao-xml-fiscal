import xml.etree.ElementTree as ET

def extrair_dados_xml(caminho_arquivo):
    # 1. Carrega e analisa o arquivo XML
    tree = ET.parse(caminho_arquivo)
    root = tree.getroot()
    
    # Define o namespace padrão que a Sefaz usa em notas fiscais
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    # 2. Busca os campos específicos dentro das tags do XML
    cnpj_emitente = root.find('.//nfe:emit/nfe:CNPJ', ns).text
    nome_emitente = root.find('.//nfe:emit/nfe:xNome', ns).text
    valor_total = root.find('.//nfe:total/nfe:ICMSTot/nfe:vNF', ns).text
    data_emissao = root.find('.//nfe:ide/nfe:dhEmi', ns).text
    
    # 3. Exibe as informações extraídas
    print("\n--- DADOS EXTRAÍDOS DO XML ---")
    print(f"Emitente:     {nome_emitente}")
    print(f"CNPJ:         {cnpj_emitente}")
    print(f"Data Emissão: {data_emissao}")
    print(f"Valor Total:  R$ {valor_total}")
    print("------------------------------\n")

# --- EXECUÇÃO DO TESTE ---
extrair_dados_xml("exemplo_nfce.xml")