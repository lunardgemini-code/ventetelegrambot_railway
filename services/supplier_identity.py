"""Extract safe display identities from supplier account responses."""

from __future__ import annotations

import re
from typing import Any


_MAX_NAME_LENGTH = 80
_EMPTY_NAMES = {"", "none", "null", "unknown", "n/a", "-"}
_GENERIC_SOURCES = {
    "api", "binance", "bot", "crypto", "telegram", "wallet",
}


def _clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    name = re.sub(r"\s+", " ", value).strip()
    if name.lower() in _EMPTY_NAMES:
        return ""
    return name[:_MAX_NAME_LENGTH]


def extract_supplier_identity(payload: Any) -> dict[str, str]:
    """Return whitelisted identity fields without copying credentials or payloads."""
    if not isinstance(payload, dict):
        return {}

    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    requester = payload.get("requester") if isinstance(payload.get("requester"), dict) else {}
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}

    bot_source = ""
    for key in (
        "botSource", "bot_source", "botName", "bot_name", "shopName",
        "shop_name", "storeName", "store_name",
    ):
        bot_source = _clean_name(payload.get(key))
        if bot_source:
            break

    account_name = ""
    for container in (requester, profile, user, payload):
        for key in ("display_name", "displayName", "name", "username"):
            account_name = _clean_name(container.get(key))
            if account_name:
                break
        if account_name:
            break

    provider_name = (
        bot_source
        if bot_source and bot_source.lower() not in _GENERIC_SOURCES
        else account_name
    )
    return {
        key: value
        for key, value in {
            "provider_name": provider_name,
            "bot_source": bot_source,
            "account_name": account_name,
        }.items()
        if value
    }


__all__ = ["extract_supplier_identity"]
