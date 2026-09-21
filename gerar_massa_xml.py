import os
import random
from datetime import datetime, timedelta

# Clientes cadastrados na sua base
clientes = [
    {"cnpj": "12345678000199", "razao": "Mercado Exemplo Ltda"},
    {"cnpj": "98765432000111", "razao": "Padaria Silva Ltda"},
    {"cnpj": "45678912000133", "razao": "Drogaria Muriae Ltda"},
    {"cnpj": "78912345000144", "razao": "Auto Posto Zona da Mata Ltda"},
    {"cnpj": "32165498000155", "razao": "Lanchonete Central Ltda"}
]

# Período solicitado: 20/08/2026 até 05/09/2026
data_inicio = datetime(2026, 8, 20)
data_fim = datetime(2026, 9, 5)
dias_totais = (data_fim - data_inicio).days + 1

pasta_base = "armazenamento"
os.makedirs(pasta_base, exist_ok=True)

total_notas = 1000
notas_geradas = 0

print(f"Gerando {total_notas} XMLs simulados da Sefaz...")

for i in range(1, total_notas + 1):
    cliente = random.choice(clientes)
    cnpj = cliente["cnpj"]
    razao = cliente["razao"]
    
    # Sorteia data no intervalo
    dias_random = random.randint(0, dias_totais - 1)
    data_emissao = data_inicio + timedelta(days=dias_random)
    str_data = data_emissao.strftime("%Y-%m-%d")
    pasta_mes = data_emissao.strftime("%Y-%m")
    
    # Tipo de nota (NFS-e de serviço ou NF-e de produto)
    tipo = random.choice(["NFSe", "NFe"])
    valor = round(random.uniform(80.0, 4500.0), 2)
    
    # Chave de acesso simulada no padrão Sefaz (44 dígitos)
    chave = f"312608{cnpj}{data_emissao.strftime('%d%m')}{i:09d}10000000"
    
    # Pasta de destino conforme a estrutura do repositório
    pasta_destino = os.path.join(pasta_base, cnpj, pasta_mes)
    os.makedirs(pasta_destino, exist_ok=True)
    
    # Estrutura XML válida conforme o tipo
    if tipo == "NFSe":
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.abrasf.org.br/nfse.xsd">
    <infNFSe>
        <chNFSe>{chave}</chNFSe>
        <dhEmi>{str_data}T10:15:00-03:00</dhEmi>
        <emit>
            <CNPJ>{cnpj}</CNPJ>
            <xNome>{razao}</xNome>
        </emit>
        <vServ>{valor:.2f}</vServ>
    </infNFSe>
</NFSe>"""
    else:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
    <NFe>
        <infNFe Id="NFe{chave}">
            <ide>
                <dhEmi>{str_data}T14:20:00-03:00</dhEmi>
            </ide>
            <emit>
                <CNPJ>{cnpj}</CNPJ>
                <xNome>{razao}</xNome>
            </emit>
            <total>
                <ICMSTot>
                    <vNF>{valor:.2f}</vNF>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
</nfeProc>"""

    # Nome do arquivo exatamente como a Sefaz grava
    nome_arquivo = f"{tipo}_{chave}.xml"
    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
    
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    notas_geradas += 1

print(f"✅ Concluído! {notas_geradas} XMLs foram salvos na pasta '{pasta_base}/'.")