import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Trata o diretório temporário criado pelo PyInstaller no modo congelado
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    os.chdir(base_dir)
    script_path = os.path.join(base_dir, "app", "app.py")

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]

    sys.exit(stcli.main())