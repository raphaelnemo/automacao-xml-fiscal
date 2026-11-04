import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Quando empacotado com PyInstaller (--onedir), sys._MEIPASS aponta para _internal (onde está app/app.py),
    # enquanto sys.executable aponta para a pasta principal do aplicativo (onde ficam segredos/, logs/, armazenamento/).
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        internal_dir = Path(getattr(sys, "_MEIPASS", exe_dir))
    else:
        exe_dir = Path(__file__).resolve().parent
        internal_dir = exe_dir

    os.chdir(exe_dir)
    script_path = str(internal_dir / "app" / "app.py")
    log_path = exe_dir / "logs" / "sistema.log"

    # O modo --windowed deixa os streams como None; grave os diagnósticos em arquivo.
    if sys.stdout is None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = log_path.open("a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        sys.stderr = log_path.open("a", encoding="utf-8", buffering=1)

    # Lê a porta configurada em porta.txt (se existir), caso contrário usa 8501
    porta = "8501"
    porta_file = exe_dir / "porta.txt"
    if porta_file.exists():
        try:
            valor = porta_file.read_text(encoding="utf-8").strip()
            if valor.isdigit() and 1024 <= int(valor) <= 65535:
                porta = valor
        except Exception:
            pass

    def registrar_erro(mensagem):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"[ERRO DE INICIALIZACAO] {mensagem}\n")

    # Aguarda o servidor responder antes de abrir o navegador.
    def abrir_navegador(url):
        url_saude = f"http://127.0.0.1:{porta}/_stcore/health"
        prazo = time.monotonic() + 60
        while time.monotonic() < prazo:
            try:
                with urllib.request.urlopen(url_saude, timeout=1) as resposta:
                    if resposta.status == 200:
                        if not webbrowser.open(url):
                            registrar_erro(f"Nao foi possivel abrir o navegador em {url}.")
                        return
            except urllib.error.URLError:
                time.sleep(0.5)
        registrar_erro(f"O servidor nao respondeu em 60 segundos: {url_saude}.")

    threading.Thread(
        target=abrir_navegador, args=(f"http://localhost:{porta}",), daemon=True
    ).start()

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.port",
        porta,
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    try:
        sys.exit(stcli.main())
    except Exception as e:
        registrar_erro(str(e))
        raise
