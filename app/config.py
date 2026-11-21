import os

from dotenv import load_dotenv

load_dotenv()


def _e(key, default=""):
    return os.environ.get(key, default).strip()


API_ID = _e("API_ID")
API_HASH = _e("API_HASH")
BOT_TOKEN = _e("BOT_TOKEN")
CHANNEL_RAW = _e("CHANNEL")
CHANNEL = int(CHANNEL_RAW) if CHANNEL_RAW.lstrip("-").isdigit() else CHANNEL_RAW


def _webapp():
    u = _e("WEBAPP_URL")
    if u and u.lower() != "auto":
        return u.rstrip("/")
    if _e("RENDER_EXTERNAL_URL"):  # set automatically by Render
        return _e("RENDER_EXTERNAL_URL").rstrip("/")
    if _e("KOYEB_PUBLIC_DOMAIN"):  # set automatically by Koyeb
        return "https://" + _e("KOYEB_PUBLIC_DOMAIN")
    return ""


WEBAPP_URL = _webapp()
PORT = int(_e("PORT", "8000"))
MONGO_URI = _e("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = _e("MONGO_DB", "sakura")
TRANSLATE_TO = _e("TRANSLATE_TO", "en")
ADMIN_IDS = {int(x) for x in _e("ADMIN_IDS").split(",") if x.strip().isdigit()}


def check():
    need = {"API_ID": API_ID, "API_HASH": API_HASH, "BOT_TOKEN": BOT_TOKEN, "CHANNEL": CHANNEL_RAW, "WEBAPP_URL": WEBAPP_URL}
    missing = [k for k, v in need.items() if not v]
    if missing:
        raise SystemExit("❌ Missing settings: " + ", ".join(missing) + "  (see .env.example)")
    if not API_ID.isdigit():
        raise SystemExit("❌ API_ID must be a number (from my.telegram.org)")
    if not WEBAPP_URL.startswith("https://"):
        raise SystemExit("❌ WEBAPP_URL must be a public https:// URL (Telegram Mini Apps require HTTPS)")
