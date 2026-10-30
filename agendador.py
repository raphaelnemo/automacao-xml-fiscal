import time
import datetime
import sqlite3
import sys
import requests
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "segredos" / "osc_sistema.db"
AMBIENTE_PATH = BASE_DIR / "ambiente.txt"
INTERVALO_ENTRE_CLIENTES_SEGUNDOS = 10  # Espaçamento de segurança entre requisições
INTERVALO_CICLO_MINUTOS = 2             # Recorrência da rodada geral


def obter_ambiente():
    if not AMBIENTE_PATH.exists():
        return "HOMOLOGACAO"
    amb = AMBIENTE_PATH.read_text(encoding="utf-8").strip().upper()
    return amb if amb in ("PRODUCAO", "HOMOLOGACAO") else "HOMOLOGACAO"


def obter_conexao():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
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
    conn.commit()
    return conn


def limpar_url(url_bruta):
    """Remove formatações de markdown ou espaços extras da URL salva no banco"""
    if not url_bruta:
        return ""
    url = str(url_bruta).strip().rstrip("/")
    if "](" in url:
        url = url.split("](")[-1].rstrip(")")
    url = url.replace("[", "").replace("]", "")
    return url


def proximo_nsu_str(ultimo_nsu):
    if not ultimo_nsu:
        return "1"
    limpo = str(ultimo_nsu).strip()
    if limpo.isdigit():
        return str(int(limpo) + 1)
    return "1"


def cliente_autorizado(cliente):
    if not cliente["ativo"] or not cliente["pode_consultar"]:
        return False
    if cliente["tipo_autenticacao"] == "procuracao" and not cliente["procuracao_ativa"]:
        return False
    if cliente["tipo_autenticacao"] == "proprio" and not cliente["thumbprint_proprio"]:
        return False
    return True


def executar_rodada_agendada():
    conn = obter_conexao()
    cursor = conn.cursor()
    ambiente_atual = obter_ambiente()

    conector = cursor.execute(
        """
        SELECT * FROM conectores_fiscais 
        WHERE ativo = 1 AND ambiente = ? AND usa_nsu = 1
        LIMIT 1
    """,
        (ambiente_atual,),
    ).fetchone()

    if not conector:
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [AGENDADOR] Nenhum conector ativo para o ambiente {ambiente_atual} encontrado."
        )
        conn.close()
        return

    url_base_limpa = limpar_url(conector["url_consulta"])

    registros_clientes = cursor.execute(
        """
        SELECT * FROM clientes 
        WHERE ativo = 1 
          AND pode_consultar = 1 
          AND outro_sistema_nsu = 'NAO'
        ORDER BY ultima_consulta_nfse_em ASC
    """
    ).fetchall()

    clientes = [c for c in registros_clientes if cliente_autorizado(c)]

    print(
        f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] === Iniciando rodada agendada ({ambiente_atual}) para {len(clientes)} cliente(s) ==="
    )

    for cli in clientes:
        cnpj = cli["cnpj"]
        razao = cli["razao_social"]
        nsu_busca = proximo_nsu_str(cli["ultimo_nsu_nfse"])

        url_consulta = f"{url_base_limpa}/{cnpj}/{nsu_busca}"
        agora_str = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        proxima_str = (
            datetime.datetime.now().astimezone() + datetime.timedelta(minutes=INTERVALO_CICLO_MINUTOS)
        ).isoformat(timespec="seconds")

        print(f" -> Consultando {razao} (CNPJ: {cnpj}) | NSU: {nsu_busca}...")

        try:
            res = requests.get(url_consulta, timeout=5)
            if res.status_code == 200:
                dados = res.json()
                detalhes = dados.get("detalhes", {})

                cursor.execute(
                    """
                    INSERT INTO documentos_fiscais (
                        cnpj_cliente, tipo_doc, chave_acesso, nsu, emitente, valor_total, xml_conteudo, data_recebimento
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
                    ON CONFLICT(chave_acesso) DO UPDATE SET data_recebimento = DATETIME('now')
                """,
                    (
                        cnpj,
                        conector["tipo_documento"],
                        detalhes.get("chave"),
                        dados.get("ultNSU"),
                        detalhes.get("emitente"),
                        dados.get("valor"),
                        dados.get("docZip"),
                    ),
                )

                cursor.execute(
                    """
                    UPDATE clientes SET 
                        ultimo_nsu_nfse = ?,
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = 'SUCESSO_NOVA_NOTA',
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """,
                    (dados.get("ultNSU"), agora_str, proxima_str, cli["id"]),
                )

                print(f"    [SUCESSO] Nota capturada! Chave: {detalhes.get('chave', '')[:20]}...")

            elif res.status_code == 404:
                cursor.execute(
                    """
                    UPDATE clientes SET 
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = 'FILA_FINALIZADA',
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """,
                    (agora_str, proxima_str, cli["id"]),
                )
                print("    [SEM NOVIDADES] Fila zerada para este cliente.")
            else:
                cursor.execute(
                    """
                    UPDATE clientes SET 
                        ultima_consulta_nfse_em = ?,
                        ultimo_status_nfse = ?,
                        proxima_consulta_nfse_em = ?
                    WHERE id = ?
                """,
                    (agora_str, f"ERRO_{res.status_code}", proxima_str, cli["id"]),
                )
                print(f"    [ERRO] Resposta Sefaz: Status {res.status_code}")

        except Exception as e:
            cursor.execute(
                """
                UPDATE clientes SET 
                    ultima_consulta_nfse_em = ?,
                    ultimo_status_nfse = 'FALHA_CONEXAO',
                    proxima_consulta_nfse_em = ?
                WHERE id = ?
            """,
                (agora_str, proxima_str, cli["id"]),
            )
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
