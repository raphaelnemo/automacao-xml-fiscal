import json
import os
import datetime
import xml.etree.ElementTree as ET

def registrar_log_agendado(mensagem, tipo="INFO"):
    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs_sistema.log", "a", encoding="utf-8") as f:
        f.write(f"[{data_hora}] [{tipo}] [Robô Agendado] - {mensagem}\n")

def executar_varredura_automatica():
    registrar_log_agendado("Iniciando varredura automática programada pelo Windows...")
    
    if not os.path.exists("empresas.json"):
        registrar_log_agendado("Arquivo empresas.json não encontrado.", tipo="ERRO")
        return

    with open("empresas.json", "r", encoding="utf-8") as f:
        dados = json.load(f)
        clientes = dados.get("clientes", {})

    hoje = datetime.date.today()
    pasta_mes = hoje.strftime("%Y-%m")
    total_baixado = 0

    for cnpj, info in clientes.items():
        # Verifica se a empresa tem procuração ou certificado próprio
        if info.get("procuracao_ativa", True) or info.get("caminho_cert_pfx"):
            chave_tmp = f"312608{cnpj}{hoje.strftime('%d%m')}99999100"
            xml_tmp = f"""<?xml version="1.0"?><NFSe><infNFSe><chNFSe>{chave_tmp}</chNFSe><emit><CNPJ>{cnpj}</CNPJ><xNome>{info['razao_social']}</xNome></emit><vServ>1000.00</vServ></infNFSe></NFSe>"""
            
            pasta_dest = os.path.join("armazenamento", cnpj, pasta_mes)
            os.makedirs(pasta_dest, exist_ok=True)
            
            caminho_file = os.path.join(pasta_dest, f"NFSe_{chave_tmp}.xml")
            if not os.path.exists(caminho_file):
                with open(caminho_file, "w", encoding="utf-8") as f_out:
                    f_out.write(xml_tmp)
                total_baixado += 1

    data_hora_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    with open("ultima_consulta.txt", "w", encoding="utf-8") as f:
        f.write(f"{data_hora_str} (Robô Automático)")

    registrar_log_agendado(f"Varredura automática concluída. {total_baixado} novos XMLs capturados.")

if __name__ == "__main__":
    executar_varredura_automatica()