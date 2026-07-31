"""Bounded Bybit Pay QR client and RSA-signed webhook verification."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from config import (
    BYBIT_PAY_API_KEY,
    BYBIT_PAY_API_SECRET,
    BYBIT_PAY_BASE_URL,
    BYBIT_PAY_ENABLED,
    BYBIT_PAY_MERCHANT_ID,
    BYBIT_PAY_RECV_WINDOW,
    BYBIT_PAY_WEBHOOK_PUBLIC_KEY,
)
from services.runtime_metrics import DependencyCircuitOpen, dependency_call


_HTTP_CLIENT: httpx.AsyncClient | None = None
SUCCESS_CODE = 100000
PAID_STATUS = "PAY_SUCCESS"
TERMINAL_STATUSES = {"PAY_SUCCESS", "PAY_FAILED", "TIMEOUT"}


class BybitPayError(RuntimeError):
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


def is_bybit_pay_configured() -> bool:
    return bool(
        BYBIT_PAY_ENABLED
        and BYBIT_PAY_API_KEY
        and BYBIT_PAY_API_SECRET
        and BYBIT_PAY_MERCHANT_ID
        and BYBIT_PAY_WEBHOOK_PUBLIC_KEY
    )


def is_safe_checkout_url(value: Any) -> bool:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme == "bybitapp":
        return bool(parsed.netloc or parsed.path)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    return hostname in {"bybit.com", "bybitglobal.com"} or hostname.endswith(
        (".bybit.com", ".bybitglobal.com")
    )


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BybitPayError("Invalid Bybit Pay amount") from exc
    if amount <= 0:
        raise BybitPayError("Bybit Pay amount must be positive")
    return format(amount, ".2f")


def _signature(timestamp: str, payload: str) -> str:
    plain = f"{timestamp}{BYBIT_PAY_API_KEY}{BYBIT_PAY_RECV_WINDOW}{payload}"
    return hmac.new(
        BYBIT_PAY_API_SECRET.encode("utf-8"),
        plain.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def _client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            base_url=BYBIT_PAY_BASE_URL,
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=120.0,
            ),
            headers={"Accept": "application/json"},
        )
    return _HTTP_CLIENT


async def close_bybit_pay_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    retry_get: bool = True,
) -> dict:
    if not is_bybit_pay_configured():
        raise BybitPayError("Bybit Pay is not configured")

    method = method.upper()
    query = urlencode(params or {})
    body = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if payload is not None
        else ""
    )
    signing_payload = query if method == "GET" else body
    attempts = 2 if method == "GET" and retry_get else 1
    for attempt in range(attempts):
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-BAPI-API-KEY": BYBIT_PAY_API_KEY,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": str(BYBIT_PAY_RECV_WINDOW),
            "X-BAPI-SIGN": _signature(timestamp, signing_payload),
            "Content-Type": "application/json",
        }
        try:
            async with dependency_call("bybit_pay"):
                response = await (await _client()).request(
                    method,
                    path,
                    params=params,
                    content=body.encode("utf-8") if body else None,
                    headers=headers,
                )
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = BybitPayError(
                    f"Bybit Pay HTTP {response.status_code}",
                    status_code=response.status_code,
                    retryable=retryable,
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(0.5)
                    continue
                raise error
            data = response.json()
            if not isinstance(data, dict):
                raise BybitPayError("Bybit Pay returned invalid JSON")
            if int(data.get("retCode", -1)) != SUCCESS_CODE:
                raise BybitPayError(str(data.get("retMsg") or "Bybit Pay request failed"))
            result = data.get("result")
            if not isinstance(result, dict):
                raise BybitPayError("Bybit Pay returned an invalid result")
            return result
        except BybitPayError:
            raise
        except DependencyCircuitOpen as exc:
            raise BybitPayError("Bybit Pay is temporarily unavailable", retryable=True) from exc
        except (httpx.TimeoutException, httpx.NetworkError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                await asyncio.sleep(0.5)
                continue
            raise BybitPayError("Bybit Pay is temporarily unreachable", retryable=True) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise BybitPayError("Bybit Pay returned invalid JSON") from exc
    raise BybitPayError("Bybit Pay request failed", retryable=True)


async def create_payment(
    *,
    amount_usd: float,
    merchant_trade_no: str,
    goods_name: str,
    callback_url: str,
    success_url: str,
    expires_in: int,
    user_telegram_id: int,
) -> dict:
    now = int(time.time())
    payload = {
        "merchantId": BYBIT_PAY_MERCHANT_ID,
        "paymentType": "E_COMMERCE",
        "merchantTradeNo": str(merchant_trade_no)[:64],
        "goods": [{
            "shoppingName": "VenteBot",
            "mccCode": "5816",
            "goodsName": str(goods_name)[:128],
            "goodsDetail": "Digital product",
        }],
        "orderAmount": _money(amount_usd),
        "currency": "USDT",
        "currencyType": "crypto",
        "successUrl": success_url[:256],
        "failedUrl": success_url[:256],
        "webhookUrl": callback_url[:256],
        "orderExpireTime": now + max(60, min(int(expires_in), 3600)),
        "env": {"terminalType": "WAP"},
        "customer": {"externalUserId": str(int(user_telegram_id))},
    }
    result = await _request(
        "POST", "/v5/bybitpay/create_pay", payload=payload, retry_get=False
    )
    if not result.get("payId") or not is_safe_checkout_url(result.get("checkoutLink")):
        raise BybitPayError("Bybit Pay did not return a checkout")
    return result


async def get_payment_result(*, pay_id: str | None = None, merchant_trade_no: str | None = None) -> dict:
    params = {"merchantId": BYBIT_PAY_MERCHANT_ID, "paymentType": "E_COMMERCE"}
    if pay_id:
        params["payId"] = str(pay_id)
    elif merchant_trade_no:
        params["merchantTradeNo"] = str(merchant_trade_no)
    else:
        raise BybitPayError("Bybit Pay payment identifier is required")
    return await _request("GET", "/v5/bybitpay/pay_result", params=params)


def verify_webhook_signature(
    raw_body: bytes,
    timestamp: str | None,
    received_signature: str | None,
    *,
    max_age_seconds: int = 600,
) -> bool:
    if not timestamp or not received_signature or not BYBIT_PAY_WEBHOOK_PUBLIC_KEY:
        return False
    try:
        numeric_timestamp = int(timestamp)
        if abs(int(time.time()) - numeric_timestamp) > max(30, int(max_age_seconds)):
            return False
        signature = base64.b64decode(received_signature, validate=True)
        public_key = serialization.load_pem_public_key(
            BYBIT_PAY_WEBHOOK_PUBLIC_KEY.encode("utf-8")
        )
        public_key.verify(
            signature,
            timestamp.encode("ascii") + raw_body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (ValueError, TypeError, InvalidSignature, UnicodeError):
        return False


def normalize_payment(payload: dict) -> dict:
    order = payload.get("order") if isinstance(payload.get("order"), dict) else payload
    status = str(order.get("status") or "INIT").upper()
    normalized_status = {
        "PAY_SUCCESS": "paid",
        "PAY_FAILED": "failed",
        "TIMEOUT": "expired",
    }.get(status, "active")
    return {
        "invoice_id": str(order.get("payId") or ""),
        "status": normalized_status,
        "amount": str(order.get("amount") or ""),
        "payload": str(order.get("merchantTradeNo") or ""),
        "web_app_invoice_url": payload.get("checkoutLink"),
        "expiration_date": payload.get("expireTime"),
        "raw_bybit_status": status,
        "provider": "bybitpay",
        "raw": payload,
    }
