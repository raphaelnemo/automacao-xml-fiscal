import sqlite3
from pathlib import Path

db_path = Path("segredos/osc_sistema.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE conectores_fiscais SET url_consulta = ? WHERE ambiente = ?",
        ("http://localhost:5000/DFe", "HOMOLOGACAO")
    )
    conn.commit()
    conn.close()
    print("Conector atualizado com sucesso para http://localhost:5000/DFe!")
else:
    print("Banco de dados não encontrado.")