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
PAYMENT_TIMEOUT_SECONDS: int = max(
    60,
    int(os.getenv("PAYMENT_TIMEOUT_SECONDS", "300")),
)

# External supplier catalog. Keep the buyer key in Railway, never in the dashboard bundle.
CANBOSO_API_KEY: str = os.getenv("CANBOSO_API_KEY", "").strip()
CANBOSO_API_BASE_URL: str = os.getenv(
    "CANBOSO_API_BASE_URL", "https://canboso.com"
).strip().rstrip("/")
CANBOSO_API_AUTH_HEADER: str = os.getenv(
    "CANBOSO_API_AUTH_HEADER", "X-API-Key"
).strip() or "X-API-Key"

# MMO NanLux dealer API. Prices and wallet values are returned in VND; the
# conversion rate is editable from the supplier dashboard.
NANLUX_API_KEY: str = os.getenv("NANLUX_API_KEY", "").strip()
NANLUX_API_BASE_URL: str = os.getenv(
    "NANLUX_API_BASE_URL", "https://api.mmonanlux.site"
).strip().rstrip("/")
NANLUX_API_AUTH_HEADER: str = os.getenv(
    "NANLUX_API_AUTH_HEADER", "X-API-KEY"
).strip() or "X-API-KEY"
NANLUX_VND_PER_USD: float = max(
    1.0,
    float(os.getenv("NANLUX_VND_PER_USD", "25000")),
)

# Optional sports catalog used by the virtual prediction game. The provider
# key stays server-side; the dashboard only talks to VenteBot's admin API.
FOOTBALL_DATA_API_KEY: str = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
FOOTBALL_DATA_BASE_URL: str = os.getenv(
    "FOOTBALL_DATA_BASE_URL", "https://api.football-data.org/v4"
).strip().rstrip("/")
GAME_DAILY_CLAIM: int = max(1, int(os.getenv("GAME_DAILY_CLAIM", "300")))
GAME_DEFAULT_MIN_STAKE: int = max(1, int(os.getenv("GAME_DEFAULT_MIN_STAKE", "25")))
GAME_DEFAULT_MAX_STAKE: int = max(
    GAME_DEFAULT_MIN_STAKE,
    int(os.getenv("GAME_DEFAULT_MAX_STAKE", "500")),
)
GAME_DEFAULT_FEE_BPS: int = min(
    2500,
    max(0, int(os.getenv("GAME_DEFAULT_FEE_BPS", "500"))),
)


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
