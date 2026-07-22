"""
VenteBot — Main entry point.

Wires all handlers together and starts the bot using python-telegram-bot v21+ async API.
Includes a FastAPI REST API with health-check for Railway deployment.
"""

import warnings
from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

import hmac
import hashlib
import base64
import asyncio
import json
import logging
import os
import secrets
import sys
import threading
import math
import re
from collections import Counter, deque
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, Header, HTTPException, Depends, Query, status, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
import uvicorn
import time

# `python bot.py` loads this module as `__main__`. Keep internal imports such as
# `from bot import tg_app` attached to this same runtime instead of loading a
# second copy with separate globals.
if __name__ == "__main__":
    sys.modules.setdefault("bot", sys.modules[__name__])

_stats_cache = {}
_stats_cache_ttl = 10

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from config import ADMIN_IDS, BOT_TOKEN, PAYMENT_TIMEOUT_SECONDS
from database import init_db
from handlers.admin import admin_complete_activation, get_admin_conversation_handler
from handlers.history import show_history, show_order_detail
from handlers.game import (
    choose_game_amount,
    choose_game_outcome,
    claim_game_coins,
    confirm_game_bet,
    show_game_leaderboard,
    show_game_match,
    show_game_menu,
    show_my_game_bets,
)
from handlers.payment import (
    get_payment_conversation_handler,
    download_txt_delivery,
    receive_activation_identifier,
    restore_nowpayments_timeout_tasks,
    safe_send_delivery_messages,
)
from handlers.products import (
    notify_product_restock,
    refresh_products,
    show_product_detail,
    show_products_list,
)
from handlers.profile import show_profile, show_referrals, view_referrals_list
from handlers.reseller_api import confirm_generate_reseller_api_key, generate_reseller_api_key, reseller_api_menu
from handlers.start import change_language, main_menu_callback, set_language, start_command, callback_check_sub
from handlers.support import (
    get_support_conversation_handler,
    show_my_tickets,
    show_ticket_detail,
    support_menu,
    support_menu_text,
)
from handlers.wallet import wallet_conversation_handler, wallet_menu, wallet_history, wallet_noop

from utils.helpers import escape_html
from utils.locales import t, get_confirmation_message

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Keep application warnings and errors while avoiding one INFO line per
# Telegram/supplier HTTP call in Railway logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Secure REST API Server (FastAPI + uvicorn)
# ──────────────────────────────────────────────

api = FastAPI(
    title="VenteBot Admin API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
_service_ready = False

# Enable CORS for browser dashboard access.
# Admin routes still require ADMIN_API_KEY. Optionally lock origins with:
#   CORS_ORIGINS=https://your-dashboard.com,https://your-app.up.railway.app
def _build_cors_origins() -> list[str]:
    allow_file_dashboard = os.environ.get("ALLOW_FILE_DASHBOARD", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw:
        origins = {o.strip() for o in raw.split(",") if o.strip()}
        if "*" in origins:
            logger.warning("CORS_ORIGINS contains '*'. Restrict it to trusted domains in production.")
            return ["*"]
        if allow_file_dashboard:
            # Browsers serialize requests made by a local file:// page as Origin: null.
            origins.add("null")
        return sorted(origins)

    origins: set[str] = set()
    for env_name in ("PUBLIC_BASE_URL", "WEBHOOK_URL"):
        value = os.environ.get(env_name, "").strip()
        if not value:
            continue
        parsed = urlparse(value if "://" in value else f"https://{value}")
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")

    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip().strip("/")
    if railway_domain:
        origins.add(f"https://{railway_domain}")

    if os.environ.get("ENV", "").lower() in {"dev", "development", "local"}:
        origins.update({"http://localhost:8000", "http://127.0.0.1:8000"})

    if allow_file_dashboard:
        origins.add("null")

    if not origins:
        logger.warning(
            "CORS_ORIGINS is empty. Same-origin /dashboard access remains available; "
            "set CORS_ORIGINS for any external dashboard."
        )
    return sorted(origins)


_cors_origins = _build_cors_origins()
_allow_netlify_dashboard = os.environ.get("ALLOW_NETLIFY_DASHBOARD", "true").strip().lower() in {
    "1", "true", "yes", "on"
}
_cors_origin_regex = r"^https://[a-zA-Z0-9-]+\.netlify\.app$" if _allow_netlify_dashboard else None
logger.info("CORS allow_origins=%s allow_origin_regex=%s", _cors_origins, _cors_origin_regex)
api.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
        "Retry-After", "ETag", "X-Catalog-Version", "X-Catalog-Stale",
    ],
)
api.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Serve dashboard static files directly from Railway ──
import pathlib
_dashboard_dir = pathlib.Path(__file__).parent / "dashboard"
if _dashboard_dir.is_dir():
    @api.get("/dashboard")
    async def redirect_dashboard_index():
        return RedirectResponse(url="/dashboard/", status_code=307)

    @api.get("/dashboard/")
    async def serve_dashboard_index():
        return FileResponse(str(_dashboard_dir / "index.html"), media_type="text/html")
    api.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir)), name="dashboard")


@api.middleware("http")
async def configure_dashboard_cache(request: Request, call_next):
    """Revalidate the shell while caching versioned dashboard assets briefly."""
    response = await call_next(request)
    path = request.url.path
    if path in {"/dashboard", "/dashboard/", "/dashboard/index.html"}:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    elif path.startswith("/dashboard/"):
        response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return response


_DASHBOARD_CONTENT_SECURITY_POLICY = "; ".join((
    "default-src 'self'",
    "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
    "font-src 'self' data: https://cdnjs.cloudflare.com",
    "img-src 'self' data: blob: https:",
    "connect-src 'self' https:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))


@api.middleware("http")
async def add_browser_security_headers(request: Request, call_next):
    """Harden browser responses without changing cross-origin API policy."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/dashboard"):
        response.headers["Content-Security-Policy"] = _DASHBOARD_CONTENT_SECURITY_POLICY
    return response

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
if not ADMIN_API_KEY:
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.critical("⚠️ ADMIN_API_KEY not set! Generated temporary key. Set ADMIN_API_KEY env var in production! (Key starts with %s)", ADMIN_API_KEY[:4])

ADMIN_SESSION_COOKIE = "__Host-ventebot_admin_session"
ADMIN_SESSION_SECRET = (
    os.environ.get("ADMIN_SESSION_SECRET", "").strip() or ADMIN_API_KEY
)


def _new_admin_session_token() -> str:
    payload = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    signature = hmac.new(
        ADMIN_SESSION_SECRET.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _valid_admin_session_token(token: str) -> bool:
    try:
        payload, supplied_signature = str(token or "").rsplit(".", 1)
    except ValueError:
        return False
    expected_signature = hmac.new(
        ADMIN_SESSION_SECRET.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return bool(payload) and hmac.compare_digest(supplied_signature, expected_signature)


def _clear_api_stats_cache() -> None:
    _stats_cache.clear()


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


ADMIN_SESSION_MAX_AGE = _env_int("ADMIN_SESSION_MAX_AGE", 10 * 365 * 24 * 60 * 60)
RESELLER_API_RATE_LIMIT = _env_int("RESELLER_API_RATE_LIMIT", 60)
RESELLER_API_RATE_WINDOW = _env_int("RESELLER_API_RATE_WINDOW", 60)
RESELLER_CATALOG_CACHE_SECONDS = _env_int("RESELLER_CATALOG_CACHE_SECONDS", 15)
THREAD_WORKERS = _env_int("THREAD_WORKERS", 32, minimum=4)
HEALTHCHECK_REQUIRE_BOT = _env_bool("HEALTHCHECK_REQUIRE_BOT", True)
_reseller_rate_buckets: dict[str, dict[str, int]] = {}
_reseller_rate_last_cleanup = 0
_reseller_catalog_cache: dict[str, dict] = {}
_reseller_catalog_lock: asyncio.Lock | None = None
_reseller_catalog_lock_loop = None
_reseller_deposit_refresh_at: dict[str, float] = {}
_reseller_deposit_refresh_locks: dict[str, asyncio.Lock] = {}
_reseller_deposit_refresh_last_cleanup = 0.0
_RESELLER_DEPOSIT_REFRESH_TTL_SECONDS = 15 * 60
_RESELLER_DEPOSIT_REFRESH_MAX_ENTRIES = 2048


def _get_reseller_catalog_lock() -> asyncio.Lock:
    global _reseller_catalog_lock, _reseller_catalog_lock_loop
    loop = asyncio.get_running_loop()
    if _reseller_catalog_lock is None or _reseller_catalog_lock_loop is not loop:
        _reseller_catalog_lock = asyncio.Lock()
        _reseller_catalog_lock_loop = loop
    return _reseller_catalog_lock


def _get_reseller_deposit_refresh_lock(deposit_id: str) -> asyncio.Lock:
    _cleanup_reseller_deposit_refresh_state()
    key = str(deposit_id)
    lock = _reseller_deposit_refresh_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _reseller_deposit_refresh_locks[key] = lock
    return lock


def _cleanup_reseller_deposit_refresh_state(*, force: bool = False) -> None:
    global _reseller_deposit_refresh_last_cleanup
    now = time.monotonic()
    if not force and now - _reseller_deposit_refresh_last_cleanup < 60:
        return
    _reseller_deposit_refresh_last_cleanup = now
    expired = []
    for key, refreshed_at in _reseller_deposit_refresh_at.items():
        lock = _reseller_deposit_refresh_locks.get(key)
        if (
            now - refreshed_at >= _RESELLER_DEPOSIT_REFRESH_TTL_SECONDS
            and (lock is None or not lock.locked())
        ):
            expired.append(key)
    for key in expired:
        _reseller_deposit_refresh_at.pop(key, None)
        _reseller_deposit_refresh_locks.pop(key, None)
    if len(_reseller_deposit_refresh_at) > _RESELLER_DEPOSIT_REFRESH_MAX_ENTRIES:
        overflow = len(_reseller_deposit_refresh_at) - _RESELLER_DEPOSIT_REFRESH_MAX_ENTRIES
        oldest = sorted(
            _reseller_deposit_refresh_at,
            key=_reseller_deposit_refresh_at.get,
        )[:overflow]
        for key in oldest:
            lock = _reseller_deposit_refresh_locks.get(key)
            if lock is None or not lock.locked():
                _reseller_deposit_refresh_at.pop(key, None)
                _reseller_deposit_refresh_locks.pop(key, None)


def _is_reseller_api_path(path: str) -> bool:
    return path == "/api/reseller" or path.startswith("/api/reseller/")


def _reseller_error_body(code: str, message: str, **extra) -> dict:
    body = {"success": False, "code": code, "message": message}
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


def _reseller_success(**payload) -> dict:
    return {"success": True, **payload}


def _reseller_error_from_detail(status_code: int, detail) -> dict:
    if isinstance(detail, dict) and detail.get("code") and detail.get("message"):
        return {"success": False, **detail}

    message = str(detail or "API error")
    known = {
        "Missing reseller API key": "MISSING_API_KEY",
        "Invalid reseller API key": "INVALID_API_KEY",
        "Product unavailable": "INVALID_PRODUCT",
        "Insufficient stock": "OUT_OF_STOCK",
        "Stock conflict, please retry": "STOCK_CONFLICT",
        "Insufficient wallet balance": "INSUFFICIENT_BALANCE",
        "Order not found": "ORDER_NOT_FOUND",
        "Order is not waiting for an activation identifier": "INVALID_ORDER_STATUS",
        "activation_identifier is required": "ACTIVATION_IDENTIFIER_REQUIRED",
        "Internal server error": "INTERNAL_ERROR",
    }
    default_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        402: "INSUFFICIENT_BALANCE",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }
    return _reseller_error_body(known.get(message, default_by_status.get(status_code, "API_ERROR")), message)


def _raise_reseller_error(status_code: int, code: str, message: str, headers: dict | None = None, **extra):
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, **extra},
        headers=headers,
    )


def _reseller_rate_headers(remaining: int, reset_at: int) -> dict:
    return {
        "X-RateLimit-Limit": str(RESELLER_API_RATE_LIMIT),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(reset_at),
    }


def _check_reseller_rate_limit(bucket_key: str) -> dict:
    global _reseller_rate_last_cleanup
    now = int(time.time())
    if now - _reseller_rate_last_cleanup >= 60:
        expired = [key for key, value in _reseller_rate_buckets.items() if now >= value.get("reset_at", 0)]
        for key in expired:
            _reseller_rate_buckets.pop(key, None)
        _reseller_rate_last_cleanup = now

    bucket = _reseller_rate_buckets.get(bucket_key)
    if not bucket or now >= bucket["reset_at"]:
        bucket = {"count": 0, "reset_at": now + RESELLER_API_RATE_WINDOW}
        _reseller_rate_buckets[bucket_key] = bucket

    bucket["count"] += 1
    remaining = RESELLER_API_RATE_LIMIT - bucket["count"]
    headers = _reseller_rate_headers(remaining, bucket["reset_at"])

    if bucket["count"] > RESELLER_API_RATE_LIMIT:
        retry_after = max(1, bucket["reset_at"] - now)
        _raise_reseller_error(
            429,
            "RATE_LIMIT_EXCEEDED",
            f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={**headers, "Retry-After": str(retry_after)},
            limit=RESELLER_API_RATE_LIMIT,
            retry_after=retry_after,
        )
    return headers


@api.exception_handler(HTTPException)
async def api_http_exception_handler(request: Request, exc: HTTPException):
    if _is_reseller_api_path(request.url.path):
        return JSONResponse(
            status_code=exc.status_code,
            content=_reseller_error_from_detail(exc.status_code, exc.detail),
            headers=exc.headers,
        )
    return await http_exception_handler(request, exc)


@api.exception_handler(RequestValidationError)
async def api_validation_exception_handler(request: Request, exc: RequestValidationError):
    if _is_reseller_api_path(request.url.path):
        return JSONResponse(
            status_code=422,
            content=_reseller_error_body(
                "VALIDATION_ERROR",
                "Invalid request format.",
                details=jsonable_encoder(exc.errors()),
            ),
        )
    return await request_validation_exception_handler(request, exc)


async def verify_api_key(request: Request, x_api_key: str = Header(None)):
    """Authenticate dashboard/API calls with a header or signed HttpOnly session."""
    header_valid = bool(x_api_key) and hmac.compare_digest(x_api_key, ADMIN_API_KEY)
    session_valid = _valid_admin_session_token(
        request.cookies.get(ADMIN_SESSION_COOKIE, "")
    )
    if not header_valid and not session_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return "api_key" if header_valid else "session"


@api.post("/api/admin/session")
async def create_admin_session(
    request: Request,
    response: Response,
    x_api_key: str = Header(None),
):
    """Exchange the admin key for a same-origin, script-inaccessible session."""
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=_new_admin_session_token(),
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True, "auth": "session"}


@api.get("/api/admin/session", dependencies=[Depends(verify_api_key)])
async def get_admin_session(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True, "authenticated": True}


@api.delete("/api/admin/session")
async def delete_admin_session(response: Response):
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


def _should_audit_admin_request(request: Request) -> bool:
    path = request.url.path
    return (
        request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        and path.startswith("/api/")
        and not path.startswith("/api/reseller/")
        and path != "/api/admin/session"
    )


@api.middleware("http")
async def queue_admin_mutation_audit(request: Request, call_next):
    if not _should_audit_admin_request(request):
        return await call_next(request)

    started_at = time.monotonic()
    response_status = 500
    try:
        response = await call_next(request)
        response_status = int(response.status_code)
        return response
    finally:
        try:
            header = request.headers.get("X-API-Key", "")
            cookie = request.cookies.get(ADMIN_SESSION_COOKIE, "")
            auth_kind = (
                "api_key"
                if header and hmac.compare_digest(header, ADMIN_API_KEY)
                else "session"
                if _valid_admin_session_token(cookie)
                else "unauthenticated"
            )
            source = request.headers.get("x-forwarded-for", "")
            if not source and request.client:
                source = request.client.host or ""
            source_hash = hashlib.sha256(
                f"{ADMIN_SESSION_SECRET}:{source}".encode("utf-8")
            ).hexdigest()[:24]
            from services.admin_audit import enqueue_admin_audit_event

            enqueue_admin_audit_event(
                {
                    "method": request.method.upper(),
                    "path": request.url.path,
                    "status_code": response_status,
                    "duration_ms": (time.monotonic() - started_at) * 1000,
                    "auth_kind": auth_kind,
                    "source_hash": source_hash,
                }
            )
        except Exception as exc:
            logger.warning("Could not queue admin audit event: %s", exc)


async def verify_reseller_key(
    request: Request,
    response: Response,
    x_reseller_key: str = Header(None),
    x_api_key: str = Header(None),
):
    """Authenticate reseller API calls with a limited reseller key."""
    reseller_key = x_reseller_key or x_api_key
    if not reseller_key:
        _raise_reseller_error(status.HTTP_401_UNAUTHORIZED, "MISSING_API_KEY", "Missing reseller API key")
    from database.models import get_reseller_by_api_key
    try:
        reseller = await get_reseller_by_api_key(reseller_key)
    except Exception as exc:
        logger.error("Reseller authentication unavailable: %s", exc, exc_info=True)
        _raise_reseller_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "API_TEMPORARILY_UNAVAILABLE",
            "Authentication service temporarily unavailable. Retry shortly.",
            headers={"Retry-After": "3"},
        )
    if not reseller:
        _raise_reseller_error(status.HTTP_401_UNAUTHORIZED, "INVALID_API_KEY", "Invalid reseller API key")
    from services.reseller_security import ip_is_allowed, request_client_ip

    client_ip = request_client_ip(request)
    if not ip_is_allowed(client_ip, reseller.get("ip_allowlist")):
        logger.warning(
            "Rejected reseller key %s from non-allowlisted IP %s",
            reseller.get("key_prefix"),
            client_ip,
        )
        _raise_reseller_error(
            status.HTTP_403_FORBIDDEN,
            "IP_NOT_ALLOWED",
            "This IP address is not allowed for the reseller API key.",
        )
    rate_headers = _check_reseller_rate_limit(str(reseller.get("id") or reseller.get("key_prefix") or reseller["user_telegram_id"]))
    for key, value in rate_headers.items():
        response.headers[key] = value
    authenticated = dict(reseller)
    authenticated["_rate_headers"] = rate_headers
    return authenticated


def _api_order_payload(order: dict | None) -> dict | None:
    if not order:
        return None
    return {
        "id": order.get("id"),
        "status": order.get("status"),
        "product_id": order.get("product_id"),
        "product_name": order.get("product_name"),
        "quantity": order.get("quantity"),
        "amount_usd": float(order.get("amount_usd") or 0),
        "delivery_type": order.get("delivery_type"),
        "customer_reference": order.get("customer_reference") or "",
        "idempotency_key": order.get("idempotency_key") or "",
        "activation_identifier": order.get("activation_identifier"),
        "created_at": order.get("created_at"),
        "items": [
            {"id": item.get("id"), "account_data": item.get("account_data")}
            for item in order.get("items", [])
        ],
    }


class ResellerQuoteRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(1, gt=0, le=10000)


class ResellerCreateOrderRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(1, gt=0, le=10000)
    activation_identifier: str | None = Field(None, max_length=500)
    customer_reference: str = Field("", max_length=120)
    idempotency_key: str | None = Field(None, max_length=120)


class ResellerActivationIdentifierRequest(BaseModel):
    activation_identifier: str = Field(..., min_length=2, max_length=500)


class ResellerDepositRequest(BaseModel):
    amount_usd: float = Field(..., ge=0.01, le=10000, allow_inf_nan=False)
    network: str = Field("BEP20", min_length=3, max_length=20)
    idempotency_key: str = Field(..., min_length=1, max_length=120)
    reference: str = Field("", max_length=120)


class ResellerSecurityRequest(BaseModel):
    ip_allowlist: list[str] | None = Field(None, max_length=20)
    webhook_url: str | None = Field(None, max_length=500)
    webhook_enabled: bool | None = None
    rotate_webhook_secret: bool = False


class ResellerSpecialPriceRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    price_usd: float = Field(..., gt=0, le=1_000_000, allow_inf_nan=False)
    is_active: bool = True
    enforce_cost_floor: bool = True
    apply_to_telegram: bool = True
    expires_at: datetime | None = None


def _public_reseller_security_config(config: dict) -> dict:
    return {
        "key_id": int(config["id"]),
        "key_prefix": str(config.get("key_prefix") or ""),
        "ip_allowlist": list(config.get("ip_allowlist") or []),
        "webhook_url": str(config.get("webhook_url") or ""),
        "webhook_enabled": bool(config.get("webhook_enabled")),
    }


async def _apply_reseller_security_update(
    key_id: int,
    data: ResellerSecurityRequest,
    *,
    user_telegram_id: int | None = None,
) -> dict:
    from database.models import get_reseller_api_security, update_reseller_api_security
    from services.reseller_security import (
        derive_webhook_secret,
        normalize_ip_allowlist,
        validate_webhook_url,
    )

    current = await get_reseller_api_security(
        key_id,
        user_telegram_id=user_telegram_id,
    )
    if not current:
        raise HTTPException(status_code=404, detail="Reseller API key not found")

    ip_allowlist = (
        normalize_ip_allowlist(data.ip_allowlist)
        if data.ip_allowlist is not None
        else None
    )
    webhook_url = None
    if data.webhook_url is not None:
        webhook_url = await validate_webhook_url(data.webhook_url)
    final_webhook_url = (
        webhook_url if webhook_url is not None else str(current.get("webhook_url") or "")
    )
    final_webhook_enabled = (
        bool(data.webhook_enabled)
        if data.webhook_enabled is not None
        else bool(current.get("webhook_enabled"))
    )
    if final_webhook_enabled and not final_webhook_url:
        raise ValueError("A valid webhook URL is required before enabling webhooks")

    rotate_secret = bool(data.rotate_webhook_secret) or (
        final_webhook_enabled and not bool(current.get("webhook_enabled"))
    )
    updated = await update_reseller_api_security(
        key_id,
        user_telegram_id=user_telegram_id,
        ip_allowlist=ip_allowlist,
        webhook_url=webhook_url,
        webhook_enabled=data.webhook_enabled,
        rotate_webhook_secret=rotate_secret,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Reseller API key not found")
    result = _public_reseller_security_config(updated)
    if rotate_secret:
        result["webhook_signing_secret"] = derive_webhook_secret(
            str(updated.get("key_prefix") or ""),
            str(updated.get("webhook_secret_salt") or ""),
        )
        result["webhook_signing_secret_note"] = (
            "Store this secret now. It is only returned after creation or rotation."
        )
    return result


class FinanceAdjustRequest(BaseModel):
    amount: float = Field(..., allow_inf_nan=False)
    method: str = Field(..., min_length=1, max_length=40)


class TicketReplyRequest(BaseModel):
    reply_text: str = Field(..., min_length=1, max_length=4000)


class PaymentReviewActionRequest(BaseModel):
    action: str = Field(..., pattern="^(recheck|dismiss|reopen|accept)$")
    note: str = Field("", max_length=1000)
    confirmation: str = Field("", max_length=300)


class GameMatchImportRequest(BaseModel):
    external_match_id: str = Field(..., min_length=1, max_length=80)
    market_type: str = Field("qualified", pattern="^(qualified|regulation)$")
    lock_minutes: int = Field(10, ge=0, le=1440)
    min_stake: int = Field(25, ge=1, le=1000000)
    max_stake: int = Field(500, ge=1, le=1000000)
    fee_bps: int = Field(500, ge=0, le=2500)
    publish: bool = True


class GameMatchConfigurationRequest(BaseModel):
    market_type: str = Field("qualified", pattern="^(qualified|regulation)$")
    lock_minutes: int = Field(10, ge=0, le=1440)
    min_stake: int = Field(25, ge=1, le=1000000)
    max_stake: int = Field(500, ge=1, le=1000000)
    fee_bps: int = Field(500, ge=0, le=2500)


class GameMatchSettlementRequest(BaseModel):
    result_outcome: str = Field(..., pattern="^(home|draw|away)$")
    confirmation: str = Field(..., min_length=3, max_length=120)


class GameMatchActionRequest(BaseModel):
    confirmation: str = Field(..., min_length=3, max_length=120)


class WebhookAutoscaleConfigRequest(BaseModel):
    mode: str | None = Field(None, pattern="^(auto|manual|off)$")
    observe_only: bool | None = None
    min_workers: int | None = Field(None, ge=1, le=64)
    max_workers: int | None = Field(None, ge=1, le=64)
    target_workers: int | None = Field(None, ge=1, le=64)


@api.get("/health/live")
async def liveness_check():
    return {"status": "ok"}


@api.get("/health/ready")
async def deployment_readiness_check():
    """Signal that Telegram workers and the webhook are ready for traffic."""
    payload = {"status": "ok" if _service_ready else "not_ready"}
    if not _service_ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


@api.get("/health")
async def health_check():
    """Readiness check for Railway and the dashboard."""
    db_ready = False
    last_db_error = None
    from database.db import get_db

    # A pooled Turso stream can expire between requests. Closing the failed
    # wrapper discards it, so one retry normally gets a fresh connection.
    for attempt in range(2):
        db = None
        try:
            db = await asyncio.wait_for(get_db(), timeout=3)
            cursor = await asyncio.wait_for(db.execute("SELECT 1 AS ok"), timeout=3)
            db_ready = bool(await asyncio.wait_for(cursor.fetchone(), timeout=3))
            if db_ready:
                break
        except Exception as exc:
            last_db_error = exc
            if attempt == 0:
                logger.debug("Healthcheck database retry after: %s", exc)
        finally:
            if db is not None:
                try:
                    await db.close()
                except Exception:
                    pass

    if not db_ready and last_db_error is not None:
        logger.warning("Healthcheck database failure after retry: %s", last_db_error)

    bot_ready = bool(tg_app and getattr(tg_app, "running", False))
    queue_size = _current_webhook_backlog()
    ready = db_ready and (bot_ready or not HEALTHCHECK_REQUIRE_BOT)
    payload = {
        "status": "ok" if ready else "not_ready",
        "bot": "running" if bot_ready else "starting",
        "database": "ok" if db_ready else "unavailable",
        "webhook_queue": queue_size,
    }
    if payload["status"] != "ok":
        return JSONResponse(status_code=503, content=payload)
    return payload


@api.get("/api/performance", dependencies=[Depends(verify_api_key)])
async def api_performance_metrics():
    """Return rolling worker, queue, latency, and database diagnostics."""
    snapshot = _webhook_performance_snapshot()
    try:
        from database.jobs import get_performance_action_history

        snapshot["history_24h"] = await get_performance_action_history(24)
    except Exception as exc:
        logger.debug("Performance history is temporarily unavailable: %s", exc)
        snapshot["history_24h"] = {"hours": 24, "actions": [], "available": False}
    if webhook_worker_manager is not None:
        snapshot["autoscaling"] = webhook_worker_manager.status()
    else:
        snapshot["autoscaling"] = {
            "mode": "off",
            "observe_only": True,
            "enabled": False,
            "state": "CALM",
            "bottleneck": "insufficient_data",
            "current_workers": 0,
            "min_workers": WEBHOOK_WORKERS,
            "max_workers": WEBHOOK_WORKERS,
            "proposed_workers": WEBHOOK_WORKERS,
            "timeline": [],
        }
    try:
        from database.jobs import list_webhook_autoscale_decisions

        snapshot["autoscaling"]["decisions"] = await list_webhook_autoscale_decisions(30)
    except Exception as exc:
        logger.debug("Autoscaling history is temporarily unavailable: %s", exc)
        snapshot["autoscaling"]["decisions"] = []
    return snapshot


@api.post("/api/performance/autoscaling", dependencies=[Depends(verify_api_key)])
async def api_configure_webhook_autoscaling(data: WebhookAutoscaleConfigRequest):
    if webhook_worker_manager is None:
        raise HTTPException(status_code=503, detail="Webhook workers are not ready")
    current = webhook_worker_manager.status()
    minimum = data.min_workers if data.min_workers is not None else current["min_workers"]
    maximum = data.max_workers if data.max_workers is not None else current["max_workers"]
    if maximum < minimum:
        raise HTTPException(status_code=400, detail="max_workers must be greater than or equal to min_workers")
    mode = data.mode or current["mode"]
    observe_only = data.observe_only if data.observe_only is not None else current["observe_only"]
    target = data.target_workers
    try:
        result = await webhook_worker_manager.configure(
            mode=mode,
            min_workers=minimum,
            max_workers=maximum,
            target_workers=target,
            observe_only=observe_only,
        )
        from database.jobs import update_webhook_autoscale_settings

        await update_webhook_autoscale_settings(
            mode=result["mode"],
            observe_only=result["observe_only"],
            min_workers=result["min_workers"],
            max_workers=result["max_workers"],
            manual_workers=result["current_workers"],
        )
        from database.jobs import list_webhook_autoscale_decisions

        result["decisions"] = await list_webhook_autoscale_decisions(30)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _log_nowpayments_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.exception("NOWPayments background processing failed: %s", exc)


async def _process_nowpayments_payment(payment_id: str) -> None:
    if not tg_app or not getattr(tg_app, "bot", None):
        return
    from database.models import get_nowpayments_wallet_topup_by_payment
    if await get_nowpayments_wallet_topup_by_payment(payment_id):
        from handlers.wallet import process_nowpayments_wallet_topup_notification
        await process_nowpayments_wallet_topup_notification(tg_app.bot, payment_id)
        return
    from handlers.payment import process_nowpayments_payment_notification
    await process_nowpayments_payment_notification(tg_app.bot, payment_id)


@api.post("/webhooks/nowpayments", include_in_schema=False)
async def nowpayments_webhook(request: Request, x_nowpayments_sig: str = Header(None)):
    """Persist a signed IPN quickly, then finish delivery outside the HTTP response."""
    from services.nowpayments import is_nowpayments_configured, verify_ipn_signature
    if not is_nowpayments_configured():
        raise HTTPException(status_code=503, detail="NOWPayments is not configured")

    raw_body = await request.body()
    if len(raw_body) > 65536:
        raise HTTPException(status_code=413, detail="IPN payload too large")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid IPN payload")
    if not verify_ipn_signature(payload, x_nowpayments_sig):
        logger.warning("Rejected NOWPayments IPN with an invalid signature")
        raise HTTPException(status_code=401, detail="Invalid IPN signature")

    from database.models import save_nowpayments_update
    try:
        payment = await save_nowpayments_update(payload)
    except ValueError as exc:
        logger.error("Rejected signed NOWPayments IPN: %s", exc)
        return {"status": "rejected"}
    if not payment:
        logger.warning("Ignored signed NOWPayments IPN for unknown payment %s", payload.get("payment_id"))
        return {"status": "ignored"}

    payment_id = str(payment["payment_id"])
    if tg_app and getattr(tg_app, "bot", None):
        task = asyncio.create_task(_process_nowpayments_payment(payment_id))
        task.add_done_callback(_log_nowpayments_task_result)
    return {"status": "accepted"}


def _reseller_openapi_schema() -> dict:
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "VenteBot Reseller API",
            "version": "1.2.0",
            "description": (
                "Public API for connecting a reseller bot to VenteBot. "
                "Purchases debit the reseller account wallet.\n\n"
                "Authenticate with X-Reseller-Key, or X-API-Key for compatibility with common reseller integrations.\n\n"
                f"Rate limit: {RESELLER_API_RATE_LIMIT} requests per {RESELLER_API_RATE_WINDOW} seconds per API key. "
                "Successful authenticated responses include X-RateLimit-Limit, "
                "X-RateLimit-Remaining, and X-RateLimit-Reset headers."
            ),
        },
        "servers": [{"url": "/"}],
        "tags": [
            {"name": "Account", "description": "Reseller account and wallet balance"},
            {"name": "Products", "description": "Catalog and pricing"},
            {"name": "Orders", "description": "Order creation and tracking"},
            {"name": "Wallet", "description": "Reseller wallet history"},
            {"name": "Deposits", "description": "Just-in-time BEP20 wallet funding"},
            {"name": "Security", "description": "IP restrictions and signed webhooks"},
        ],
        "components": {
            "securitySchemes": {
                "ResellerKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Reseller-Key",
                    "description": "API key generated from the Telegram bot or created by the admin in the Resellers tab.",
                },
                "ResellerApiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Compatibility header accepted on reseller endpoints. Admin dashboard keys are separate.",
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "code": {"type": "string", "example": "INVALID_API_KEY"},
                        "message": {"type": "string", "example": "Invalid reseller API key"},
                    },
                },
                "ValidationError": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "code": {"type": "string", "example": "VALIDATION_ERROR"},
                        "message": {"type": "string", "example": "Invalid request format."},
                        "details": {
                            "type": "array",
                            "items": {"type": "object"},
                            "example": [
                                {
                                    "loc": ["body", "product_id"],
                                    "msg": "field required",
                                    "type": "value_error.missing",
                                }
                            ],
                        }
                    },
                },
                "MeResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "user_telegram_id": {"type": "integer", "example": 123456789},
                        "username": {"type": "string", "nullable": True, "example": "partner_bot"},
                        "first_name": {"type": "string", "nullable": True, "example": "Partner"},
                        "wallet_balance": {"type": "number", "format": "float", "example": 42.5},
                        "key_name": {"type": "string", "example": "Partner bot"},
                        "key_prefix": {"type": "string", "example": "abc123"},
                    },
                },
                "PriceTier": {
                    "type": "object",
                    "properties": {
                        "min_qty": {"type": "integer", "example": 10},
                        "max_qty": {"type": "integer", "nullable": True, "example": 99},
                        "price_usd": {"type": "number", "format": "float", "example": 1.75},
                    },
                },
                "Product": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 12},
                        "name": {"type": "string", "example": "Grok 1 month"},
                        "description": {"type": "string", "example": "Manual activation"},
                        "emoji": {"type": "string", "nullable": True, "example": "bolt"},
                        "image_url": {"type": "string", "nullable": True, "example": "https://example.com/product.png"},
                        "price_usd": {"type": "number", "format": "float", "example": 5.0},
                        "standard_price_usd": {"type": "number", "format": "float", "nullable": True, "example": 6.0},
                        "pricing_type": {"type": "string", "enum": ["standard", "reseller_special"], "example": "reseller_special"},
                        "special_price_expires_at": {"type": "string", "nullable": True, "example": "2026-08-01 12:00:00"},
                        "warranty_days": {"type": "integer", "example": 30},
                        "delivery_type": {"type": "string", "enum": ["stock", "activation", "supplier_api", "api_test"], "example": "activation"},
                        "stock": {"type": "integer", "nullable": True, "example": None},
                        "price_tiers": {"type": "array", "items": {"$ref": "#/components/schemas/PriceTier"}},
                        "api_test": {"type": "boolean", "default": False},
                    },
                },
                "QuoteRequest": {
                    "type": "object",
                    "required": ["product_id"],
                    "properties": {
                        "product_id": {"type": "integer", "minimum": 1, "example": 12},
                        "quantity": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 1, "example": 1},
                    },
                },
                "QuoteResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "quote": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "integer", "example": 12},
                                "quantity": {"type": "integer", "example": 1},
                                "unit_price": {"type": "number", "format": "float", "example": 5.0},
                                "standard_unit_price": {"type": "number", "format": "float", "example": 6.0},
                                "pricing_type": {"type": "string", "enum": ["standard", "reseller_special"], "example": "reseller_special"},
                                "total": {"type": "number", "format": "float", "example": 5.0},
                                "delivery_type": {"type": "string", "example": "activation"},
                                "stock": {
                                    "type": "integer",
                                    "nullable": True,
                                    "description": "Available units for stock delivery; null for activation products.",
                                    "example": 12,
                                },
                            },
                        },
                        "wallet_balance": {"type": "number", "format": "float", "example": 42.5},
                    },
                },
                "CreateOrderRequest": {
                    "type": "object",
                    "required": ["product_id"],
                    "properties": {
                        "product_id": {"type": "integer", "minimum": 1, "example": 12},
                        "quantity": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 1, "example": 1},
                        "activation_identifier": {
                            "type": "string",
                            "maxLength": 500,
                            "description": "Telegram ID, Grok ID, email, or any service identifier to activate.",
                            "example": "@client",
                        },
                        "customer_reference": {
                            "type": "string",
                            "maxLength": 120,
                            "description": "Internal customer reference from the reseller bot.",
                            "example": "telegram_user_555",
                        },
                        "idempotency_key": {
                            "type": "string",
                            "maxLength": 120,
                            "description": "Unique value per purchase attempt. Retrying the exact same request returns the original order; reusing it with a different payload returns HTTP 409.",
                            "example": "order-555-20260706-001",
                        },
                    },
                },
                "ActivationIdentifierRequest": {
                    "type": "object",
                    "required": ["activation_identifier"],
                    "properties": {
                        "activation_identifier": {"type": "string", "minLength": 2, "maxLength": 500, "example": "@client"},
                    },
                },
                "OrderItem": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 99},
                        "account_data": {"type": "string", "example": "login:password"},
                    },
                },
                "Order": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 124},
                        "status": {
                            "type": "string",
                            "enum": ["COMPLETED", "PAID_PENDING_DELIVERY", "AWAITING_ACTIVATION_INFO", "AWAITING_ACTIVATION", "CANCELLED"],
                            "example": "AWAITING_ACTIVATION",
                        },
                        "product_id": {"type": "integer", "example": 12},
                        "product_name": {"type": "string", "example": "Grok 1 month"},
                        "quantity": {"type": "integer", "example": 1},
                        "amount_usd": {"type": "number", "format": "float", "example": 5.0},
                        "delivery_type": {"type": "string", "example": "activation"},
                        "customer_reference": {"type": "string", "example": "telegram_user_555"},
                        "idempotency_key": {"type": "string", "example": "order-555-20260706-001"},
                        "activation_identifier": {"type": "string", "nullable": True, "example": "@client"},
                        "created_at": {"type": "string", "example": "2026-07-06 12:30:00"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/OrderItem"}},
                    },
                },
                "WalletTransaction": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 456},
                        "user_telegram_id": {"type": "integer", "example": 123456789},
                        "type": {"type": "string", "example": "purchase"},
                        "amount": {"type": "number", "format": "float", "example": 5.0},
                        "balance_after": {"type": "number", "format": "float", "example": 37.5},
                        "description": {"type": "string", "example": "Reseller API order #123"},
                        "created_at": {"type": "string", "example": "2026-07-06 12:30:00"},
                        "tx_hash": {"type": "string", "nullable": True, "example": None},
                    },
                },
            },
        },
        "security": [{"ResellerKey": []}, {"ResellerApiKey": []}],
        "paths": {
            "/api/reseller/me": {
                "get": {
                    "tags": ["Account"],
                    "summary": "Verify the key and read the wallet balance",
                    "responses": {
                        "200": {"description": "Reseller account", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MeResponse"}}}},
                        "401": {"description": "Invalid key", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/products": {
                "get": {
                    "tags": ["Products"],
                    "summary": "List active products",
                    "parameters": [
                        {
                            "name": "lang",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["en", "fr", "ar", "zh", "vi", "ru"], "default": "en"},
                            "description": "Product description language.",
                        },
                        {
                            "name": "If-None-Match",
                            "in": "header",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "ETag from the previous catalog response. Returns 304 when unchanged.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Catalog",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean", "example": True},
                                            "products": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}}
                                        },
                                    }
                                }
                            },
                        },
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/quote": {
                "post": {
                    "tags": ["Products"],
                    "summary": "Calculate the price before buying",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/QuoteRequest"}}},
                    },
                    "responses": {
                        "200": {"description": "Calculated price", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/QuoteResponse"}}}},
                        "400": {"description": "Invalid product or quantity", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ValidationError"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/orders": {
                "post": {
                    "tags": ["Orders"],
                    "summary": "Create an order",
                    "description": "Debits the reseller wallet. idempotency_key remains safe after client timeouts and retries. The authenticated catalog includes a low-cost synthetic API test product that is never shown to regular Telegram customers.",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateOrderRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Order created or idempotent response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean", "example": True},
                                            "status": {"type": "string", "example": "ok"},
                                            "idempotent": {"type": "boolean", "example": False},
                                            "balance_after": {
                                                "type": "number", "format": "float", "nullable": True, "example": 37.5,
                                                "description": "Balance after a new purchase; null when replaying an existing idempotent order.",
                                            },
                                            "unit_price": {
                                                "type": "number", "format": "float", "nullable": True, "example": 5.0,
                                                "description": "Unit price for a new purchase; null when replaying an existing idempotent order.",
                                            },
                                            "standard_unit_price": {
                                                "type": "number", "format": "float", "nullable": True, "example": 6.0,
                                                "description": "Standard price before the reseller-specific override.",
                                            },
                                            "pricing_type": {
                                                "type": "string", "nullable": True, "enum": ["standard", "reseller_special"],
                                            },
                                            "total": {
                                                "type": "number", "format": "float", "nullable": True, "example": 5.0,
                                                "description": "Total for a new purchase; null when replaying an existing idempotent order. order.amount_usd remains available.",
                                            },
                                            "order": {"$ref": "#/components/schemas/Order"},
                                        },
                                    }
                                }
                            },
                        },
                        "400": {"description": "Invalid order", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "402": {"description": "Insufficient wallet balance", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ValidationError"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/orders/{order_id}": {
                "get": {
                    "tags": ["Orders"],
                    "summary": "Read an order",
                    "parameters": [{"name": "order_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Order", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean", "example": True}, "order": {"$ref": "#/components/schemas/Order"}}}}}},
                        "404": {"description": "Order not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Invalid order_id", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ValidationError"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/orders/{order_id}/activation-identifier": {
                "post": {
                    "tags": ["Orders"],
                    "summary": "Submit the activation identifier later",
                    "parameters": [{"name": "order_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ActivationIdentifierRequest"}}},
                    },
                    "responses": {
                        "200": {"description": "Identifier saved", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean", "example": True}, "status": {"type": "string", "example": "ok"}, "order": {"$ref": "#/components/schemas/Order"}}}}}},
                        "400": {"description": "The order is not waiting for an identifier", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "409": {"description": "The order state changed before the identifier was saved", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "404": {"description": "Order not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ValidationError"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/api/reseller/wallet/transactions": {
                "get": {
                    "tags": ["Wallet"],
                    "summary": "Reseller wallet history",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0, "minimum": 0}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Transactions",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean", "example": True},
                                            "transactions": {"type": "array", "items": {"$ref": "#/components/schemas/WalletTransaction"}}
                                        },
                                    }
                                }
                            },
                        },
                        "422": {"description": "Invalid pagination value", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ValidationError"}}}},
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
        },
    }
    schemas = schema["components"]["schemas"]
    schemas.update({
        "DepositRequest": {
            "type": "object",
            "required": ["amount_usd", "idempotency_key"],
            "properties": {
                "amount_usd": {"type": "number", "minimum": 0.01, "maximum": 10000, "example": 5.0},
                "network": {"type": "string", "enum": ["BEP20"], "default": "BEP20"},
                "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 120, "example": "deposit-customer-555-001"},
                "reference": {"type": "string", "maxLength": 120, "example": "checkout-555"},
            },
        },
        "Deposit": {
            "type": "object",
            "properties": {
                "deposit_id": {"type": "string", "example": "dep_a1b2c3d4e5f6"},
                "status": {"type": "string", "enum": ["CREATING", "CREATION_UNKNOWN", "WAITING", "CONFIRMING", "UNDERPAID", "CREDITED", "EXPIRED", "FAILED", "REFUNDED", "REVIEW_REQUIRED"]},
                "provider_status": {"type": "string", "example": "waiting"},
                "wallet_credit_amount": {"type": "number", "example": 5.0},
                "pay_amount": {"type": "number", "nullable": True, "example": 5.012345},
                "pay_currency": {"type": "string", "example": "USDTBSC"},
                "network": {"type": "string", "example": "BEP20"},
                "address": {"type": "string", "nullable": True, "example": "0x..."},
                "internal_transfer_uid": {"type": "string", "nullable": True},
                "memo": {"type": "string", "nullable": True},
                "reference": {"type": "string"},
                "idempotency_key": {"type": "string"},
                "actually_paid": {"type": "number", "example": 0},
                "fees": {"type": "object"},
                "expires_at": {"type": "string", "nullable": True},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string", "nullable": True},
                "credited_at": {"type": "string", "nullable": True},
                "processing_error": {"type": "string", "nullable": True},
            },
        },
        "SecurityRequest": {
            "type": "object",
            "properties": {
                "ip_allowlist": {"type": "array", "maxItems": 20, "items": {"type": "string"}, "example": ["203.0.113.10/32"]},
                "webhook_url": {"type": "string", "example": "https://store.example.com/webhooks/ventebot"},
                "webhook_enabled": {"type": "boolean"},
                "rotate_webhook_secret": {"type": "boolean", "default": False},
            },
        },
        "Security": {
            "type": "object",
            "properties": {
                "key_id": {"type": "integer"},
                "key_prefix": {"type": "string"},
                "ip_allowlist": {"type": "array", "items": {"type": "string"}},
                "webhook_url": {"type": "string"},
                "webhook_enabled": {"type": "boolean"},
                "webhook_signing_secret": {"type": "string", "description": "Only returned after initial enablement or explicit rotation."},
            },
        },
    })
    schema["paths"].update({
        "/api/reseller/wallet/deposit-methods": {
            "get": {
                "tags": ["Deposits"],
                "summary": "List supported deposit networks and current minimums",
                "responses": {"200": {"description": "Deposit methods"}},
            }
        },
        "/api/reseller/wallet/deposits": {
            "post": {
                "tags": ["Deposits"],
                "summary": "Create an idempotent USDT BEP20 wallet deposit",
                "description": "Send exactly deposit.pay_amount to deposit.address before expires_at. Poll the status endpoint or configure a signed webhook.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DepositRequest"}}}},
                "responses": {
                    "200": {"description": "Existing idempotent deposit", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean"}, "idempotent": {"type": "boolean"}, "deposit": {"$ref": "#/components/schemas/Deposit"}}}}}},
                    "201": {"description": "Deposit created", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean"}, "idempotent": {"type": "boolean"}, "deposit": {"$ref": "#/components/schemas/Deposit"}}}}}},
                    "409": {"description": "Idempotency key reused with a different payload"},
                },
            }
        },
        "/api/reseller/wallet/deposits/{deposit_id}": {
            "get": {
                "tags": ["Deposits"],
                "summary": "Read and optionally refresh a deposit",
                "parameters": [
                    {"name": "deposit_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "refresh", "in": "query", "schema": {"type": "boolean", "default": True}},
                ],
                "responses": {"200": {"description": "Deposit status"}, "404": {"description": "Deposit not found"}},
            }
        },
        "/api/reseller/security": {
            "get": {"tags": ["Security"], "summary": "Read IP and webhook settings", "responses": {"200": {"description": "Security settings"}}},
            "put": {
                "tags": ["Security"],
                "summary": "Configure IP allowlisting and signed deposit webhooks",
                "description": "Webhook requests contain X-Vente-Timestamp and X-Vente-Signature. Verify HMAC-SHA256 over timestamp + '.' + the raw request body. Events are retried durably.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SecurityRequest"}}}},
                "responses": {"200": {"description": "Updated settings"}},
            },
        },
    })
    error_response = {
        "description": "Unexpected server error.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    unauthorized_response = {
        "description": "Missing, invalid, or revoked reseller API key.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    forbidden_response = {
        "description": "The calling IP is not in the API key allowlist.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    rate_limit_response = {
        "description": "Rate limit exceeded. Use Retry-After before retrying.",
        "headers": {
            "Retry-After": {
                "description": "Required retry delay in seconds.",
                "schema": {"type": "integer"},
            }
        },
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    rate_limit_headers = {
        "X-RateLimit-Limit": {
            "description": "Maximum requests allowed in the current window.",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Remaining": {
            "description": "Requests remaining in the current window.",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Reset": {
            "description": "Unix timestamp when the current window resets.",
            "schema": {"type": "integer"},
        },
    }
    unavailable_response = {
        "description": "Authentication database temporarily unavailable. Retry after a short delay.",
        "headers": {
            "Retry-After": {
                "description": "Recommended retry delay in seconds.",
                "schema": {"type": "integer", "example": 3},
            }
        },
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "responses" in operation:
                operation["responses"].setdefault("401", unauthorized_response)
                operation["responses"].setdefault("403", forbidden_response)
                operation["responses"].setdefault("429", rate_limit_response)
                operation["responses"].setdefault("500", error_response)
                operation["responses"].setdefault("503", unavailable_response)
                operation["responses"]["429"].setdefault("headers", rate_limit_response["headers"])
                if "200" in operation["responses"]:
                    operation["responses"]["200"].setdefault("headers", rate_limit_headers)
    catalog_responses = schema["paths"]["/api/reseller/products"]["get"]["responses"]
    catalog_responses["200"]["headers"].update({
        "ETag": {
            "description": "Stable catalog entity tag for conditional requests.",
            "schema": {"type": "string"},
        },
        "X-Catalog-Version": {
            "description": "In-process catalog generation used for cache invalidation.",
            "schema": {"type": "integer"},
        },
        "X-Catalog-Stale": {
            "description": "True when a cached snapshot is served during a temporary dependency failure.",
            "schema": {"type": "boolean"},
        },
    })
    catalog_responses["304"] = {
        "description": "Catalog unchanged. Reuse the previously cached response body.",
        "headers": catalog_responses["200"]["headers"],
    }
    return schema


@api.get("/api/reseller/openapi.json", include_in_schema=False)
async def api_reseller_openapi_json():
    return _reseller_openapi_schema()


@api.get("/api/swagger", include_in_schema=False)
@api.get("/api/swagger/", include_in_schema=False)
async def api_reseller_swagger():
    return get_swagger_ui_html(
        openapi_url="/api/reseller/openapi.json",
        title="VenteBot Reseller API",
        swagger_ui_parameters={"persistAuthorization": True},
    )


@api.get("/api/resellers", dependencies=[Depends(verify_api_key)])
async def api_admin_list_resellers():
    from database.models import list_reseller_api_keys
    try:
        return {"resellers": await list_reseller_api_keys()}
    except Exception as exc:
        logger.error("API error list resellers: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/resellers/keys", dependencies=[Depends(verify_api_key)])
async def api_admin_create_reseller_key(data: dict):
    from database.models import create_reseller_api_key, get_user
    try:
        telegram_id = int(data.get("user_telegram_id"))
        user = await get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        key = await create_reseller_api_key(telegram_id, data.get("name", ""))
        return {"status": "created", "key": key}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error create reseller key: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/resellers/keys/{key_id}", dependencies=[Depends(verify_api_key)])
async def api_admin_revoke_reseller_key(key_id: int):
    from database.models import revoke_reseller_api_key
    try:
        if not await revoke_reseller_api_key(key_id):
            raise HTTPException(status_code=404, detail="Key not found")
        return {"status": "revoked"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error revoke reseller key: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.patch(
    "/api/resellers/keys/{key_id}/security",
    dependencies=[Depends(verify_api_key)],
)
async def api_admin_update_reseller_security(
    key_id: int,
    data: ResellerSecurityRequest,
):
    try:
        return {"status": "updated", "security": await _apply_reseller_security_update(key_id, data)}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API error update reseller security: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get(
    "/api/resellers/{user_telegram_id}/special-prices",
    dependencies=[Depends(verify_api_key)],
)
async def api_admin_list_reseller_special_prices(user_telegram_id: int):
    from database.models import get_user, list_reseller_special_prices

    try:
        if not await get_user(user_telegram_id):
            raise HTTPException(status_code=404, detail="Reseller user not found")
        return {
            "prices": await list_reseller_special_prices(user_telegram_id)
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error list reseller special prices: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put(
    "/api/resellers/{user_telegram_id}/special-prices",
    dependencies=[Depends(verify_api_key)],
)
async def api_admin_upsert_reseller_special_price(
    user_telegram_id: int,
    data: ResellerSpecialPriceRequest,
):
    from database.models import upsert_reseller_special_price

    try:
        price = await upsert_reseller_special_price(
            user_telegram_id,
            data.product_id,
            data.price_usd,
            is_active=data.is_active,
            enforce_cost_floor=data.enforce_cost_floor,
            apply_to_telegram=data.apply_to_telegram,
            expires_at=data.expires_at,
        )
        return {"status": "updated", "price": price}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API error save reseller special price: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete(
    "/api/resellers/{user_telegram_id}/special-prices/{product_id}",
    dependencies=[Depends(verify_api_key)],
)
async def api_admin_delete_reseller_special_price(
    user_telegram_id: int,
    product_id: int,
):
    from database.models import delete_reseller_special_price

    try:
        deleted = await delete_reseller_special_price(user_telegram_id, product_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Special price not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error delete reseller special price: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/supplier-bots", dependencies=[Depends(verify_api_key)])
async def api_list_supplier_bots():
    from collections import Counter

    from database.suppliers import get_supplier_dashboard_summaries
    from services.supplier_registry import (
        is_supplier_configured,
        list_supplier_providers,
    )

    registered = list_supplier_providers()
    summaries = await get_supplier_dashboard_summaries(
        [str(provider["code"]) for provider in registered]
    )
    detected_counts = Counter(
        str(data.get("detected_name") or "").strip().casefold()
        for data in summaries.values()
        if str(data.get("detected_name") or "").strip()
    )
    providers = []
    for provider in registered:
        data = summaries.get(provider["code"], {})
        custom_name = str(data.get("display_name") or "").strip()
        detected_name = str(data.get("detected_name") or "").strip()
        unique_detected_name = (
            detected_name
            if detected_name and detected_counts[detected_name.casefold()] == 1
            else ""
        )
        providers.append(
            {
                **provider,
                "name": custom_name or unique_detected_name or provider["name"],
                "display_name": custom_name,
                "detected_name": detected_name,
                "configured": is_supplier_configured(provider["code"]),
                "enabled": bool(data["enabled"]),
                "products_count": int(data.get("products_count") or 0),
                "selected_count": int(data.get("selected_count") or 0),
                "last_sync": data.get("last_sync"),
            }
        )
    return {"providers": providers}


@api.get("/api/supplier-bots/{supplier_code}", dependencies=[Depends(verify_api_key)])
async def api_get_supplier_bot(supplier_code: str):
    from database.suppliers import get_supplier_dashboard, supplier_price_is_safe
    from services.supplier_api import SupplierAPIError, calculate_affordable_stock
    from services.supplier_registry import (
        get_supplier_balance,
        get_supplier_provider,
        is_supplier_configured,
    )

    try:
        provider = get_supplier_provider(supplier_code)
        data = await get_supplier_dashboard(provider["code"])
        configured = is_supplier_configured(provider["code"])
        data.update(
            configured=configured,
            supplier=data.get("display_name") or provider["name"],
            base_url=provider["base_url"],
            source_currency=provider["source_currency"],
            credential_env=provider["credential_env"],
            wallet=None,
            wallet_error=None,
        )
        if configured:
            try:
                data["wallet"] = await get_supplier_balance(
                    provider["code"],
                    units_per_usd=float(data["units_per_usd"]),
                )
                balance = float(data["wallet"].get("balance") or 0)
                for product in data.get("products", []):
                    product["affordable_stock"] = (
                        calculate_affordable_stock(
                            product.get("remote_stock"),
                            product.get("base_price"),
                            balance,
                        )
                        if supplier_price_is_safe(
                            product.get("base_price"),
                            str(product.get("effective_margin_type") or "inherit"),
                            product.get("effective_margin_value") or 0,
                        )
                        else 0
                    )
            except SupplierAPIError as exc:
                data["wallet_error"] = str(exc)
        for product in data.get("products", []):
            product.setdefault("affordable_stock", 0)
        return data
    except ValueError as exc:
        if str(exc) == "SUPPLIER_NOT_FOUND":
            raise HTTPException(status_code=404, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier dashboard error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get(
    "/api/supplier-bots/{supplier_code}/stats",
    dependencies=[Depends(verify_api_key)],
)
async def api_get_supplier_stats(supplier_code: str, days: int = 30):
    from database.suppliers import get_supplier_stats
    from services.supplier_registry import get_supplier_provider

    try:
        provider = get_supplier_provider(supplier_code)
        return await get_supplier_stats(provider["code"], days=days)
    except ValueError as exc:
        code = 404 if str(exc) == "SUPPLIER_NOT_FOUND" else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier stats error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post(
    "/api/supplier-bots/{supplier_code}/sync",
    dependencies=[Depends(verify_api_key)],
)
async def api_sync_supplier_bot(supplier_code: str):
    from database.suppliers import get_supplier_dashboard
    from services.supplier_api import SupplierAPIError
    from services.supplier_registry import (
        get_supplier_provider,
    )
    from services.supplier_sync import sync_supplier_catalog

    try:
        provider = get_supplier_provider(supplier_code)
        result = await sync_supplier_catalog(
            provider["code"],
            min_interval_seconds=0,
            refresh_balance=True,
        )
        return {
            **result,
            "dashboard": await get_supplier_dashboard(provider["code"]),
        }
    except ValueError as exc:
        code = 404 if str(exc) == "SUPPLIER_NOT_FOUND" else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except SupplierAPIError as exc:
        logger.warning(
            "%s catalog sync failed (HTTP %s): %s",
            supplier_code,
            exc.status_code or "n/a",
            exc,
        )
        raise HTTPException(status_code=502, detail=f"Supplier API: {exc}")
    except Exception as exc:
        logger.error("API supplier sync error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put(
    "/api/supplier-bots/{supplier_code}/settings",
    dependencies=[Depends(verify_api_key)],
)
async def api_update_supplier_settings(supplier_code: str, data: dict):
    from database.suppliers import get_supplier_dashboard, update_supplier_settings
    from services.supplier_registry import get_supplier_provider

    try:
        provider = get_supplier_provider(supplier_code)
        await update_supplier_settings(
            enabled=bool(data.get("enabled", True)),
            margin_type=str(data.get("margin_type") or "fixed").lower(),
            margin_value=float(data.get("margin_value") or 0),
            supplier_code=provider["code"],
            units_per_usd=(
                float(data["units_per_usd"])
                if data.get("units_per_usd") is not None
                else None
            ),
            display_name=(
                str(data.get("display_name") or "")
                if "display_name" in data
                else None
            ),
        )
        return {
            "status": "updated",
            "dashboard": await get_supplier_dashboard(provider["code"]),
        }
    except (TypeError, ValueError) as exc:
        code = 404 if str(exc) == "SUPPLIER_NOT_FOUND" else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier settings error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put(
    "/api/supplier-bots/{supplier_code}/products/{mapping_id}",
    dependencies=[Depends(verify_api_key)],
)
async def api_update_supplier_product(
    supplier_code: str, mapping_id: int, data: dict
):
    from database.suppliers import (
        get_supplier_dashboard,
        get_supplier_product_by_mapping_id,
        update_supplier_product,
    )
    from services.supplier_api import SupplierAPIError
    from services.supplier_registry import get_supplier_provider
    from services.supplier_sync import sync_supplier_catalog

    try:
        provider = get_supplier_provider(supplier_code)
        enabled = bool(data.get("enabled", False))
        current_mapping = await get_supplier_product_by_mapping_id(
            mapping_id,
            provider["code"],
        )
        if not current_mapping:
            raise ValueError("SUPPLIER_PRODUCT_NOT_FOUND")
        if enabled and not bool(current_mapping.get("enabled")):
            sync_result = await sync_supplier_catalog(
                provider["code"],
                min_interval_seconds=0,
                refresh_disabled=True,
            )
            if sync_result.get("status") == "not_configured":
                raise HTTPException(
                    status_code=409,
                    detail="Supplier API is not configured",
                )
        await update_supplier_product(
            mapping_id,
            enabled=enabled,
            margin_type=str(data.get("margin_type") or "inherit").lower(),
            margin_value=data.get("margin_value"),
            supplier_code=provider["code"],
        )
        return {
            "status": "updated",
            "dashboard": await get_supplier_dashboard(provider["code"]),
        }
    except HTTPException:
        raise
    except SupplierAPIError as exc:
        raise HTTPException(status_code=502, detail=f"Supplier API: {exc}")
    except ValueError as exc:
        code = 404 if str(exc) in {
            "SUPPLIER_NOT_FOUND",
            "SUPPLIER_PRODUCT_NOT_FOUND",
        } else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier product error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put(
    "/api/supplier-bots/{supplier_code}/products/{mapping_id}/descriptions",
    dependencies=[Depends(verify_api_key)],
)
async def api_update_supplier_product_descriptions(
    supplier_code: str, mapping_id: int, data: dict
):
    from database.suppliers import (
        get_supplier_dashboard,
        update_supplier_product_descriptions,
    )
    from services.supplier_registry import get_supplier_provider

    try:
        provider = get_supplier_provider(supplier_code)
        descriptions = data.get("descriptions")
        if not isinstance(descriptions, dict):
            raise ValueError("INVALID_DESCRIPTIONS")
        await update_supplier_product_descriptions(
            mapping_id,
            descriptions,
            provider["code"],
            custom_name=data.get("custom_name"),
            custom_emoji=data.get("custom_emoji"),
            custom_emoji_id=data.get("custom_emoji_id"),
            custom_image_url=data.get("custom_image_url"),
        )
        return {
            "status": "updated",
            "dashboard": await get_supplier_dashboard(provider["code"]),
        }
    except ValueError as exc:
        code = 404 if str(exc) in {
            "SUPPLIER_NOT_FOUND",
            "SUPPLIER_PRODUCT_NOT_FOUND",
        } else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier descriptions error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/supplier-router/routes", dependencies=[Depends(verify_api_key)])
async def api_list_supplier_routes(status: str = ""):
    from database.suppliers import list_supplier_routes

    try:
        normalized = str(status or "").strip().lower()
        if normalized and normalized not in {"proposed", "confirmed", "rejected"}:
            raise HTTPException(status_code=400, detail="Invalid route status")
        return {"routes": await list_supplier_routes(normalized)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API supplier router list error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/supplier-router/propose", dependencies=[Depends(verify_api_key)])
async def api_propose_supplier_routes(data: dict | None = None):
    from services.supplier_router import propose_supplier_routes

    payload = data or {}
    try:
        return await propose_supplier_routes(
            use_ai=bool(payload.get("use_ai", True)),
            max_pairs=max(1, min(int(payload.get("max_pairs") or 80), 200)),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier router proposal error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put("/api/supplier-router/routes/{route_id}", dependencies=[Depends(verify_api_key)])
async def api_review_supplier_route(route_id: int, data: dict):
    from database.suppliers import review_supplier_route

    try:
        route = await review_supplier_route(
            route_id, str(data.get("status") or "").strip().lower()
        )
        return {"status": "updated", "route": route}
    except ValueError as exc:
        code = 404 if str(exc) == "SUPPLIER_ROUTE_NOT_FOUND" else 400
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier router review error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/ai-supplier/status", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_status():
    from services.supplier_ai import get_supplier_ai_status

    try:
        return await get_supplier_ai_status()
    except Exception as exc:
        logger.error("API supplier AI status error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/ai-supplier/sync", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_sync(data: dict | None = None):
    from services.supplier_ai import enqueue_supplier_ai_sync

    try:
        job, created = await enqueue_supplier_ai_sync(
            use_ai=bool((data or {}).get("use_ai", True))
        )
        return {"created": created, "job": job}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier AI sync error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/ai-supplier/analyze", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_analyze(data: dict | None = None):
    from services.supplier_ai import enqueue_supplier_ai_analysis

    try:
        job, created = await enqueue_supplier_ai_analysis(
            use_ai=bool((data or {}).get("use_ai", True))
        )
        return {"created": created, "job": job}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier AI analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/ai-supplier/sync/{job_id}", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_sync_job(job_id: str):
    from database.jobs import get_background_job
    from services.supplier_ai import SUPPLIER_AI_JOB_TYPE

    try:
        job = await get_background_job(job_id)
        if not job or job.get("job_type") != SUPPLIER_AI_JOB_TYPE:
            raise HTTPException(status_code=404, detail="Sync job not found")
        return {
            "job_id": job.get("id"),
            "status": job.get("status"),
            "done": int(job.get("progress_done") or 0),
            "failed": int(job.get("progress_failed") or 0),
            "total": int(job.get("progress_total") or 0),
            "error": job.get("error"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "completed_at": job.get("completed_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API supplier AI sync job error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/ai-supplier/job/{job_id}", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_job(job_id: str):
    from database.jobs import get_background_job
    from services.supplier_ai import SUPPLIER_AI_ANALYZE_JOB_TYPE, SUPPLIER_AI_JOB_TYPE

    try:
        job = await get_background_job(job_id)
        if not job or job.get("job_type") not in {SUPPLIER_AI_JOB_TYPE, SUPPLIER_AI_ANALYZE_JOB_TYPE}:
            raise HTTPException(status_code=404, detail="Supplier AI job not found")
        return {
            "job_id": job.get("id"),
            "kind": "analysis" if job.get("job_type") == SUPPLIER_AI_ANALYZE_JOB_TYPE else "sync",
            "status": job.get("status"),
            "done": int(job.get("progress_done") or 0),
            "failed": int(job.get("progress_failed") or 0),
            "total": int(job.get("progress_total") or 0),
            "error": job.get("error"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "completed_at": job.get("completed_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API supplier AI job error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/ai-supplier/groups", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_groups():
    from services.supplier_ai import list_supplier_product_groups

    try:
        return await list_supplier_product_groups()
    except Exception as exc:
        logger.error("API supplier AI groups error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/ai-supplier/search", dependencies=[Depends(verify_api_key)])
async def api_ai_supplier_search(data: dict):
    from services.supplier_ai import search_supplier_catalog

    try:
        return await search_supplier_catalog(data or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API supplier AI search error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def _raise_game_api_error(exc) -> None:
    from database.games import GameError
    from services.sports_api import SportsAPIError

    if isinstance(exc, GameError):
        status_code = {
            "not_found": 404,
            "bets_exist": 409,
            "already_settled": 409,
            "invalid_status": 409,
            "match_started": 409,
            "invalid_provider_status": 409,
        }.get(exc.code, 400)
        raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})
    if isinstance(exc, SportsAPIError):
        status_code = 429 if exc.status_code == 429 else 503 if exc.retryable else 502
        raise HTTPException(
            status_code=status_code,
            detail={"code": "SPORTS_PROVIDER_ERROR", "message": str(exc)},
            headers={"Retry-After": "10"} if status_code in {429, 503} else None,
        )
    logger.error("Unhandled game API error: %s", exc, exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/game/provider", dependencies=[Depends(verify_api_key)])
async def api_game_provider_status():
    from services.sports_api import sports_provider_status

    try:
        return sports_provider_status()
    except Exception as exc:
        logger.error("Game provider status failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/game/catalog", dependencies=[Depends(verify_api_key)])
async def api_game_catalog(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    competition: str = Query("", max_length=20),
    provider_status: str = Query("", max_length=30),
    search: str = Query("", max_length=120),
    force: bool = Query(False),
):
    from database.games import selected_external_match_ids
    from services.sports_api import (
        is_sports_api_configured,
        list_football_matches,
        sports_provider_status,
    )

    try:
        start = date.fromisoformat(date_from) if date_from else date.today()
        end = date.fromisoformat(date_to) if date_to else start + timedelta(days=7)
    except ValueError:
        raise HTTPException(status_code=422, detail="date_from and date_to must use YYYY-MM-DD")
    if end < start or (end - start).days > 31:
        raise HTTPException(status_code=422, detail="The catalog range must be between 0 and 31 days")
    if not is_sports_api_configured():
        return {
            **sports_provider_status(),
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "competitions": [],
            "matches": [],
        }

    try:
        matches = await list_football_matches(
            start,
            end,
            competition=competition,
            force=force,
        )
        selected = await selected_external_match_ids()
        status_filter = provider_status.strip().upper()
        search_filter = search.strip().casefold()
        filtered = []
        for match in matches:
            if status_filter and match.get("provider_status") != status_filter:
                continue
            haystack = " ".join((
                str(match.get("home_name") or ""),
                str(match.get("away_name") or ""),
                str(match.get("competition_name") or ""),
                str(match.get("stage") or ""),
            )).casefold()
            if search_filter and search_filter not in haystack:
                continue
            item = dict(match)
            item.pop("raw_payload", None)
            item["selected"] = str(item["external_match_id"]) in selected
            filtered.append(item)
        competitions = sorted(
            {
                (str(item.get("competition_code") or ""), str(item.get("competition_name") or "Football"))
                for item in matches
            },
            key=lambda item: item[1].casefold(),
        )
        return {
            **sports_provider_status(),
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "competitions": [{"code": code, "name": name} for code, name in competitions],
            "matches": filtered,
        }
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game catalog failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/game/matches", dependencies=[Depends(verify_api_key)])
async def api_game_matches(include_cancelled: bool = Query(False)):
    from database.games import list_game_matches, summarize_game_matches

    try:
        matches = await list_game_matches(include_cancelled=include_cancelled)
        return {
            "summary": summarize_game_matches(matches),
            "matches": matches,
        }
    except Exception as exc:
        logger.error("Game matches failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/game/matches", dependencies=[Depends(verify_api_key)], status_code=201)
async def api_game_import_match(data: GameMatchImportRequest):
    from database.games import import_game_match
    from services.sports_api import get_football_match

    if data.max_stake < data.min_stake:
        raise HTTPException(status_code=422, detail="max_stake must be greater than or equal to min_stake")
    try:
        provider_match = await get_football_match(data.external_match_id)
        match = await import_game_match(
            provider_match,
            market_type=data.market_type,
            lock_minutes=data.lock_minutes,
            min_stake=data.min_stake,
            max_stake=data.max_stake,
            fee_bps=data.fee_bps,
            publish=data.publish,
        )
        return {"status": "published" if data.publish else "draft", "match": match}
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match import failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put("/api/game/matches/{match_id}", dependencies=[Depends(verify_api_key)])
async def api_game_update_match(match_id: int, data: GameMatchConfigurationRequest):
    from database.games import update_game_match_configuration

    if data.max_stake < data.min_stake:
        raise HTTPException(status_code=422, detail="max_stake must be greater than or equal to min_stake")
    try:
        return {
            "status": "updated",
            "match": await update_game_match_configuration(
                match_id,
                market_type=data.market_type,
                lock_minutes=data.lock_minutes,
                min_stake=data.min_stake,
                max_stake=data.max_stake,
                fee_bps=data.fee_bps,
            ),
        }
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/game/matches/{match_id}/publish", dependencies=[Depends(verify_api_key)])
async def api_game_publish_match(match_id: int):
    from database.games import publish_game_match

    try:
        return {"status": "published", "match": await publish_game_match(match_id)}
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match publish failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/game/matches/{match_id}/sync", dependencies=[Depends(verify_api_key)])
async def api_game_sync_match(match_id: int):
    from database.games import get_game_match, update_game_match_from_provider
    from services.sports_api import get_football_match

    try:
        match = await get_game_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match.get("status") in {"SETTLED", "CANCELLED"}:
            raise HTTPException(status_code=409, detail="A terminal match cannot be synchronized")
        provider_match = await get_football_match(str(match["external_match_id"]))
        return {
            "status": "synchronized",
            "match": await update_game_match_from_provider(match_id, provider_match),
        }
    except HTTPException:
        raise
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match synchronization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/game/matches/{match_id}/settle", dependencies=[Depends(verify_api_key)])
async def api_game_settle_match(match_id: int, data: GameMatchSettlementRequest):
    from database.games import settle_game_match

    if not hmac.compare_digest(data.confirmation.strip().upper(), f"SETTLE {match_id}"):
        raise HTTPException(status_code=400, detail=f"Type SETTLE {match_id} to confirm")
    try:
        return {"status": "settled", "match": await settle_game_match(match_id, data.result_outcome)}
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match settlement failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/game/matches/{match_id}/cancel", dependencies=[Depends(verify_api_key)])
async def api_game_cancel_match(match_id: int, data: GameMatchActionRequest):
    from database.games import cancel_game_match

    if not hmac.compare_digest(data.confirmation.strip().upper(), f"CANCEL {match_id}"):
        raise HTTPException(status_code=400, detail=f"Type CANCEL {match_id} to confirm")
    try:
        return {"status": "cancelled", "match": await cancel_game_match(match_id)}
    except Exception as exc:
        try:
            _raise_game_api_error(exc)
        except HTTPException:
            raise
        logger.error("Game match cancellation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/reseller/me")
async def api_reseller_me(reseller: dict = Depends(verify_reseller_key)):
    return _reseller_success(
        user_telegram_id=reseller["user_telegram_id"],
        username=reseller.get("username"),
        first_name=reseller.get("first_name"),
        wallet_balance=float(reseller.get("wallet_balance") or 0),
        key_name=reseller.get("name") or "",
        key_prefix=reseller.get("key_prefix"),
    )


async def _build_reseller_catalog(lang: str) -> dict:
    from database.models import (
        dynamic_tier_price,
        get_all_products,
        get_all_stock_counts,
        get_price_tiers_for_products,
        get_reseller_test_product,
    )

    products = await get_all_products()
    stock_counts = await get_all_stock_counts()
    active_products = [
        p for p in products
        if p.get("is_active", 1) and not p.get("is_deleted", 0)
    ]
    tiers_by_product = await get_price_tiers_for_products([p["id"] for p in active_products])
    result = []
    for p in active_products:
        desc = p.get(f"description_{lang}") if lang in {"fr", "ar", "zh", "vi", "ru"} else p.get("description")
        if not desc:
            desc = p.get("description", "")
        tiers = tiers_by_product.get(p["id"], [])
        result.append({
            "id": p["id"],
            "name": p["name"],
            "description": desc or "",
            "emoji": p.get("emoji"),
            "image_url": p.get("image_url"),
            "price_usd": float(p.get("price_usd") or 0),
            "warranty_days": p.get("warranty_days", 0),
            "delivery_type": p.get("delivery_type") or "stock",
            "stock": None if p.get("delivery_type") == "activation" else stock_counts.get(p["id"], 0),
            "price_tiers": [
                {
                    "min_qty": item["min_qty"],
                    "max_qty": item["max_qty"],
                    "price_usd": dynamic_tier_price(p, float(item["price_usd"])),
                }
                for item in tiers
            ],
        })
    test_product = get_reseller_test_product()
    if test_product:
        result.append(test_product)
    return _reseller_success(products=result)


def _catalog_response(
    payload: dict,
    etag: str,
    generation: int,
    *,
    stale: bool = False,
    rate_headers: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={
            **(rate_headers or {}),
            "Cache-Control": (
                f"private, max-age={RESELLER_CATALOG_CACHE_SECONDS}, stale-while-revalidate=30"
            ),
            "ETag": etag,
            "X-Catalog-Version": str(generation),
            "X-Catalog-Stale": "true" if stale else "false",
        },
    )


async def _personalized_catalog_response(
    request: Request,
    reseller: dict,
    base_payload: dict,
    generation: int,
    *,
    stale: bool = False,
) -> Response:
    from database.models import apply_reseller_special_prices_to_catalog

    payload = await apply_reseller_special_prices_to_catalog(
        base_payload, int(reseller["user_telegram_id"])
    )
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    etag = f'"{hashlib.sha256(encoded).hexdigest()[:24]}"'
    rate_headers = dict(reseller.get("_rate_headers") or {})
    if request.headers.get("if-none-match") == etag:
        return Response(
            status_code=304,
            headers={
                **rate_headers,
                "ETag": etag,
                "X-Catalog-Version": str(generation),
                "X-Catalog-Stale": "true" if stale else "false",
            },
        )
    return _catalog_response(
        payload,
        etag,
        generation,
        stale=stale,
        rate_headers=rate_headers,
    )


@api.get("/api/reseller/products")
async def api_reseller_products(
    request: Request,
    lang: str = "en",
    reseller: dict = Depends(verify_reseller_key),
):
    from database.models import get_catalog_cache_generation

    lang = lang if lang in {"en", "fr", "ar", "zh", "vi", "ru"} else "en"
    generation = get_catalog_cache_generation()
    now = time.monotonic()
    cached = _reseller_catalog_cache.get(lang)
    if (
        cached
        and cached["generation"] == generation
        and now - cached["created_at"] < RESELLER_CATALOG_CACHE_SECONDS
    ):
        return await _personalized_catalog_response(
            request, reseller, cached["payload"], generation
        )

    async with _get_reseller_catalog_lock():
        generation = get_catalog_cache_generation()
        now = time.monotonic()
        cached = _reseller_catalog_cache.get(lang)
        if (
            cached
            and cached["generation"] == generation
            and now - cached["created_at"] < RESELLER_CATALOG_CACHE_SECONDS
        ):
            return await _personalized_catalog_response(
                request, reseller, cached["payload"], generation
            )
        try:
            payload = await _build_reseller_catalog(lang)
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            etag = f'"{hashlib.sha256(encoded).hexdigest()[:24]}"'
            cached = {
                "payload": payload,
                "etag": etag,
                "generation": generation,
                "created_at": time.monotonic(),
            }
            _reseller_catalog_cache[lang] = cached
            return await _personalized_catalog_response(
                request, reseller, payload, generation
            )
        except Exception as exc:
            stale = _reseller_catalog_cache.get(lang)
            if stale:
                logger.warning("Serving stale reseller catalog after refresh failure: %s", exc)
                return await _personalized_catalog_response(
                    request,
                    reseller,
                    stale["payload"],
                    int(stale["generation"]),
                    stale=True,
                )
            logger.error("API error reseller products: %s", exc, exc_info=True)
            raise HTTPException(status_code=503, detail="Catalog temporarily unavailable")


@api.post("/api/reseller/quote")
async def api_reseller_quote(data: ResellerQuoteRequest, reseller: dict = Depends(verify_reseller_key)):
    from database.models import quote_reseller_order
    try:
        quote = await quote_reseller_order(
            data.product_id,
            data.quantity,
            reseller_user_telegram_id=reseller["user_telegram_id"],
        )
        return _reseller_success(quote=quote, wallet_balance=float(reseller.get("wallet_balance") or 0))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API error reseller quote: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/reseller/orders")
async def api_reseller_create_order(data: ResellerCreateOrderRequest, reseller: dict = Depends(verify_reseller_key)):
    from database.models import create_reseller_order
    from services.supplier_api import SupplierAPIError
    try:
        result = await create_reseller_order(
            reseller_user_telegram_id=reseller["user_telegram_id"],
            reseller_api_key_id=reseller["id"],
            product_id=data.product_id,
            quantity=data.quantity,
            activation_identifier=data.activation_identifier,
            customer_reference=data.customer_reference,
            idempotency_key=data.idempotency_key,
        )
        order = result.get("order")
        if order and order.get("status") == "AWAITING_ACTIVATION":
            try:
                await notify_admins(
                    "<b>Nouvelle activation revendeur</b>\n\n"
                    f"Commande: #{order['id']}\n"
                    f"Revendeur: <code>{reseller['user_telegram_id']}</code>\n"
                    f"Produit: {escape_html(order.get('product_name') or str(order.get('product_id')))} x{order.get('quantity', 1)}\n"
                    f"Identifiant: <code>{escape_html(order.get('activation_identifier') or '')}</code>"
                )
            except Exception:
                pass
        return _reseller_success(
            status="ok",
            idempotent=bool(result.get("idempotent")),
            balance_after=result.get("balance_after"),
            unit_price=result.get("unit_price"),
            standard_unit_price=result.get("standard_unit_price"),
            pricing_type=result.get("pricing_type"),
            total=result.get("total"),
            order=_api_order_payload(order),
        )
    except SupplierAPIError:
        _raise_reseller_error(
            503,
            "SUPPLIER_TEMPORARILY_UNAVAILABLE",
            "Supplier stock could not be verified. Retry shortly.",
            headers={"Retry-After": "5"},
        )
    except ValueError as exc:
        msg = str(exc)
        if "Idempotency key already used" in msg:
            _raise_reseller_error(409, "IDEMPOTENCY_CONFLICT", msg)
        code = 402 if "wallet" in msg.lower() else 400
        error_code = "INSUFFICIENT_BALANCE" if code == 402 else _reseller_error_from_detail(code, msg)["code"]
        _raise_reseller_error(code, error_code, msg)
    except Exception as exc:
        logger.error("API error reseller create order: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/reseller/orders/{order_id}")
async def api_reseller_get_order(order_id: int, reseller: dict = Depends(verify_reseller_key)):
    from database.models import get_reseller_order
    try:
        order = await get_reseller_order(reseller["user_telegram_id"], order_id)
        if not order:
            _raise_reseller_error(404, "ORDER_NOT_FOUND", "Order not found")
        return _reseller_success(order=_api_order_payload(order))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error reseller get order: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/reseller/orders/{order_id}/activation-identifier")
async def api_reseller_submit_activation(order_id: int, data: ResellerActivationIdentifierRequest, reseller: dict = Depends(verify_reseller_key)):
    from database.models import get_reseller_order, submit_activation_identifier
    try:
        identifier = data.activation_identifier.strip()
        if len(identifier) < 2:
            _raise_reseller_error(400, "ACTIVATION_IDENTIFIER_REQUIRED", "activation_identifier is required")
        order = await get_reseller_order(reseller["user_telegram_id"], order_id)
        if not order:
            _raise_reseller_error(404, "ORDER_NOT_FOUND", "Order not found")
        if order.get("status") != "AWAITING_ACTIVATION_INFO":
            _raise_reseller_error(400, "INVALID_ORDER_STATUS", "Order is not waiting for an activation identifier")
        submitted = await submit_activation_identifier(order_id, identifier)
        if not submitted:
            _raise_reseller_error(409, "ORDER_STATE_CHANGED", "Order state changed; reload the order")
        try:
            await notify_admins(
                "<b>Nouvelle activation revendeur</b>\n\n"
                f"Commande: #{order_id}\n"
                f"Revendeur: <code>{reseller['user_telegram_id']}</code>\n"
                f"Produit: {escape_html(order.get('product_name') or str(order.get('product_id')))} x{order.get('quantity', 1)}\n"
                f"Identifiant: <code>{escape_html(identifier)}</code>"
            )
        except Exception as exc:
            logger.warning(
                "Could not notify admins about reseller activation order %s: %s",
                order_id,
                exc,
            )
        updated = await get_reseller_order(reseller["user_telegram_id"], order_id)
        return _reseller_success(status="ok", order=_api_order_payload(updated))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error reseller activation identifier: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/reseller/security")
async def api_reseller_get_security(reseller: dict = Depends(verify_reseller_key)):
    from database.models import get_reseller_api_security

    config = await get_reseller_api_security(
        int(reseller["id"]),
        user_telegram_id=int(reseller["user_telegram_id"]),
        active_only=True,
    )
    if not config:
        _raise_reseller_error(404, "API_KEY_NOT_FOUND", "Reseller API key not found")
    return _reseller_success(security=_public_reseller_security_config(config))


@api.put("/api/reseller/security")
async def api_reseller_update_security(
    data: ResellerSecurityRequest,
    reseller: dict = Depends(verify_reseller_key),
):
    try:
        config = await _apply_reseller_security_update(
            int(reseller["id"]),
            data,
            user_telegram_id=int(reseller["user_telegram_id"]),
        )
        return _reseller_success(security=config)
    except HTTPException:
        raise
    except ValueError as exc:
        _raise_reseller_error(400, "INVALID_SECURITY_CONFIGURATION", str(exc))
    except Exception as exc:
        logger.error("API error update reseller security: %s", exc, exc_info=True)
        _raise_reseller_error(500, "INTERNAL_ERROR", "Internal server error")


@api.get("/api/reseller/wallet/deposit-methods")
async def api_reseller_deposit_methods(reseller: dict = Depends(verify_reseller_key)):
    from services.nowpayments import get_minimum_amount, is_nowpayments_configured

    available = is_nowpayments_configured()
    minimum = None
    provider_error = None
    if available:
        try:
            quote = await get_minimum_amount(
                currency_from="usdtbsc",
                currency_to="usdtbsc",
                fiat_equivalent="usd",
                is_fixed_rate=False,
                is_fee_paid_by_user=False,
            )
            minimum = float(quote.get("min_amount") or 0) or None
        except Exception as exc:
            provider_error = "Minimum currently unavailable; retry before creating a deposit."
            logger.warning("Could not read reseller deposit minimum: %s", exc)
    return _reseller_success(
        methods=[{
            "network": "BEP20",
            "asset": "USDT",
            "provider_currency": "USDTBSC",
            "available": available,
            "minimum_deposit_usd": minimum,
            "fee": {"ventebot_fee_usd": 0.0, "provider_quote_included": True},
            "expiry_seconds": PAYMENT_TIMEOUT_SECONDS,
            "error": provider_error,
        }],
    )


async def _refresh_reseller_deposit(deposit: dict) -> tuple[dict, bool]:
    from database.models import (
        finalize_nowpayments_wallet_topup,
        get_reseller_deposit,
        save_nowpayments_update,
    )
    from handlers.wallet import process_nowpayments_wallet_topup_notification
    from services.nowpayments import get_payment_status

    public_id = str(deposit.get("public_id") or "")
    payment_id = str(deposit.get("payment_id") or "").strip()
    terminal = {"CREDITED", "EXPIRED", "FAILED", "REFUNDED", "REVIEW_REQUIRED"}
    from database.models import public_reseller_deposit

    public = public_reseller_deposit(deposit) or {}
    if not payment_id or public.get("status") in terminal:
        _reseller_deposit_refresh_at.pop(public_id, None)
        lock = _reseller_deposit_refresh_locks.get(public_id)
        if lock is None or not lock.locked():
            _reseller_deposit_refresh_locks.pop(public_id, None)
        return deposit, False
    now = time.monotonic()
    if now - _reseller_deposit_refresh_at.get(public_id, 0.0) < 10:
        return deposit, False

    async with _get_reseller_deposit_refresh_lock(public_id):
        now = time.monotonic()
        if now - _reseller_deposit_refresh_at.get(public_id, 0.0) < 10:
            return deposit, False
        _reseller_deposit_refresh_at[public_id] = now
        try:
            payload = await get_payment_status(payment_id)
            await save_nowpayments_update(payload)
            if tg_app and getattr(tg_app, "bot", None):
                await process_nowpayments_wallet_topup_notification(tg_app.bot, payment_id)
            else:
                await finalize_nowpayments_wallet_topup(payment_id)
            refreshed = await get_reseller_deposit(
                int(deposit["user_telegram_id"]),
                public_id,
            )
            return refreshed or deposit, False
        except Exception as exc:
            logger.warning("Reseller deposit refresh failed for %s: %s", public_id, exc)
            return deposit, True


async def _safe_enqueue_reseller_deposit_webhook(deposit: dict | None) -> None:
    try:
        from services.reseller_webhooks import enqueue_reseller_deposit_webhook

        await enqueue_reseller_deposit_webhook(deposit)
    except Exception as exc:
        logger.warning("Could not enqueue reseller deposit webhook: %s", exc)


@api.post("/api/reseller/wallet/deposits")
async def api_reseller_create_deposit(
    data: ResellerDepositRequest,
    reseller: dict = Depends(verify_reseller_key),
):
    from database.models import (
        attach_nowpayments_wallet_topup,
        get_reseller_deposit,
        mark_nowpayments_wallet_topup_creation_failed,
        prepare_reseller_deposit,
        public_reseller_deposit,
    )
    from handlers.payment import _nowpayments_callback_url
    from services.nowpayments import (
        NowPaymentsError,
        create_payment,
        get_minimum_amount,
        is_nowpayments_configured,
    )

    network = data.network.strip().upper()
    if network not in {"BEP20", "BSC", "USDTBSC"}:
        _raise_reseller_error(400, "UNSUPPORTED_NETWORK", "Only USDT on BEP20 is supported")
    if not is_nowpayments_configured():
        _raise_reseller_error(503, "DEPOSITS_UNAVAILABLE", "BEP20 deposits are temporarily unavailable")
    callback_url = _nowpayments_callback_url()
    if not callback_url.lower().startswith("https://"):
        _raise_reseller_error(503, "DEPOSITS_UNAVAILABLE", "Deposit callback is not configured")

    try:
        minimum_quote = await get_minimum_amount(
            currency_from="usdtbsc",
            currency_to="usdtbsc",
            fiat_equivalent="usd",
            is_fixed_rate=False,
            is_fee_paid_by_user=False,
        )
        minimum = float(minimum_quote.get("min_amount") or 0)
    except Exception as exc:
        logger.warning("Reseller deposit minimum lookup failed: %s", exc)
        _raise_reseller_error(
            503,
            "DEPOSIT_PROVIDER_UNAVAILABLE",
            "Deposit provider is temporarily unavailable. Retry shortly.",
            headers={"Retry-After": "5"},
        )
    if minimum > 0 and float(data.amount_usd) + 1e-9 < minimum:
        _raise_reseller_error(
            400,
            "MINIMUM_DEPOSIT_NOT_MET",
            f"Minimum BEP20 deposit is {minimum:g} USDT.",
            minimum_deposit_usd=minimum,
        )

    try:
        prepared = await prepare_reseller_deposit(
            int(reseller["id"]),
            int(reseller["user_telegram_id"]),
            float(data.amount_usd),
            "BEP20",
            data.idempotency_key,
            data.reference,
        )
    except ValueError as exc:
        message = str(exc)
        if "Idempotency key already used" in message:
            _raise_reseller_error(409, "IDEMPOTENCY_CONFLICT", message)
        _raise_reseller_error(400, "INVALID_DEPOSIT", message)

    deposit = prepared["deposit"]
    if not prepared["created"]:
        return _reseller_success(idempotent=True, deposit=public_reseller_deposit(deposit))

    request_key = str(deposit.get("request_key") or "")
    try:
        provider_payment = await create_payment(
            price_amount=float(data.amount_usd),
            order_id=request_key,
            order_description=f"VenteBot reseller wallet deposit {deposit['public_id']}",
            callback_url=callback_url,
            pay_currency="usdtbsc",
            is_fixed_rate=False,
            is_fee_paid_by_user=False,
        )
    except NowPaymentsError as exc:
        await mark_nowpayments_wallet_topup_creation_failed(
            request_key,
            uncertain=bool(exc.retryable),
            error=str(exc),
        )
        deposit = await get_reseller_deposit(
            int(reseller["user_telegram_id"]),
            str(deposit["public_id"]),
        )
        await _safe_enqueue_reseller_deposit_webhook(deposit)
        code = 503 if exc.retryable else 400
        _raise_reseller_error(
            code,
            "DEPOSIT_CREATION_UNCERTAIN" if exc.retryable else "DEPOSIT_CREATION_REJECTED",
            str(exc),
            headers={"Retry-After": "5"} if exc.retryable else None,
            deposit=public_reseller_deposit(deposit),
        )

    try:
        from database.db import is_transient_db_connection_error

        attach_error = None
        for attempt in range(3):
            try:
                await attach_nowpayments_wallet_topup(request_key, provider_payment)
                attach_error = None
                break
            except Exception as exc:
                attach_error = exc
                if not is_transient_db_connection_error(exc) or attempt == 2:
                    break
                await asyncio.sleep(0.15 * (attempt + 1))
        if attach_error is not None:
            raise attach_error
        deposit = await get_reseller_deposit(
            int(reseller["user_telegram_id"]),
            str(deposit["public_id"]),
        )
        await _safe_enqueue_reseller_deposit_webhook(deposit)
        return JSONResponse(
            status_code=201,
            content=jsonable_encoder(
                _reseller_success(idempotent=False, deposit=public_reseller_deposit(deposit))
            ),
            headers=dict(reseller.get("_rate_headers") or {}),
        )
    except Exception as exc:
        provider_payment_id = str(provider_payment.get("payment_id") or "unknown")
        logger.error(
            "NOWPayments created reseller deposit %s but persistence failed for provider payment %s: %s",
            deposit.get("public_id"),
            provider_payment_id,
            exc,
            exc_info=True,
        )
        await mark_nowpayments_wallet_topup_creation_failed(
            request_key,
            uncertain=True,
            error=f"Provider payment {provider_payment_id} persistence failed: {exc}",
        )
        deposit = await get_reseller_deposit(
            int(reseller["user_telegram_id"]),
            str(deposit["public_id"]),
        )
        await _safe_enqueue_reseller_deposit_webhook(deposit)
        _raise_reseller_error(
            503,
            "DEPOSIT_PERSISTENCE_UNCERTAIN",
            "The provider may have created this deposit, but its state could not be persisted. Do not create another deposit; contact support with the deposit ID.",
            headers={"Retry-After": "5"},
            deposit=public_reseller_deposit(deposit),
        )


@api.get("/api/reseller/wallet/deposits/{deposit_id}")
async def api_reseller_get_deposit(
    deposit_id: str,
    refresh: bool = True,
    reseller: dict = Depends(verify_reseller_key),
):
    from database.models import get_reseller_deposit, public_reseller_deposit

    deposit = await get_reseller_deposit(
        int(reseller["user_telegram_id"]),
        deposit_id,
    )
    if not deposit:
        _raise_reseller_error(404, "DEPOSIT_NOT_FOUND", "Deposit not found")
    stale = False
    if refresh:
        deposit, stale = await _refresh_reseller_deposit(deposit)
    await _safe_enqueue_reseller_deposit_webhook(deposit)
    return _reseller_success(deposit=public_reseller_deposit(deposit), stale=stale)


@api.get("/api/reseller/wallet/transactions")
async def api_reseller_wallet_transactions(limit: int = 50, offset: int = 0, reseller: dict = Depends(verify_reseller_key)):
    from database.models import get_reseller_wallet_transactions
    try:
        return _reseller_success(transactions=await get_reseller_wallet_transactions(reseller["user_telegram_id"], limit, offset))
    except Exception as exc:
        logger.error("API error reseller wallet tx: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.get("/api/finance", dependencies=[Depends(verify_api_key)])
async def api_get_finance(method: str = None):
    from database.models import get_stats, get_setting
    try:
        stats_1, stats_7, stats_30 = await asyncio.gather(
            get_stats(days=1),
            get_stats(days=7),
            get_stats(days=30)
        )
        
        balance = 0.0
        if method and method != "all":
            # Get balance for specific method
            balance_str = await get_setting(f"finance_bot_balance_{method}")
            balance = _finite_float(balance_str, "stored balance") if balance_str else 0.0
        else:
            # Sum all balances
            methods = ["binance", "bep20", "trc20", "wallet"]
            for m in methods:
                b_str = await get_setting(f"finance_bot_balance_{m}")
                if b_str:
                    balance += _finite_float(b_str, "stored balance")
        
        return {
            "daily_revenue": stats_1.get("total_revenue", 0),
            "weekly_revenue": stats_7.get("total_revenue", 0),
            "monthly_revenue": stats_30.get("total_revenue", 0),
            "bot_balance": balance,
            "sales_binance_30d": stats_30.get("sales_binance", 0),
            "sales_bep20_30d": stats_30.get("sales_bep20", 0),
            "sales_trc20_30d": stats_30.get("sales_trc20", 0),
            "sales_wallet_30d": stats_30.get("sales_wallet", 0),
            "topup_count_30d": stats_30.get("topup_count", 0),
            "topup_revenue_30d": stats_30.get("topup_revenue", 0)
        }
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.post("/api/finance/adjust", dependencies=[Depends(verify_api_key)])
async def api_adjust_finance(data: FinanceAdjustRequest):
    from database.models import get_setting, set_setting
    try:
        amount = _finite_float(data.amount, "amount")
        method = data.method.strip().lower()
        
        if not method or method == "all":
            raise HTTPException(status_code=400, detail="Veuillez sélectionner une méthode spécifique (Binance, BEP20, etc.) pour ajuster le solde.")
            
        setting_key = f"finance_bot_balance_{method}"
        balance_str = await get_setting(setting_key)
        balance = _finite_float(balance_str, "stored balance") if balance_str else 0.0
        
        new_balance = round(balance + amount, 4)
        if new_balance < 0:
            new_balance = 0.0
            
        await set_setting(setting_key, str(new_balance))
        _clear_api_stats_cache()
        return {"status": "success", "new_balance": new_balance}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/finance/reconciliation", dependencies=[Depends(verify_api_key)])
async def api_get_financial_reconciliation():
    from services.reconciliation import get_latest_financial_reconciliation

    try:
        report = await get_latest_financial_reconciliation()
        return {"available": report is not None, "report": report}
    except Exception as exc:
        logger.error("API reconciliation read error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load reconciliation report")


@api.post("/api/finance/reconciliation/run", dependencies=[Depends(verify_api_key)])
async def api_run_financial_reconciliation():
    from services.reconciliation import run_financial_reconciliation

    try:
        return await run_financial_reconciliation()
    except Exception as exc:
        logger.error("API reconciliation run error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Financial reconciliation failed")


@api.get("/api/audit", dependencies=[Depends(verify_api_key)])
async def api_get_admin_audit(limit: int = 100, offset: int = 0):
    from database.audit import list_admin_audit_events

    try:
        return await list_admin_audit_events(limit=limit, offset=offset)
    except Exception as exc:
        logger.error("API admin audit read error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load admin audit")


@api.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def api_get_stats():
    current_time = time.time()
    if "stats" in _stats_cache and current_time - _stats_cache["stats"]["time"] < _stats_cache_ttl:
        return _stats_cache["stats"]["data"]

    from database.models import get_stats, get_total_users_count, get_all_products, get_all_stock_counts, get_stock_forecast
    try:
        stats_30, total_users, products, stock_counts, forecast = await asyncio.gather(
            get_stats(days=30),
            get_total_users_count(),
            get_all_products(),
            get_all_stock_counts(),
            get_stock_forecast(days=7),
        )

        stock_summary = []
        for p in products:
            is_activation = p.get("delivery_type") == "activation"
            stock = int(stock_counts.get(p["id"], 0) or 0)
            velocity = forecast.get(p["id"], {})
            avg_daily = float(velocity.get("avg_daily_sales") or 0)
            days_left = None if is_activation or avg_daily <= 0 else round(stock / avg_daily, 1)
            stock_summary.append({
                "id": p["id"],
                "name": p["name"],
                "emoji": p["emoji"],
                "stock": stock,
                "delivery_type": p.get("delivery_type") or "stock",
                "avg_daily_sales_7d": avg_daily,
                "days_left": days_left,
                "stock_risk": "activation" if is_activation else ("out" if stock <= 0 else ("soon" if days_left is not None and days_left <= 3 else ("watch" if days_left is not None and days_left <= 7 else "ok"))),
            })

        response_data = {
            "total_users": total_users,
            "total_orders": stats_30.get("total_orders", 0),
            "completed_orders": stats_30.get("completed_orders", 0),
            "pending_orders": stats_30.get("pending_orders", 0),
            "total_revenue": stats_30.get("total_revenue", 0),
            "stock_summary": stock_summary,
            "new_users": stats_30.get("new_users", 0),
            "returning_users": stats_30.get("returning_users", 0)
        }
        _stats_cache["stats"] = {"time": current_time, "data": response_data}
        return response_data
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/dashboard/overview", dependencies=[Depends(verify_api_key)])
async def api_dashboard_overview():
    current_time = time.time()
    cache_key = "dashboard_overview"
    if cache_key in _stats_cache and current_time - _stats_cache[cache_key]["time"] < _stats_cache_ttl:
        return _stats_cache[cache_key]["data"]

    from database.models import get_dashboard_overview
    try:
        data = await get_dashboard_overview()
        _stats_cache[cache_key] = {"time": current_time, "data": data}
        return data
    except Exception as exc:
        logger.error("API dashboard overview error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products", dependencies=[Depends(verify_api_key)])
async def api_get_products():
    from database.models import get_all_products, get_all_stock_counts
    try:
        products = await get_all_products()
        stock_counts = await get_all_stock_counts()
        result = []
        for p in products:
            item = dict(p)
            item["stock"] = stock_counts.get(p["id"], 0)
            result.append(item)
        return result
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


_DYNAMIC_PRICING_FIELDS = {
    "dynamic_pricing_enabled", "dynamic_pricing_mode", "dynamic_min_price",
    "dynamic_max_price", "dynamic_target_daily_sales", "dynamic_max_change_pct",
    "dynamic_cooldown_hours", "dynamic_sensitivity", "dynamic_daily_cap_pct",
    "dynamic_weekly_cap_pct", "dynamic_min_confidence",
    "dynamic_psychological_rounding",
}


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _finite_float(value, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid number",
        ) from exc
    if not math.isfinite(parsed):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a finite number",
        )
    return parsed


def _validated_dynamic_pricing_updates(data: dict, current_price: float, existing: dict | None = None) -> dict:
    if not any(field in data for field in _DYNAMIC_PRICING_FIELDS):
        return {}
    existing = existing or {}
    enabled = _as_bool(data.get("dynamic_pricing_enabled", existing.get("dynamic_pricing_enabled", False)))
    if not enabled:
        return {"dynamic_pricing_enabled": 0}

    current_price = _finite_float(current_price, "Current price")
    try:
        min_price = _finite_float(data.get("dynamic_min_price", existing.get("dynamic_min_price") or current_price * 0.8), "Dynamic minimum price")
        max_price = _finite_float(data.get("dynamic_max_price", existing.get("dynamic_max_price") or current_price * 1.2), "Dynamic maximum price")
        target = _finite_float(data.get("dynamic_target_daily_sales", existing.get("dynamic_target_daily_sales") or 1.0), "Target daily sales")
        max_change = _finite_float(data.get("dynamic_max_change_pct", existing.get("dynamic_max_change_pct") or 5.0), "Maximum dynamic variation")
        cooldown = int(data.get("dynamic_cooldown_hours", existing.get("dynamic_cooldown_hours") or 6))
        daily_cap = _finite_float(data.get("dynamic_daily_cap_pct", existing.get("dynamic_daily_cap_pct") or 10.0), "Daily dynamic cap")
        weekly_cap = _finite_float(data.get("dynamic_weekly_cap_pct", existing.get("dynamic_weekly_cap_pct") or 25.0), "Weekly dynamic cap")
        min_confidence = _finite_float(data.get("dynamic_min_confidence", existing.get("dynamic_min_confidence") or 0.30), "Minimum confidence")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Dynamic pricing values must be valid numbers")

    mode = str(data.get("dynamic_pricing_mode", existing.get("dynamic_pricing_mode") or "automatic"))
    sensitivity = str(data.get("dynamic_sensitivity", existing.get("dynamic_sensitivity") or "normal"))
    if min_price <= 0 or max_price <= 0 or min_price > max_price:
        raise HTTPException(status_code=400, detail="Dynamic minimum price must be positive and not exceed maximum price")
    if not min_price <= current_price <= max_price:
        raise HTTPException(status_code=400, detail="Current price must remain between dynamic minimum and maximum prices")
    if not 0.1 <= target <= 10000:
        raise HTTPException(status_code=400, detail="Target daily sales must be between 0.1 and 10000")
    if not 0.5 <= max_change <= 20:
        raise HTTPException(status_code=400, detail="Maximum dynamic variation must be between 0.5% and 20%")
    if not 1 <= cooldown <= 168:
        raise HTTPException(status_code=400, detail="Dynamic pricing cooldown must be between 1 and 168 hours")
    if not 0.5 <= daily_cap <= 100:
        raise HTTPException(status_code=400, detail="Daily dynamic variation cap must be between 0.5% and 100%")
    if not 0.5 <= weekly_cap <= 200 or weekly_cap < daily_cap:
        raise HTTPException(status_code=400, detail="Weekly dynamic variation cap must be at least the daily cap and not exceed 200%")
    if not 0 <= min_confidence <= 1:
        raise HTTPException(status_code=400, detail="Minimum dynamic pricing confidence must be between 0 and 1")
    if mode not in {"suggestion", "automatic"}:
        raise HTTPException(status_code=400, detail="Dynamic pricing mode must be suggestion or automatic")
    if sensitivity not in {"cautious", "normal", "aggressive"}:
        raise HTTPException(status_code=400, detail="Invalid dynamic pricing sensitivity")

    base_price = _finite_float(
        existing.get("dynamic_base_price") or current_price,
        "Dynamic base price",
    )
    return {
        "dynamic_pricing_enabled": 1,
        "dynamic_pricing_mode": mode,
        "dynamic_min_price": round(min_price, 2),
        "dynamic_max_price": round(max_price, 2),
        "dynamic_base_price": round(base_price, 2),
        "dynamic_target_daily_sales": target,
        "dynamic_max_change_pct": max_change,
        "dynamic_cooldown_hours": cooldown,
        "dynamic_sensitivity": sensitivity,
        "dynamic_daily_cap_pct": daily_cap,
        "dynamic_weekly_cap_pct": weekly_cap,
        "dynamic_min_confidence": min_confidence,
        "dynamic_psychological_rounding": 1 if _as_bool(data.get("dynamic_psychological_rounding", existing.get("dynamic_psychological_rounding", False))) else 0,
    }
@api.post("/api/products", dependencies=[Depends(verify_api_key)])
async def api_create_product(data: dict):
    from database.models import add_product, get_categories, add_category, update_product, recalculate_dynamic_prices
    try:
        if "price_usd" not in data or "name" not in data:
            raise HTTPException(status_code=400, detail="Missing required fields: name, price_usd")
            
        # Auto-create a default category if none exists (categories hidden from UI)
        cats = await get_categories()
        if not cats:
            cat_id = await add_category(name="Produits", emoji="📦", description="Catégorie par défaut")
        else:
            cat_id = cats[0]["id"]

        price = _finite_float(data["price_usd"], "Price")
        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be positive")
        warranty = int(data.get("warranty_days", 0))
        if warranty < 0:
            raise HTTPException(status_code=400, detail="Warranty days cannot be negative")
        dynamic_updates = _validated_dynamic_pricing_updates(data, price)

        prod_id = await add_product(
            category_id=cat_id,
            name=data["name"],
            description=data.get("description", ""),
            price_usd=price,
            warranty_days=warranty,
            emoji=data.get("emoji", "📦"),
            custom_emoji_id=data.get("custom_emoji_id"),
            image_url=data.get("image_url"),
            binance_account_id=data.get("binance_account_id"),
            description_fr=data.get("description_fr", ""),
            description_ar=data.get("description_ar", ""),
            description_zh=data.get("description_zh", ""),
            description_vi=data.get("description_vi", ""),
            description_ru=data.get("description_ru", ""),
            delivery_type=data.get("delivery_type", "stock"),
            activation_message=data.get("activation_message", ""),
            activation_message_fr=data.get("activation_message_fr", ""),
            activation_message_ar=data.get("activation_message_ar", ""),
            activation_message_zh=data.get("activation_message_zh", ""),
            activation_message_vi=data.get("activation_message_vi", ""),
            activation_message_ru=data.get("activation_message_ru", ""),
            confirmation_message=data.get("confirmation_message", ""),
            confirmation_message_fr=data.get("confirmation_message_fr", ""),
            confirmation_message_ar=data.get("confirmation_message_ar", ""),
            confirmation_message_zh=data.get("confirmation_message_zh", ""),
            confirmation_message_vi=data.get("confirmation_message_vi", ""),
            confirmation_message_ru=data.get("confirmation_message_ru", "")
        )
        if dynamic_updates:
            await update_product(prod_id, **dynamic_updates)
            if dynamic_updates.get("dynamic_pricing_enabled"):
                await recalculate_dynamic_prices(product_id=prod_id, force=True, apply_automatic=False)
        _clear_api_stats_cache()
        return {"id": prod_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/tiers", dependencies=[Depends(verify_api_key)])
async def api_get_product_tiers(product_id: int):
    from database.models import get_price_tiers
    try:
        tiers = await get_price_tiers(product_id)
        return tiers
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put("/api/products/{product_id}/tiers", dependencies=[Depends(verify_api_key)])
async def api_set_product_tiers(product_id: int, data: dict):
    from database.models import set_price_tiers
    try:
        tiers = data.get("tiers", [])
        await set_price_tiers(product_id, tiers)
        _clear_api_stats_cache()
        return {"status": "updated", "count": len(tiers)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")



@api.post("/api/products/reorder", dependencies=[Depends(verify_api_key)])
@api.post("/api/products/update-sort", dependencies=[Depends(verify_api_key)])
async def api_reorder_products(request: Request):
    from database.db import get_db
    from database.models import clear_products_cache
    db = None
    try:
        data = await request.json()
        orders = data.get("orders", [])
        if not orders:
            return {"status": "ok"}
            
        db = await get_db()
        for item in orders:
            prod_id = item.get("id")
            sort_order = item.get("sort_order")
            if prod_id is not None and sort_order is not None:
                await db.execute("UPDATE products SET sort_order = ? WHERE id = ?", (sort_order, prod_id))
        await db.commit()
        clear_products_cache()
        _clear_api_stats_cache()
        return {"status": "reordered"}
    except Exception as exc:
        logger.error("API error reorder products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if db is not None:
            await db.close()

@api.put("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_update_product(product_id: int, data: dict):
    from database.models import update_product, get_product
    try:
        allowed = {"name", "price_usd", "emoji", "custom_emoji_id", "warranty_days", "description", "description_fr", "description_ar", "description_zh", "description_vi", "description_ru", "is_active", "binance_account_id", "image_url", "delivery_type", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "activation_message_vi", "activation_message_ru", "confirmation_message", "confirmation_message_fr", "confirmation_message_ar", "confirmation_message_zh", "confirmation_message_vi", "confirmation_message_ru"}
        updates = {k: v for k, v in data.items() if k in allowed}
        product = await get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        supplier_mapping = None
        if product.get("delivery_type") == "supplier_api":
            from database.suppliers import get_supplier_mapping_by_local_product

            supplier_mapping = await get_supplier_mapping_by_local_product(product_id)
            updates["delivery_type"] = "supplier_api"
        updated_price = _finite_float(
            updates.get("price_usd", product["price_usd"]),
            "Price",
        )
        if updated_price <= 0:
            raise HTTPException(status_code=400, detail="Price must be positive")
        dynamic_updates = _validated_dynamic_pricing_updates(data, updated_price, existing=product)
        updates.update(dynamic_updates)
        pricing_changed = False
        for key, value in dynamic_updates.items():
            previous = product.get(key)
            if isinstance(value, (int, float)) and previous is not None:
                try:
                    changed = abs(float(previous) - float(value)) > 1e-9
                except (TypeError, ValueError):
                    changed = previous != value
            else:
                changed = previous != value
            pricing_changed = pricing_changed or changed
        price_changed = "price_usd" in updates and abs(float(product["price_usd"]) - float(updates["price_usd"])) >= 0.01
        if pricing_changed or price_changed:
            updates.update({
                "dynamic_suggested_price": None,
                "dynamic_last_input_hash": None,
                "dynamic_last_applied_hash": None,
                "dynamic_last_confidence": None,
            })
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        if "price_usd" in updates:
            updates["price_usd"] = float(updates["price_usd"])
        if "warranty_days" in updates:
            updates["warranty_days"] = int(updates["warranty_days"])
        await update_product(product_id, **updates)
        if supplier_mapping:
            from database.suppliers import update_supplier_product_descriptions

            description_columns = {
                "description": "en",
                "description_fr": "fr",
                "description_ar": "ar",
                "description_zh": "zh",
                "description_vi": "vi",
                "description_ru": "ru",
            }
            descriptions = {
                language: updates[column]
                for column, language in description_columns.items()
                if column in updates
            }
            has_content_updates = bool(descriptions) or any(
                column in updates
                for column in (
                    "name",
                    "emoji",
                    "custom_emoji_id",
                    "warranty_days",
                    "image_url",
                )
            )
            if has_content_updates:
                await update_supplier_product_descriptions(
                    int(supplier_mapping["id"]),
                    descriptions,
                    str(supplier_mapping["supplier_code"]),
                    custom_name=updates.get("name") if "name" in updates else None,
                    custom_emoji=updates.get("emoji") if "emoji" in updates else None,
                    custom_emoji_id=(
                        updates.get("custom_emoji_id")
                        if "custom_emoji_id" in updates
                        else None
                    ),
                    custom_warranty_days=(
                        updates.get("warranty_days")
                        if "warranty_days" in updates
                        else None
                    ),
                    custom_image_url=(
                        (updates.get("image_url") or "")
                        if "image_url" in updates
                        else None
                    ),
                )
        _clear_api_stats_cache()
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/dynamic-pricing/history", dependencies=[Depends(verify_api_key)])
async def api_dynamic_pricing_history(product_id: int, limit: int = 20):
    from database.models import get_dynamic_price_history
    try:
        history = await get_dynamic_price_history(product_id, limit=limit)
        for item in history:
            item["applied"] = bool(item.get("applied"))
            item["confidence_pct"] = round(float(item.get("confidence") or 0) * 100)
            if not item.get("explanation"):
                item["explanation"] = item.get("reason") or "Décision dynamique enregistrée."
        return {"history": history}
    except Exception as exc:
        logger.error("API dynamic pricing history error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products/{product_id}/dynamic-pricing/recalculate", dependencies=[Depends(verify_api_key)])
async def api_recalculate_dynamic_price(product_id: int, data: dict | None = None):
    from database.models import get_product, recalculate_dynamic_prices
    try:
        if data:
            await api_update_product(product_id, {**data, "skip_dynamic_recalculation": True})
        product = await get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not product.get("dynamic_pricing_enabled"):
            raise HTTPException(status_code=400, detail="Dynamic pricing is disabled for this product")
        results = await recalculate_dynamic_prices(product_id=product_id, force=True, apply_automatic=False)
        _clear_api_stats_cache()
        return results[0] if results else {"product_id": product_id, "status": "unchanged"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API dynamic price recalculation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/dynamic-pricing/simulate", dependencies=[Depends(verify_api_key)])
async def api_simulate_dynamic_price(product_id: int, days: int = 30):
    from database.models import simulate_dynamic_pricing
    try:
        return await simulate_dynamic_pricing(product_id, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("API dynamic price simulation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products/{product_id}/dynamic-pricing/apply", dependencies=[Depends(verify_api_key)])
async def api_apply_dynamic_price(product_id: int):
    from database.models import apply_dynamic_price_suggestion
    try:
        result = await apply_dynamic_price_suggestion(product_id)
        _clear_api_stats_cache()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API apply dynamic price error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_product(product_id: int):
    from database.models import delete_product
    try:
        await delete_product(product_id)
        _clear_api_stats_cache()
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products/{product_id}/toggle-active", dependencies=[Depends(verify_api_key)])
async def api_toggle_product_active(product_id: int):
    from database.models import toggle_product_active
    try:
        res = await toggle_product_active(product_id)
        _clear_api_stats_cache()
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/translate", dependencies=[Depends(verify_api_key)])
async def api_translate(data: dict):
    import httpx
    
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text to translate")
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY non configurée")
        
    prompt = (
        "Detect the source language and translate the following product description into English, French, Arabic, Chinese, Vietnamese, and Russian. "
        "Return a valid JSON object with the exact keys: 'en', 'fr', 'ar', 'zh', 'vi', 'ru'. "
        "Do not return markdown, just the raw JSON object.\n\n"
        f"Text to translate: {text}"
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
                json=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            )
            
            if response.status_code != 200:
                logger.warning("Gemini 3.5 Flash failed (HTTP %d). Attempting dynamic fallback.", response.status_code)
                try:
                    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    models_resp = await client.get(models_url)
                    if models_resp.status_code == 200:
                        available_models = models_resp.json().get("models", [])
                        flash_models = [
                            m["name"].split("/")[-1] for m in available_models 
                            if "flash" in m.get("name", "").lower() and "generateContent" in m.get("supportedGenerationMethods", [])
                        ]
                        if flash_models:
                            # Sort to prioritize newer versions (e.g. 3.x over 2.x)
                            flash_models.sort(reverse=True)
                            for fallback_model in flash_models:
                                if fallback_model == "gemini-3.5-flash": 
                                    continue
                                logger.info("Trying fallback model: %s", fallback_model)
                                fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback_model}:generateContent"
                                response = await client.post(
                                    fallback_url,
                                    json=payload,
                                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                                )
                                if response.status_code == 200:
                                    break
                except Exception as e:
                    logger.error("Dynamic fallback failed: %s", e)

            if response is None or response.status_code != 200:
                error_body = response.text if response else "No response"
                logger.error("All Gemini models failed. Last HTTP %s: %s", getattr(response, 'status_code', 'N/A'), error_body)
                raise HTTPException(status_code=502, detail=f"Erreur API Gemini: {error_body}")
            
            result_json = response.json()
            
            # Extract text from Gemini response format
            response_text = result_json["candidates"][0]["content"]["parts"][0]["text"]
            
            # Clean up potential markdown formatting block if Gemini disobeys "no markdown"
            import re
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
            else:
                response_text = response_text.strip()
                
            translations = json.loads(response_text)
            return translations
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gemini API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur de traduction")


@api.post("/api/fix-db", dependencies=[Depends(verify_api_key)])
async def api_fix_db():
    from database.db import get_db
    db = await get_db()
    results = []
    cols = [
        "description_fr", "description_ar", "description_zh", "description_vi", "description_ru",
        "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh",
        "activation_message_vi", "activation_message_ru", "confirmation_message", "confirmation_message_fr",
        "confirmation_message_ar", "confirmation_message_zh", "confirmation_message_vi", "confirmation_message_ru",
    ]
    try:
        existing_rows = await (await db.execute("PRAGMA table_info(products)")).fetchall()
        existing = {str(row["name"]) for row in existing_rows}
        for col in cols:
            if col in existing:
                results.append(f"Skipped {col}: already exists")
                continue
            await db.execute(f"ALTER TABLE products ADD COLUMN {col} TEXT DEFAULT ''")
            results.append(f"Added {col}")
        await db.commit()
        return {"status": "done", "results": results}
    except Exception as exc:
        logger.error("Database repair failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Database repair failed")
    finally:
        await db.close()

@api.post("/api/recalculate-stats", dependencies=[Depends(verify_api_key)])
async def api_recalculate_stats():
    from database.db import get_db
    db = await get_db()
    try:
        # Update users stats based on their COMPLETED orders
        await db.execute("""
            UPDATE users 
            SET 
                total_orders = (
                    SELECT COUNT(*) FROM orders 
                    WHERE orders.user_telegram_id = users.telegram_id AND orders.status = 'COMPLETED'
                ),
                total_spent = COALESCE((
                    SELECT SUM(amount_usd) FROM orders 
                    WHERE orders.user_telegram_id = users.telegram_id AND orders.status = 'COMPLETED'
                ), 0)
            WHERE EXISTS (
                SELECT 1 FROM orders WHERE orders.user_telegram_id = users.telegram_id
            )
        """)
        await db.commit()
        return {"status": "success", "message": "Statistiques recalculées avec succès"}
    except Exception as exc:
        logger.exception("User statistics recalculation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Statistics recalculation failed",
        ) from exc
    finally:
        await db.close()

# ── Binance Accounts Endpoints ──

@api.get("/api/binance-accounts", dependencies=[Depends(verify_api_key)])
async def api_get_binance_accounts():
    from database.models import get_binance_accounts
    try:
        accounts = await get_binance_accounts()
        return [
            {
                "id": account.get("id"),
                "label": account.get("label"),
                "uid": account.get("uid"),
                "is_default": account.get("is_default"),
                "created_at": account.get("created_at"),
                "has_api_key": bool(account.get("api_key")),
                "has_api_secret": bool(account.get("api_secret")),
            }
            for account in accounts
        ]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.post("/api/binance-accounts", dependencies=[Depends(verify_api_key)])
async def api_create_binance_account(data: dict):
    from database.models import add_binance_account
    try:
        if "label" not in data or "uid" not in data:
            raise HTTPException(status_code=400, detail="label and uid are required")
        acc_id = await add_binance_account(
            label=data["label"],
            uid=data["uid"],
            api_key=data.get("api_key", ""),
            api_secret=data.get("api_secret", ""),
            is_default=data.get("is_default", 0)
        )
        return {"id": acc_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.put("/api/binance-accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def api_update_binance_account(account_id: int, data: dict):
    from database.models import update_binance_account
    try:
        allowed_keys = {"label", "uid", "api_key", "api_secret", "is_default"}
        safe_data = {k: v for k, v in data.items() if k in allowed_keys}
        for secret_field in ("api_key", "api_secret"):
            if safe_data.get(secret_field) == "":
                safe_data.pop(secret_field, None)
        await update_binance_account(account_id, **safe_data)
        return {"status": "updated"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.delete("/api/binance-accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_binance_account(account_id: int):
    from database.models import delete_binance_account
    try:
        await delete_binance_account(account_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/categories", dependencies=[Depends(verify_api_key)])
async def api_get_categories():
    from database.models import get_categories
    try:
        categories = await get_categories()
        return [dict(c) for c in categories]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/categories", dependencies=[Depends(verify_api_key)])
async def api_create_category(data: dict):
    from database.models import add_category
    try:
        cat_id = await add_category(
            name=data["name"],
            emoji=data.get("emoji", "📂"),
            description=data.get("description", "")
        )
        return {"id": cat_id, "status": "created"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/categories/{category_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_category(category_id: int):
    from database.models import delete_category
    try:
        await delete_category(category_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders", dependencies=[Depends(verify_api_key)])
async def api_get_orders():
    from database.models import get_pending_orders
    try:
        orders = await get_pending_orders()
        return [dict(o) for o in orders]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/{order_id}/confirm", dependencies=[Depends(verify_api_key)])
async def api_confirm_order(order_id: int):
    from database.models import get_order, update_order_status, get_product, get_user_lang
    from services.delivery import deliver_order
    try:
        order = await get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_status = order.get("status")
        product = await get_product(order.get("product_id"))
        if product and product.get("delivery_type") == "activation":
            if order_status == "COMPLETED":
                return {"status": "already_completed"}
            if order_status == "AWAITING_ACTIVATION_INFO":
                return {"status": "already_awaiting_activation_identifier"}
            if order_status not in ("PENDING", "AWAITING_PAYMENT"):
                raise HTTPException(status_code=409, detail=f"Order cannot be confirmed from status {order_status}")
            transitioned = await update_order_status(
                order_id,
                "AWAITING_ACTIVATION_INFO",
                expected_statuses=("PENDING", "AWAITING_PAYMENT"),
                payment_method=order.get("payment_method") or "manual",
            )
            if not transitioned:
                return {"status": "already_processing"}
            _clear_api_stats_cache()
            try:
                user_lang = await get_user_lang(order["user_telegram_id"])
                text = t("activation_manual_payment_prompt", user_lang).format(
                    product=escape_html(product["name"])
                )
                if tg_app:
                    await tg_app.bot.send_message(
                        chat_id=order["user_telegram_id"],
                        text=text,
                        parse_mode="HTML",
                    )
            except Exception as notify_exc:
                logger.warning("Failed to notify activation user via API: %s", notify_exc)
            return {"status": "awaiting_activation_identifier"}

        if order_status == "COMPLETED":
            delivered = await deliver_order(order_id, order.get("product_id"))
            if delivered:
                return {"status": "already_confirmed_and_delivered"}
            return {"status": "already_completed"}

        if order_status not in ("PENDING", "AWAITING_PAYMENT", "PAID_PENDING_DELIVERY"):
            raise HTTPException(status_code=409, detail=f"Order cannot be confirmed from status {order_status}")

        delivered = await deliver_order(order_id, order.get("product_id"))

        if not delivered:
            raise HTTPException(status_code=409, detail="Insufficient stock for this order")

        transitioned = await update_order_status(
            order_id,
            "COMPLETED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT", "PAID_PENDING_DELIVERY"),
        )
        if not transitioned:
            return {"status": "already_confirmed_and_delivered"}
        _clear_api_stats_cache()

        if delivered:
            product = await get_product(order.get("product_id"))
            warranty_days = product.get("warranty_days", 0) if product else 0
            
            # Notify user
            delivery_message_sent = False
            try:
                user_lang = await get_user_lang(order["user_telegram_id"])
                if tg_app:
                    conf_msg = get_confirmation_message(product, user_lang, order_id)
                    footer = (
                        f"{t('warranty_lbl', user_lang).format(days=warranty_days)}\n"
                        f"{t('save_info', user_lang)}\n\n"
                        f"{conf_msg}"
                    )
                    delivery_message_sent = await safe_send_delivery_messages(
                        tg_app.bot,
                        order["user_telegram_id"],
                        t("payment_confirmed", user_lang),
                        delivered,
                        footer,
                        user_lang,
                        order_id,
                    )
            except Exception as notify_exc:
                logger.warning("Failed to notify user via API: %s", notify_exc)

            return {"status": "confirmed_and_delivered", "delivery_message_sent": delivery_message_sent}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/tickets", dependencies=[Depends(verify_api_key)])
async def api_get_tickets():
    from database.models import get_open_tickets
    try:
        tickets = await get_open_tickets()
        return [dict(t_item) for t_item in tickets]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/tickets/{ticket_id}/reply", dependencies=[Depends(verify_api_key)])
async def api_reply_ticket(ticket_id: int, data: TicketReplyRequest):
    from database.models import get_ticket, reply_ticket, get_user_lang
    try:
        ticket = await get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        reply_text = data.reply_text.strip()
        if not reply_text:
            raise HTTPException(status_code=400, detail="Reply text cannot be empty")
        await reply_ticket(ticket_id, reply_text)
        
        # Notify user
        try:
            from utils.locales import t
            user_lang = await get_user_lang(ticket["user_telegram_id"])
            if tg_app:
                await tg_app.bot.send_message(
                    chat_id=ticket["user_telegram_id"],
                    text=f"{t('ticket_replied', user_lang).format(id=ticket_id)}\n\n{escape_html(reply_text)}",
                    parse_mode="HTML"
                )
        except Exception as notify_exc:
            logger.warning("Failed to notify user reply via API: %s", notify_exc)
            
        return {"status": "replied"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/stock", dependencies=[Depends(verify_api_key)])
async def api_get_product_stock(
    product_id: int,
    limit: int = 200,
    offset: int = 0,
    sold: bool | None = None,
):
    from database.models import get_stock_items_page_for_product
    try:
        return await get_stock_items_page_for_product(
            product_id,
            limit=limit,
            offset=offset,
            sold=sold,
        )
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products/{product_id}/stock", dependencies=[Depends(verify_api_key)])
async def api_add_product_stock(product_id: int, data: dict):
    from database.models import add_stock_items
    try:
        items = data.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="No items provided")
        count = await add_stock_items(product_id, items)
        _clear_api_stats_cache()
        if tg_app and tg_app.bot:
            try:
                from services.background_jobs import enqueue_restock_notification

                await enqueue_restock_notification(product_id)
            except Exception:
                logger.warning(
                    "Could not persist restock notifications; using direct fallback",
                    exc_info=True,
                )
                from handlers.products import notify_restock_subscribers

                asyncio.create_task(notify_restock_subscribers(tg_app.bot, product_id))
        
        broadcast = data.get("broadcast_restock", False)
        if broadcast:
            from database.models import get_product
            product = await get_product(product_id)
            if product:
                from utils.helpers import format_price
                broadcast_text = (
                    "🔔 <b>Product Restocked!</b>\n\n"
                    f"{product['emoji']} <b>{product['name']}</b> is back in stock!\n"
                    f"💰 Price: <b>{format_price(product['price_usd'])}</b>\n\n"
                    f"{product.get('description', '')}"
                )
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🛒 Buy now", callback_data=f"buy:{product_id}")
                ]])
                from handlers.admin import _execute_broadcast
                if tg_app and tg_app.bot:
                    # Run in background tasks to not block API response
                    asyncio.create_task(_execute_broadcast(tg_app.bot, broadcast_text, reply_markup=markup))

        return {"status": "added", "count": count}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/stock/{stock_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_stock_item(stock_id: int):
    from database.models import delete_stock_item
    try:
        await delete_stock_item(stock_id)
        _clear_api_stats_cache()
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


from fastapi import Query as _Q

@api.get("/api/orders/all", dependencies=[Depends(verify_api_key)])
async def api_get_all_orders(order_status: str = _Q(None, alias="status"), limit: int = 50, offset: int = 0):
    from database.models import get_all_orders_filtered, get_all_topups_filtered
    try:
        # Validate & bound inputs
        VALID_STATUSES = {"PENDING", "PROCESSING", "PAID_PENDING_DELIVERY", "COMPLETED", "CANCELLED", "AWAITING_PAYMENT", "AWAITING_ACTIVATION_INFO", "AWAITING_ACTIVATION", "TOPUP"}
        if order_status and order_status.upper() not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {', '.join(VALID_STATUSES)}")
        limit = max(1, min(limit, 200))  # Cap between 1-200
        offset = max(0, offset)

        # TOPUP filter returns wallet top-up transactions instead of orders
        if order_status and order_status.upper() == "TOPUP":
            topups, total = await get_all_topups_filtered(limit=limit, offset=offset)
            return {"orders": topups, "total": total}

        orders, total = await get_all_orders_filtered(status=order_status, limit=limit, offset=offset, exclude_activation=not order_status)
        return {"orders": orders, "total": total}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders/{order_id}/items", dependencies=[Depends(verify_api_key)])
async def api_get_order_items(order_id: int):
    from database.models import get_stock_items_for_order, get_order
    try:
        order = await get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        items = await get_stock_items_for_order(order_id)
        return {"order_id": order_id, "status": order["status"], "items": items}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/{order_id}/cancel", dependencies=[Depends(verify_api_key)])
async def api_cancel_order(order_id: int):
    from database.models import cancel_order_if_allowed
    try:
        order = await cancel_order_if_allowed(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        _clear_api_stats_cache()
        return {"status": "cancelled" if order.get("status") == "CANCELLED" else order.get("status")}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders/activations", dependencies=[Depends(verify_api_key)])
async def api_get_activation_orders(limit: int = 100, offset: int = 0):
    from database.models import get_activation_orders
    try:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        orders, total = await get_activation_orders(limit=limit, offset=offset)
        return {"orders": orders, "total": total}
    except Exception as exc:
        logger.error("API error activation orders: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/{order_id}/activate", dependencies=[Depends(verify_api_key)])
async def api_activate_order(order_id: int):
    from database.models import get_order, get_product, get_user_lang, update_order_status
    try:
        order = await get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.get("status") == "COMPLETED":
            return {"status": "already_completed"}
        if order.get("status") != "AWAITING_ACTIVATION":
            raise HTTPException(status_code=400, detail="Order is not awaiting activation")

        transitioned = await update_order_status(
            order_id,
            "COMPLETED",
            expected_statuses=("AWAITING_ACTIVATION",),
            activation_status="done",
            activated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        )
        if not transitioned:
            return {"status": "already_completed"}
        _clear_api_stats_cache()

        if tg_app and tg_app.bot:
            try:
                lang = await get_user_lang(order["user_telegram_id"])
                product = await get_product(order["product_id"])
                product_name = product["name"] if product else f"#{order['product_id']}"
                
                custom_msg = ""
                if product:
                    lang_msg = product.get(f"activation_message_{lang}") if lang != "en" else ""
                    if lang_msg:
                        custom_msg = lang_msg
                    elif product.get("activation_message"):
                        custom_msg = product["activation_message"]
                
                if custom_msg:
                    final_msg = custom_msg.replace("{product}", escape_html(product_name)).replace("{order_id}", str(order_id))
                else:
                    final_msg = t("activation_completed_user", lang).format(
                        product=escape_html(product_name),
                        order_id=order_id,
                    )
                
                await tg_app.bot.send_message(
                    chat_id=order["user_telegram_id"],
                    text=final_msg,
                    parse_mode="HTML",
                )
            except Exception:
                pass

        return {"status": "activated"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error activate order: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/cleanup", dependencies=[Depends(verify_api_key)])
async def api_cleanup_stale_orders():
    """Auto-cancel all PENDING/AWAITING_PAYMENT orders older than 5 minutes and notify users."""
    from database.models import expire_stale_nowpayments_payments
    try:
        expired_payment_ids = await expire_stale_nowpayments_payments(
            timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
        )
        if tg_app and tg_app.bot:
            for payment_id in expired_payment_ids:
                try:
                    await _process_nowpayments_payment(payment_id)
                except Exception as exc:
                    logger.warning("Could not notify expired NOWPayments payment %s: %s", payment_id, exc)
        bot = tg_app.bot if tg_app and tg_app.bot else None
        expired_orders = await _expire_stale_orders_and_notify(bot)
        return {
            "status": "ok",
            "cancelled": len(expired_orders) + len(expired_payment_ids),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders/{order_id}/timeline", dependencies=[Depends(verify_api_key)])
async def api_get_order_timeline(order_id: int):
    from database.audit import get_order_timeline

    try:
        timeline = await get_order_timeline(order_id)
        if not timeline:
            raise HTTPException(status_code=404, detail="Order not found")
        return timeline
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API order timeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load order timeline")


@api.get("/api/stats/daily", dependencies=[Depends(verify_api_key)])
async def api_get_daily_stats(days: int = 30):
    from database.models import get_daily_stats
    try:
        days = max(1, min(days, 365))  # Cap between 1-365
        data = await get_daily_stats(days=days)
        return data
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats/products", dependencies=[Depends(verify_api_key)])
async def api_get_products_stats():
    current_time = time.time()
    if "products_stats" in _stats_cache and current_time - _stats_cache["products_stats"]["time"] < _stats_cache_ttl:
        return _stats_cache["products_stats"]["data"]

    from database.models import get_products_sales_stats
    try:
        data = await get_products_sales_stats()
        _stats_cache["products_stats"] = {"time": current_time, "data": data}
        return data
    except Exception as exc:
        logger.error("API error products stats: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats/products/momentum", dependencies=[Depends(verify_api_key)])
async def api_get_products_momentum(days: int = 30):
    days = max(1, min(days, 90))
    cache_key = f"products_momentum_{days}"
    current_time = time.time()
    if cache_key in _stats_cache and current_time - _stats_cache[cache_key]["time"] < _stats_cache_ttl:
        return _stats_cache[cache_key]["data"]

    from database.models import get_product_sales_momentum
    try:
        data = await get_product_sales_momentum(days=days)
        _stats_cache[cache_key] = {"time": current_time, "data": data}
        return data
    except Exception as exc:
        logger.error("API error products momentum: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats/products/dead-alerts", dependencies=[Depends(verify_api_key)])
async def api_get_dead_product_alerts(days: int = 7, min_views: int = 10, max_conversion: float = 0.05):
    days = max(1, min(days, 90))
    min_views = max(1, min(min_views, 1000))
    max_conversion = max(0.0, min(max_conversion, 1.0))
    cache_key = f"dead_product_alerts_{days}_{min_views}_{max_conversion}"
    current_time = time.time()
    if cache_key in _stats_cache and current_time - _stats_cache[cache_key]["time"] < _stats_cache_ttl:
        return _stats_cache[cache_key]["data"]

    from database.models import get_dead_product_alerts
    try:
        data = {"alerts": await get_dead_product_alerts(days=days, min_views=min_views, max_conversion=max_conversion)}
        _stats_cache[cache_key] = {"time": current_time, "data": data}
        return data
    except Exception as exc:
        logger.error("API error dead product alerts: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/payments/review", dependencies=[Depends(verify_api_key)])
async def api_get_payment_review(
    category: str = "all",
    include_resolved: bool = False,
    limit: int = 100,
):
    allowed = {"all", "underpaid", "expired", "confirming", "late_after_cancel", "validation_error", "accepted"}
    if category not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported payment review category")
    from database.models import get_payment_review_items
    try:
        return await get_payment_review_items(
            category=category,
            include_resolved=include_resolved,
            limit=limit,
        )
    except Exception as exc:
        logger.error("API payment review error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load payment review")


@api.post("/api/payments/review/{payment_kind}/{payment_id}/action", dependencies=[Depends(verify_api_key)])
async def api_payment_review_action(
    payment_kind: str,
    payment_id: str,
    payload: PaymentReviewActionRequest,
):
    if payment_kind not in {"order", "wallet_topup"}:
        raise HTTPException(status_code=404, detail="Unknown payment kind")

    from database.models import (
        claim_payment_review_accept,
        finalize_nowpayments_payment,
        finalize_nowpayments_wallet_topup,
        get_nowpayments_payment,
        get_nowpayments_wallet_topup_by_payment,
        record_payment_review_action,
        reset_nowpayments_notification,
        save_nowpayments_update,
    )

    getter = get_nowpayments_payment if payment_kind == "order" else get_nowpayments_wallet_topup_by_payment
    payment = await getter(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # The authenticated browser cannot choose its own audit identity.
    actor = "dashboard-admin"
    if payload.action == "dismiss":
        if not payload.note.strip():
            raise HTTPException(status_code=422, detail="A note is required to dismiss a payment")
        audit = await record_payment_review_action(
            payment_kind, payment_id, "dismiss", note=payload.note, actor=actor,
        )
        return {"status": "dismissed", "audit": audit}
    if payload.action == "reopen":
        if payment.get("processed_at") is not None:
            raise HTTPException(status_code=409, detail="A processed payment cannot be reopened")
        audit = await record_payment_review_action(
            payment_kind, payment_id, "reopen", note=payload.note, actor=actor,
        )
        return {"status": "reopened", "audit": audit}

    if payload.action == "accept":
        expected_confirmation = f"ACCEPT {payment_kind} {payment_id}"
        if not hmac.compare_digest(payload.confirmation.strip(), expected_confirmation):
            raise HTTPException(
                status_code=409,
                detail=f"Confirmation must exactly match: {expected_confirmation}",
            )

    try:
        from services.nowpayments import get_payment_status
        provider_payment = await get_payment_status(payment_id)
        payment = await save_nowpayments_update(provider_payment) or payment
    except Exception as exc:
        logger.warning("Manual NOWPayments recheck failed for %s: %s", payment_id, exc)
        raise HTTPException(status_code=502, detail="NOWPayments could not be reached")

    if payload.action == "recheck":
        result_action = str(payment.get("provider_status") or "waiting")
        if tg_app and getattr(tg_app, "bot", None):
            await _process_nowpayments_payment(payment_id)
        audit = await record_payment_review_action(
            payment_kind, payment_id, "recheck", note=payload.note,
            actor=actor, result_action=result_action,
        )
        return {"status": "rechecked", "provider_status": result_action, "audit": audit}

    if str(payment.get("provider_status") or "").lower() != "finished":
        raise HTTPException(status_code=409, detail="Provider payment is not finished")
    if float(payment.get("actually_paid") or 0) <= 0:
        raise HTTPException(status_code=409, detail="No received amount can be accepted")

    claim = await claim_payment_review_accept(
        payment_kind,
        payment_id,
        note=payload.note,
        actor=actor,
    )
    if not claim.get("claimed"):
        last_action = str(claim.get("last_action") or "")
        details = {
            "accept": "Payment was already manually accepted",
            "accept_requested": "A manual acceptance is already in progress",
            "dismiss": "Reopen the dismissed payment before accepting it",
        }
        raise HTTPException(status_code=409, detail=details.get(last_action, "Payment cannot be claimed"))

    try:
        if payment_kind == "order":
            result = await finalize_nowpayments_payment(
                payment_id,
                allow_underpayment=True,
                allow_cancelled=True,
            )
        else:
            result = await finalize_nowpayments_wallet_topup(
                payment_id,
                allow_underpayment=True,
                allow_cancelled=True,
            )
    except Exception as exc:
        await record_payment_review_action(
            payment_kind, payment_id, "accept_failed", note=payload.note,
            actor=actor, result_action=str(exc)[:80],
        )
        logger.error("Manual payment acceptance failed for %s: %s", payment_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Payment finalization failed") from exc
    result_action = str(result.get("action") or "unknown")
    if result_action == "review_required":
        reason = str((result.get("payment") or {}).get("processing_error") or "Validation failed")
        await record_payment_review_action(
            payment_kind, payment_id, "accept_failed", note=payload.note,
            actor=actor, result_action=reason,
        )
        raise HTTPException(status_code=409, detail=reason)
    accepted_actions = {"completed", "activation", "paid_pending_delivery", "wallet_credited"}
    if result_action not in accepted_actions:
        raise HTTPException(status_code=409, detail=f"Payment cannot be accepted from state: {result_action}")

    audit = await record_payment_review_action(
        payment_kind, payment_id, "accept", note=payload.note,
        actor=actor, result_action=result_action,
    )
    notification_warning = None
    try:
        await reset_nowpayments_notification(payment_id, wallet_topup=payment_kind == "wallet_topup")
        if tg_app and getattr(tg_app, "bot", None):
            if payment_kind == "order":
                from handlers.payment import process_nowpayments_payment_notification
                result = await process_nowpayments_payment_notification(
                    tg_app.bot,
                    payment_id,
                    finalized_result=result,
                    force_notification=True,
                )
            else:
                from handlers.wallet import process_nowpayments_wallet_topup_notification
                result = await process_nowpayments_wallet_topup_notification(
                    tg_app.bot,
                    payment_id,
                    finalized_result=result,
                    force_notification=True,
                )
    except Exception as exc:
        notification_warning = "Payment accepted, but Telegram notification must be retried"
        logger.error("Accepted payment %s notification failed: %s", payment_id, exc, exc_info=True)
    _clear_api_stats_cache()
    return {
        "status": "accepted",
        "result": result.get("action"),
        "audit": audit,
        "warning": notification_warning,
    }


@api.get("/api/stats/conversion", dependencies=[Depends(verify_api_key)])
async def api_get_conversion_funnel(days: int = 30):
    days = max(1, min(int(days), 90))
    cache_key = f"conversion_funnel_{days}"
    current_time = time.time()
    if cache_key in _stats_cache and current_time - _stats_cache[cache_key]["time"] < _stats_cache_ttl:
        return _stats_cache[cache_key]["data"]
    from database.models import get_conversion_funnel
    try:
        data = await get_conversion_funnel(days=days)
        _stats_cache[cache_key] = {"time": current_time, "data": data}
        return data
    except Exception as exc:
        logger.error("API conversion funnel error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats/bundle", dependencies=[Depends(verify_api_key)])
async def api_get_stats_bundle(days: int = 30):
    """Load the complete statistics tab through one browser request."""
    days = max(1, min(int(days), 90))
    try:
        stats, daily, products, momentum, dead_alerts, conversion = await asyncio.gather(
            api_get_stats(),
            api_get_daily_stats(days=days),
            api_get_products_stats(),
            api_get_products_momentum(days=30),
            api_get_dead_product_alerts(days=7, min_views=10, max_conversion=0.05),
            api_get_conversion_funnel(days=days),
        )
        return {
            "stats": stats,
            "daily": daily,
            "products": products,
            "momentum": momentum,
            "dead_alerts": dead_alerts,
            "conversion": conversion,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API stats bundle error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/broadcast/{job_id}", dependencies=[Depends(verify_api_key)])
async def api_broadcast_status(job_id: str):
    from services.background_jobs import get_public_background_job

    job = await get_public_background_job(job_id)
    if not job or job.get("job_type") != "broadcast":
        raise HTTPException(status_code=404, detail="Broadcast job not found")
    return job


@api.post("/api/broadcast", dependencies=[Depends(verify_api_key)], status_code=202)
async def api_broadcast(data: dict):
    from services.background_jobs import enqueue_broadcast_job
    from services.broadcast import validate_broadcast_content
    try:
        message = data.get("message", "").strip()
        photo_url = data.get("photo_url", "").strip()
        btn_type = data.get("btn_type", "none")
        btn_prod_id = data.get("btn_prod_id")
        btn_text = data.get("btn_text", "").strip()
        btn_url = data.get("btn_url", "").strip()

        try:
            validate_broadcast_content(message, photo_url)
        except ValueError as exc:
            detail = "Message required" if str(exc) == "EMPTY_BROADCAST" else "Message exceeds Telegram's 4096 character limit"
            raise HTTPException(status_code=400, detail=detail) from exc

        # Construct reply markup if button requested
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        reply_markup = None
        if btn_type == "buy" and btn_prod_id:
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f"buy:{btn_prod_id}")
            ]])
        elif btn_type == "url" and btn_text and btn_url:
            if not btn_url.startswith(("http://", "https://")):
                btn_url = "https://" + btn_url
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(btn_text, url=btn_url)
            ]])

        if not tg_app or not tg_app.bot:
            raise HTTPException(status_code=503, detail="Bot not initialized")

        return await enqueue_broadcast_job(
            message,
            photo=photo_url,
            reply_markup=reply_markup,
            source="dashboard",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/promos", dependencies=[Depends(verify_api_key)])
async def api_get_promos():
    from database.models import get_all_promos
    try:
        return await get_all_promos()
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/promos", dependencies=[Depends(verify_api_key)])
async def api_create_promo(data: dict):
    from database.models import create_promo, get_product
    from utils.promos import PROMO_DISCOUNT_TYPES, parse_applicable_product_ids
    try:
        discount_type = data.get("discount_type", "percent")
        if discount_type not in PROMO_DISCOUNT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="discount_type must be 'percent', 'fixed', or 'product_price'",
            )
        try:
            discount_value = float(data["discount_value"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=400, detail="discount_value must be a valid number")
        if not math.isfinite(discount_value) or discount_value <= 0:
            raise HTTPException(status_code=400, detail="discount_value must be positive")
        if discount_type == "percent" and discount_value > 100:
            raise HTTPException(status_code=400, detail="Percent discount cannot exceed 100")

        applicable_product_ids = parse_applicable_product_ids(data.get("applicable_product_ids"))
        if discount_type == "product_price" and len(applicable_product_ids) != 1:
            raise HTTPException(
                status_code=400,
                detail="A product-price promo must target exactly one product",
            )
        for product_id in applicable_product_ids:
            if not await get_product(product_id):
                raise HTTPException(status_code=400, detail=f"Product {product_id} does not exist")

        code = str(data.get("code", "")).strip().upper()
        if not code:
            raise HTTPException(status_code=400, detail="code is required")
        try:
            max_uses = int(data.get("max_uses", 0))
            max_uses_per_user = int(data.get("max_uses_per_user", 0))
            max_qty_per_order = int(data.get("max_qty_per_order", 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Promo limits must be integers")
        if min(max_uses, max_uses_per_user, max_qty_per_order) < 0:
            raise HTTPException(status_code=400, detail="Promo limits cannot be negative")

        promo_id = await create_promo(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=max_uses,
            max_uses_per_user=max_uses_per_user,
            applicable_product_ids=",".join(map(str, applicable_product_ids)) or None,
            max_qty_per_order=max_qty_per_order,
            expires_at=data.get("expires_at"),
        )
        return {"id": promo_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/promos/{promo_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_promo(promo_id: int):
    from database.models import delete_promo
    try:
        await delete_promo(promo_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/users", dependencies=[Depends(verify_api_key)])
async def api_get_users(limit: int = 20, offset: int = 0, search: str = "", sort: str = "joined", order: str = "desc"):
    from database.models import get_users_paginated
    try:
        users, total = await get_users_paginated(limit, offset, search, sort, order)
        return {"users": users, "total": total}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/users/{telegram_id}/orders", dependencies=[Depends(verify_api_key)])
async def api_get_user_orders(telegram_id: int, limit: int = 20, offset: int = 0):
    from database.models import get_user_purchase_history
    try:
        history = await get_user_purchase_history(
            telegram_id,
            limit=max(1, min(int(limit), 50)),
            offset=max(0, int(offset)),
        )
        if not history:
            raise HTTPException(status_code=404, detail="User not found")
        return history
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error loading purchases for user %s: %s", telegram_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/ban", dependencies=[Depends(verify_api_key)])
async def api_ban_user(telegram_id: int, notify: bool = False):
    from database.models import ban_user, get_user_lang
    try:
        await ban_user(telegram_id)
        if notify:
            lang = "fr"
            try:
                lang = await get_user_lang(telegram_id)
            except Exception:
                pass
            
            ban_msg = {
                "fr": "🚫 Vous avez été banni du bot.",
                "en": "🚫 You have been banned from the bot.",
                "ar": "🚫 لقد تم حظرك من البوت."
            }
            text = ban_msg.get(lang, ban_msg["fr"])
            
            if tg_app and tg_app.bot:
                try:
                    await tg_app.bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
                except Exception as e:
                    logger.error("Failed to send ban notification to user %s: %s", telegram_id, e)
                    
        return {"status": "banned"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/unban", dependencies=[Depends(verify_api_key)])
async def api_unban_user(telegram_id: int):
    from database.models import unban_user
    try:
        await unban_user(telegram_id)
        return {"status": "unbanned"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/wallet/topup", dependencies=[Depends(verify_api_key)])
async def api_wallet_topup(telegram_id: int, data: dict):
    from database.models import topup_wallet
    try:
        amount = _finite_float(data.get("amount", 0), "Amount")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await topup_wallet(telegram_id, amount, "Admin credit")
        _clear_api_stats_cache()
        return {"status": "credited", "new_balance": new_balance}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/wallet/deduct", dependencies=[Depends(verify_api_key)])
async def api_wallet_deduct(telegram_id: int, data: dict):
    from database.models import deduct_wallet
    try:
        amount = _finite_float(data.get("amount", 0), "Amount")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await deduct_wallet(telegram_id, amount, "Admin debit")
        _clear_api_stats_cache()
        return {"status": "debited", "new_balance": new_balance}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/wallet/history", dependencies=[Depends(verify_api_key)])
async def api_wallet_history(limit: int = 50, offset: int = 0, tx_type: str = None):
    """Return all wallet transactions across all users (admin view)."""
    from database.models import get_all_wallet_transactions
    try:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        txs, total = await get_all_wallet_transactions(limit=limit, offset=offset, tx_type=tx_type or None)
        return {"transactions": txs, "total": total}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/settings/payment", dependencies=[Depends(verify_api_key)])
async def api_get_payment_settings():
    from database.models import get_setting
    try:
        bep20_address = await get_setting("bep20_address") or ""
        trc20_address = await get_setting("trc20_address") or ""
        return {"bep20_address": bep20_address, "trc20_address": trc20_address}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/settings/payment", dependencies=[Depends(verify_api_key)])
async def api_set_payment_settings(data: dict):
    from database.models import set_setting
    try:
        bep20_address = data.get("bep20_address", "").strip()
        trc20_address = data.get("trc20_address", "").strip()
        
        if bep20_address and (not bep20_address.startswith("0x") or len(bep20_address) != 42):
            raise HTTPException(status_code=400, detail="Invalid BEP20 address. Must start with 0x and be 42 characters.")
            
        if trc20_address and (not trc20_address.startswith("T") or len(trc20_address) != 34):
            raise HTTPException(status_code=400, detail="Invalid TRC20 address. Must start with T and be 34 characters.")
            
        await set_setting("bep20_address", bep20_address)
        await set_setting("trc20_address", trc20_address)
        return {"status": "saved"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Admin notifications utility ──
async def notify_admins(text: str, reply_markup=None):
    """Send a notification message to all admin Telegram IDs."""
    if not tg_app or not tg_app.bot:
        return

    async def _send(admin_id: int) -> None:
        try:
            await tg_app.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass

    await asyncio.gather(*(_send(admin_id) for admin_id in ADMIN_IDS), return_exceptions=True)


tg_app = None
webhook_update_queue: asyncio.Queue | None = None
webhook_worker_tasks: list[asyncio.Task] = []
WEBHOOK_WORKERS = _env_int("WEBHOOK_WORKERS", 8, minimum=1)
WEBHOOK_QUEUE_MAX = _env_int("WEBHOOK_QUEUE_MAX", 1000, minimum=10)
WEBHOOK_USER_QUEUE_MAX = _env_int("WEBHOOK_USER_QUEUE_MAX", 12, minimum=2)
SUBSCRIPTION_CACHE_SECONDS = _env_int("SUBSCRIPTION_CACHE_SECONDS", 3600, minimum=60)
NOWPAYMENTS_POLL_BATCH = _env_int("NOWPAYMENTS_POLL_BATCH", 5, minimum=1)
_webhook_metrics_started_at = time.monotonic()
_webhook_enqueued_at: dict[int, float] = {}
_webhook_dequeued_at: dict[int, float] = {}
_webhook_samples = deque(maxlen=10000)
_webhook_queue_samples = deque(maxlen=10000)
_webhook_handler_error_times = deque(maxlen=2000)
_webhook_deduplicated_times = deque(maxlen=5000)
_webhook_pending_by_key: dict[str, deque] = {}
_webhook_active_keys: set[str] = set()
_webhook_active_dedupe_signatures: set[tuple[str, str]] = set()
_webhook_dedupe_by_update: dict[int, tuple[str, str]] = {}
_webhook_recent_start_signatures: dict[tuple[str, str], float] = {}
_webhook_active_update_ids: set[int] = set()
_webhook_recent_update_ids: dict[int, float] = {}
_webhook_update_id_by_object: dict[int, int] = {}
_WEBHOOK_START_DEBOUNCE_SECONDS = 2.0
_webhook_action_samples = deque(maxlen=10000)
_webhook_active_workers = 0
_webhook_peak_active_workers = 0
_webhook_worker_states: dict[int, str] = {}
_webhook_worker_activity_samples = deque(maxlen=10000)
_webhook_queued_by_key: Counter[str] = Counter()
_webhook_pending_hourly: dict[tuple[str, str], dict[str, float | int | str]] = {}
webhook_worker_manager = None


def _configured_webhook_workers() -> int:
    if webhook_worker_manager is not None:
        count = int(webhook_worker_manager.worker_count)
        if count > 0:
            return count
    return WEBHOOK_WORKERS


def _record_webhook_worker_activity() -> None:
    configured = max(1, _configured_webhook_workers())
    _webhook_worker_activity_samples.append(
        (time.monotonic(), _webhook_active_workers, configured)
    )


def _record_persistent_action_sample(action: str, duration_seconds: float, succeeded: bool) -> None:
    bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00:00")
    key = (bucket, action)
    item = _webhook_pending_hourly.setdefault(key, {
        "bucket_hour": bucket,
        "action": action,
        "sample_count": 0,
        "error_count": 0,
        "total_duration_ms": 0.0,
        "max_duration_ms": 0.0,
    })
    duration_ms = max(0.0, float(duration_seconds) * 1000.0)
    item["sample_count"] = int(item["sample_count"]) + 1
    if not succeeded:
        item["error_count"] = int(item["error_count"]) + 1
    item["total_duration_ms"] = float(item["total_duration_ms"]) + duration_ms
    item["max_duration_ms"] = max(float(item["max_duration_ms"]), duration_ms)


def _merge_pending_performance_rows(rows: list[dict]) -> None:
    for row in rows:
        key = (str(row["bucket_hour"]), str(row["action"]))
        item = _webhook_pending_hourly.setdefault(key, {
            "bucket_hour": key[0],
            "action": key[1],
            "sample_count": 0,
            "error_count": 0,
            "total_duration_ms": 0.0,
            "max_duration_ms": 0.0,
        })
        item["sample_count"] = int(item["sample_count"]) + int(row["sample_count"])
        item["error_count"] = int(item["error_count"]) + int(row["error_count"])
        item["total_duration_ms"] = float(item["total_duration_ms"]) + float(row["total_duration_ms"])
        item["max_duration_ms"] = max(float(item["max_duration_ms"]), float(row["max_duration_ms"]))


async def _flush_performance_metrics() -> None:
    if not _webhook_pending_hourly:
        return
    rows = [dict(item) for item in _webhook_pending_hourly.values()]
    _webhook_pending_hourly.clear()
    try:
        from database.jobs import flush_performance_action_hourly

        await flush_performance_action_hourly(rows)
    except Exception:
        _merge_pending_performance_rows(rows)
        raise


async def _performance_history_worker() -> None:
    while True:
        try:
            await asyncio.sleep(60)
            await _flush_performance_metrics()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Could not persist performance metrics: %s", exc)


def _metrics_percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[index]


def _record_webhook_queue_depth() -> None:
    depth = webhook_update_queue.qsize() if webhook_update_queue is not None else 0
    depth += sum(len(pending) for pending in _webhook_pending_by_key.values())
    _webhook_queue_samples.append((time.monotonic(), depth))


def _record_webhook_handler_error() -> None:
    _webhook_handler_error_times.append(time.monotonic())


def _webhook_dedupe_signature(update: Update) -> tuple[str, str] | None:
    """Deduplicate identical expensive actions while one is already pending."""
    callback = getattr(update, "callback_query", None)
    if callback is not None:
        message = getattr(callback, "message", None)
        chat = getattr(message, "chat", None)
        chat_id = getattr(chat, "id", None)
        message_id = getattr(message, "message_id", None)
        inline_message_id = getattr(callback, "inline_message_id", None)
        target = inline_message_id or f"{chat_id}:{message_id}"
        return (
            _webhook_lock_key(update),
            f"callback:{target}:{str(callback.data or '')}",
        )

    message = update.effective_message
    text = str(getattr(message, "text", "") or "").strip()
    if not text:
        return None
    command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
    if command != "/start":
        return None
    return (_webhook_lock_key(update), text)


def _release_webhook_dedupe(update: Update, *, completed: bool = True) -> None:
    signature = _webhook_dedupe_by_update.pop(id(update), None)
    if signature is not None:
        _webhook_active_dedupe_signatures.discard(signature)
        if completed and signature[1].lower().startswith("/start"):
            _webhook_recent_start_signatures[signature] = time.monotonic()
    update_id = _webhook_update_id_by_object.pop(id(update), None)
    if update_id is not None:
        _webhook_active_update_ids.discard(update_id)
        if completed:
            _webhook_recent_update_ids[update_id] = time.monotonic()


def _current_webhook_backlog() -> int:
    queued = webhook_update_queue.qsize() if webhook_update_queue is not None else 0
    return queued + sum(len(pending) for pending in _webhook_pending_by_key.values())


def _webhook_performance_snapshot() -> dict:
    from database.db import get_db_performance_snapshot
    from services.runtime_metrics import get_runtime_snapshot

    now = time.monotonic()
    cutoff_5m = now - 300
    cutoff_1m = now - 60
    samples = [sample for sample in _webhook_samples if sample[0] >= cutoff_5m]
    one_minute = [sample for sample in samples if sample[0] >= cutoff_1m]
    queue_waits = [sample[1] for sample in samples]
    user_waits = [sample[2] for sample in samples]
    processing = [sample[3] for sample in samples]
    totals = [sample[1] + sample[2] + sample[3] for sample in samples]
    queue_depths = [sample[1] for sample in _webhook_queue_samples if sample[0] >= cutoff_5m]
    handler_errors = sum(1 for timestamp in _webhook_handler_error_times if timestamp >= cutoff_5m)
    deduplicated = sum(1 for timestamp in _webhook_deduplicated_times if timestamp >= cutoff_5m)
    db_metrics = get_db_performance_snapshot(300)
    db_write_metrics = db_metrics.get("write_serialization") or {}
    runtime_metrics = get_runtime_snapshot(300)
    external_metrics = runtime_metrics.get("external_apis") or {}
    event_loop_metrics = runtime_metrics.get("event_loop") or {}
    memory_metrics = runtime_metrics.get("memory") or {}
    configured_workers = max(1, _configured_webhook_workers())
    activity_samples = [
        sample for sample in _webhook_worker_activity_samples if sample[0] >= cutoff_1m
    ]
    utilizations = [
        min(1.0, max(0.0, sample[1] / max(1, sample[2])))
        for sample in activity_samples
    ]
    utilization_1m = (
        sum(utilizations) / len(utilizations)
        if utilizations
        else min(1.0, _webhook_active_workers / configured_workers)
    )
    observed_1m = max(1.0, min(60.0, now - _webhook_metrics_started_at))
    throughput_per_minute = len(one_minute) * 60.0 / observed_1m
    average_processing = sum(processing) / len(processing) if processing else 0.0
    estimated_workers = max(1, math.ceil((throughput_per_minute / 60.0) * average_processing * 1.5))
    queue_p95_ms = _metrics_percentile(queue_waits, 0.95) * 1000
    user_wait_p95_ms = _metrics_percentile(user_waits, 0.95) * 1000
    processing_p95_ms = _metrics_percentile(processing, 0.95) * 1000
    max_queue = max(queue_depths, default=0)
    midpoint = cutoff_5m + 150
    older_depths = [
        sample[1] for sample in _webhook_queue_samples
        if cutoff_5m <= sample[0] < midpoint
    ]
    recent_depths = [
        sample[1] for sample in _webhook_queue_samples
        if midpoint <= sample[0]
    ]
    older_average = sum(older_depths) / len(older_depths) if older_depths else 0.0
    recent_average = sum(recent_depths) / len(recent_depths) if recent_depths else 0.0
    queue_rising = recent_average >= max(1.0, older_average * 1.25)
    total_user_backlog = sum(_webhook_queued_by_key.values())
    max_user_backlog = max(_webhook_queued_by_key.values(), default=0)
    largest_user_share = max_user_backlog / total_user_backlog if total_user_backlog else 0.0
    timeline = []
    for bucket_index in range(10):
        bucket_start = cutoff_5m + bucket_index * 30
        bucket_end = bucket_start + 30
        bucket_samples = [sample for sample in samples if bucket_start <= sample[0] < bucket_end]
        bucket_waits = [sample[1] for sample in bucket_samples]
        bucket_user_waits = [sample[2] for sample in bucket_samples]
        bucket_processing = [sample[3] for sample in bucket_samples]
        bucket_queue_depths = [
            sample[1]
            for sample in _webhook_queue_samples
            if bucket_start <= sample[0] < bucket_end
        ]
        timeline.append({
            "from_seconds_ago": 300 - bucket_index * 30,
            "to_seconds_ago": 270 - bucket_index * 30,
            "processed": len(bucket_samples),
            "worker_errors": sum(1 for sample in bucket_samples if not sample[4]),
            "queue_peak": max(bucket_queue_depths, default=0),
            "average_wait_ms": round((sum(bucket_waits) / len(bucket_waits) * 1000) if bucket_waits else 0, 1),
            "average_user_wait_ms": round((sum(bucket_user_waits) / len(bucket_user_waits) * 1000) if bucket_user_waits else 0, 1),
            "p95_processing_ms": round(_metrics_percentile(bucket_processing, 0.95) * 1000, 1),
        })

    action_groups: dict[str, list[tuple]] = {}
    for sample in _webhook_action_samples:
        if sample[0] >= cutoff_5m:
            action_groups.setdefault(sample[1], []).append(sample)
    action_stats = []
    for action, action_samples in action_groups.items():
        durations = [sample[2] for sample in action_samples]
        action_stats.append({
            "action": action,
            "count": len(action_samples),
            "average_ms": round(sum(durations) / len(durations) * 1000, 1),
            "p95_ms": round(_metrics_percentile(durations, 0.95) * 1000, 1),
            "max_ms": round(max(durations) * 1000, 1),
            "errors": sum(1 for sample in action_samples if not sample[3]),
        })
    action_stats.sort(key=lambda item: (item["p95_ms"], item["count"]), reverse=True)

    if (
        db_metrics["connection_errors"] > 0
        or db_metrics["p95_ms"] >= 750
        or int(db_write_metrics.get("timeouts") or 0) > 0
        or float(db_write_metrics.get("p95_wait_ms") or 0) >= 750
    ):
        bottleneck = "database"
        recommended_workers = configured_workers
        message = "Database latency or write contention is limiting throughput; adding workers would increase contention."
        confidence = "high"
    elif (
        float(event_loop_metrics.get("p95_lag_ms") or 0) >= 250
        or float(event_loop_metrics.get("max_lag_ms") or 0) >= 1000
    ):
        bottleneck = "event_loop"
        recommended_workers = configured_workers
        message = "The event loop is delayed; adding workers would make the process less responsive."
        confidence = "high"
    elif float(memory_metrics.get("rss_mb") or 0) >= 450:
        bottleneck = "memory"
        recommended_workers = configured_workers
        message = "Process memory is near its safety limit; worker growth is blocked."
        confidence = "high"
    elif (
        int(external_metrics.get("calls") or 0) >= 3
        and (
            float(external_metrics.get("p95_ms") or 0) >= 3000
            or int(external_metrics.get("timeouts") or 0) > 0
        )
    ) or processing_p95_ms >= 3000:
        bottleneck = "external_api"
        recommended_workers = configured_workers
        message = "Handlers or external APIs are slow; more workers may only move the queue downstream."
        confidence = "medium"
    elif len(samples) < 20:
        bottleneck = "insufficient_data"
        recommended_workers = configured_workers
        message = "Collecting traffic data. At least 20 updates are needed."
        confidence = "low"
    elif user_wait_p95_ms >= 500 and queue_p95_ms < 500:
        bottleneck = "single_user_backlog"
        recommended_workers = configured_workers
        message = "One or more users are sending actions faster than their ordered queue can process them."
        confidence = "high"
    elif queue_p95_ms >= 500 or max_queue > configured_workers:
        bottleneck = "workers"
        recommended_workers = min(32, max(configured_workers + 2, estimated_workers))
        message = "Updates wait for a free worker; increase workers gradually."
        confidence = "high"
    else:
        bottleneck = "healthy"
        recommended_workers = configured_workers
        message = "Current worker capacity is sufficient for the observed traffic."
        confidence = "high"

    return {
        "window_seconds": 300,
        "workers": {
            "configured": configured_workers,
            "active": _webhook_active_workers,
            "peak_active": _webhook_peak_active_workers,
            "utilization_1m": round(utilization_1m, 3),
            "recommended": recommended_workers,
            "estimated_for_observed_load": estimated_workers,
        },
        "queue": {
            "current": _current_webhook_backlog(),
            "peak_5m": max_queue,
            "average_wait_ms": round((sum(queue_waits) / len(queue_waits) * 1000) if queue_waits else 0, 1),
            "p95_wait_ms": round(queue_p95_ms, 1),
            "rising": queue_rising,
            "max_user_backlog": max_user_backlog,
            "largest_user_share": round(largest_user_share, 3),
        },
        "traffic": {
            "processed_1m": len(one_minute),
            "processed_5m": len(samples),
            "throughput_per_minute": round(throughput_per_minute, 1),
            "handler_errors_5m": handler_errors,
            "deduplicated_starts_5m": deduplicated,
        },
        "latency": {
            "average_user_wait_ms": round((sum(user_waits) / len(user_waits) * 1000) if user_waits else 0, 1),
            "p95_user_wait_ms": round(user_wait_p95_ms, 1),
            "average_processing_ms": round(average_processing * 1000, 1),
            "p95_processing_ms": round(processing_p95_ms, 1),
            "p95_total_ms": round(_metrics_percentile(totals, 0.95) * 1000, 1),
        },
        "database": db_metrics,
        "external_apis": external_metrics,
        "event_loop": event_loop_metrics,
        "memory": memory_metrics,
        "actions_5m": action_stats,
        "timeline_30s": timeline,
        "diagnosis": {
            "bottleneck": bottleneck,
            "confidence": confidence,
            "message": message,
        },
    }


# ──────────────────────────────────────────────
#  Post-init hook: database setup
# ──────────────────────────────────────────────

DYNAMIC_PRICING_CHECK_SECONDS = _env_int("DYNAMIC_PRICING_CHECK_SECONDS", 900, minimum=60)
NOWPAYMENTS_RECONCILE_SECONDS = _env_int("NOWPAYMENTS_RECONCILE_SECONDS", 180, minimum=30)
STALE_ORDER_CLEANUP_SECONDS = _env_int("STALE_ORDER_CLEANUP_SECONDS", 60, minimum=30)
SUPPLIER_CATALOG_SYNC_SECONDS = _env_int(
    "SUPPLIER_CATALOG_SYNC_SECONDS", 90, minimum=60
)
SUPPLIER_CATALOG_FULL_SYNC_SECONDS = _env_int(
    "SUPPLIER_CATALOG_FULL_SYNC_SECONDS", 1800, minimum=300
)


async def _dynamic_pricing_worker() -> None:
    from database.models import recalculate_dynamic_prices
    while True:
        next_delay = DYNAMIC_PRICING_CHECK_SECONDS
        try:
            results = await recalculate_dynamic_prices()
            changed = [item for item in results if item.get("status") == "updated"]
            if changed:
                logger.info("Dynamic pricing updated %d product(s)", len(changed))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Dynamic pricing cycle failed: %s", exc)
            next_delay = 30
        await asyncio.sleep(next_delay)


async def _expire_stale_orders_and_notify(bot=None) -> list[dict]:
    from database.models import expire_stale_orders, get_user_lang

    expired_orders = await expire_stale_orders(
        timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
    )
    if expired_orders:
        logger.info("Auto-cancelled %d stale unpaid order(s)", len(expired_orders))

    if bot:
        for order in expired_orders:
            try:
                lang = await get_user_lang(int(order["user_telegram_id"]))
                message = t("order_expired_notification", lang).format(
                    order_id=order["id"],
                )
                await bot.send_message(
                    chat_id=order["user_telegram_id"],
                    text=message,
                    parse_mode="HTML",
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Could not notify user %s about expired order %s: %s",
                    order.get("user_telegram_id"),
                    order.get("id"),
                    exc,
                )
    return expired_orders


async def _stale_order_worker(bot) -> None:
    while True:
        next_delay = STALE_ORDER_CLEANUP_SECONDS
        try:
            await _expire_stale_orders_and_notify(bot)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Stale-order cleanup cycle failed: %s", exc)
            next_delay = 30
        await asyncio.sleep(next_delay)


def _should_process_polled_nowpayment(saved: dict | None) -> bool:
    if not saved:
        return False
    if saved.get("status_changed"):
        return True
    provider_status = str(saved.get("provider_status") or "").lower()
    actionable_statuses = {"finished", "partially_paid", "expired", "failed", "refunded"}
    return provider_status in actionable_statuses and saved.get("notified_at") is None


async def _nowpayments_worker() -> None:
    from database.models import (
        expire_stale_nowpayments_payments,
        expire_stale_nowpayments_wallet_topups,
        list_nowpayments_to_finalize,
        list_nowpayments_to_poll,
        list_nowpayments_wallet_topups_to_finalize,
        list_nowpayments_wallet_topups_to_poll,
        save_nowpayments_update,
    )
    from services.nowpayments import NowPaymentsError, get_payment_status

    while True:
        next_delay = NOWPAYMENTS_RECONCILE_SECONDS
        try:
            expired_payment_ids = await expire_stale_nowpayments_payments(
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
            for payment_id in expired_payment_ids:
                try:
                    await _process_nowpayments_payment(payment_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "NOWPayments expiration notification failed for %s: %s",
                        payment_id,
                        exc,
                    )

            expired_topup_ids = await expire_stale_nowpayments_wallet_topups(
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
            for payment_id in expired_topup_ids:
                try:
                    await _process_nowpayments_payment(payment_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "NOWPayments wallet top-up expiration notification failed for %s: %s",
                        payment_id,
                        exc,
                    )

            finalizable = await list_nowpayments_to_finalize(limit=25)
            finalizable += await list_nowpayments_wallet_topups_to_finalize(limit=25)
            for payment in finalizable:
                try:
                    await _process_nowpayments_payment(str(payment["payment_id"]))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "NOWPayments finalization failed for %s; it will be retried: %s",
                        payment.get("payment_id"),
                        exc,
                    )

            # Signed IPNs and already-finished payments stay prioritized. Polling
            # older pending payments can wait briefly while clients are queued.
            queue_busy = _current_webhook_backlog() > 0
            if queue_busy:
                logger.debug("Deferring NOWPayments polling while webhook clients are queued")
            else:
                pollable = await list_nowpayments_to_poll(limit=NOWPAYMENTS_POLL_BATCH)
                pollable += await list_nowpayments_wallet_topups_to_poll(limit=NOWPAYMENTS_POLL_BATCH)
                pollable.sort(key=lambda item: str(item.get("updated_at") or ""))
                for payment in pollable[:NOWPAYMENTS_POLL_BATCH]:
                    if _current_webhook_backlog() > 0:
                        logger.debug("Stopping NOWPayments polling because webhook clients are queued")
                        break
                    try:
                        provider_payment = await get_payment_status(payment["payment_id"])
                        saved = await save_nowpayments_update(provider_payment)
                        if _should_process_polled_nowpayment(saved):
                            await _process_nowpayments_payment(str(saved["payment_id"]))
                    except NowPaymentsError as exc:
                        logger.warning("NOWPayments reconciliation failed for %s: %s", payment.get("payment_id"), exc)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception(
                            "NOWPayments reconciliation failed for %s; continuing the cycle: %s",
                            payment.get("payment_id"),
                            exc,
                        )
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("NOWPayments reconciliation cycle failed: %s", exc)
            next_delay = 30
        await asyncio.sleep(next_delay)


async def post_init(application: Application) -> None:
    """Called after the Application has been initialised — set up the database."""
    await init_db()
    runtime_task = application.bot_data.get("runtime_health_task")
    if not runtime_task or runtime_task.done():
        from services.runtime_metrics import runtime_health_monitor

        application.bot_data["runtime_health_task"] = asyncio.create_task(
            runtime_health_monitor(), name="runtime-health-monitor"
        )
        logger.info("Runtime dependency, event-loop, and memory monitor started")
    logger.info("✅ Database initialized")

    try:
        from database.models import cleanup_product_views, recover_stale_processing_wallet_orders
        recovered = await recover_stale_processing_wallet_orders(age_minutes=5)
        if any(recovered.values()):
            logger.warning("Recovered interrupted wallet orders: %s", recovered)
        deleted_views = await cleanup_product_views(retention_days=90)
        if deleted_views:
            logger.info("Deleted %d expired product analytics rows", deleted_views)
    except Exception as exc:
        logger.exception("Could not recover interrupted wallet orders: %s", exc)

    try:
        await _expire_stale_orders_and_notify(application.bot)
    except Exception as exc:
        logger.warning("Could not clean stale orders: %s", exc)

    task = application.bot_data.get("stale_order_task")
    if not task or task.done():
        application.bot_data["stale_order_task"] = asyncio.create_task(
            _stale_order_worker(application.bot)
        )
        logger.info(
            "Stale-order cleanup worker started (check every %ds)",
            STALE_ORDER_CLEANUP_SECONDS,
        )

    task = application.bot_data.get("dynamic_pricing_task")
    if not task or task.done():
        application.bot_data["dynamic_pricing_task"] = asyncio.create_task(_dynamic_pricing_worker())
        logger.info("Dynamic pricing worker started (check every %ds)", DYNAMIC_PRICING_CHECK_SECONDS)

    task = application.bot_data.get("background_job_task")
    if not task or task.done():
        from services.background_jobs import background_job_worker

        application.bot_data["background_job_task"] = asyncio.create_task(
            background_job_worker(application.bot)
        )
        logger.info("Persistent background job worker started")

    task = application.bot_data.get("admin_audit_task")
    if not task or task.done():
        from services.admin_audit import admin_audit_worker

        application.bot_data["admin_audit_task"] = asyncio.create_task(
            admin_audit_worker(),
            name="admin-audit-worker",
        )
        logger.info("Bounded admin audit worker started")

    task = application.bot_data.get("financial_reconciliation_task")
    if not task or task.done():
        from services.reconciliation import financial_reconciliation_worker

        application.bot_data["financial_reconciliation_task"] = asyncio.create_task(
            financial_reconciliation_worker(_webhook_performance_snapshot),
            name="financial-reconciliation",
        )
        logger.info("Adaptive daily financial reconciliation worker started")

    task = application.bot_data.get("performance_history_task")
    if not task or task.done():
        try:
            from database.jobs import cleanup_performance_history

            await cleanup_performance_history(retention_days=8)
        except Exception as exc:
            logger.warning("Could not clean performance history: %s", exc)
        application.bot_data["performance_history_task"] = asyncio.create_task(
            _performance_history_worker()
        )
        logger.info("Persistent performance history worker started")

    task = application.bot_data.get("game_sync_task")
    if not task or task.done():
        from services.game_sync import game_sync_worker

        application.bot_data["game_sync_task"] = asyncio.create_task(game_sync_worker())
        logger.info("Lightweight game match synchronization worker started")

    task = application.bot_data.get("supplier_catalog_sync_task")
    if not task or task.done():
        from services.supplier_sync import supplier_catalog_sync_worker

        application.bot_data["supplier_catalog_sync_task"] = asyncio.create_task(
            supplier_catalog_sync_worker(
                SUPPLIER_CATALOG_SYNC_SECONDS,
                SUPPLIER_CATALOG_FULL_SYNC_SECONDS,
            ),
            name="supplier-catalog-sync",
        )
        logger.info(
            "Supplier catalog synchronization worker started "
            "(active every %ds, full every %ds)",
            SUPPLIER_CATALOG_SYNC_SECONDS,
            SUPPLIER_CATALOG_FULL_SYNC_SECONDS,
        )

    task = application.bot_data.get("supplier_ai_job_task")
    if not task or task.done():
        from services.supplier_ai import supplier_ai_job_worker

        application.bot_data["supplier_ai_job_task"] = asyncio.create_task(
            supplier_ai_job_worker(_webhook_performance_snapshot),
            name="supplier-ai-job-worker",
        )
        logger.info("Persistent supplier AI job worker started")

    task = application.bot_data.get("supplier_ai_auto_cycle_task")
    if not task or task.done():
        from services.supplier_ai import supplier_ai_auto_cycle_worker

        application.bot_data["supplier_ai_auto_cycle_task"] = asyncio.create_task(
            supplier_ai_auto_cycle_worker(_webhook_performance_snapshot),
            name="supplier-ai-auto-cycle",
        )
        logger.info("Automatic supplier AI cycle scheduler started")

    from services.nowpayments import is_nowpayments_configured
    if is_nowpayments_configured():
        task = application.bot_data.get("nowpayments_task")
        if not task or task.done():
            application.bot_data["nowpayments_task"] = asyncio.create_task(_nowpayments_worker())
            logger.info("NOWPayments reconciliation worker started (check every %ds)", NOWPAYMENTS_RECONCILE_SECONDS)
        try:
            restored = await restore_nowpayments_timeout_tasks(application.bot)
            if restored:
                logger.info("Restored %d NOWPayments expiration timer(s)", restored)
            from handlers.wallet import restore_nowpayments_wallet_topup_timeout_tasks
            restored_topups = await restore_nowpayments_wallet_topup_timeout_tasks(application.bot)
            if restored_topups:
                logger.info(
                    "Restored %d NOWPayments wallet top-up expiration timer(s)",
                    restored_topups,
                )
        except Exception as exc:
            logger.warning("Could not restore NOWPayments expiration timers: %s", exc)


async def post_shutdown(application: Application) -> None:
    tasks = [
        application.bot_data.pop("dynamic_pricing_task", None),
        application.bot_data.pop("nowpayments_task", None),
        application.bot_data.pop("stale_order_task", None),
        application.bot_data.pop("background_job_task", None),
        application.bot_data.pop("admin_audit_task", None),
        application.bot_data.pop("financial_reconciliation_task", None),
        application.bot_data.pop("performance_history_task", None),
        application.bot_data.pop("game_sync_task", None),
        application.bot_data.pop("supplier_catalog_sync_task", None),
        application.bot_data.pop("supplier_ai_job_task", None),
        application.bot_data.pop("supplier_ai_auto_cycle_task", None),
        application.bot_data.pop("runtime_health_task", None),
    ]
    for task in tasks:
        if task and not task.done():
            task.cancel()
    await asyncio.gather(*(task for task in tasks if task), return_exceptions=True)
    try:
        await _flush_performance_metrics()
    except Exception as exc:
        logger.warning("Final performance metric flush failed: %s", exc)
    from services.nowpayments import close_nowpayments_client
    await close_nowpayments_client()
    from services.reseller_webhooks import close_reseller_webhook_client
    await close_reseller_webhook_client()
    from services.supplier_registry import close_supplier_clients
    await close_supplier_clients()
    from services.sports_api import close_sports_client
    await close_sports_client()


# ──────────────────────────────────────────────
#  Webhook endpoint for Telegram updates
# ──────────────────────────────────────────────

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
DROP_PENDING_UPDATES = _env_bool("DROP_PENDING_UPDATES", False)
WEBHOOK_MAX_BODY_BYTES = _env_int("WEBHOOK_MAX_BODY_BYTES", 256 * 1024, minimum=1024)
WEBHOOK_UPDATE_DEDUPE_SECONDS = _env_int(
    "WEBHOOK_UPDATE_DEDUPE_SECONDS", 10 * 60, minimum=60
)


def _is_production_webhook(webhook_url: str) -> bool:
    environment = (
        os.environ.get("RAILWAY_ENVIRONMENT_NAME", "")
        or os.environ.get("ENV", "")
    ).strip().lower()
    return bool(webhook_url) and environment not in {"dev", "development", "local", "test"}


def _validate_runtime_security(webhook_url: str) -> None:
    if not _is_production_webhook(webhook_url):
        return
    if len(WEBHOOK_SECRET) < 32:
        raise RuntimeError(
            "WEBHOOK_SECRET must be configured with at least 32 characters in production"
        )
    if not os.environ.get("ADMIN_API_KEY", "").strip():
        raise RuntimeError("ADMIN_API_KEY must be configured in production")
    if len(os.environ.get("ADMIN_SESSION_SECRET", "").strip()) < 32:
        raise RuntimeError(
            "ADMIN_SESSION_SECRET must be configured with at least 32 characters in production"
        )
    if len(os.environ.get("RESELLER_WEBHOOK_MASTER_SECRET", "").strip()) < 32:
        raise RuntimeError(
            "RESELLER_WEBHOOK_MASTER_SECRET must be configured with at least 32 characters in production"
        )
    from utils.secret_store import validate_secret_store_configuration
    validate_secret_store_configuration()

from starlette.requests import Request as StarletteRequest

@api.post("/webhook")
async def telegram_webhook(request: StarletteRequest):
    """Receive Telegram updates via webhook — zero polling, zero wasted CPU."""
    update = None
    update_enqueued = False
    try:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not WEBHOOK_SECRET or not hmac.compare_digest(token, WEBHOOK_SECRET):
            logger.warning("Webhook secret mismatch; rejecting Telegram update")
            raise HTTPException(status_code=403, detail="Forbidden")

        # The previous webhook remains active while Railway restarts a
        # container. Ask Telegram to retry until Application.initialize(),
        # the update queue, and its workers are ready instead of acknowledging
        # and losing an update in the startup window.
        if tg_app is None or webhook_update_queue is None:
            raise HTTPException(
                status_code=503,
                detail="Telegram workers are starting",
                headers={"Retry-After": "2"},
            )

        content_length = request.headers.get("content-length", "").strip()
        if content_length:
            try:
                if int(content_length) > WEBHOOK_MAX_BODY_BYTES:
                    raise HTTPException(status_code=413, detail="Webhook payload too large")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length")
        raw_body = await request.body()
        if len(raw_body) > WEBHOOK_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Webhook payload too large")
        try:
            data = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="Invalid Telegram update JSON")
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Invalid Telegram update")
        logger.debug("Webhook received update: %s", data.get("update_id", "?"))
        if tg_app:
            update = Update.de_json(data, tg_app.bot)
            update_id = getattr(update, "update_id", None)
            if isinstance(update_id, int):
                now = time.monotonic()
                recent_at = _webhook_recent_update_ids.get(update_id)
                if (
                    update_id in _webhook_active_update_ids
                    or recent_at is not None
                    and now - recent_at < WEBHOOK_UPDATE_DEDUPE_SECONDS
                ):
                    _webhook_deduplicated_times.append(now)
                    return {"ok": True, "deduplicated": True}
                if len(_webhook_recent_update_ids) > 5000:
                    cutoff = now - WEBHOOK_UPDATE_DEDUPE_SECONDS
                    for recent_id, completed_at in list(_webhook_recent_update_ids.items()):
                        if completed_at < cutoff:
                            _webhook_recent_update_ids.pop(recent_id, None)
                _webhook_active_update_ids.add(update_id)
                _webhook_update_id_by_object[id(update)] = update_id
            lock_key = _webhook_lock_key(update)
            if _webhook_queued_by_key[lock_key] >= WEBHOOK_USER_QUEUE_MAX:
                _release_webhook_dedupe(update, completed=False)
                _webhook_deduplicated_times.append(time.monotonic())
                logger.info(
                    "Dropped webhook update for saturated per-user queue key=%s depth=%d",
                    lock_key,
                    _webhook_queued_by_key[lock_key],
                )
                return {"ok": True, "rate_limited": True}
            dedupe_signature = _webhook_dedupe_signature(update)
            if dedupe_signature is not None:
                now = time.monotonic()
                recent_start = _webhook_recent_start_signatures.get(dedupe_signature)
                if (
                    dedupe_signature in _webhook_active_dedupe_signatures
                    or (
                        recent_start is not None
                        and now - recent_start < _WEBHOOK_START_DEBOUNCE_SECONDS
                    )
                ):
                    _release_webhook_dedupe(update, completed=False)
                    _webhook_deduplicated_times.append(time.monotonic())
                    return {"ok": True, "deduplicated": True}
                if len(_webhook_recent_start_signatures) > 2000:
                    cutoff = now - _WEBHOOK_START_DEBOUNCE_SECONDS
                    for signature, completed_at in list(_webhook_recent_start_signatures.items()):
                        if completed_at < cutoff:
                            _webhook_recent_start_signatures.pop(signature, None)
                _webhook_active_dedupe_signatures.add(dedupe_signature)
                _webhook_dedupe_by_update[id(update)] = dedupe_signature
            _webhook_enqueued_at[id(update)] = time.monotonic()
            try:
                webhook_update_queue.put_nowait(update)
                update_enqueued = True
                _webhook_queued_by_key[lock_key] += 1
                _record_webhook_queue_depth()
            except asyncio.QueueFull:
                _webhook_enqueued_at.pop(id(update), None)
                _release_webhook_dedupe(update, completed=False)
                logger.error(
                    "Webhook queue full (%d updates); asking Telegram to retry",
                    WEBHOOK_QUEUE_MAX,
                )
                raise HTTPException(
                    status_code=503,
                    detail="Webhook queue is full",
                    headers={"Retry-After": "2"},
                )
        return {"ok": True}
    except HTTPException:
        if update is not None and not update_enqueued:
            _webhook_enqueued_at.pop(id(update), None)
            _release_webhook_dedupe(update, completed=False)
        raise
    except Exception as exc:
        if update is not None and not update_enqueued:
            _webhook_enqueued_at.pop(id(update), None)
            _release_webhook_dedupe(update, completed=False)
        logger.error("❌ Webhook error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


def _webhook_lock_key(update: Update) -> str:
    user = update.effective_user
    if user:
        return f"user:{user.id}"
    chat = update.effective_chat
    if chat:
        return f"chat:{chat.id}"
    return f"update:{update.update_id}"


def _webhook_action_name(update: Update) -> str:
    """Return a bounded action label for performance diagnostics."""
    callback = getattr(update, "callback_query", None)
    if callback:
        raw = str(callback.data or "unknown").split(":", 1)[0].lower()
        safe = "".join(char for char in raw if char.isalnum() or char in {"_", "-"})[:40]
        return f"callback:{safe or 'unknown'}"
    message = getattr(update, "effective_message", None)
    text = str(getattr(message, "text", "") or "").strip()
    if text.startswith("/"):
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()[:40]
        return f"command:{command}"
    if getattr(message, "photo", None):
        return "message:photo"
    if text:
        compact = text.replace(" ", "")
        if re.fullmatch(r"0x[a-fA-F0-9]{64}", compact):
            return "message:evm_tx_hash"
        if re.fullmatch(r"[a-fA-F0-9]{64}", compact):
            return "message:tx_hash"
        if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", text):
            return "message:number"
        if "@" in text or re.fullmatch(r"[A-Za-z0-9_.-]{3,}", text):
            return "message:identifier"
        if len(text) > 200:
            return "message:long_text"
        return "message:short_text"
    return "update:other"


async def _webhook_update_worker(
    application: Application,
    worker_id: int,
    stop_event: asyncio.Event | None = None,
) -> None:
    global webhook_update_queue, _webhook_active_workers, _webhook_peak_active_workers
    if webhook_update_queue is None:
        webhook_update_queue = asyncio.Queue(maxsize=WEBHOOK_QUEUE_MAX)
    stop_event = stop_event or asyncio.Event()
    _webhook_worker_states[worker_id] = "IDLE"
    _record_webhook_worker_activity()

    while not stop_event.is_set():
        try:
            update = await webhook_update_queue.get()
        except asyncio.CancelledError:
            _webhook_worker_states.pop(worker_id, None)
            _record_webhook_worker_activity()
            raise
        key = _webhook_lock_key(update)
        _webhook_dequeued_at[id(update)] = time.monotonic()
        if key in _webhook_active_keys:
            _webhook_pending_by_key.setdefault(key, deque()).append(update)
            _record_webhook_queue_depth()
            continue

        _webhook_active_keys.add(key)
        current_update = update
        try:
            while current_update is not None:
                started_at = time.monotonic()
                enqueued_at = _webhook_enqueued_at.pop(id(current_update), started_at)
                dequeued_at = _webhook_dequeued_at.pop(id(current_update), started_at)
                queue_wait = max(0.0, dequeued_at - enqueued_at)
                user_wait = max(0.0, started_at - dequeued_at)
                _webhook_active_workers += 1
                _webhook_worker_states[worker_id] = "ACTIVE"
                _webhook_peak_active_workers = max(
                    _webhook_peak_active_workers,
                    _webhook_active_workers,
                )
                succeeded = True
                action_name = _webhook_action_name(current_update)
                try:
                    await application.process_update(current_update)
                except asyncio.CancelledError:
                    succeeded = False
                    raise
                except Exception as exc:
                    succeeded = False
                    logger.error(
                        "Webhook worker %s update failed: %s",
                        worker_id,
                        exc,
                        exc_info=True,
                    )
                finally:
                    completed_at = time.monotonic()
                    _webhook_active_workers = max(0, _webhook_active_workers - 1)
                    _webhook_worker_states[worker_id] = (
                        "DRAINING" if stop_event.is_set() else "IDLE"
                    )
                    _record_webhook_worker_activity()
                    _webhook_samples.append((
                        completed_at,
                        queue_wait,
                        user_wait,
                        max(0.0, completed_at - started_at),
                        succeeded,
                    ))
                    _webhook_action_samples.append((
                        completed_at,
                        action_name,
                        max(0.0, completed_at - started_at),
                        succeeded,
                    ))
                    _record_persistent_action_sample(
                        action_name,
                        max(0.0, completed_at - started_at),
                        succeeded,
                    )
                    webhook_update_queue.task_done()
                    _webhook_queued_by_key[key] = max(
                        0, _webhook_queued_by_key[key] - 1
                    )
                    if _webhook_queued_by_key[key] == 0:
                        _webhook_queued_by_key.pop(key, None)
                    _release_webhook_dedupe(current_update)
                    _record_webhook_queue_depth()

                pending = _webhook_pending_by_key.get(key)
                if pending:
                    current_update = pending.popleft()
                    if not pending:
                        _webhook_pending_by_key.pop(key, None)
                else:
                    current_update = None
        finally:
            _webhook_active_keys.discard(key)
            _record_webhook_queue_depth()
    _webhook_worker_states.pop(worker_id, None)
    _record_webhook_worker_activity()


async def get_emoji_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to get the HTML code of any custom emoji sent with the message."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access denied.")
        return

    message = update.message
    if not message:
        return

    custom_emojis = [
        e for e in (message.entities or []) if e.type == "custom_emoji"
    ]
    
    if not custom_emojis:
        await message.reply_text(
            "Veuillez envoyer cette commande suivie d'un emoji premium.\n"
            "Exemple: `/getemoji` 🔥 (avec un emoji premium animé)",
            parse_mode="Markdown"
        )
        return

    response = "Voici le(s) code(s) HTML pour vos emojis custom :\n\n"
    for entity in custom_emojis:
        emoji_char = message.text[entity.offset:entity.offset+entity.length]
        emoji_id = entity.custom_emoji_id
        html_code = f"<code>&lt;tg-emoji emoji-id=\"{emoji_id}\"&gt;{emoji_char}&lt;/tg-emoji&gt;</code>"
        response += f"Emoji {emoji_char} (ID: <code>{emoji_id}</code>) :\n{html_code}\n\n"

    await message.reply_text(response, parse_mode="HTML")


async def run_migrations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to manually force run database migrations and print output."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Access denied.")
        return
        
    try:
        from database.db import get_db
        db = await get_db()
        # count promo usages table
        c = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='promo_code_usages'")
        table_exists = await c.fetchone() is not None
        
        c = await db.execute("SELECT * FROM promo_codes ORDER BY id DESC LIMIT 1")
        last_row = await c.fetchone()
        last_promo = dict(last_row) if last_row else None
        
        usage_count = 0
        if last_promo and table_exists:
            c = await db.execute("SELECT COUNT(*) as c FROM promo_code_usages WHERE promo_code_id = ?", (last_promo["id"],))
            res = await c.fetchone()
            usage_count = res["c"] if res else 0

        await update.message.reply_text(
            f"Table usages existe: {table_exists}\n"
            f"Dernier promo max_per_user: {last_promo.get('max_uses_per_user') if last_promo else 'None'}\n"
            f"Usages dans la table: {usage_count}"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    
    await update.message.reply_text("🔄 Starting manual database migrations...")
    
    from database.db import get_db
    logs = []
    
    queries = [
        ("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)", "Table 'settings'"),
        ("CREATE TABLE IF NOT EXISTS used_bep20_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_hash TEXT UNIQUE NOT NULL, order_id INTEGER, user_telegram_id INTEGER, amount REAL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'used_bep20_transactions'"),
        ("CREATE TABLE IF NOT EXISTS used_trc20_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_hash TEXT UNIQUE NOT NULL, order_id INTEGER, user_telegram_id INTEGER, amount REAL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'used_trc20_transactions'"),
        ("ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1", "Column 'orders.quantity'"),
        ("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'binance'", "Column 'orders.payment_method'"),
        ("ALTER TABLE orders ADD COLUMN promo_code_id INTEGER", "Column 'orders.promo_code_id'"),
        ("ALTER TABLE orders ADD COLUMN promo_discount REAL DEFAULT 0.0", "Column 'orders.promo_discount'"),
        ("ALTER TABLE users ADD COLUMN referred_by INTEGER", "Column 'users.referred_by'"),
        ("ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0", "Column 'users.referral_earnings'"),
        ("ALTER TABLE users ADD COLUMN referral_commission_paid REAL DEFAULT 0", "Column 'users.referral_commission_paid'"),
        ("ALTER TABLE categories ADD COLUMN is_deleted INTEGER DEFAULT 0", "Column 'categories.is_deleted'"),
        ("ALTER TABLE products ADD COLUMN is_deleted INTEGER DEFAULT 0", "Column 'products.is_deleted'"),
        ("ALTER TABLE products ADD COLUMN binance_account_id INTEGER DEFAULT NULL", "Column 'products.binance_account_id'"),
        ("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT NULL", "Column 'products.image_url'"),
        ("ALTER TABLE products ADD COLUMN telegram_file_id TEXT DEFAULT NULL", "Column 'products.telegram_file_id'"),
        ("ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT NULL", "Column 'products.custom_emoji_id'"),
        ("ALTER TABLE products ADD COLUMN sort_order INTEGER DEFAULT 0", "Column 'products.sort_order'"),
        ("ALTER TABLE products ADD COLUMN delivery_type TEXT DEFAULT 'stock'", "Column 'products.delivery_type'"),
        ("ALTER TABLE orders ADD COLUMN activation_identifier TEXT", "Column 'orders.activation_identifier'"),
        ("ALTER TABLE orders ADD COLUMN activation_status TEXT DEFAULT NULL", "Column 'orders.activation_status'"),
        ("ALTER TABLE orders ADD COLUMN activation_requested_at TIMESTAMP", "Column 'orders.activation_requested_at'"),
        ("ALTER TABLE orders ADD COLUMN activated_at TIMESTAMP", "Column 'orders.activated_at'"),
        ("CREATE TABLE IF NOT EXISTS reseller_api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, user_telegram_id INTEGER NOT NULL, name TEXT DEFAULT '', key_prefix TEXT UNIQUE NOT NULL, key_hash TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used_at TIMESTAMP)", "Table 'reseller_api_keys'"),
        ("CREATE TABLE IF NOT EXISTS reseller_order_links (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER UNIQUE NOT NULL, reseller_user_telegram_id INTEGER NOT NULL, customer_reference TEXT DEFAULT '', idempotency_key TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(reseller_user_telegram_id, idempotency_key))", "Table 'reseller_order_links'"),
        ("CREATE TABLE IF NOT EXISTS nowpayments_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, request_key TEXT UNIQUE NOT NULL, payment_id TEXT UNIQUE, provider_status TEXT DEFAULT 'creating', price_amount REAL NOT NULL, price_currency TEXT DEFAULT 'usd', pay_amount REAL, pay_currency TEXT DEFAULT 'usdtbsc', pay_address TEXT, actually_paid REAL DEFAULT 0, network TEXT, valid_until TEXT, raw_payload TEXT DEFAULT '{}', processing_error TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP, notification_claimed_at TIMESTAMP, notified_at TIMESTAMP)", "Table 'nowpayments_payments'"),
        ("CREATE TABLE IF NOT EXISTS nowpayments_wallet_topups (id INTEGER PRIMARY KEY AUTOINCREMENT, user_telegram_id INTEGER NOT NULL, request_key TEXT UNIQUE NOT NULL, payment_id TEXT UNIQUE, provider_status TEXT DEFAULT 'creating', wallet_amount REAL NOT NULL, price_amount REAL NOT NULL, price_currency TEXT DEFAULT 'usd', pay_amount REAL, pay_currency TEXT DEFAULT 'usdtbsc', pay_address TEXT, actually_paid REAL DEFAULT 0, network TEXT, valid_until TEXT, raw_payload TEXT DEFAULT '{}', processing_error TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP, notification_claimed_at TIMESTAMP, notified_at TIMESTAMP)", "Table 'nowpayments_wallet_topups'"),
        ("ALTER TABLE nowpayments_payments ADD COLUMN notification_claimed_at TIMESTAMP", "Column 'nowpayments_payments.notification_claimed_at'"),
        ("CREATE INDEX IF NOT EXISTS idx_nowpayments_order ON nowpayments_payments(order_id, created_at)", "Index 'idx_nowpayments_order'"),
        ("CREATE INDEX IF NOT EXISTS idx_nowpayments_status ON nowpayments_payments(provider_status, updated_at)", "Index 'idx_nowpayments_status'"),
        ("CREATE INDEX IF NOT EXISTS idx_nowpayments_topups_user ON nowpayments_wallet_topups(user_telegram_id, created_at)", "Index 'idx_nowpayments_topups_user'"),
        ("CREATE INDEX IF NOT EXISTS idx_nowpayments_topups_status ON nowpayments_wallet_topups(provider_status, updated_at)", "Index 'idx_nowpayments_topups_status'"),
        ("CREATE INDEX IF NOT EXISTS idx_stock_product_added ON stock_items(product_id, added_at DESC)", "Index 'idx_stock_product_added'"),
        ("CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_telegram_id, status)", "Index 'idx_orders_user_status'"),
        ("CREATE INDEX IF NOT EXISTS idx_orders_binance_id ON orders(binance_order_id)", "Index 'idx_orders_binance_id'"),
        ("CREATE INDEX IF NOT EXISTS idx_reseller_keys_user ON reseller_api_keys(user_telegram_id)", "Index 'idx_reseller_keys_user'"),
        ("CREATE INDEX IF NOT EXISTS idx_reseller_keys_prefix ON reseller_api_keys(key_prefix)", "Index 'idx_reseller_keys_prefix'"),
        ("CREATE INDEX IF NOT EXISTS idx_reseller_orders_user ON reseller_order_links(reseller_user_telegram_id, created_at)", "Index 'idx_reseller_orders_user'"),
        ("CREATE TABLE IF NOT EXISTS binance_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, uid TEXT NOT NULL, api_key TEXT DEFAULT '', api_secret TEXT DEFAULT '', is_default INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'binance_accounts'"),
        ("UPDATE orders SET binance_order_id = (SELECT transaction_id FROM used_binance_transactions WHERE used_binance_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_binance_transactions WHERE order_id IS NOT NULL)", "Retroactive Binance Pay IDs"),
        ("UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_bep20_transactions WHERE used_bep20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_bep20_transactions WHERE order_id IS NOT NULL)", "Retroactive BEP20 Tx Hashes"),
        ("UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_trc20_transactions WHERE used_trc20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_trc20_transactions WHERE order_id IS NOT NULL)", "Retroactive TRC20 Tx Hashes"),
        ("ALTER TABLE promo_codes ADD COLUMN max_uses_per_user INTEGER DEFAULT 0", "Column 'promo_codes.max_uses_per_user'"),
        ("CREATE TABLE IF NOT EXISTS promo_code_usages (id INTEGER PRIMARY KEY AUTOINCREMENT, promo_code_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, usage_count INTEGER DEFAULT 0, last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(promo_code_id, user_telegram_id))", "Table 'promo_code_usages'"),
        ("ALTER TABLE promo_codes ADD COLUMN applicable_product_ids TEXT DEFAULT NULL", "Column 'promo_codes.applicable_product_ids'"),
        ("ALTER TABLE promo_codes ADD COLUMN max_qty_per_order INTEGER DEFAULT 0", "Column 'promo_codes.max_qty_per_order'"),
    ]
    
    for sql, name in queries:
        try:
            mig_db = await get_db()
            await mig_db.execute(sql)
            await mig_db.commit()
            logs.append(f"✅ {name} added/verified.")
        except Exception as e:
            logs.append(f"⚠️ {name} skipped: {e}")
        finally:
            try:
                await mig_db.close()
            except Exception:
                pass
                
    # ── Mises à jour rétroactives des Order IDs Binance (18 chiffres) ──
    # 1. Nettoyage des formats avec slash (ex: 'P_... / 18_chiffres') pour ne garder que la partie à 18 chiffres
    try:
        mig_db = None
        mig_db = await get_db()
        cursor = await mig_db.execute("SELECT id, binance_order_id FROM orders WHERE binance_order_id LIKE '%/%'")
        rows = await cursor.fetchall()
        cleaned_count = 0
        for r in rows:
            parts = [p.strip() for p in r["binance_order_id"].split("/")]
            numeric_part = next((p for p in parts if p.isdigit() and len(p) >= 15), None)
            if numeric_part:
                await mig_db.execute("UPDATE orders SET binance_order_id = ? WHERE id = ?", (numeric_part, r["id"]))
                cleaned_count += 1
        if cleaned_count > 0:
            await mig_db.commit()
            logs.append(f"✅ Nettoyage de {cleaned_count} commande(s) au format slash.")
    except Exception as e:
        logs.append(f"⚠️ Échec du nettoyage des formats slash : {e}")
    finally:
        if mig_db: await mig_db.close()

    # 3. Interrogation de l'API SAPI pour les autres commandes contenant uniquement un Prepay ID (commençant par 'P_')
    try:
        mig_db = None
        from services.binance_verify import verify_payment
        mig_db = await get_db()
        cursor = await mig_db.execute(
            "SELECT id, product_id, binance_order_id, amount_usd FROM orders WHERE status = 'COMPLETED' AND binance_order_id LIKE 'P_%'"
        )
        orders_to_update = await cursor.fetchall()
        updated_count = 0
        
        for o in orders_to_update:
            p_id = o["product_id"]
            prepay_id = o["binance_order_id"]
            amount = float(o["amount_usd"])
            
            # Récupération des clés API associées au produit
            api_key_to_use = None
            api_secret_to_use = None
            if p_id:
                from database.models import get_product
                product = await get_product(p_id)
                if product and product.get("binance_account_id"):
                    from database.models import get_binance_account
                    acc = await get_binance_account(product["binance_account_id"])
                    if acc:
                        api_key_to_use = acc.get("api_key")
                        api_secret_to_use = acc.get("api_secret")
            
            # Requête API Binance SAPI pour récupérer le véritable orderId
            result = await verify_payment(prepay_id, amount, api_key=api_key_to_use, api_secret=api_secret_to_use)
            if result.get("verified") and result.get("transaction"):
                tx = result["transaction"]
                order_id_18 = tx.get("orderId", "")
                if order_id_18 and order_id_18.isdigit():
                    await mig_db.execute("UPDATE orders SET binance_order_id = ? WHERE id = ?", (order_id_18, o["id"]))
                    updated_count += 1
                    
        if updated_count > 0:
            await mig_db.commit()
            logs.append(f"✅ Mise à jour de {updated_count} commande(s) passée(s) avec leur Order ID SAPI.")
    except Exception as e:
        logs.append(f"⚠️ Échec de la récupération des Order IDs via SAPI : {e}")
    finally:
        if mig_db: await mig_db.close()

    try:
        await update.message.reply_text("\n".join(logs))
    except Exception:
        await update.message.reply_text("❌ Completed with some errors, check logs.")




# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────

def main() -> None:
    """Build the Application, register handlers, and start in webhook or polling mode."""
    global tg_app, _service_ready

    _service_ready = False

    from services.process_watchdog import enable_fault_diagnostics
    enable_fault_diagnostics()

    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    _validate_runtime_security(webhook_url)

    # In webhook mode, disable the built-in Updater (we handle updates via FastAPI)
    builder = Application.builder().token(BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).pool_timeout(30.0).post_init(post_init).post_shutdown(post_shutdown)
    if webhook_url:
        builder = builder.updater(None)
    app = builder.build()

    tg_app = app

    # ── Global Error Handler ─────────────
    from telegram.error import BadRequest

    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and handle specific harmless errors."""
        if isinstance(context.error, BadRequest):
            err_text = str(context.error).lower()
            if (
                "message is not modified" in err_text
                or "query is too old" in err_text
                or "query id is invalid" in err_text
            ):
                # Harmless error caused by users spamming inline buttons that don't change the message content
                return

        _record_webhook_handler_error()
        logger.error("Exception while handling an update:", exc_info=context.error)

    app.add_error_handler(global_error_handler)

    # ── Anti-spam middleware (runs before everything) ─────────────
    from utils.antispam import is_spam, should_warn, get_cooldown_remaining, SPAM_MESSAGES, WARN_MESSAGES, check_and_mark_cooldown_warned

    async def _antispam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global anti-spam pre-check. Blocks spamming users."""
        user = update.effective_user
        if not user:
            return
        user_id = user.id

        # Global Ban Check
        try:
            from database.models import is_user_banned
            if await is_user_banned(user_id):
                try:
                    if update.callback_query:
                        await update.callback_query.answer()
                except Exception:
                    pass
                raise ApplicationHandlerStop()
        except ApplicationHandlerStop:
            raise
        except Exception as exc:
            logger.warning("Ban check failed closed for user %s: %s", user_id, exc)
            try:
                if update.callback_query:
                    await update.callback_query.answer(
                        "Service temporarily unavailable. Please retry.",
                        show_alert=True,
                    )
                elif update.message:
                    await update.message.reply_text(
                        "Service temporarily unavailable. Please retry."
                    )
            except Exception:
                pass
            raise ApplicationHandlerStop()

        # Check if they clicked a referral link and store it in context.user_data
        if update.message and update.message.text:
            text = update.message.text
            if text.startswith("/start ref_"):
                try:
                    ref_id = int(text.split("_")[1])
                    if context.user_data is not None:
                        context.user_data["referred_by"] = ref_id
                except (ValueError, IndexError):
                    pass

        # Forced Channel Subscription Check
        import time
        from config import REQUIRED_CHANNEL, ADMIN_IDS
        if REQUIRED_CHANNEL and user_id not in ADMIN_IDS:
            is_sub_callback = False
            if update.callback_query and update.callback_query.data == "check_sub":
                is_sub_callback = True

            if not is_sub_callback:
                now = time.time()
                cached_time = context.user_data.get("sub_verified_at", 0) if context.user_data else 0
                if (now - cached_time) < SUBSCRIPTION_CACHE_SECONDS:
                    is_subscribed = True
                else:
                    is_subscribed = False
                    try:
                        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
                        if member.status in ["creator", "administrator", "member", "restricted"]:
                            is_subscribed = True
                            if context.user_data is not None:
                                context.user_data["sub_verified_at"] = now
                    except Exception as exc:
                        logger.warning(
                            "Subscription verification failed closed for user %s: %s",
                            user_id,
                            exc,
                        )

                if not is_subscribed:
                    lang = "fr"
                    try:
                        from database.models import get_user_lang
                        lang = await get_user_lang(user_id)
                    except Exception:
                        pass

                    sub_msg = {
                        "fr": (
                            "📢 <b>Abonnement requis</b>\n\n"
                            "Pour utiliser ce bot, vous devez d'abord rejoindre notre canal Telegram.\n\n"
                            "Rejoignez-nous ici : https://t.me/Batmanstore2\n\n"
                            "Une fois rejoint, cliquez sur le bouton ci-dessous pour valider."
                        ),
                        "en": (
                            "📢 <b>Subscription Required</b>\n\n"
                            "To use this bot, you must first join our Telegram channel.\n\n"
                            "Join here: https://t.me/Batmanstore2\n\n"
                            "Once joined, click the button below to verify."
                        ),
                        "ar": (
                            "📢 <b>الاشتراك مطلوب</b>\n\n"
                            "لاستخدام هذا البوت، يجب عليك أولاً الانضمام إلى قناتنا على Telegram.\n\n"
                            "انضم هنا: https://t.me/Batmanstore2\n\n"
                            "بمجرد الانضمام، انقر فوق الزر أدناه للتحقق."
                        )
                    }

                    btn_text = {
                        "fr": "✅ Vérifier mon abonnement",
                        "en": "✅ Verify my subscription",
                        "ar": "✅ التحقق من الاشتراك"
                    }

                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 Rejoindre le Canal", url="https://t.me/Batmanstore2")],
                        [InlineKeyboardButton(btn_text.get(lang, btn_text["fr"]), callback_data="check_sub")]
                    ])

                    try:
                        if update.callback_query:
                            await update.callback_query.answer()
                            await update.callback_query.message.reply_text(sub_msg.get(lang, sub_msg["fr"]), reply_markup=markup, parse_mode="HTML")
                        elif update.message:
                            await update.message.reply_text(sub_msg.get(lang, sub_msg["fr"]), reply_markup=markup, parse_mode="HTML")
                    except Exception:
                        pass
                    raise ApplicationHandlerStop()

        if is_spam(user_id):
            if not check_and_mark_cooldown_warned(user_id):
                remaining = get_cooldown_remaining(user_id)
                lang = "fr"
                try:
                    from database.models import get_user_lang
                    lang = await get_user_lang(user_id)
                except Exception:
                    pass
                msg = SPAM_MESSAGES.get(lang, SPAM_MESSAGES["fr"]).format(sec=remaining)

                try:
                    if update.callback_query:
                        await update.callback_query.answer(msg, show_alert=True)
                    elif update.message:
                        await update.message.reply_text(msg)
                except Exception:
                    pass
            else:
                try:
                    if update.callback_query:
                        await update.callback_query.answer()
                except Exception:
                    pass
            raise ApplicationHandlerStop()

        if should_warn(user_id):
            lang = "fr"
            try:
                from database.models import get_user_lang
                lang = await get_user_lang(user_id)
            except Exception:
                pass
            warn = WARN_MESSAGES.get(lang, WARN_MESSAGES["fr"])
            try:
                # Callback handlers acknowledge their own query. Answering here
                # and then continuing causes Telegram's "query id is invalid".
                if update.message:
                    await update.message.reply_text(warn)
            except Exception:
                pass

    app.add_handler(TypeHandler(Update, _antispam_check), group=-1)

    # ── Conversation handlers (added first for priority) ─────────────
    app.add_handler(get_admin_conversation_handler(), group=0)
    app.add_handler(get_payment_conversation_handler(), group=1)
    app.add_handler(get_support_conversation_handler(), group=2)
    app.add_handler(wallet_conversation_handler(), group=3)

    # ── Command handlers ─────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("run_migrations", run_migrations_command))
    app.add_handler(CommandHandler("getemoji", get_emoji_command))

    # ── Callback query handlers ──────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_check_sub, pattern=r"^check_sub$"))
    app.add_handler(CallbackQueryHandler(download_txt_delivery, pattern=r"^dl_txt:"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(change_language, pattern=r"^change_lang$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(show_products_list, pattern=r"^menu_buy$"))
    app.add_handler(CallbackQueryHandler(show_products_list, pattern=r"^back_products$"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern=r"^prod:"))
    app.add_handler(CallbackQueryHandler(notify_product_restock, pattern=r"^notify_stock:"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern=r"^menu_profile$"))
    app.add_handler(CallbackQueryHandler(show_referrals, pattern=r"^show_referrals$"))
    app.add_handler(CallbackQueryHandler(view_referrals_list, pattern=r"^view_referrals_list$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern=r"^menu_history$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern=r"^hist_page:"))
    app.add_handler(CallbackQueryHandler(show_order_detail, pattern=r"^order:"))
    app.add_handler(CallbackQueryHandler(reseller_api_menu, pattern=r"^menu_api$"))
    app.add_handler(CallbackQueryHandler(generate_reseller_api_key, pattern=r"^api_generate_key$"))
    app.add_handler(CallbackQueryHandler(confirm_generate_reseller_api_key, pattern=r"^api_confirm_generate_key$"))
    app.add_handler(CallbackQueryHandler(refresh_products, pattern=r"^refresh_prods$"))
    app.add_handler(CallbackQueryHandler(support_menu, pattern=r"^menu_support$"))
    app.add_handler(CallbackQueryHandler(show_my_tickets, pattern=r"^my_tickets$"))
    app.add_handler(CallbackQueryHandler(show_ticket_detail, pattern=r"^ticket:"))
    app.add_handler(CallbackQueryHandler(admin_complete_activation, pattern=r"^adm_activate_order:"))
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern=r"^menu_wallet$"))
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern=r"^back_wallet$"))
    app.add_handler(CallbackQueryHandler(wallet_history, pattern=r"^wallet_history$"))
    app.add_handler(CallbackQueryHandler(wallet_noop, pattern=r"^wallet_noop$"))
    app.add_handler(CallbackQueryHandler(show_game_menu, pattern=r"^menu_game$"))
    app.add_handler(CallbackQueryHandler(claim_game_coins, pattern=r"^game_claim$"))
    app.add_handler(CallbackQueryHandler(show_game_match, pattern=r"^game_match:"))
    app.add_handler(CallbackQueryHandler(choose_game_outcome, pattern=r"^game_pick:"))
    app.add_handler(CallbackQueryHandler(choose_game_amount, pattern=r"^game_amount:"))
    app.add_handler(CallbackQueryHandler(confirm_game_bet, pattern=r"^game_confirm:"))
    app.add_handler(CallbackQueryHandler(show_my_game_bets, pattern=r"^game_my_bets$"))
    app.add_handler(CallbackQueryHandler(show_game_leaderboard, pattern=r"^game_leaderboard$"))

    # ── Reply keyboard text handlers ─────────────────────────────
    app.add_handler(MessageHandler(filters.Regex(r"(?i)(Produits|Products|المنتجات|产品)"), show_products_list))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)(Support|الدعم|客服)"), support_menu_text))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)(Commencer|Start|ابدأ|开始)"), start_command))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)(Langue|Language|اللغة|语言)"), change_language))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_activation_identifier), group=4)

    # ── Decide: Webhook (production) or Polling (local dev) ──────
    port = int(os.environ.get("PORT", 8000))

    if webhook_url:
        # ── WEBHOOK MODE (Railway production) ────────────────────
        import asyncio

        async def _setup_and_run():
            """Initialize the bot, set webhook, and run FastAPI with connection retries."""
            global webhook_update_queue, webhook_worker_tasks, webhook_worker_manager, _service_ready
            
            loop = asyncio.get_running_loop()
            from concurrent.futures import ThreadPoolExecutor
            loop.set_default_executor(ThreadPoolExecutor(max_workers=THREAD_WORKERS))

            # Bind the HTTP port before Telegram and Turso finish initializing.
            # Railway can then probe /health instead of seeing a closed port.
            config = uvicorn.Config(api, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            server_task = asyncio.create_task(server.serve())
            await asyncio.sleep(0)


            for attempt in range(1, 6):
                try:
                    logger.info("⚡ Initializing Telegram bot (attempt %d/5)...", attempt)
                    await app.initialize()
                    await post_init(app)
                    await app.start()
                    break
                except Exception as err:
                    if attempt == 5:
                        logger.error("❌ Failed to initialize Telegram bot after 5 attempts: %s", err)
                        raise
                    logger.warning("⚠️ Bot initialization failed (%s). Retrying in 4s...", err)
                    await asyncio.sleep(4)

            webhook_update_queue = asyncio.Queue(maxsize=WEBHOOK_QUEUE_MAX)
            from services.webhook_autoscaler import AutoscaleConfig, WebhookWorkerManager
            from database.jobs import (
                get_recent_webhook_autoscale_decision,
                get_webhook_autoscale_settings,
                save_webhook_autoscale_decision,
            )

            autoscale_config = AutoscaleConfig.from_env()
            autoscale_settings = await get_webhook_autoscale_settings()
            environment_min_workers = autoscale_config.min_workers
            environment_max_workers = autoscale_config.max_workers
            autoscale_config.min_workers = max(
                environment_min_workers,
                int(autoscale_settings.get("min_workers") or environment_min_workers),
            )
            autoscale_config.max_workers = min(
                environment_max_workers,
                max(
                    autoscale_config.min_workers,
                    int(autoscale_settings.get("max_workers") or environment_max_workers),
                ),
            )
            autoscale_config.initial_workers = autoscale_config.clamp(
                autoscale_config.initial_workers
            )
            webhook_worker_manager = WebhookWorkerManager(
                lambda worker_id, stop_event: _webhook_update_worker(
                    app, worker_id, stop_event
                ),
                _webhook_performance_snapshot,
                config=autoscale_config,
                persist_decision=save_webhook_autoscale_decision,
                worker_is_active=lambda worker_id: _webhook_worker_states.get(worker_id) == "ACTIVE",
            )
            webhook_worker_manager.mode = (
                str(autoscale_settings.get("mode") or "auto")
                if autoscale_config.enabled
                else "off"
            )
            webhook_worker_manager.observe_only = bool(
                autoscale_settings.get("observe_only", autoscale_config.observe_only)
            )
            initial_workers = autoscale_config.initial_workers
            if webhook_worker_manager.mode == "manual":
                initial_workers = autoscale_config.clamp(
                    int(autoscale_settings.get("manual_workers") or initial_workers)
                )
            elif webhook_worker_manager.mode == "auto" and not webhook_worker_manager.observe_only:
                recent_decision = await get_recent_webhook_autoscale_decision(300)
                if recent_decision:
                    restored = autoscale_config.clamp(
                        int(recent_decision.get("workers_after") or initial_workers)
                    )
                    if (
                        restored >= autoscale_config.max_workers
                        and autoscale_config.max_workers > autoscale_config.min_workers
                    ):
                        restored = autoscale_config.max_workers - 1
                    initial_workers = restored
            await webhook_worker_manager.start(initial_workers)
            webhook_worker_tasks = webhook_worker_manager.tasks
            logger.info(
                "Webhook workers started: %d mode=%s observe_only=%s range=%d-%d",
                webhook_worker_manager.worker_count,
                webhook_worker_manager.mode,
                webhook_worker_manager.observe_only,
                autoscale_config.min_workers,
                autoscale_config.max_workers,
            )

            wh = f"{webhook_url}/webhook"
            for attempt in range(1, 6):
                try:
                    await app.bot.set_webhook(
                        url=wh,
                        secret_token=WEBHOOK_SECRET or None,
                        drop_pending_updates=DROP_PENDING_UPDATES,
                    )
                    logger.info("🔗 Webhook set successfully: %s", wh)
                    break
                except Exception as err:
                    if attempt == 5:
                        logger.error("❌ Failed to set webhook after 5 attempts: %s", err)
                        raise
                    logger.warning("⚠️ Webhook setup failed (%s). Retrying in 4s...", err)
                    await asyncio.sleep(4)

            _service_ready = True
            watchdog_process = None
            try:
                from services.process_watchdog import (
                    WatchdogConfig,
                    start_process_watchdog,
                )
                watchdog_process = start_process_watchdog(
                    os.getpid(),
                    port,
                    WatchdogConfig.from_env(),
                )
            except Exception as exc:
                # A watchdog setup issue must not prevent the bot from serving.
                logger.exception("Could not start process watchdog: %s", exc)

            try:
                await server_task
                if not server.should_exit:
                    raise RuntimeError(
                        "Uvicorn stopped unexpectedly; exiting so Railway can restart the service"
                    )
            finally:
                _service_ready = False
                from services.process_watchdog import stop_process_watchdog
                stop_process_watchdog(watchdog_process)
                # Do NOT delete the webhook on shutdown. In a rolling deployment,
                # the old container shutting down would delete the webhook set by the new container.
                if webhook_worker_manager is not None:
                    await webhook_worker_manager.stop()
                else:
                    for task in webhook_worker_tasks:
                        task.cancel()
                    if webhook_worker_tasks:
                        await asyncio.gather(*webhook_worker_tasks, return_exceptions=True)
                await post_shutdown(app)
                await app.stop()
                await app.shutdown()

        logger.info("🚀 Bot starting in WEBHOOK mode (zero polling, saves credits)…")
        asyncio.run(_setup_and_run())
    else:
        # ── POLLING MODE (local development) ─────────────────────
        def _start_api_bg():
            def run_server():
                logger.info("🌐 REST API server starting on port %s", port)
                uvicorn.run(api, host="0.0.0.0", port=port, log_level="warning")
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()

        _start_api_bg()
        logger.info("🚀 Bot starting in POLLING mode (local dev)…")
        logger.info("💡 Set WEBHOOK_URL env var for production webhook mode")
        app.run_polling(drop_pending_updates=DROP_PENDING_UPDATES)


@api.get("/api/export/transactions", dependencies=[Depends(verify_api_key)])
async def api_export_transactions(start_date: str, end_date: str):
    from database.models import get_transactions_for_export
    try:
        transactions = await get_transactions_for_export(start_date, end_date)
        return transactions
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    main()




