"""Bounded Crypto Pay API client and signed webhook verification."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import httpx

from config import (
    CRYPTO_PAY_ACCEPTED_ASSETS,
    CRYPTO_PAY_API_TOKEN,
    CRYPTO_PAY_BASE_URL,
    CRYPTO_PAY_ENABLED,
    CRYPTO_PAY_WEBHOOK_SECRET,
)
from services.runtime_metrics import DependencyCircuitOpen, dependency_call


logger = logging.getLogger(__name__)
_HTTP_CLIENT: httpx.AsyncClient | None = None
_ALLOWED_ASSETS = {"USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX", "USDC"}


class CryptoPayError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def is_crypto_pay_configured() -> bool:
    return bool(
        CRYPTO_PAY_ENABLED
        and CRYPTO_PAY_API_TOKEN
        and CRYPTO_PAY_WEBHOOK_SECRET
    )


def accepted_assets() -> str:
    values = [
        value.strip().upper()
        for value in CRYPTO_PAY_ACCEPTED_ASSETS.split(",")
        if value.strip().upper() in _ALLOWED_ASSETS
    ]
    return ",".join(dict.fromkeys(values)) or "USDT"


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CryptoPayError("Invalid invoice amount") from exc
    if amount <= 0:
        raise CryptoPayError("Invoice amount must be positive")
    return format(amount, ".2f")


async def _client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            base_url=CRYPTO_PAY_BASE_URL,
            timeout=httpx.Timeout(12.0, connect=5.0),
            headers={
                "Crypto-Pay-API-Token": CRYPTO_PAY_API_TOKEN,
                "Accept": "application/json",
            },
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )
    return _HTTP_CLIENT


async def close_crypto_pay_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                return str(error.get("name") or error.get("code") or error)
            return str(error or data.get("message") or response.text)
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


async def _request(
    method: str,
    path: str,
    *,
    retry_get: bool = True,
    **kwargs,
) -> Any:
    if not CRYPTO_PAY_ENABLED or not CRYPTO_PAY_API_TOKEN:
        raise CryptoPayError("Crypto Pay is not configured")

    attempts = 2 if method.upper() == "GET" and retry_get else 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            async with dependency_call("crypto_pay"):
                response = await (await _client()).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = CryptoPayError(
                    _error_message(response),
                    status_code=response.status_code,
                    retryable=retryable,
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(0.5)
                    last_error = error
                    continue
                raise error

            data = response.json()
            if not isinstance(data, dict) or data.get("ok") is not True:
                raise CryptoPayError(
                    str((data or {}).get("error") or "Crypto Pay returned an invalid response")
                )
            return data.get("result")
        except CryptoPayError:
            raise
        except DependencyCircuitOpen as exc:
            raise CryptoPayError(
                "Crypto Pay is temporarily unavailable",
                retryable=True,
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(0.5)
                continue
            raise CryptoPayError(
                "Crypto Pay is temporarily unreachable",
                retryable=True,
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise CryptoPayError("Crypto Pay returned invalid JSON") from exc

    raise CryptoPayError(str(last_error or "Crypto Pay request failed"), retryable=True)


async def create_invoice(
    *,
    amount_usd: float,
    payload: str,
    description: str,
    expires_in: int,
) -> dict:
    result = await _request(
        "POST",
        "/createInvoice",
        data={
            "currency_type": "fiat",
            "fiat": "USD",
            "amount": _money(amount_usd),
            "accepted_assets": accepted_assets(),
            "payload": str(payload)[:4000],
            "description": str(description)[:1024],
            "expires_in": max(60, min(int(expires_in), 2678400)),
            "allow_comments": "false",
            "allow_anonymous": "false",
        },
        retry_get=False,
    )
    if not isinstance(result, dict) or not result.get("invoice_id"):
        raise CryptoPayError("Crypto Pay did not return an invoice")
    return result


async def get_invoices(invoice_ids: list[str | int]) -> list[dict]:
    normalized = [str(value).strip() for value in invoice_ids if str(value).strip()]
    if not normalized:
        return []
    result = await _request(
        "GET",
        "/getInvoices",
        params={"invoice_ids": ",".join(normalized[:100])},
    )
    if not isinstance(result, dict):
        raise CryptoPayError("Crypto Pay returned an invalid invoice list")
    items = result.get("items")
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def calculate_webhook_signature(raw_body: bytes, token: str | None = None) -> str:
    signing_token = CRYPTO_PAY_API_TOKEN if token is None else token
    if not signing_token:
        raise CryptoPayError("Crypto Pay token is not configured")
    secret = hashlib.sha256(signing_token.encode("utf-8")).digest()
    return hmac.new(secret, raw_body, hashlib.sha256).hexdigest()


def verify_webhook_signature(raw_body: bytes, received_signature: str | None) -> bool:
    if not received_signature or not CRYPTO_PAY_API_TOKEN:
        return False
    expected = calculate_webhook_signature(raw_body)
    return hmac.compare_digest(expected.lower(), received_signature.strip().lower())


def verify_webhook_path_secret(received_secret: str) -> bool:
    return bool(
        CRYPTO_PAY_WEBHOOK_SECRET
        and hmac.compare_digest(CRYPTO_PAY_WEBHOOK_SECRET, str(received_secret or ""))
    )


def request_date_is_fresh(value: Any, *, max_age_seconds: int = 600) -> bool:
    try:
        if isinstance(value, str) and not value.strip().isdigit():
            request_time = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        else:
            request_time = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return abs(time.time() - request_time) <= max(30, int(max_age_seconds))
