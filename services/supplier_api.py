"""Outbound client for the Canboso Telegram buyer API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from config import CANBOSO_API_AUTH_HEADER, CANBOSO_API_BASE_URL, CANBOSO_API_KEY


logger = logging.getLogger(__name__)
_CLIENT: httpx.AsyncClient | None = None


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
    global _CLIENT
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
    _CLIENT = None


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
        external_id = raw.get("id", raw.get("product_id", raw.get("productId")))
        name = raw.get("name", raw.get("title", raw.get("product_name")))
        price = raw.get("price_usd", raw.get("price", raw.get("unit_price")))
        if external_id is None or not name or price is None:
            continue
        try:
            price_value = round(float(price), 4)
        except (TypeError, ValueError):
            continue
        stock = raw.get("stock", raw.get("available_stock", raw.get("quantity", raw.get("available", 0))))
        if isinstance(stock, bool):
            stock_value = 999999 if stock else 0
        else:
            try:
                stock_value = max(0, int(float(stock or 0)))
            except (TypeError, ValueError):
                stock_value = 0
        products.append({
            "external_product_id": str(external_id),
            "name": str(name).strip(),
            "description": str(raw.get("description") or raw.get("details") or "").strip(),
            "base_price": price_value,
            "remote_stock": stock_value,
            "warranty_days": max(0, int(raw.get("warranty_days") or raw.get("warranty") or 0)),
            "image_url": str(raw.get("image_url") or raw.get("image") or "").strip(),
            "emoji": str(raw.get("emoji") or "📦").strip() or "📦",
            "raw_payload": raw,
        })
    return products


async def list_canboso_products() -> list[dict]:
    payload = await _request("GET", "/api/telegram-buyer/products")
    products = normalize_products(payload)
    if not products and payload not in ([], {}, None):
        logger.warning("Canboso catalog response contained no recognizable products")
    return products


def _delivery_values(payload: Any) -> list[Any]:
    values = _unwrap_list(payload, ("items", "accounts", "credentials", "products", "deliveries"))
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
            if value is None:
                value = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        else:
            value = item
        if value not in (None, ""):
            items.append({"account_data": str(value)})
    external_order_id = payload.get("order_id", payload.get("purchase_id", payload.get("id")))
    return {
        "external_order_id": str(external_order_id or ""),
        "items": items,
        "raw_payload": payload,
    }


async def purchase_canboso_product(product_id: str, quantity: int) -> dict:
    payload = await _request(
        "POST",
        "/api/telegram-buyer/purchase",
        json={"product_id": product_id, "quantity": max(1, int(quantity))},
    )
    result = normalize_purchase(payload)
    if len(result["items"]) < max(1, int(quantity)):
        raise SupplierAPIError(
            "Canboso purchase response did not contain all delivery items",
            outcome_unknown=True,
        )
    return result
