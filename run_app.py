import os
import sys
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

    sys.exit(stcli.main())
