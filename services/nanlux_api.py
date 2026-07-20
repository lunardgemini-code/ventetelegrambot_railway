"""Outbound client for the MMO NanLux dealer API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx

from config import NANLUX_API_AUTH_HEADER, NANLUX_API_BASE_URL, NANLUX_API_KEY
from services.runtime_metrics import DependencyCircuitOpen, dependency_call
from services.supplier_api import SupplierAPIError


logger = logging.getLogger(__name__)
_CLIENT: httpx.AsyncClient | None = None
_BALANCE_CACHE: tuple[float, dict] | None = None
_BALANCE_LOCK = asyncio.Lock()
_BALANCE_REFRESH_TASK: asyncio.Task | None = None
_BALANCE_CACHE_SECONDS = max(
    10, int(os.environ.get("SUPPLIER_BALANCE_CACHE_SECONDS", "120"))
)


def is_nanlux_configured() -> bool:
    return bool(NANLUX_API_KEY and NANLUX_API_BASE_URL.startswith("https://"))


async def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(
            base_url=NANLUX_API_BASE_URL,
            timeout=httpx.Timeout(20.0, connect=7.0),
            headers={
                NANLUX_API_AUTH_HEADER: NANLUX_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
    return _CLIENT


async def close_nanlux_client() -> None:
    global _CLIENT, _BALANCE_CACHE
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
    _CLIENT = None
    _BALANCE_CACHE = None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(
                body.get("message")
                or body.get("error")
                or body.get("detail")
                or response.text
            )
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


async def _request(method: str, path: str, **kwargs) -> Any:
    if not is_nanlux_configured():
        raise SupplierAPIError("MMO NanLux API key is not configured")
    method = method.upper()
    attempts = 2 if method == "GET" else 1
    for attempt in range(attempts):
        try:
            async with dependency_call("supplier:nanlux"):
                response = await (await _client()).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = SupplierAPIError(
                    _error_message(response),
                    status_code=response.status_code,
                    retryable=retryable,
                    outcome_unknown=(method == "POST" and response.status_code >= 500),
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(1)
                    continue
                raise error
            return response.json()
        except SupplierAPIError:
            raise
        except DependencyCircuitOpen as exc:
            raise SupplierAPIError(
                "MMO NanLux is temporarily unavailable",
                retryable=True,
                outcome_unknown=False,
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError, TimeoutError) as exc:
            if method == "GET" and attempt + 1 < attempts:
                await asyncio.sleep(1)
                continue
            raise SupplierAPIError(
                "MMO NanLux is temporarily unreachable",
                retryable=True,
                outcome_unknown=method == "POST",
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise SupplierAPIError(
                "MMO NanLux returned invalid JSON",
                outcome_unknown=method == "POST",
            ) from exc
    raise SupplierAPIError("MMO NanLux request failed", retryable=True)


def _data(payload: Any) -> dict:
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise SupplierAPIError("MMO NanLux returned an invalid response")
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def normalize_nanlux_products(payload: Any, units_per_usd: float) -> list[dict]:
    data = _data(payload)
    raw_products = data.get("products")
    if not isinstance(raw_products, list):
        return []
    rate = max(1.0, float(units_per_usd or 0))
    products: list[dict] = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        external_id = raw.get("id") or raw.get("product_id")
        name = str(raw.get("name") or "").strip()
        source_price = raw.get("cost_price")
        if source_price is None:
            source_price = raw.get("price")
        if external_id is None or not name or source_price is None:
            continue
        try:
            source_price_value = max(0.0, float(source_price))
            remote_stock = max(0, int(float(raw.get("stock") or 0)))
        except (TypeError, ValueError):
            continue
        if bool(raw.get("is_maintenance")):
            remote_stock = 0
        products.append(
            {
                "external_product_id": str(external_id),
                "name": name,
                "description": str(raw.get("description") or "").strip(),
                "base_price": round(source_price_value / rate, 4),
                "source_price": source_price_value,
                "source_currency": "VND",
                "remote_stock": remote_stock,
                "warranty_days": 0,
                "image_url": "",
                "emoji": "📦",
                "raw_payload": raw,
            }
        )
    return products


async def list_nanlux_products(units_per_usd: float) -> list[dict]:
    payload = await _request("GET", "/api/dealer/products")
    products = normalize_nanlux_products(payload, units_per_usd)
    if not products:
        logger.warning("MMO NanLux catalog response contained no recognizable products")
    return products


def normalize_nanlux_balance(payload: Any, units_per_usd: float) -> dict:
    data = _data(payload)
    try:
        source_balance = max(0.0, float(data.get("balance") or 0))
        rate = max(1.0, float(units_per_usd or 0))
    except (TypeError, ValueError) as exc:
        raise SupplierAPIError("MMO NanLux returned an invalid wallet balance") from exc
    balance = source_balance / rate
    return {
        "balance": balance,
        "currency": "USD",
        "source_balance": source_balance,
        "source_currency": "VND",
        "balance_text": f"{source_balance:,.0f} VND (~${balance:.2f})",
        "dealer_name": str(data.get("name") or ""),
        "discount_percent": float(data.get("discount_percent") or 0),
    }


async def get_nanlux_balance(units_per_usd: float, *, force: bool = False) -> dict:
    global _BALANCE_CACHE, _BALANCE_REFRESH_TASK
    now = time.monotonic()
    rate = max(1.0, float(units_per_usd or 0))
    if not force and _BALANCE_CACHE:
        cached = dict(_BALANCE_CACHE[1])
        normalized = normalize_nanlux_balance({"success": True, "data": cached}, rate)
        if now - _BALANCE_CACHE[0] < _BALANCE_CACHE_SECONDS:
            return normalized
        normalized["stale"] = True
        if _BALANCE_REFRESH_TASK is None or _BALANCE_REFRESH_TASK.done():
            _BALANCE_REFRESH_TASK = asyncio.create_task(
                _refresh_nanlux_balance(rate), name="refresh-nanlux-balance"
            )
        return normalized
    async with _BALANCE_LOCK:
        now = time.monotonic()
        if not force and _BALANCE_CACHE and now - _BALANCE_CACHE[0] < _BALANCE_CACHE_SECONDS:
            return normalize_nanlux_balance(
                {"success": True, "data": dict(_BALANCE_CACHE[1])}, rate
            )
        try:
            payload = await _request("GET", "/api/dealer/balance")
            raw_balance = _data(payload)
            balance = normalize_nanlux_balance(payload, rate)
        except SupplierAPIError as exc:
            if _BALANCE_CACHE:
                stale = normalize_nanlux_balance(
                    {"success": True, "data": dict(_BALANCE_CACHE[1])}, rate
                )
                stale["stale"] = True
                logger.warning("Serving stale MMO NanLux balance: %s", exc)
                return stale
            raise
        _BALANCE_CACHE = (time.monotonic(), dict(raw_balance))
        return balance


async def _refresh_nanlux_balance(rate: float) -> None:
    try:
        await get_nanlux_balance(rate, force=True)
    except Exception as exc:
        logger.warning("Background MMO NanLux balance refresh failed: %s", exc)


def invalidate_nanlux_balance_cache() -> None:
    global _BALANCE_CACHE
    _BALANCE_CACHE = None


def normalize_nanlux_purchase(payload: Any) -> dict:
    data = _data(payload)
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raw_items = []
    items: list[dict] = []
    for item in raw_items:
        if isinstance(item, dict):
            value = (
                item.get("account_data")
                or item.get("content")
                or item.get("credential")
                or item.get("account")
                or item.get("data")
            )
            if value is None:
                value = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        else:
            value = item
        if value not in (None, ""):
            items.append({"account_data": str(value)})
    return {
        "external_order_id": str(data.get("order_id") or data.get("id") or ""),
        "items": items,
        "raw_payload": payload,
    }


async def purchase_nanlux_product(
    product_id: str, quantity: int, *, buyer_info: str = ""
) -> dict:
    quantity = max(1, int(quantity))
    payload = await _request(
        "POST",
        "/api/dealer/buy",
        json={
            "product_id": int(product_id) if str(product_id).isdigit() else product_id,
            "quantity": quantity,
            "buyer_info": str(buyer_info or "")[:500],
        },
    )
    result = normalize_nanlux_purchase(payload)
    if len(result["items"]) < quantity:
        raise SupplierAPIError(
            "MMO NanLux purchase response did not contain all delivery items",
            outcome_unknown=True,
        )
    invalidate_nanlux_balance_cache()
    return result
