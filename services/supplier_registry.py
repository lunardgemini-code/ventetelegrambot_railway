"""Provider registry and dispatch for external supplier bots.

Dynamic account credentials are loaded from ``SUPPLIER_ACCOUNTS_JSON``. Public
registry helpers deliberately omit the credential value.
"""

from __future__ import annotations

import json
import logging
import os
import re

from config import (
    CANBOSO_API_AUTH_HEADER,
    CANBOSO_API_BASE_URL,
    CANBOSO_API_KEY,
    NANLUX_API_AUTH_HEADER,
    NANLUX_API_BASE_URL,
    NANLUX_API_KEY,
    NANLUX_VND_PER_USD,
)
from services.supplier_api import SupplierAPIError


logger = logging.getLogger(__name__)

_PUBLIC_FIELDS = {
    "code", "name", "base_url", "source_currency", "default_units_per_usd",
    "credential_env", "adapter", "docs_url",
}

_PROVIDER_CONFIGS = {
    "canboso": {
        "code": "canboso",
        "name": "Canboso",
        "base_url": CANBOSO_API_BASE_URL,
        "source_currency": "USD",
        "default_units_per_usd": 1.0,
        "credential_env": "CANBOSO_API_KEY",
        "adapter": "canboso",
        "api_key": CANBOSO_API_KEY,
        "auth_mode": "header",
        "auth_header": CANBOSO_API_AUTH_HEADER,
        "docs_url": "https://canboso.com/api/swagger/",
    },
    "nanlux": {
        "code": "nanlux",
        "name": "MMO NanLux",
        "base_url": NANLUX_API_BASE_URL,
        "source_currency": "VND",
        "default_units_per_usd": float(NANLUX_VND_PER_USD),
        "credential_env": "NANLUX_API_KEY",
        "adapter": "nanlux",
        "api_key": NANLUX_API_KEY,
        "auth_mode": "header",
        "auth_header": NANLUX_API_AUTH_HEADER,
        "docs_url": "",
    },
}


def _load_dynamic_providers() -> None:
    raw = os.environ.get("SUPPLIER_ACCOUNTS_JSON", "").strip()
    if not raw:
        return
    try:
        accounts = json.loads(raw)
        if not isinstance(accounts, list):
            raise ValueError("expected a JSON array")
        for account in accounts:
            if not isinstance(account, dict):
                continue
            code = re.sub(r"[^a-z0-9_-]+", "_", str(account.get("code") or "").lower()).strip("_")
            adapter = str(account.get("adapter") or "canboso").strip().lower()
            base_url = str(account.get("base_url") or "").strip().rstrip("/")
            if not code or code in _PROVIDER_CONFIGS or adapter not in {
                "canboso", "tunvn", "akunding", "pixverify", "safwan"
            } or not base_url.startswith("https://"):
                continue
            source_currency = str(account.get("source_currency") or "USD").upper()
            default_rate = account.get("default_units_per_usd") or (25000 if source_currency == "VND" else 1)
            _PROVIDER_CONFIGS[code] = {
                "code": code,
                "name": str(account.get("name") or code)[:80],
                "base_url": base_url,
                "source_currency": source_currency,
                "default_units_per_usd": max(1.0, float(default_rate)),
                "credential_env": f"SUPPLIER_ACCOUNTS_JSON[{code}]",
                "adapter": adapter,
                "api_key": str(account.get("api_key") or "").strip(),
                "auth_mode": str(account.get("auth_mode") or "header").lower(),
                "auth_header": str(account.get("auth_header") or "X-API-Key"),
                "docs_url": str(account.get("docs_url") or ""),
            }
    except Exception as exc:
        logger.error("SUPPLIER_ACCOUNTS_JSON is invalid: %s", exc)


_load_dynamic_providers()
# Backwards-compatible public constant. It never contains credentials.
PROVIDERS = {
    code: {key: value for key, value in provider.items() if key in _PUBLIC_FIELDS}
    for code, provider in _PROVIDER_CONFIGS.items()
}


def _provider_config(supplier_code: str) -> dict:
    code = str(supplier_code or "").strip().lower()
    provider = _PROVIDER_CONFIGS.get(code)
    if not provider:
        raise ValueError("SUPPLIER_NOT_FOUND")
    return dict(provider)


def get_supplier_provider(supplier_code: str) -> dict:
    code = str(supplier_code or "").strip().lower()
    provider = PROVIDERS.get(code)
    if not provider:
        raise ValueError("SUPPLIER_NOT_FOUND")
    return dict(provider)


def list_supplier_providers() -> list[dict]:
    return [dict(provider) for provider in PROVIDERS.values()]


def is_supplier_configured(supplier_code: str) -> bool:
    provider = _provider_config(supplier_code)
    code = provider["code"]
    if code == "canboso":
        from services.supplier_api import is_canboso_configured

        return is_canboso_configured()
    if code == "nanlux":
        from services.nanlux_api import is_nanlux_configured

        return is_nanlux_configured()
    return bool(provider.get("api_key") and provider["base_url"].startswith("https://"))


async def list_supplier_products(
    supplier_code: str, *, units_per_usd: float
) -> list[dict]:
    provider = _provider_config(supplier_code)
    code = provider["code"]
    if code == "canboso":
        from services.supplier_api import list_canboso_products

        return await list_canboso_products()
    if code == "nanlux":
        from services.nanlux_api import list_nanlux_products

        return await list_nanlux_products(units_per_usd)
    from services.supplier_multi_api import list_products

    return await list_products(provider, units_per_usd)


async def get_supplier_balance(
    supplier_code: str, *, units_per_usd: float, force: bool = False
) -> dict:
    provider = _provider_config(supplier_code)
    code = provider["code"]
    if code == "canboso":
        from services.supplier_api import get_canboso_balance

        return await get_canboso_balance(force=force)
    if code == "nanlux":
        from services.nanlux_api import get_nanlux_balance

        return await get_nanlux_balance(units_per_usd, force=force)
    from services.supplier_multi_api import get_balance

    return await get_balance(provider, units_per_usd, force=force)


async def purchase_supplier_product(
    supplier_code: str,
    product_id: str,
    quantity: int,
    *,
    buyer_info: str = "",
) -> dict:
    provider = _provider_config(supplier_code)
    code = provider["code"]
    if code == "canboso":
        from services.supplier_api import purchase_canboso_product

        return await purchase_canboso_product(product_id, quantity)
    if code == "nanlux":
        from services.nanlux_api import purchase_nanlux_product

        return await purchase_nanlux_product(
            product_id, quantity, buyer_info=buyer_info
        )
    from services.supplier_multi_api import purchase

    return await purchase(provider, product_id, quantity)


async def close_supplier_clients() -> None:
    from services.nanlux_api import close_nanlux_client
    from services.supplier_api import close_supplier_client
    from services.supplier_multi_api import close_clients

    await close_supplier_client()
    await close_nanlux_client()
    await close_clients()


__all__ = [
    "SupplierAPIError",
    "close_supplier_clients",
    "get_supplier_balance",
    "get_supplier_provider",
    "is_supplier_configured",
    "list_supplier_products",
    "list_supplier_providers",
    "purchase_supplier_product",
]
