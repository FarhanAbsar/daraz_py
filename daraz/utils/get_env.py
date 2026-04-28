from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parents[2]

# ── ENV LOAD ──
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

url = os.getenv("DARAZ_BASE_URL", "https://api.daraz.com.bd/rest")
appkey = os.getenv("DARAZ_APP_KEY")
appSecret = os.getenv("DARAZ_APP_SECRET")
authUrl = os.getenv("DARAZ_AUTH_URL")