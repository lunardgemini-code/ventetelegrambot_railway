"""
VenteBot — Main entry point.

Wires all handlers together and starts the bot using python-telegram-bot v21+ async API.
Includes a FastAPI REST API with health-check for Railway deployment.
"""

import warnings
from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

import hmac
import asyncio
import logging
import os
import threading
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Depends, status, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import httpx
import time

_stats_cache = {}
_stats_cache_ttl = 60

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

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers.admin import admin_complete_activation, get_admin_conversation_handler
from handlers.history import show_history, show_order_detail
from handlers.payment import (
    get_payment_conversation_handler,
    initiate_purchase,
    download_txt_delivery,
    receive_activation_identifier,
)
from handlers.products import (
    refresh_products,
    show_product_detail,
    show_products_list,
)
from handlers.profile import show_profile, show_referrals
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
from utils.locales import t

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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

# Enable CORS for browser access — restrict origins in production
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["*"]
api.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "X-Reseller-Key", "Content-Type"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
)

# ── Serve dashboard static files directly from Railway ──
import pathlib
_dashboard_dir = pathlib.Path(__file__).parent / "dashboard"
if _dashboard_dir.is_dir():
    @api.get("/dashboard")
    @api.get("/dashboard/")
    async def serve_dashboard_index():
        return FileResponse(str(_dashboard_dir / "index.html"), media_type="text/html")
    api.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir)), name="dashboard")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
if not ADMIN_API_KEY:
    import secrets
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.critical("⚠️ ADMIN_API_KEY not set! Generated temporary key. Set ADMIN_API_KEY env var in production! (Key starts with %s)", ADMIN_API_KEY[:4])

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


RESELLER_API_RATE_LIMIT = _env_int("RESELLER_API_RATE_LIMIT", 60)
RESELLER_API_RATE_WINDOW = _env_int("RESELLER_API_RATE_WINDOW", 60)
THREAD_WORKERS = _env_int("THREAD_WORKERS", 32, minimum=4)
_reseller_rate_buckets: dict[str, dict[str, int]] = {}


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
    now = int(time.time())
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


async def verify_api_key(x_api_key: str = Header(None)):
    """Dependency to check the custom X-API-Key header using constant-time comparison."""
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key


async def verify_reseller_key(
    response: Response,
    x_reseller_key: str = Header(None),
    x_api_key: str = Header(None),
):
    """Authenticate reseller API calls with a limited reseller key."""
    reseller_key = x_reseller_key or x_api_key
    if not reseller_key:
        _raise_reseller_error(status.HTTP_401_UNAUTHORIZED, "MISSING_API_KEY", "Missing reseller API key")
    from database.models import get_reseller_by_api_key
    reseller = await get_reseller_by_api_key(reseller_key)
    if not reseller:
        _raise_reseller_error(status.HTTP_401_UNAUTHORIZED, "INVALID_API_KEY", "Invalid reseller API key")
    rate_headers = _check_reseller_rate_limit(str(reseller.get("id") or reseller.get("key_prefix") or reseller["user_telegram_id"]))
    for key, value in rate_headers.items():
        response.headers[key] = value
    return reseller


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


@api.get("/health")
async def health_check():
    """Anonymous endpoint for Railway health check."""
    return {"status": "ok", "bot": "running"}


def _reseller_openapi_schema() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "VenteBot Reseller API",
            "version": "1.0.0",
            "description": (
                "Public API for connecting a reseller bot to VenteBot. "
                "Purchases debit the reseller account wallet.\n\n"
                "Authenticate with X-Reseller-Key, or X-API-Key for compatibility with common reseller integrations.\n\n"
                f"Rate limit: {RESELLER_API_RATE_LIMIT} requests per {RESELLER_API_RATE_WINDOW} seconds per API key. "
                "Responses include X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers."
            ),
        },
        "servers": [{"url": "/"}],
        "tags": [
            {"name": "Account", "description": "Reseller account and wallet balance"},
            {"name": "Products", "description": "Catalog and pricing"},
            {"name": "Orders", "description": "Order creation and tracking"},
            {"name": "Wallet", "description": "Reseller wallet history"},
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
                        "warranty_days": {"type": "integer", "example": 30},
                        "delivery_type": {"type": "string", "enum": ["stock", "activation"], "example": "activation"},
                        "stock": {"type": "integer", "nullable": True, "example": None},
                        "price_tiers": {"type": "array", "items": {"$ref": "#/components/schemas/PriceTier"}},
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
                                "total": {"type": "number", "format": "float", "example": 5.0},
                                "delivery_type": {"type": "string", "example": "activation"},
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
                            "description": "Unique value per purchase attempt to prevent duplicate orders.",
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
                        "status": {"type": "string", "example": "AWAITING_ACTIVATION"},
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
                        }
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
                    "description": "Debits the reseller wallet. Use idempotency_key to prevent duplicate purchases.",
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
                                            "balance_after": {"type": "number", "format": "float", "example": 37.5},
                                            "unit_price": {"type": "number", "format": "float", "example": 5.0},
                                            "total": {"type": "number", "format": "float", "example": 5.0},
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
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200}},
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
                                            "transactions": {"type": "array", "items": {"type": "object"}}
                                        },
                                    }
                                }
                            },
                        },
                        "429": {"description": "Rate limit exceeded", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
        },
    }


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


@api.get("/api/reseller/products")
async def api_reseller_products(lang: str = "en", reseller: dict = Depends(verify_reseller_key)):
    from database.models import get_all_products, get_all_stock_counts, get_price_tiers
    try:
        lang = lang if lang in {"en", "fr", "ar", "zh", "vi", "ru"} else "en"
        products = await get_all_products()
        stock_counts = await get_all_stock_counts()
        result = []
        for p in products:
            if not p.get("is_active", 1) or p.get("is_deleted", 0):
                continue
            desc = p.get(f"description_{lang}") if lang in {"fr", "ar", "zh", "vi", "ru"} else p.get("description")
            if not desc:
                desc = p.get("description", "")
            tiers = await get_price_tiers(p["id"])
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
                    {"min_qty": t_item["min_qty"], "max_qty": t_item["max_qty"], "price_usd": float(t_item["price_usd"])}
                    for t_item in tiers
                ],
            })
        return _reseller_success(products=result)
    except Exception as exc:
        logger.error("API error reseller products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/reseller/quote")
async def api_reseller_quote(data: ResellerQuoteRequest, reseller: dict = Depends(verify_reseller_key)):
    from database.models import quote_reseller_order
    try:
        quote = await quote_reseller_order(data.product_id, data.quantity)
        return _reseller_success(quote=quote, wallet_balance=float(reseller.get("wallet_balance") or 0))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("API error reseller quote: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/reseller/orders")
async def api_reseller_create_order(data: ResellerCreateOrderRequest, reseller: dict = Depends(verify_reseller_key)):
    from database.models import create_reseller_order
    try:
        result = await create_reseller_order(
            reseller_user_telegram_id=reseller["user_telegram_id"],
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
            total=result.get("total"),
            order=_api_order_payload(order),
        )
    except ValueError as exc:
        msg = str(exc)
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
        await submit_activation_identifier(order_id, identifier)
        try:
            await notify_admins(
                "<b>Nouvelle activation revendeur</b>\n\n"
                f"Commande: #{order_id}\n"
                f"Revendeur: <code>{reseller['user_telegram_id']}</code>\n"
                f"Produit: {escape_html(order.get('product_name') or str(order.get('product_id')))} x{order.get('quantity', 1)}\n"
                f"Identifiant: <code>{escape_html(identifier)}</code>"
            )
        except Exception:
            pass
        updated = await get_reseller_order(reseller["user_telegram_id"], order_id)
        return _reseller_success(status="ok", order=_api_order_payload(updated))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error reseller activation identifier: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
            balance = float(balance_str) if balance_str else 0.0
        else:
            # Sum all balances
            methods = ["binance", "bep20", "trc20", "wallet"]
            for m in methods:
                b_str = await get_setting(f"finance_bot_balance_{m}")
                if b_str:
                    balance += float(b_str)
        
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
async def api_adjust_finance(data: dict):
    from database.models import get_setting, set_setting
    try:
        amount = float(data.get("amount", 0))
        method = data.get("method")
        
        if not method or method == "all":
            raise HTTPException(status_code=400, detail="Veuillez sélectionner une méthode spécifique (Binance, BEP20, etc.) pour ajuster le solde.")
            
        setting_key = f"finance_bot_balance_{method}"
        balance_str = await get_setting(setting_key)
        balance = float(balance_str) if balance_str else 0.0
        
        new_balance = balance + amount
        if new_balance < 0:
            new_balance = 0.0
            
        await set_setting(setting_key, str(new_balance))
        return {"status": "success", "new_balance": new_balance}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def api_get_stats():
    current_time = time.time()
    if "stats" in _stats_cache and current_time - _stats_cache["stats"]["time"] < _stats_cache_ttl:
        return _stats_cache["stats"]["data"]

    from database.models import get_stats, get_all_users, get_all_products, get_all_stock_counts
    try:
        stats_30 = await get_stats(days=30)
        users = await get_all_users()
        products = await get_all_products()
        stock_counts = await get_all_stock_counts()

        stock_summary = [{
            "id": p["id"],
            "name": p["name"],
            "emoji": p["emoji"],
            "stock": stock_counts.get(p["id"], 0)
        } for p in products]

        response_data = {
            "total_users": len(users),
            "total_orders": stats_30.get("total_orders", 0),
            "completed_orders": stats_30.get("completed_orders", 0),
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


@api.post("/api/products", dependencies=[Depends(verify_api_key)])
async def api_create_product(data: dict):
    from database.models import add_product, get_categories, add_category
    try:
        if "price_usd" not in data or "name" not in data:
            raise HTTPException(status_code=400, detail="Missing required fields: name, price_usd")
            
        # Auto-create a default category if none exists (categories hidden from UI)
        cats = await get_categories()
        if not cats:
            cat_id = await add_category(name="Produits", emoji="📦", description="Catégorie par défaut")
        else:
            cat_id = cats[0]["id"]

        price = float(data["price_usd"])
        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be positive")
        warranty = int(data.get("warranty_days", 0))
        if warranty < 0:
            raise HTTPException(status_code=400, detail="Warranty days cannot be negative")

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
        return {"status": "updated", "count": len(tiers)}
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
        return {"status": "reordered"}
    except Exception as exc:
        logger.error("API error reorder products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if db is not None:
            await db.close()

@api.put("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_update_product(product_id: int, data: dict):
    from database.models import update_product
    try:
        allowed = {"name", "price_usd", "emoji", "custom_emoji_id", "warranty_days", "description", "description_fr", "description_ar", "description_zh", "description_vi", "description_ru", "is_active", "binance_account_id", "image_url", "delivery_type", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "activation_message_vi", "activation_message_ru", "confirmation_message", "confirmation_message_fr", "confirmation_message_ar", "confirmation_message_zh", "confirmation_message_vi", "confirmation_message_ru"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        if "price_usd" in updates:
            updates["price_usd"] = float(updates["price_usd"])
        if "warranty_days" in updates:
            updates["warranty_days"] = int(updates["warranty_days"])
        await update_product(product_id, **updates)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_product(product_id: int):
    from database.models import delete_product
    try:
        await delete_product(product_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/translate", dependencies=[Depends(verify_api_key)])
async def api_translate(data: dict):
    import os
    import json
    import httpx
    
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text to translate")
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY non configurée")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
    prompt = (
        "Translate the following product description into French, Arabic, Chinese, Vietnamese, and Russian. "
        "Return a valid JSON object with the exact keys: 'fr', 'ar', 'zh', 'vi', 'ru'. "
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
                url,
                json=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            )
            if response.status_code != 200:
                logger.error("Gemini API HTTP %d", response.status_code)
                raise HTTPException(status_code=502, detail="Erreur de traduction (service indisponible)")
            
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


@api.get("/api/fix-db", dependencies=[Depends(verify_api_key)])
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
    for col in cols:
        try:
            await db.execute(f"ALTER TABLE products ADD COLUMN {col} TEXT DEFAULT ''")
            await db.commit()
            results.append(f"Added {col}")
        except Exception as e:
            results.append(f"Skipped {col}: already exists")
    try:
        await db.close()
    except Exception:
        pass
    return {"status": "done", "results": results}

# ── Binance Accounts Endpoints ──

@api.get("/api/binance-accounts", dependencies=[Depends(verify_api_key)])
async def api_get_binance_accounts():
    from database.models import get_binance_accounts
    try:
        accounts = await get_binance_accounts()
        return accounts
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
            if order_status not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED"):
                raise HTTPException(status_code=409, detail=f"Order cannot be confirmed from status {order_status}")
            await update_order_status(order_id, "AWAITING_ACTIVATION_INFO", payment_method=order.get("payment_method") or "manual")
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

        if order_status not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED"):
            raise HTTPException(status_code=409, detail=f"Order cannot be confirmed from status {order_status}")

        delivered = await deliver_order(order_id, order.get("product_id"))

        if not delivered:
            raise HTTPException(status_code=409, detail="Insufficient stock for this order")

        await update_order_status(order_id, "COMPLETED")

        if delivered:
            product = await get_product(order.get("product_id"))
            warranty_days = product.get("warranty_days", 0) if product else 0
            
            # Notify user
            try:
                from utils.locales import t
                user_lang = await get_user_lang(order["user_telegram_id"])
                accounts_text = "\n".join(f"🔑 <code>{escape_html(item['account_data'])}</code>" for item in delivered)
                
                if tg_app:
                    await tg_app.bot.send_message(
                        chat_id=order["user_telegram_id"],
                        text=f"{t('payment_confirmed', user_lang)}\n\n"
                             f"{t('your_account', user_lang)}\n"
                             f"{accounts_text}\n\n"
                             f"{t('warranty_lbl', user_lang).format(days=warranty_days)}\n"
                             f"{t('save_info', user_lang)}\n\n"
                             f"{t('thank_you', user_lang)}",
                        parse_mode="HTML"
                    )
            except Exception as notify_exc:
                logger.warning("Failed to notify user via API: %s", notify_exc)

            return {"status": "confirmed_and_delivered"}
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
async def api_reply_ticket(ticket_id: int, data: dict):
    from database.models import get_ticket, reply_ticket, get_user_lang
    try:
        ticket = await get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        reply_text = data["reply_text"]
        await reply_ticket(ticket_id, reply_text)
        
        # Notify user
        try:
            from utils.locales import t
            user_lang = await get_user_lang(ticket["user_telegram_id"])
            global tg_app
            if tg_app:
                await tg_app.bot.send_message(
                    chat_id=ticket["user_telegram_id"],
                    text=f"{t('ticket_replied', user_lang).format(id=ticket_id)}\n\n{escape_html(reply_text)}",
                    parse_mode="HTML"
                )
        except Exception as notify_exc:
            logger.warning("Failed to notify user reply via API: %s", notify_exc)
            
        return {"status": "replied"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/stock", dependencies=[Depends(verify_api_key)])
async def api_get_product_stock(product_id: int):
    from database.models import get_stock_items_for_product
    try:
        items = await get_stock_items_for_product(product_id)
        return items
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
                global tg_app
                if tg_app and tg_app.bot:
                    # Run in background tasks to not block API response
                    import asyncio
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
        VALID_STATUSES = {"PENDING", "COMPLETED", "CANCELLED", "AWAITING_PAYMENT", "AWAITING_ACTIVATION_INFO", "AWAITING_ACTIVATION", "TOPUP"}
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
    from database.models import update_order_status
    try:
        await update_order_status(order_id, "CANCELLED")
        return {"status": "cancelled"}
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

        await update_order_status(
            order_id,
            "COMPLETED",
            activation_status="done",
            activated_at=datetime.utcnow().isoformat(),
        )

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
    from database.db import get_db
    try:
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT id, user_telegram_id FROM orders 
                   WHERE status IN ('PENDING', 'AWAITING_PAYMENT')
                     AND created_at <= datetime('now', '-5 minutes')"""
            )
            stale_orders = await cursor.fetchall()
            count = 0
            
            if stale_orders:
                stale_ids = [str(o["id"]) for o in stale_orders]
                placeholders = ",".join(["?"] * len(stale_ids))
                await db.execute(
                    f"UPDATE orders SET status = 'CANCELLED' WHERE id IN ({placeholders})",
                    stale_ids
                )
                await db.commit()
                count = len(stale_ids)
                
                from database.models import get_user_lang
                from utils.locales import t
                
                if tg_app and tg_app.bot:
                    for order in stale_orders:
                        try:
                            lang = await get_user_lang(order["user_telegram_id"])
                            msg = t("order_expired_notification", lang).format(order_id=order["id"])
                            await tg_app.bot.send_message(
                                chat_id=order["user_telegram_id"],
                                text=msg,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify user {order['user_telegram_id']} of expired order {order['id']}: {e}")
                            
            return {"status": "ok", "cancelled": count}
        finally:
            await db.close()
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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


@api.post("/api/broadcast", dependencies=[Depends(verify_api_key)])
async def api_broadcast(data: dict):
    from database.models import get_all_users
    try:
        message = data.get("message", "").strip()
        photo_url = data.get("photo_url", "").strip()
        btn_type = data.get("btn_type", "none")
        btn_prod_id = data.get("btn_prod_id")
        btn_text = data.get("btn_text", "").strip()
        btn_url = data.get("btn_url", "").strip()

        if not message and not photo_url:
            raise HTTPException(status_code=400, detail="Empty message and photo_url")

        users = await get_all_users()
        sent = 0
        failed = 0

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

        if tg_app and tg_app.bot:
            for user in users:
                if user.get("is_banned"):
                    continue
                try:
                    if photo_url:
                        await tg_app.bot.send_photo(
                            chat_id=user["telegram_id"],
                            photo=photo_url,
                            caption=message or None,
                            parse_mode="HTML" if message else None,
                            reply_markup=reply_markup
                        )
                    else:
                        await tg_app.bot.send_message(
                            chat_id=user["telegram_id"],
                            text=message,
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                    sent += 1
                except Exception as e:
                    logger.debug("Failed sending broadcast to %s: %s", user["telegram_id"], e)
                    failed += 1
        else:
            raise HTTPException(status_code=503, detail="Bot not initialized")

        return {"sent": sent, "failed": failed, "total": len(users)}
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
    from database.models import create_promo
    try:
        discount_type = data.get("discount_type", "percent")
        if discount_type not in ("percent", "fixed"):
            raise HTTPException(status_code=400, detail="discount_type must be 'percent' or 'fixed'")
        discount_value = float(data["discount_value"])
        if discount_value <= 0:
            raise HTTPException(status_code=400, detail="discount_value must be positive")
        if discount_type == "percent" and discount_value > 100:
            raise HTTPException(status_code=400, detail="Percent discount cannot exceed 100")

        promo_id = await create_promo(
            code=data["code"],
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=int(data.get("max_uses", 0)),
            max_uses_per_user=int(data.get("max_uses_per_user", 0)),
            applicable_product_ids=data.get("applicable_product_ids"),
            max_qty_per_order=int(data.get("max_qty_per_order", 0)),
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
async def api_get_users(limit: int = 20, offset: int = 0, search: str = ""):
    from database.models import get_users_paginated
    try:
        users, total = await get_users_paginated(limit, offset, search)
        return {"users": users, "total": total}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
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
            
            global tg_app
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
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await topup_wallet(telegram_id, amount, "Admin credit")
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
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await deduct_wallet(telegram_id, amount, "Admin debit")
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
WEBHOOK_WORKERS = _env_int("WEBHOOK_WORKERS", 4, minimum=1)
WEBHOOK_LOCK_STRIPES = _env_int("WEBHOOK_LOCK_STRIPES", 1024, minimum=8)
webhook_user_locks: list[asyncio.Lock] = [asyncio.Lock() for _ in range(WEBHOOK_LOCK_STRIPES)]


# ──────────────────────────────────────────────
#  Post-init hook: database setup
# ──────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Called after the Application has been initialised — set up the database."""
    await init_db()
    logger.info("✅ Database initialized")

    # Auto-cancel stale PENDING/AWAITING_PAYMENT orders older than 5 minutes
    # This handles orders that were left hanging after a bot restart
    try:
        from database.db import get_db
        db = await get_db()
        try:
            cursor = await db.execute(
                """UPDATE orders SET status = 'CANCELLED'
                   WHERE status IN ('PENDING', 'AWAITING_PAYMENT')
                     AND created_at <= datetime('now', '-5 minutes')"""
            )
            await db.commit()
            count = cursor.rowcount if cursor.rowcount > 0 else 0
            if count:
                logger.info("🧹 Auto-cancelled %d stale PENDING/AWAITING_PAYMENT orders on startup", count)
        finally:
            await db.close()
    except Exception as exc:
        logger.warning("Could not clean stale orders: %s", exc)


# ──────────────────────────────────────────────
#  Webhook endpoint for Telegram updates
# ──────────────────────────────────────────────

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
DROP_PENDING_UPDATES = _env_bool("DROP_PENDING_UPDATES", False)

from starlette.requests import Request as StarletteRequest

@api.post("/webhook")
async def telegram_webhook(request: StarletteRequest):
    """Receive Telegram updates via webhook — zero polling, zero wasted CPU."""
    try:
        # Verify webhook secret if configured
        if WEBHOOK_SECRET:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not hmac.compare_digest(token, WEBHOOK_SECRET):
                logger.warning("⚠️ Webhook secret mismatch — rejecting update")
                raise HTTPException(status_code=403, detail="Forbidden")

        data = await request.json()
        logger.debug("Webhook received update: %s", data.get("update_id", "?"))
        if tg_app:
            update = Update.de_json(data, tg_app.bot)
            if webhook_update_queue is not None:
                webhook_update_queue.put_nowait(update)
            else:
                task = asyncio.create_task(tg_app.process_update(update))
                task.add_done_callback(_log_update_task_result)
        else:
            logger.error("❌ tg_app is None — cannot process update")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("❌ Webhook error: %s", exc, exc_info=True)
        return {"ok": False}


def _log_update_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning("Webhook update task was cancelled")
    except Exception as exc:
        logger.error("Webhook update task failed: %s", exc, exc_info=True)


def _webhook_lock_key(update: Update) -> str:
    user = update.effective_user
    if user:
        return f"user:{user.id}"
    chat = update.effective_chat
    if chat:
        return f"chat:{chat.id}"
    return f"update:{update.update_id}"


def _webhook_user_lock(update: Update) -> asyncio.Lock:
    key = _webhook_lock_key(update)
    return webhook_user_locks[abs(hash(key)) % len(webhook_user_locks)]


async def _webhook_update_worker(application: Application, worker_id: int) -> None:
    global webhook_update_queue
    if webhook_update_queue is None:
        webhook_update_queue = asyncio.Queue()

    while True:
        update = await webhook_update_queue.get()
        try:
            lock = _webhook_user_lock(update)
            async with lock:
                await application.process_update(update)
        except Exception as exc:
            logger.error("Webhook worker %s update failed: %s", worker_id, exc, exc_info=True)
        finally:
            webhook_update_queue.task_done()


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
        ("ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT NULL", "Column 'products.custom_emoji_id'"),
        ("ALTER TABLE products ADD COLUMN sort_order INTEGER DEFAULT 0", "Column 'products.sort_order'"),
        ("ALTER TABLE products ADD COLUMN delivery_type TEXT DEFAULT 'stock'", "Column 'products.delivery_type'"),
        ("ALTER TABLE orders ADD COLUMN activation_identifier TEXT", "Column 'orders.activation_identifier'"),
        ("ALTER TABLE orders ADD COLUMN activation_status TEXT DEFAULT NULL", "Column 'orders.activation_status'"),
        ("ALTER TABLE orders ADD COLUMN activation_requested_at TIMESTAMP", "Column 'orders.activation_requested_at'"),
        ("ALTER TABLE orders ADD COLUMN activated_at TIMESTAMP", "Column 'orders.activated_at'"),
        ("CREATE TABLE IF NOT EXISTS reseller_api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, user_telegram_id INTEGER NOT NULL, name TEXT DEFAULT '', key_prefix TEXT UNIQUE NOT NULL, key_hash TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used_at TIMESTAMP)", "Table 'reseller_api_keys'"),
        ("CREATE TABLE IF NOT EXISTS reseller_order_links (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER UNIQUE NOT NULL, reseller_user_telegram_id INTEGER NOT NULL, customer_reference TEXT DEFAULT '', idempotency_key TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(reseller_user_telegram_id, idempotency_key))", "Table 'reseller_order_links'"),
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
    except Exception as exc:
        await update.message.reply_text(f"❌ Completed with some errors, check logs.")




# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────

def main() -> None:
    """Build the Application, register handlers, and start in webhook or polling mode."""
    global tg_app, webhook_update_queue, webhook_worker_tasks

    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()

    # In webhook mode, disable the built-in Updater (we handle updates via FastAPI)
    builder = Application.builder().token(BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).pool_timeout(30.0).post_init(post_init)
    if webhook_url:
        builder = builder.updater(None)
    app = builder.build()

    tg_app = app

    # ── Global Error Handler ─────────────
    from telegram.error import BadRequest

    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and handle specific harmless errors."""
        if isinstance(context.error, BadRequest):
            err_text = str(context.error)
            if "Message is not modified" in err_text or "Query is too old" in err_text:
                # Harmless error caused by users spamming inline buttons that don't change the message content
                return
        
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
        except Exception:
            pass

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
                if (now - cached_time) < 900:
                    is_subscribed = True
                else:
                    is_subscribed = False
                    try:
                        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
                        if member.status in ["creator", "administrator", "member", "restricted"]:
                            is_subscribed = True
                            if context.user_data is not None:
                                context.user_data["sub_verified_at"] = now
                    except Exception as e:
                        err_msg = str(e).lower()
                        if "chat not found" in err_msg or "not enough rights" in err_msg or "admin" in err_msg:
                            is_subscribed = True
                            if context.user_data is not None:
                                context.user_data["sub_verified_at"] = now

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
                if update.callback_query:
                    await update.callback_query.answer(warn, show_alert=False)
                elif update.message:
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
    app.add_handler(CallbackQueryHandler(show_profile, pattern=r"^menu_profile$"))
    app.add_handler(CallbackQueryHandler(show_referrals, pattern=r"^show_referrals$"))
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
            global webhook_update_queue, webhook_worker_tasks
            
            loop = asyncio.get_running_loop()
            from concurrent.futures import ThreadPoolExecutor
            loop.set_default_executor(ThreadPoolExecutor(max_workers=THREAD_WORKERS))


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

            webhook_update_queue = asyncio.Queue()
            webhook_worker_tasks = [
                asyncio.create_task(_webhook_update_worker(app, worker_id))
                for worker_id in range(1, WEBHOOK_WORKERS + 1)
            ]
            logger.info("Webhook update workers started: %d", len(webhook_worker_tasks))

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

            config = uvicorn.Config(api, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            try:
                await server.serve()
            finally:
                # Do NOT delete the webhook on shutdown. In a rolling deployment,
                # the old container shutting down would delete the webhook set by the new container.
                for task in webhook_worker_tasks:
                    task.cancel()
                if webhook_worker_tasks:
                    await asyncio.gather(*webhook_worker_tasks, return_exceptions=True)
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




