"""HTTP adapters for dynamically configured external supplier accounts."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

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


def _normalized_product(
    raw: dict,
    *,
    external_id: Any,
    name: Any,
    price: Any,
    stock: Any,
    source_currency: str = "USD",
    units_per_usd: float = 1.0,
    description: Any = "",
    image_url: Any = "",
) -> dict | None:
    if external_id is None or not str(name or "").strip():
        return None
    source_price = _number(price)
    if source_price <= 0:
        return None
    currency = str(source_currency or "USD").upper()
    if currency in {"USDT", "USDC"}:
        currency = "USD"
    base_price = (
        source_price / max(1.0, float(units_per_usd or 1))
        if currency != "USD"
        else source_price
    )
    return {
        "external_product_id": str(external_id),
        "name": str(name).strip(),
        "description": str(description or "").strip(),
        "base_price": round(base_price, 4),
        "source_price": source_price,
        "source_currency": currency,
        "remote_stock": _positive_int(stock),
        "warranty_days": _positive_int(
            raw.get("warranty_days") or raw.get("warrantyDays")
        ),
        "image_url": str(image_url or "").strip(),
        "emoji": str(raw.get("emoji") or "\U0001f4e6"),
        "raw_payload": raw,
    }


def _normalize_zoom_products(payload: Any, units_per_usd: float) -> list[dict]:
    products = []
    for raw in _as_list(payload, "products", "items"):
        if not isinstance(raw, dict):
            continue
        stock = raw.get("stock")
        if stock is None and raw.get("in_stock") is True:
            stock = 999999
        product = _normalized_product(
            raw,
            external_id=raw.get("id"),
            name=raw.get("name"),
            price=raw.get("price"),
            stock=stock,
            source_currency=raw.get("currency") or "USD",
            units_per_usd=units_per_usd,
            description=raw.get("description"),
            image_url=raw.get("image_url") or raw.get("image"),
        )
        if product:
            products.append(product)
    return products


def _normalize_cat_products(payload: Any, units_per_usd: float) -> list[dict]:
    products = []
    for raw in _as_list(payload, "data", "products", "items"):
        if not isinstance(raw, dict):
            continue
        product = _normalized_product(
            raw,
            external_id=raw.get("id"),
            name=raw.get("name"),
            price=raw.get("price"),
            stock=raw.get("stock"),
            source_currency="VND",
            units_per_usd=units_per_usd,
            description=raw.get("description"),
            image_url=raw.get("image_url") or raw.get("image"),
        )
        if product:
            products.append(product)
    return products


def _normalize_goldfish_products(payload: Any, units_per_usd: float) -> list[dict]:
    products = []
    for raw in _as_list(payload, "data", "products", "items"):
        if not isinstance(raw, dict) or bool(raw.get("requires_input")):
            continue
        product = _normalized_product(
            raw,
            external_id=raw.get("id"),
            name=raw.get("name"),
            price=raw.get("price"),
            stock=raw.get("quantity"),
            source_currency="VND",
            units_per_usd=units_per_usd,
            description=raw.get("description") or raw.get("category"),
            image_url=raw.get("image_url") or raw.get("image"),
        )
        if product:
            products.append(product)
    return products


def _normalize_robotic_product(payload: Any, units_per_usd: float) -> list[dict]:
    raw_product = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(raw_product, dict):
        return []
    products = []
    parent_title = str(raw_product.get("title") or "").strip()
    for variant in raw_product.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        prices = variant.get("prices") if isinstance(variant.get("prices"), dict) else {}
        usd_price = _number(prices.get("usd"))
        currency = "USD" if usd_price > 0 else "VND"
        source_price = usd_price or _number(prices.get("vnd"))
        variant_title = str(variant.get("title") or "").strip()
        name = " - ".join(part for part in (parent_title, variant_title) if part)
        raw = {
            **variant,
            "parent_product_id": raw_product.get("id"),
            "parent_title": parent_title,
        }
        product = _normalized_product(
            raw,
            external_id=variant.get("id"),
            name=name,
            price=source_price,
            stock=(
                variant.get("available_quantity")
                if variant.get("in_stock") is not False
                else 0
            ),
            source_currency=currency,
            units_per_usd=units_per_usd,
            description=raw_product.get("description"),
            image_url=raw_product.get("thumbnail"),
        )
        if product:
            products.append(product)
    return products


async def _list_robotic_products(provider: dict, units_per_usd: float) -> list[dict]:
    payload = await _request(
        provider,
        "GET",
        "/api/v2/products",
        params={"limit": 100, "offset": 0, "locale": "en-US"},
    )
    summaries = _as_list(payload, "data", "products", "items")
    semaphore = asyncio.Semaphore(6)

    async def load(raw: Any) -> Any:
        product_id = raw.get("id") if isinstance(raw, dict) else None
        if not product_id:
            return None
        async with semaphore:
            return await _request(
                provider,
                "GET",
                f"/api/v2/products/{quote(str(product_id), safe='')}",
                params={"locale": "en-US"},
            )

    details = await asyncio.gather(*(load(raw) for raw in summaries), return_exceptions=True)
    products = []
    failures = 0
    for detail in details:
        if isinstance(detail, Exception) or detail is None:
            failures += 1
            continue
        products.extend(_normalize_robotic_product(detail, units_per_usd))
    if summaries and not products:
        raise SupplierAPIError(
            f"{provider['name']} product details are temporarily unavailable",
            retryable=True,
        )
    if failures:
        logger.warning(
            "%s catalog skipped %d unavailable product detail(s)",
            provider["name"],
            failures,
        )
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
    if adapter == "roboticvn":
        return await _list_robotic_products(provider, units_per_usd)
    if adapter == "zoom":
        return _normalize_zoom_products(
            await _request(provider, "GET", "/products"), units_per_usd
        )
    if adapter == "cat_ai":
        return _normalize_cat_products(
            await _request(provider, "GET", "/api/v1/telehub/products"),
            units_per_usd,
        )
    if adapter == "goldfish":
        return _normalize_goldfish_products(
            await _request(provider, "GET", "/products"), units_per_usd
        )
    raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")


def _normalize_balance(payload: Any, adapter: str, units_per_usd: float) -> dict:
    from services.supplier_identity import extract_supplier_identity

    if (
        not isinstance(payload, dict)
        or payload.get("success") is False
        or payload.get("error") is True
    ):
        raise SupplierAPIError("Supplier returned an invalid balance response")
    identity = extract_supplier_identity(payload)
    if adapter == "canboso":
        currency = str(payload.get("walletCurrency") or "USD").upper()
        raw = payload.get("balanceUsd") if payload.get("balanceUsd") is not None else payload.get("balance")
        balance = _number(raw)
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "tunvn":
        balance = _number(payload.get("balance_usdt"))
        if balance <= 0 and _number(payload.get("balance_vnd")) > 0:
            balance = _number(payload.get("balance_vnd")) / max(1.0, units_per_usd)
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "akunding":
        balance = _number(payload.get("balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "pixverify":
        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
        balance = _number(profile.get("api_usable_balance") or profile.get("topup_credit_balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "safwan":
        balance = _number(payload.get("balance") or payload.get("wallet_balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "roboticvn":
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        balance = _number(data.get("usd"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter == "zoom":
        balance = _number(payload.get("balance"))
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
    if adapter in {"cat_ai", "goldfish"}:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        raw_balance = _number(data.get("balance"))
        balance = raw_balance / max(1.0, units_per_usd)
        return {"balance": balance, "currency": "USD", "balance_text": f"{balance:.2f} USD", **identity}
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
            "roboticvn": "/api/v2/wallet/balance",
            "zoom": "/balance",
            "cat_ai": "/api/v1/telehub/user",
            "goldfish": "/balance",
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


def _delivery_values(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return [payload] if payload not in (None, "") else []
    for key in (
        "credentials", "items", "accounts", "delivered_items", "codes",
        "deliveredAccount", "delivered_accounts", "deliveries", "products",
    ):
        values = payload.get(key)
        if isinstance(values, list) and values:
            return values
        if isinstance(values, str) and values:
            return [values]
    for key in ("data", "result", "order", "purchase", "delivery"):
        nested = payload.get(key)
        if isinstance(nested, (dict, list)):
            values = _delivery_values(nested)
            if values:
                return values
    if any(payload.get(key) not in (None, "") for key in (
        "account_data", "content", "credential", "account", "password"
    )):
        return [payload]
    return []


def _delivery_content(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "")
    direct = value.get("account_data") or value.get("content") or value.get("credential")
    if direct not in (None, ""):
        return str(direct)
    parts = [
        value.get("account") or value.get("user") or value.get("username"),
        value.get("password"),
        value.get("additional_info") or value.get("note"),
    ]
    if any(part not in (None, "") for part in parts):
        return " | ".join(str(part) for part in parts if part not in (None, ""))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _generic_purchase(payload: Any, quantity: int) -> dict:
    if not isinstance(payload, dict):
        raise SupplierAPIError("Supplier purchase response is not an object", outcome_unknown=True)
    if payload.get("success") is False:
        raise SupplierAPIError(_payload_error(payload))
    order = payload.get("order") if isinstance(payload.get("order"), dict) else payload
    values = _delivery_values(order)
    items = []
    for value in values:
        content = _delivery_content(value)
        if content not in (None, ""):
            items.append({"account_data": str(content)})
    if len(items) < quantity:
        raise SupplierAPIError(
            "Supplier purchase response did not contain all delivery items",
            outcome_unknown=True,
        )
    external_id = order.get("order_id") or order.get("orderCode") or order.get("id") or order.get("order_group")
    if not external_id and isinstance(order.get("data"), dict):
        data = order["data"]
        external_id = (
            data.get("order_id") or data.get("orderCode")
            or data.get("id") or data.get("order_group")
        )
    return {"external_order_id": str(external_id or ""), "items": items, "raw_payload": payload}


def _payload_error(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or "Purchase rejected")
    return str(payload.get("message") or error or payload.get("detail") or "Purchase rejected")


def _purchase_idempotency_key(
    provider: dict,
    product_id: str,
    quantity: int,
    buyer_info: str,
) -> str:
    identity = str(buyer_info or "").strip() or uuid4().hex
    raw = f"{provider['code']}:{identity}:{product_id}:{quantity}".encode("utf-8")
    return f"ventebot-{hashlib.sha256(raw).hexdigest()[:40]}"


async def _purchase_roboticvn(
    provider: dict,
    product_id: str,
    quantity: int,
) -> dict:
    payload = await _request(
        provider,
        "POST",
        "/api/v2/orders",
        params={"locale": "en-US"},
        json={
            "items": [{"variant_id": product_id, "quantity": quantity}],
            "currency_code": "usd",
            "payment_method": "wallet",
        },
    )
    data = payload.get("data") if isinstance(payload, dict) else None
    order_id = data.get("order_id") if isinstance(data, dict) else None
    if not order_id:
        raise SupplierAPIError(
            "ROBOTICVN accepted an order without an order id",
            outcome_unknown=True,
        )
    delivery_path = f"/api/v2/orders/{quote(str(order_id), safe='')}/delivery"
    for attempt in range(6):
        if attempt:
            await asyncio.sleep(1.0)
        try:
            delivery = await _request(
                provider,
                "GET",
                delivery_path,
                params={"locale": "en-US"},
            )
            if len(_delivery_values(delivery)) < quantity:
                continue
            result = _generic_purchase(delivery, quantity)
            result["external_order_id"] = str(order_id)
            return result
        except SupplierAPIError as exc:
            if exc.status_code not in {404, 409, 425} and not exc.retryable:
                raise SupplierAPIError(str(exc), outcome_unknown=True) from exc
    raise SupplierAPIError(
        "ROBOTICVN order is accepted but delivery is still pending",
        retryable=True,
        outcome_unknown=True,
    )


async def purchase(
    provider: dict,
    product_id: str,
    quantity: int,
    *,
    buyer_info: str = "",
) -> dict:
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
    elif adapter == "roboticvn":
        result = await _purchase_roboticvn(provider, product_id, quantity)
    else:
        path = {
            "tunvn": "/api/buy",
            "akunding": "/api/v1/orders",
            "pixverify": "/api/v1/shop/buy",
            "safwan": "/api/order",
            "zoom": "/purchase",
            "cat_ai": "/api/v1/telehub/buy",
            "goldfish": "/order",
        }.get(adapter)
        if not path:
            raise SupplierAPIError(f"Unsupported supplier adapter: {adapter}")
        key = "category_id" if adapter == "pixverify" else "product_id"
        product_value: Any = (
            str(product_id) if adapter in {"zoom", "goldfish"} else int(product_id)
        )
        kwargs: dict[str, Any] = {
            "json": {key: product_value, "quantity": quantity}
        }
        if adapter == "goldfish":
            kwargs = {"params": {key: product_value, "quantity": quantity}}
        elif adapter == "zoom":
            kwargs["headers"] = {
                "Idempotency-Key": _purchase_idempotency_key(
                    provider, product_id, quantity, buyer_info
                )
            }
        payload = await _request(provider, "POST", path, **kwargs)
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
