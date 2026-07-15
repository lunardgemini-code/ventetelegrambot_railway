"""Provider registry and dispatch for external supplier bots."""

from __future__ import annotations

from config import (
    CANBOSO_API_BASE_URL,
    NANLUX_API_BASE_URL,
    NANLUX_VND_PER_USD,
)
from services.supplier_api import SupplierAPIError


PROVIDERS = {
    "canboso": {
        "code": "canboso",
        "name": "Canboso",
        "base_url": CANBOSO_API_BASE_URL,
        "source_currency": "USD",
        "default_units_per_usd": 1.0,
        "credential_env": "CANBOSO_API_KEY",
    },
    "nanlux": {
        "code": "nanlux",
        "name": "MMO NanLux",
        "base_url": NANLUX_API_BASE_URL,
        "source_currency": "VND",
        "default_units_per_usd": float(NANLUX_VND_PER_USD),
        "credential_env": "NANLUX_API_KEY",
    },
}


def get_supplier_provider(supplier_code: str) -> dict:
    code = str(supplier_code or "").strip().lower()
    provider = PROVIDERS.get(code)
    if not provider:
        raise ValueError("SUPPLIER_NOT_FOUND")
    return dict(provider)


def list_supplier_providers() -> list[dict]:
    return [dict(provider) for provider in PROVIDERS.values()]


def is_supplier_configured(supplier_code: str) -> bool:
    code = get_supplier_provider(supplier_code)["code"]
    if code == "canboso":
        from services.supplier_api import is_canboso_configured

        return is_canboso_configured()
    from services.nanlux_api import is_nanlux_configured

    return is_nanlux_configured()


async def list_supplier_products(
    supplier_code: str, *, units_per_usd: float
) -> list[dict]:
    code = get_supplier_provider(supplier_code)["code"]
    if code == "canboso":
        from services.supplier_api import list_canboso_products

        return await list_canboso_products()
    from services.nanlux_api import list_nanlux_products

    return await list_nanlux_products(units_per_usd)


async def get_supplier_balance(
    supplier_code: str, *, units_per_usd: float, force: bool = False
) -> dict:
    code = get_supplier_provider(supplier_code)["code"]
    if code == "canboso":
        from services.supplier_api import get_canboso_balance

        return await get_canboso_balance(force=force)
    from services.nanlux_api import get_nanlux_balance

    return await get_nanlux_balance(units_per_usd, force=force)


async def purchase_supplier_product(
    supplier_code: str,
    product_id: str,
    quantity: int,
    *,
    buyer_info: str = "",
) -> dict:
    code = get_supplier_provider(supplier_code)["code"]
    if code == "canboso":
        from services.supplier_api import purchase_canboso_product

        return await purchase_canboso_product(product_id, quantity)
    from services.nanlux_api import purchase_nanlux_product

    return await purchase_nanlux_product(
        product_id, quantity, buyer_info=buyer_info
    )


async def close_supplier_clients() -> None:
    from services.nanlux_api import close_nanlux_client
    from services.supplier_api import close_supplier_client

    await close_supplier_client()
    await close_nanlux_client()


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
