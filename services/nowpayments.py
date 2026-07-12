"""Small, server-side NOWPayments client and IPN signature verification."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from config import (
    NOWPAYMENTS_API_KEY,
    NOWPAYMENTS_BASE_URL,
    NOWPAYMENTS_ENABLED,
    NOWPAYMENTS_FEE_PAID_BY_USER,
    NOWPAYMENTS_FIXED_RATE,
    NOWPAYMENTS_IPN_SECRET,
)


logger = logging.getLogger(__name__)
_HTTP_CLIENT: httpx.AsyncClient | None = None
_MINIMUM_CACHE: tuple[float, dict] | None = None


class NowPaymentsError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def is_nowpayments_configured() -> bool:
    return bool(NOWPAYMENTS_ENABLED and NOWPAYMENTS_API_KEY and NOWPAYMENTS_IPN_SECRET)


def _sort_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_payload(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_payload(item) for item in value]
    return value


def canonical_ipn_payload(payload: dict) -> bytes:
    sorted_payload = _sort_payload(payload)
    return json.dumps(
        sorted_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def calculate_ipn_signature(payload: dict, secret: str | None = None) -> str:
    signing_secret = NOWPAYMENTS_IPN_SECRET if secret is None else secret
    if not signing_secret:
        raise NowPaymentsError("NOWPayments IPN secret is not configured")
    return hmac.new(
        signing_secret.encode("utf-8"),
        canonical_ipn_payload(payload),
        hashlib.sha512,
    ).hexdigest()


def verify_ipn_signature(payload: dict, received_signature: str | None) -> bool:
    if not received_signature or not NOWPAYMENTS_IPN_SECRET:
        return False
    expected = calculate_ipn_signature(payload)
    return hmac.compare_digest(expected.lower(), received_signature.strip().lower())


async def _client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            base_url=NOWPAYMENTS_BASE_URL,
            timeout=httpx.Timeout(12.0, connect=5.0),
            headers={
                "x-api-key": NOWPAYMENTS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
    return _HTTP_CLIENT


async def close_nowpayments_client() -> None:
    global _HTTP_CLIENT, _MINIMUM_CACHE
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None
    _MINIMUM_CACHE = None


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("message") or data.get("error") or data.get("code") or response.text)
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


async def _request(method: str, path: str, *, retry_get: bool = True, **kwargs) -> dict:
    if not NOWPAYMENTS_ENABLED or not NOWPAYMENTS_API_KEY:
        raise NowPaymentsError("NOWPayments is not configured")

    attempts = 2 if method.upper() == "GET" and retry_get else 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await (await _client()).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = NowPaymentsError(
                    _error_message(response),
                    status_code=response.status_code,
                    retryable=retryable,
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(1)
                    last_error = error
                    continue
                raise error
            data = response.json()
            if not isinstance(data, dict):
                raise NowPaymentsError("NOWPayments returned an invalid response")
            return data
        except NowPaymentsError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(1)
                continue
            raise NowPaymentsError(
                "NOWPayments is temporarily unreachable",
                retryable=True,
            ) from exc

    raise NowPaymentsError(str(last_error or "NOWPayments request failed"), retryable=True)


async def create_payment(
    *,
    price_amount: float,
    order_id: int,
    order_description: str,
    callback_url: str,
    pay_currency: str = "usdtbsc",
    is_fixed_rate: bool | None = None,
    is_fee_paid_by_user: bool | None = None,
) -> dict:
    configured_fee_mode = (
        NOWPAYMENTS_FEE_PAID_BY_USER
        if is_fee_paid_by_user is None
        else bool(is_fee_paid_by_user)
    )
    configured_fixed_rate = (
        NOWPAYMENTS_FIXED_RATE if is_fixed_rate is None else bool(is_fixed_rate)
    )
    # NOWPayments requires fee-paid-by-user payments to use a fixed rate.
    effective_fixed_rate = bool(configured_fixed_rate or configured_fee_mode)
    payload = {
        "price_amount": round(float(price_amount), 2),
        "price_currency": "usd",
        "pay_currency": pay_currency.lower(),
        "order_id": str(int(order_id)),
        "order_description": str(order_description)[:255],
        "ipn_callback_url": callback_url,
        "is_fixed_rate": effective_fixed_rate,
        "is_fee_paid_by_user": configured_fee_mode,
    }
    # POST is deliberately not retried: the provider may have created a payment
    # even when the response is lost.
    return await _request("POST", "/payment", json=payload, retry_get=False)


async def get_payment_status(payment_id: str | int) -> dict:
    return await _request("GET", f"/payment/{payment_id}")


async def get_minimum_amount(
    *,
    currency_from: str = "usdtbsc",
    currency_to: str = "usdtbsc",
    fiat_equivalent: str = "usd",
) -> dict:
    global _MINIMUM_CACHE
    now = time.monotonic()
    if _MINIMUM_CACHE and now - _MINIMUM_CACHE[0] < 300:
        return dict(_MINIMUM_CACHE[1])
    result = await _request(
        "GET",
        "/min-amount",
        params={
            "currency_from": currency_from.lower(),
            "currency_to": currency_to.lower(),
            "fiat_equivalent": fiat_equivalent.lower(),
            "is_fixed_rate": "true" if (NOWPAYMENTS_FIXED_RATE or NOWPAYMENTS_FEE_PAID_BY_USER) else "false",
            "is_fee_paid_by_user": "true" if NOWPAYMENTS_FEE_PAID_BY_USER else "false",
        },
    )
    _MINIMUM_CACHE = (now, dict(result))
    return result
