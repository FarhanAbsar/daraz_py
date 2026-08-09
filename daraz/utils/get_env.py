from pathlib import Path
from dotenv import load_dotenv
import os
from .dual_print import dual_print, IN_JUPYTER

def refresh_env():
    BASE_DIR = Path(__file__).resolve().parents[2]
    # ── ENV LOAD ──
    ENV_PATH = BASE_DIR / ".env"
    load_dotenv(ENV_PATH, override=True)

    return ENV_PATH

ENV_PATH = refresh_env()

url = os.getenv("DARAZ_BASE_URL", "https://api.daraz.com.bd/rest")
appkey = os.getenv("DARAZ_APP_KEY")
appSecret = os.getenv("DARAZ_APP_SECRET")
authUrl = os.getenv("DARAZ_AUTH_URL")