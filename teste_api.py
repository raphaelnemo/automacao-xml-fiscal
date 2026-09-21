import requests

def buscar_endereco_por_cep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    print(f"Conectando à API: {url}...")
    
    resposta = requests.get(url)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        print("\n--- RESPOSTA RECEBIDA DA API ---")
        print(f"Logradouro: {dados.get('logradouro')}")
        print(f"Bairro:     {dados.get('bairro')}")
        print(f"Cidade/UF:  {dados.get('localidade')}/{dados.get('uf')}")
        print("--------------------------------\n")
    else:
        print(f"Erro na requisição. Código: {resposta.status_code}")

# Testando conexão com um CEP de exemplo
buscar_endereco_por_cep("36880000")