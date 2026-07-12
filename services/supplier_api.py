"""Outbound client for the Canboso Telegram buyer API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Any

import httpx

from config import CANBOSO_API_AUTH_HEADER, CANBOSO_API_BASE_URL, CANBOSO_API_KEY


logger = logging.getLogger(__name__)
_CLIENT: httpx.AsyncClient | None = None
_BALANCE_CACHE: tuple[float, dict] | None = None


class SupplierAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        outcome_unknown: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.outcome_unknown = outcome_unknown


def is_canboso_configured() -> bool:
    return bool(CANBOSO_API_KEY and CANBOSO_API_BASE_URL.startswith("https://"))


async def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(
            base_url=CANBOSO_API_BASE_URL,
            timeout=httpx.Timeout(20.0, connect=7.0),
            headers={
                CANBOSO_API_AUTH_HEADER: CANBOSO_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
    return _CLIENT


async def close_supplier_client() -> None:
    global _CLIENT, _BALANCE_CACHE
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
    _CLIENT = None
    _BALANCE_CACHE = None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("message") or body.get("error") or body.get("detail") or response.text)
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


async def _request(method: str, path: str, **kwargs) -> Any:
    if not is_canboso_configured():
        raise SupplierAPIError("Canboso API key is not configured")
    attempts = 2 if method.upper() == "GET" else 1
    for attempt in range(attempts):
        try:
            response = await (await _client()).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = SupplierAPIError(
                    _error_message(response),
                    status_code=response.status_code,
                    retryable=retryable,
                    outcome_unknown=False,
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(1)
                    continue
                raise error
            return response.json()
        except SupplierAPIError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if method.upper() == "GET" and attempt + 1 < attempts:
                await asyncio.sleep(1)
                continue
            raise SupplierAPIError(
                "Canboso is temporarily unreachable",
                retryable=True,
                outcome_unknown=method.upper() == "POST",
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise SupplierAPIError("Canboso returned invalid JSON") from exc
    raise SupplierAPIError("Canboso request failed", retryable=True)


def _unwrap_list(payload: Any, keys: tuple[str, ...]) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _unwrap_list(value, keys)
            if nested:
                return nested
    for key in ("data", "result", "response"):
        nested = payload.get(key)
        if isinstance(nested, (dict, list)):
            result = _unwrap_list(nested, keys)
            if result:
                return result
    return []


def normalize_products(payload: Any) -> list[dict]:
    raw_products = _unwrap_list(payload, ("products", "items", "catalog"))
    products: list[dict] = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        external_id = raw.get("id") or raw.get("_id") or raw.get("product_id") or raw.get("productId")
        name = raw.get("name") or raw.get("title") or raw.get("product_name")
        price = (
            raw.get("walletPricing")
            if raw.get("walletPricing") is not None
            else raw.get("usdPricing")
            if raw.get("usdPricing") is not None
            else raw.get("price_usd")
            if raw.get("price_usd") is not None
            else raw.get("price")
            if raw.get("price") is not None
            else raw.get("unit_price")
        )
        if external_id is None or not name or price is None:
            continue
        try:
            price_value = round(float(price), 4)
        except (TypeError, ValueError):
            continue
        stats = raw.get("stats") if isinstance(raw.get("stats"), dict) else {}
        stock = (
            raw.get("stock")
            if raw.get("stock") is not None
            else raw.get("available_stock")
            if raw.get("available_stock") is not None
            else raw.get("quantity")
            if raw.get("quantity") is not None
            else raw.get("available")
            if raw.get("available") is not None
            else stats.get("available", 0)
        )
        if isinstance(stock, bool):
            stock_value = 999999 if stock else 0
        else:
            try:
                stock_value = max(0, int(float(stock or 0)))
            except (TypeError, ValueError):
                stock_value = 0
        image_url = str(raw.get("image_url") or raw.get("image") or raw.get("descriptionImage") or "").strip()
        if image_url.startswith("/"):
            image_url = f"{CANBOSO_API_BASE_URL}{image_url}"
        raw_emoji = str(raw.get("emoji") or "").strip()
        emoji = raw_emoji if raw_emoji and any(ord(char) > 127 for char in raw_emoji) else "📦"
        products.append({
            "external_product_id": str(external_id),
            "name": str(name).strip(),
            "description": str(raw.get("description") or raw.get("details") or "").strip(),
            "base_price": price_value,
            "remote_stock": stock_value,
            "warranty_days": max(0, int(raw.get("warranty_days") or raw.get("warrantyDays") or raw.get("warranty") or 0)),
            "image_url": image_url,
            "emoji": emoji,
            "raw_payload": raw,
        })
    return products


async def list_canboso_products() -> list[dict]:
    # Canboso accepts the buyer key header even though Swagger documents a query
    # field. Keeping it out of the URL prevents credentials leaking into HTTP logs.
    payload = await _request("GET", "/api/telegram-buyer/products")
    products = normalize_products(payload)
    if not products and payload not in ([], {}, None):
        logger.warning("Canboso catalog response contained no recognizable products")
    return products


def normalize_balance(payload: Any) -> dict:
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise SupplierAPIError("Canboso returned an invalid balance response")
    currency = str(payload.get("walletCurrency") or "USD").upper()
    raw_balance = payload.get("balanceUsd") if currency == "USD" and payload.get("balanceUsd") is not None else payload.get("balance")
    try:
        balance = float(raw_balance or 0)
    except (TypeError, ValueError) as exc:
        raise SupplierAPIError("Canboso returned an invalid wallet balance") from exc
    return {
        "balance": balance,
        "currency": currency,
        "balance_text": str(payload.get("balanceText") or f"{balance:.2f} {currency}"),
        "updated_at": payload.get("updatedAt"),
    }


async def get_canboso_balance(*, force: bool = False) -> dict:
    global _BALANCE_CACHE
    now = time.monotonic()
    if not force and _BALANCE_CACHE and now - _BALANCE_CACHE[0] < 30:
        return dict(_BALANCE_CACHE[1])
    payload = await _request("GET", "/api/telegram-buyer/balance")
    balance = normalize_balance(payload)
    _BALANCE_CACHE = (now, dict(balance))
    return balance


def invalidate_canboso_balance_cache() -> None:
    """Force the next availability check to read the supplier wallet again."""
    global _BALANCE_CACHE
    _BALANCE_CACHE = None


def calculate_affordable_stock(remote_stock: int, base_price: float, wallet_balance: float) -> int:
    """Cap supplier stock by the number of units the supplier wallet can fund."""
    try:
        stock = max(0, int(remote_stock or 0))
        price = Decimal(str(base_price or 0))
        balance = max(Decimal("0"), Decimal(str(wallet_balance or 0)))
    except (TypeError, ValueError, InvalidOperation):
        return 0
    if stock <= 0:
        return 0
    if price <= 0:
        return stock
    affordable = int((balance / price).to_integral_value(rounding=ROUND_FLOOR))
    return min(stock, max(0, affordable))


def _delivery_values(payload: Any) -> list[Any]:
    values = _unwrap_list(payload, ("items", "accounts", "deliveredAccounts", "credentials", "products", "deliveries"))
    if values:
        return values
    if isinstance(payload, dict):
        for key in ("account_data", "account", "credential", "content", "delivery", "code"):
            if payload.get(key) not in (None, ""):
                return [payload[key]]
        for key in ("data", "result", "order", "purchase"):
            if isinstance(payload.get(key), (dict, list)):
                nested = _delivery_values(payload[key])
                if nested:
                    return nested
    return []


def normalize_purchase(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise SupplierAPIError("Canboso purchase response is not an object", outcome_unknown=True)
    if payload.get("success") is False:
        raise SupplierAPIError(str(payload.get("message") or payload.get("error") or "Purchase rejected"))
    raw_items = _delivery_values(payload)
    items: list[dict] = []
    for item in raw_items:
        if isinstance(item, dict):
            value = item.get("account_data", item.get("content", item.get("credential", item.get("account"))))
            if value is None and (item.get("user") or item.get("password")):
                parts = [str(item.get("user") or ""), str(item.get("password") or "")]
                if item.get("verifyEmail"):
                    parts.append(str(item["verifyEmail"]))
                value = " | ".join(parts)
            if value is None:
                value = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        else:
            value = item
        if value not in (None, ""):
            items.append({"account_data": str(value)})
    external_order_id = payload.get("orderCode") or payload.get("order_id") or payload.get("purchase_id") or payload.get("id")
    return {
        "external_order_id": str(external_order_id or ""),
        "items": items,
        "raw_payload": payload,
    }


async def purchase_canboso_product(product_id: str, quantity: int) -> dict:
    payload = await _request(
        "POST",
        "/api/telegram-buyer/purchase",
        json={
            "key": CANBOSO_API_KEY,
            "product_id": product_id,
            "quantity": max(1, int(quantity)),
        },
    )
    result = normalize_purchase(payload)
    if len(result["items"]) < max(1, int(quantity)):
        raise SupplierAPIError(
            "Canboso purchase response did not contain all delivery items",
            outcome_unknown=True,
        )
    invalidate_canboso_balance_cache()
    return result
