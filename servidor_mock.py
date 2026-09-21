from flask import Flask, Response

app = Flask(__name__)

# Simula a rota de download da Sefaz/API
@app.route("/sefaz/download/<cnpj>/<chave>", methods=["GET"])
def simular_sefaz(cnpj, chave):
    print(f"\n[SEFAZ SIMULADA] Recebida requisição para CNPJ: {cnpj} | Chave: {chave}")
    
    # XML fictício idêntico ao formato real da Sefaz
    xml_ficticio = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
    <NFe>
        <infNFe Id="NFe{chave}">
            <ide>
                <dhEmi>2026-09-05T15:00:00-03:00</dhEmi>
            </ide>
            <emit>
                <CNPJ>{cnpj}</CNPJ>
                <xNome>Supermercado Simulado LTDA</xNome>
            </emit>
            <total>
                <ICMSTot>
                    <vNF>345.80</vNF>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
</nfeProc>"""
    
    return Response(xml_ficticio, mimetype="text/xml")

if __name__ == "__main__":
    print("=" * 60)
    print("Servidor Simulador da Sefaz ativo em: http://127.0.0.1:5000")
    print("Mantenha esta janela aberta enquanto testa!")
    print("=" * 60)
    app.run(port=5000)