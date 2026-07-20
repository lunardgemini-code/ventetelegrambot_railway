"""HTTP adapters for dynamically configured external supplier accounts."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from services.runtime_metrics import DependencyCircuitOpen, dependency_call
from services.supplier_api import SupplierAPIError, normalize_purchase, normalize_products


logger = logging.getLogger(__name__)
_CLIENTS: dict[str, httpx.AsyncClient] = {}
_BALANCE_CACHE: dict[str, tuple[float, dict]] = {}
_BALANCE_LOCKS: dict[str, asyncio.Lock] = {}
_BALANCE_CACHE_SECONDS = 120


def _auth_headers(provider: dict) -> dict[str, str]:
    key = str(provider.get("api_key") or "")
    mode = str(provider.get("auth_mode") or "header").lower()
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if mode == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif mode == "header":
        headers[str(provider.get("auth_header") or "X-API-Key")] = key
    return headers


async def _client(provider: dict) -> httpx.AsyncClient:
    code = str(provider["code"])
    client = _CLIENTS.get(code)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            base_url=str(provider["base_url"]).rstrip("/"),
            timeout=httpx.Timeout(25.0, connect=7.0),
            headers=_auth_headers(provider),
        )
        _CLIENTS[code] = client
    return client


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("code") or response.text)
            return str(payload.get("message") or error or payload.get("detail") or response.text)
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


async def _request(provider: dict, method: str, path: str, **kwargs) -> Any:
    code = str(provider["code"])
    if not provider.get("api_key"):
        raise SupplierAPIError(f"{provider['name']} API key is not configured")
    attempts = 2 if method.upper() == "GET" else 1
    for attempt in range(attempts):
        try:
            async with dependency_call(f"supplier:{code}"):
                response = await (await _client(provider)).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = SupplierAPIError(
                    _error_message(response),
                    status_code=response.status_code,
                    retryable=retryable,
                    outcome_unknown=(
                        method.upper() == "POST" and response.status_code >= 500
                    ),
                )
                if retryable and attempt + 1 < attempts:
                    await asyncio.sleep(0.7)
                    continue
                raise error
            return response.json()
        except SupplierAPIError:
            raise
        except DependencyCircuitOpen as exc:
            raise SupplierAPIError(
                f"{provider['name']} is temporarily unavailable",
                retryable=True,
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError, TimeoutError) as exc:
            if method.upper() == "GET" and attempt + 1 < attempts:
                await asyncio.sleep(0.7)
                continue
            raise SupplierAPIError(
                f"{provider['name']} is temporarily unreachable",
                retryable=True,
                outcome_unknown=method.upper() == "POST",
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise SupplierAPIError(
                f"{provider['name']} returned invalid JSON",
                outcome_unknown=method.upper() == "POST",
            ) from exc
    raise SupplierAPIError(f"{provider['name']} request failed", retryable=True)


def _as_list(payload: Any, *keys: str) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _positive_int(value: Any) -> int:
    if isinstance(value, dict):
        value = value.get("available") or value.get("count") or 0
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def _number(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _normalize_tunvn_products(payload: Any, provider: dict) -> list[dict]:
    products = []
    for raw in _as_list(payload, "products", "items"):
        if not isinstance(raw, dict) or raw.get("id") is None or not raw.get("name"):
            continue
        source_price = _number(raw.get("price_vnd"))
        usd_price = _number(raw.get("price_usdt"))
        products.append({
            "external_product_id": str(raw["id"]),
            "name": str(raw["name"]).strip(),
            "description": str(raw.get("description") or "").strip(),
            "base_price": usd_price,
            "source_price": source_price or usd_price,
            "source_currency": "VND" if source_price else "USD",
            "remote_stock": _positive_int(raw.get("stock")),
            "warranty_days": _positive_int(raw.get("warranty_days")),
            "image_url": str(raw.get("image_url") or "").strip(),
            "emoji": str(raw.get("emoji") or "\U0001f4e6"),
            "raw_payload": raw,
        })
    return products


def _normalize_akunding_products(payload: Any, provider: dict) -> list[dict]:
    products = []
    for raw in _as_list(payload, "products", "items"):
        if not isinstance(raw, dict) or raw.get("id") is None or not raw.get("name"):
            continue
        products.append({
            "external_product_id": str(raw["id"]),
            "name": str(raw["name"]).strip(),
            "description": "\n\n".join(
                part for part in (
                    str(raw.get("description") or "").strip(),
                    str(raw.get("features") or "").strip(),
                ) if part
            ),
            "base_price": _number(raw.get("base_price") or raw.get("price")),
            "source_price": _number(raw.get("base_price") or raw.get("price")),
            "source_currency": "USD",
            "remote_stock": _positive_int(raw.get("stock")),
            "warranty_days": _positive_int(raw.get("warranty_days")),
            "image_url": str(raw.get("image_url") or "").strip(),
            "emoji": str(raw.get("emoji") or "\U0001f4e6"),
            "raw_payload": raw,
        })
    return products


def _normalize_pixverify_products(payload: Any, provider: dict) -> list[dict]:
    products = []
    for raw in _as_list(payload, "categories", "products", "items"):
        if not isinstance(raw, dict) or raw.get("id") is None or not raw.get("name"):
            continue
        price = _number(raw.get("discounted_price") or raw.get("price_per_unit"))
        products.append({
            "external_product_id": str(raw["id"]),
            "name": str(raw["name"]).strip(),
            "description": str(raw.get("description") or "").strip(),
            "base_price": price,
            "source_price": price,
            "source_currency": "USD",
            "remote_stock": _positive_int(raw.get("stock")),
            "warranty_days": _positive_int(raw.get("warranty_days")),
            "image_url": str(raw.get("image_url") or "").strip(),
            "emoji": str(raw.get("emoji") or "\U0001f4e6"),
            "raw_payload": raw,
        })
    return products


async def list_products(provider: dict, units_per_usd: float) -> list[dict]:
    adapter = str(provider.get("adapter") or "canboso")
    if adapter == "canboso":
        payload = await _request(provider, "GET", "/api/telegram-buyer/products")
        products = normalize_products(payload)
        products = [
            product for product in products
            if not bool((product.get("raw_payload") or {}).get("requiresCustomerEmail"))
            and not bool((product.get("raw_payload") or {}).get("requiresSlotMonths"))
        ]
        base_url = str(provider["base_url"]).rstrip("/")
        for product in products:
            image_url = str(product.get("image_url") or "")
            if image_url.startswith("/"):
                product["image_url"] = f"{base_url}{image_url}"
        return products
    if adapter == "tunvn":
        return _normalize_tunvn_products(
            await _request(provider, "GET", "/api/products"), provider
        )
    if adapter == "akunding":
        payload = await _request(provider, "GET", "/api/v1/products")
        return _normalize_akunding_products(payload, provider)
    if adapter == "pixverify":
        payload = await _request(provider, "GET", "/api/v1/shop/categories")
        return _normalize_pixverify_products(payload, provider)
    if adapter == "safwan":
        products = normalize_products(await _request(provider, "GET", "/api/products"))
        base_url = str(provider["base_url"]).rstrip("/")
        for product in products:
            if str(product.get("image_url") or "").startswith("/"):
                product["image_url"] = f"{base_url}{product['image_url']}"
        return products
    raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")


def _normalize_balance(payload: Any, adapter: str, units_per_usd: float) -> dict:
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise SupplierAPIError("Supplier returned an invalid balance response")
    if adapter == "canboso":
        currency = str(payload.get("walletCurrency") or "USD").upper()
        raw = payload.get("balanceUsd") if payload.get("balanceUsd") is not None else payload.get("balance")
        balance = _number(raw)
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD"}
    if adapter == "tunvn":
        balance = _number(payload.get("balance_usdt"))
        if balance <= 0 and _number(payload.get("balance_vnd")) > 0:
            balance = _number(payload.get("balance_vnd")) / max(1.0, units_per_usd)
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD"}
    if adapter == "akunding":
        balance = _number(payload.get("balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD"}
    if adapter == "pixverify":
        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
        balance = _number(profile.get("api_usable_balance") or profile.get("topup_credit_balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD"}
    if adapter == "safwan":
        balance = _number(payload.get("balance") or payload.get("wallet_balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD"}
    raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")


async def get_balance(
    provider: dict, units_per_usd: float, *, force: bool = False
) -> dict:
    code = str(provider["code"])
    now = time.monotonic()
    cached = _BALANCE_CACHE.get(code)
    if cached and not force and now - cached[0] < _BALANCE_CACHE_SECONDS:
        return dict(cached[1])
    lock = _BALANCE_LOCKS.setdefault(code, asyncio.Lock())
    async with lock:
        cached = _BALANCE_CACHE.get(code)
        if cached and not force and time.monotonic() - cached[0] < _BALANCE_CACHE_SECONDS:
            return dict(cached[1])
        adapter = str(provider.get("adapter") or "canboso")
        path = {
            "canboso": "/api/telegram-buyer/balance",
            "tunvn": "/api/balance",
            "akunding": "/api/v1/me",
            "pixverify": "/api/v1/profile",
            "safwan": "/api/balance",
        }.get(adapter)
        if not path:
            raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")
        try:
            balance = _normalize_balance(
                await _request(provider, "GET", path), adapter, units_per_usd
            )
        except SupplierAPIError:
            if cached:
                stale = dict(cached[1])
                stale["stale"] = True
                return stale
            raise
        _BALANCE_CACHE[code] = (time.monotonic(), dict(balance))
        return balance


def _generic_purchase(payload: Any, quantity: int) -> dict:
    if not isinstance(payload, dict):
        raise SupplierAPIError("Supplier purchase response is not an object", outcome_unknown=True)
    if payload.get("success") is False:
        raise SupplierAPIError(_payload_error(payload))
    order = payload.get("order") if isinstance(payload.get("order"), dict) else payload
    values = (
        order.get("credentials")
        or order.get("items")
        or order.get("accounts")
        or order.get("delivered_items")
        or order.get("products")
        or order.get("data")
        or []
    )
    if isinstance(values, str):
        values = [values]
    if isinstance(values, dict):
        values = [values]
    items = []
    for value in values if isinstance(values, list) else []:
        if isinstance(value, dict):
            content = value.get("account_data") or value.get("content") or value.get("credential") or value.get("data")
            if content is None:
                content = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            content = value
        if content not in (None, ""):
            items.append({"account_data": str(content)})
    if len(items) < quantity:
        raise SupplierAPIError(
            "Supplier purchase response did not contain all delivery items",
            outcome_unknown=True,
        )
    external_id = order.get("order_id") or order.get("orderCode") or order.get("id") or order.get("order_group")
    return {"external_order_id": str(external_id or ""), "items": items, "raw_payload": payload}


def _payload_error(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or "Purchase rejected")
    return str(payload.get("message") or error or payload.get("detail") or "Purchase rejected")


async def purchase(provider: dict, product_id: str, quantity: int) -> dict:
    adapter = str(provider.get("adapter") or "canboso")
    quantity = max(1, int(quantity))
    if adapter == "canboso":
        payload = await _request(
            provider,
            "POST",
            "/api/telegram-buyer/purchase",
            json={"key": provider["api_key"], "product_id": product_id, "quantity": quantity},
        )
        result = normalize_purchase(payload)
        if len(result["items"]) < quantity:
            raise SupplierAPIError(
                "Supplier purchase response did not contain all delivery items",
                outcome_unknown=True,
            )
    else:
        path = {"tunvn": "/api/buy", "akunding": "/api/v1/orders", "pixverify": "/api/v1/shop/buy", "safwan": "/api/order"}.get(adapter)
        if not path:
            raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")
        key = "category_id" if adapter == "pixverify" else "product_id"
        payload = await _request(
            provider, "POST", path, json={key: int(product_id), "quantity": quantity}
        )
        result = _generic_purchase(payload, quantity)
    _BALANCE_CACHE.pop(str(provider["code"]), None)
    return result


async def close_clients() -> None:
    for client in list(_CLIENTS.values()):
        if not client.is_closed:
            await client.aclose()
    _CLIENTS.clear()
    _BALANCE_CACHE.clear()
    _BALANCE_LOCKS.clear()


__all__ = ["close_clients", "get_balance", "list_products", "purchase"]
