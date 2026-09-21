import json

def carregar_credenciais(cnpj):
    # Lê o arquivo empresas.json que criamos
    with open("empresas.json", "r", encoding="utf-8") as arquivo:
        dados_empresas = json.load(arquivo)
    
    # Procura o CNPJ informado
    if cnpj in dados_empresas:
        empresa = dados_empresas[cnpj]
        print("=" * 40)
        print(f"Empresa Localizada: {empresa['razao_social']}")
        print(f"Caminho do Certificado: {empresa['certificado']}")
        print(f"Status: Pronta para consultar a Sefaz/API")
        print("=" * 40)
        return empresa
    else:
        print(f"Erro: O CNPJ {cnpj} não está cadastrado no empresas.json")
        return None

# --- TESTE DA CONSULTA ---
# Digite aqui o CNPJ que quer buscar (para testar)
cnpj_para_consultar = "12345678000199"

carregar_credenciais(cnpj_para_consultar)