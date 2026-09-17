import sqlite3
from pathlib import Path

db_path = Path("segredos/osc_sistema.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.execute('UPDATE clientes SET ultimo_nsu_nfse = "1"')
    conn.execute('DELETE FROM documentos_fiscais')
    conn.commit()
    conn.close()
    print("Ponteiros de NSU e notas resetados com sucesso!")
else:
    print("Banco de dados não encontrado.")