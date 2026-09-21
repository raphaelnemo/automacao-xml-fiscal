import os
import shutil
import xml.etree.ElementTree as ET

def organizar_xml(caminho_xml_origem):
    tree = ET.parse(caminho_xml_origem)
    root = tree.getroot()
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    cnpj = root.find('.//nfe:emit/nfe:CNPJ', ns).text
    data_emissao = root.find('.//nfe:ide/nfe:dhEmi', ns).text
    ano_mes = data_emissao[:7]
    
    pasta_destino = os.path.join("armazenamento", cnpj, ano_mes)
    os.makedirs(pasta_destino, exist_ok=True)
    
    nome_arquivo = os.path.basename(caminho_xml_origem)
    caminho_final = os.path.join(pasta_destino, nome_arquivo)
    
    shutil.copy(caminho_xml_origem, caminho_final)
    print(f"\nSucesso! Arquivo organizado em: {caminho_final}\n")

# Testa organizando o exemplo_nfce.xml que criamos antes
organizar_xml("exemplo_nfce.xml")