import datetime
import random
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from flask import Flask, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "segredos" / "osc_sistema.db"

SERVICOS_EXEMPLO = [
    ("Consultoria em Tecnologia da Informacao", 2500.00),
    ("Servicos de Assessoria Contabil e Fiscal", 1800.50),
    ("Desenvolvimento de Software Sob Medida", 5400.00),
    ("Manutencao e Suporte de Redes", 950.00),
    ("Treinamento e Capacitacao Profissional", 1200.00)
]

def gerar_chave_acesso(uf="35", cnpj="00000000000000", mod="55", nsu="1"):
    agora = datetime.datetime.now()
    aamm = agora.strftime("%y%m")
    cnpj_pad = cnpj.zfill(14)
    mod_pad = mod.zfill(2)
    serie = "001"
    numero = str(nsu).zfill(9)
    tp_emiss = "1"
    codigo_num = str(random.randint(10000000, 99999999))
    
    chave_sem_dv = f"{uf}{aamm}{cnpj_pad}{mod_pad}{serie}{numero}{tp_emiss}{codigo_num}"
    
    # Cálculo do Dígito Verificador Módulo 11
    pesos = [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] * 4
    soma = sum(int(digit) * weight for digit, weight in zip(chave_sem_dv, pesos[:43]))
    resto = soma % 11
    dv = 0 if resto in (0, 1) else 11 - resto
    
    return f"{chave_sem_dv}{dv}"

def gerar_xml_completo(cnpj_dest, nsu):
    descricao_servico, valor = random.choice(SERVICOS_EXEMPLO)
    chave = gerar_chave_acesso(cnpj=cnpj_dest, nsu=nsu)
    data_emissao = datetime.datetime.now().isoformat(timespec="seconds")
    
    xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.portalfiscal.inf.br/nfse">
    <infNFSe Id="NFS{chave}">
        <ambiente>2</ambiente>
        <dataEmissao>{data_emissao}</dataEmissao>
        <chaveAcesso>{chave}</chaveAcesso>
        <nsu>{str(nsu).zfill(15)}</nsu>
        <emitente>
            <CNPJ>99999999000191</CNPJ>
            <razaoSocial>PROVEDOR DE SERVICOS S.A.</razaoSocial>
            <nomeFantasia>TechServices Brasil</nomeFantasia>
        </emitente>
        <tomador>
            <CNPJ>{cnpj_dest}</CNPJ>
        </tomador>
        <servico>
            <discriminacao>{descricao_servico}</discriminacao>
            <valorTotal>{valor:.2f}</valorTotal>
            <aliquotaISS>5.00</aliquotaISS>
            <valorISS>{valor * 0.05:.2f}</valorISS>
        </servico>
    </infNFSe>
</NFSe>"""
    
    return {
        "nsu": str(nsu).zfill(15),
        "chave": chave,
        "tipo": "NFS-e",
        "emitente": "PROVEDOR DE SERVICOS S.A.",
        "valor": valor,
        "xml": xml_str
    }

@app.route("/DFe/<cnpj>/<nsu>", methods=["GET"])
def consultar_nsu_dinamico(cnpj, nsu):
    """Retorna notas fiscais geradas dinamicamente por CNPJ e NSU"""
    try:
        nsu_int = int(nsu)
    except ValueError:
        nsu_int = 1

    # O mock simula que cada cliente tem até 50 notas na fila
    if nsu_int <= 50:
        nota = gerar_xml_completo(cnpj, nsu_int)
        proximo_nsu = str(nsu_int + 1).zfill(15)
        
        return jsonify({
            "status": "200",
            "mensagem": "Documento localizado com sucesso.",
            "ultNSU": nota["nsu"],
            "maxNSU": "000000000000050",
            "docZip": nota["xml"],
            "detalhes": {
                "chave": nota["chave"],
                "valor": nota["valor"],
                "emitente": nota["emitente"]
            }
        }), 200
    else:
        return jsonify({
            "status": "137",
            "mensagem": "Nenhum documento localizado para o NSU informado (Fila finalizada).",
            "ultNSU": str(nsu_int).zfill(15),
            "maxNSU": "000000000000050"
        }), 404

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "107", "servico": "Mock Sefaz Dinamico Operacional"}), 200

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Servidor Mock Sefaz Dinâmico Ativo na porta 5000")
    print("Endpoint: http://localhost:5000/DFe/<CNPJ>/<NSU>")
    print("--------------------------------------------------")
    app.run(host="127.0.0.1", port=5000, debug=False)
    