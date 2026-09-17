import time
import datetime
import sqlite3
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "segredos" / "osc_sistema.db"
INTERVALO_ENTRE_CLIENTES_SEGUNDOS = 10  # Espaçamento de segurança entre requisições
INTERVALO_CICLO_MINUTOS = 2            # Recorrência da rodada geral

def obter_conexao():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def limpar_url(url_bruta):
    """Remove formatações de markdown ou espaços extras da URL salva no banco"""
    if not url_bruta:
        return ""
    url = url_bruta.strip().rstrip('/')
    # Se veio no formato [texto](url), extrai apenas a URL real de dentro dos parênteses
    if '](' in url:
        url = url.split('](')[-1].rstrip(')')
    # Remove eventuais colchetes perdidos
    url = url.replace('[', '').replace(']', '')
    return url

def executar_rodada_agendada():
    conn = obter_conexao()
    cursor = conn.cursor()
    
    # Busca conector de homologação ativo
    conector = cursor.execute("""
        SELECT * FROM conectores_fiscais 
        WHERE ativo = 1 AND ambiente = 'HOMOLOGACAO' AND usa_nsu = 1
        LIMIT 1
    """).fetchone()
    
    if not conector:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [AGENDADOR] Nenhum conector de homologação ativo encontrado.")
        conn.close()
        return

    url_base_limpa = limpar_url(conector['url_consulta'])

    # Busca clientes aptos para consulta por NSU
    clientes = cursor.execute("""
        SELECT * FROM clientes 
        WHERE ativo = 1 
          AND pode_consultar = 1 
          AND outro_sistema_nsu = 'NAO'
        ORDER BY ultima_consulta_nfse_em ASC
    """).fetchall()

    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] === Iniciando rodada agendada para {len(clientes)} cliente(s) ===")

    for cli in clientes:
        cnpj = cli["cnpj"]
        razao = cli["razao_social"]
        ultimo_nsu = cli["ultimo_nsu_nfse"] or "1"
        nsu_busca = str(int(ultimo_nsu) + 1 if ultimo_nsu.isdigit() else 1)
        
        url_consulta = f"{url_base_limpa}/{cnpj}/{nsu_busca}"
        agora_str = datetime.datetime.now().isoformat(timespec="seconds")
        proxima_str = (datetime.datetime.now() + datetime.timedelta(minutes=INTERVALO_CICLO_MINUTOS)).isoformat(timespec="seconds")
        
        print(f" -> Consultando {razao} (CNPJ: {cnpj}) | NSU: {nsu_busca}...")
        
        try:
            res = requests.get(url_consulta, timeout=5)
            if res.status_code == 200:
                dados = res.json()
                detalhes = dados.get("detalhes", {})
                
                # Inserção da Nota Fiscal no Banco
                cursor.execute("""
                    INSERT INTO documentos_fiscais (
                        cnpj_cliente, tipo_doc, chave_acesso, nsu, emitente, valor_total, xml_conteudo, data_recebimento
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
                    ON CONFLICT(chave_acesso) DO UPDATE SET data_recebimento = DATETIME('now')
                """, (
                    cnpj, conector["tipo_documento"], detalhes.get("chave"),
                    dados.get("ultNSU"), detalhes.get("emitente"), detalhes.get("valor"), dados.get("docZip")
                ))
                
                # Atualização do ponteiro e timestamps
                cursor.execute("""
                    UPDATE clientes SET 
                        ultimo_nsu_nfse = ?,
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = 'SUCESSO_NOVA_NOTA',
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """, (dados.get("ultNSU"), agora_str, proxima_str, cli["id"]))
                
                print(f"    [SUCESSO] Nota capturada! Chave: {detalhes.get('chave', '')[:20]}...")
                
            elif res.status_code == 404:
                cursor.execute("""
                    UPDATE clientes SET 
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = 'FILA_FINALIZADA',
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """, (agora_str, proxima_str, cli["id"]))
                print("    [SEM NOVIDADES] Fila zerada para este cliente.")
            else:
                cursor.execute("""
                    UPDATE clientes SET 
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = ?,
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """, (agora_str, f"ERRO_{res.status_code}", proxima_str, cli["id"]))
                print(f"    [ERRO] Resposta Sefaz: Status {res.status_code}")
                
        except Exception as e:
            cursor.execute("""
                UPDATE clientes SET 
                    ultima_consulta_nfse_em = ?,
                    ultimo_status_nfse = 'FALHA_CONEXAO',
                    proxima_consulta_nfse_em = ?
                WHERE id = ?
            """, (agora_str, proxima_str, cli["id"]))
            print(f"    [FALHA] Não foi possível conectar ({url_consulta}): {e}")

        conn.commit()
        time.sleep(INTERVALO_ENTRE_CLIENTES_SEGUNDOS)

    conn.close()
    print(f"=== Rodada finalizada. Próxima execução em {INTERVALO_CICLO_MINUTOS} minuto(s) ===\n")

if __name__ == "__main__":
    print("==================================================")
    print("   MOTOR DE AGENDAMENTO DE CONSULTAS FISCAIS")
    print("==================================================")
    while True:
        executar_rodada_agendada()
        time.sleep(INTERVALO_CICLO_MINUTOS * 60)