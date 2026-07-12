# config.py — Configuration centrale du bot
# Charge les variables d'environnement depuis le fichier .env (si présent)

import os
from dotenv import load_dotenv

# override=False → les variables Railway/système ont la priorité sur .env
load_dotenv(override=False)

import logging

_log = logging.getLogger(__name__)

# ── Token du bot Telegram ──────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    _log.warning("BOT_TOKEN is EMPTY! Check your Railway Variables tab.")

# ── Clés API Binance ───────────────────────────────────────────────
BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
BINANCE_PAY_ID: str = os.getenv("BINANCE_PAY_ID", "")

# NOWPayments credentials must stay in Railway environment variables.
NOWPAYMENTS_API_KEY: str = os.getenv("NOWPAYMENTS_API_KEY", "").strip()
NOWPAYMENTS_IPN_SECRET: str = os.getenv("NOWPAYMENTS_IPN_SECRET", "").strip()
NOWPAYMENTS_BASE_URL: str = os.getenv(
    "NOWPAYMENTS_BASE_URL", "https://api.nowpayments.io/v1"
).strip().rstrip("/")
NOWPAYMENTS_ENABLED: bool = os.getenv("NOWPAYMENTS_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
NOWPAYMENTS_FIXED_RATE: bool = os.getenv("NOWPAYMENTS_FIXED_RATE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
NOWPAYMENTS_FEE_PAID_BY_USER: bool = os.getenv(
    "NOWPAYMENTS_FEE_PAID_BY_USER", "false"
).strip().lower() in {"1", "true", "yes", "on"}


# ── Identifiants des administrateurs (séparés par des virgules) ────
ADMIN_IDS: list[int] = [
    int(uid.strip())
    for uid in os.getenv("ADMIN_IDS", "").split(",")
    if uid.strip().isdigit()
]

# ── Paramètres généraux ───────────────────────────────────────────
CURRENCY: str = "USDT"
ORDER_EXPIRY_MINUTES: int = 60
LOW_STOCK_THRESHOLD: int = 3
DB_PATH: str = "bot_data.db"
REQUIRED_CHANNEL: str = os.getenv("REQUIRED_CHANNEL", "@Batmanstore2")
