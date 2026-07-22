"""Security helpers for reseller IP rules and signed outbound webhooks."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import os
import socket
from dataclasses import dataclass
from urllib.parse import quote, urlparse


def normalize_ip_allowlist(values: list[str] | str | None) -> list[str]:
    if isinstance(values, str):
        raw = values.strip()
        if not raw:
            values = []
        else:
            try:
                decoded = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                decoded = [item.strip() for item in raw.split(",")]
            values = decoded if isinstance(decoded, list) else []
    normalized: list[str] = []
    for raw_value in values or []:
        value = str(raw_value or "").strip()
        if not value:
            continue
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid IP or CIDR: {value}") from exc
        canonical = str(network)
        if canonical not in normalized:
            normalized.append(canonical)
    if len(normalized) > 20:
        raise ValueError("A maximum of 20 IP or CIDR entries is allowed")
    return normalized


def request_client_ip(request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for") or "").strip()
    candidate = forwarded.split(",")[-1].strip() if forwarded else ""
    if not candidate and getattr(request, "client", None):
        candidate = str(request.client.host or "").strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return candidate


def ip_is_allowed(client_ip: str, allowlist: list[str] | str | None) -> bool:
    entries = normalize_ip_allowlist(allowlist)
    if not entries:
        return True
    try:
        address = ipaddress.ip_address(str(client_ip or "").strip())
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(entry) for entry in entries)


def _webhook_master_secret() -> str:
    secret = os.environ.get("RESELLER_WEBHOOK_MASTER_SECRET", "").strip()
    if not secret:
        raise RuntimeError("Reseller webhook signing is not configured")
    return secret


def derive_webhook_secret(key_prefix: str, salt: str) -> str:
    material = f"ventebot-reseller-webhook:{key_prefix}:{salt}".encode("utf-8")
    digest = hmac.new(
        _webhook_master_secret().encode("utf-8"),
        material,
        hashlib.sha256,
    ).hexdigest()
    return f"vbr_whsec_{digest}"


def canonical_webhook_body(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sign_webhook_body(secret: str, timestamp: int, body: bytes) -> str:
    signed = str(int(timestamp)).encode("ascii") + b"." + body
    signature = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"v1={signature}"


def _public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


async def validate_webhook_url(webhook_url: str) -> str:
    target = await resolve_webhook_target(webhook_url)
    return target.url if target else ""


@dataclass(frozen=True)
class ResolvedWebhookTarget:
    url: str
    hostname: str
    authority: str
    port: int
    request_target: str
    addresses: tuple[str, ...]


async def resolve_webhook_target(webhook_url: str) -> ResolvedWebhookTarget | None:
    """Resolve and freeze a public HTTPS webhook destination for one delivery."""
    value = str(webhook_url or "").strip()
    if not value:
        return None
    if any(ord(character) < 32 for character in value):
        raise ValueError("Webhook URL contains invalid control characters")
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Webhook URL must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Webhook URL cannot contain credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Webhook URL contains an invalid port") from exc
    if port not in (None, 443):
        raise ValueError("Webhook URL must use HTTPS port 443")
    if parsed.fragment:
        raise ValueError("Webhook URL cannot contain a fragment")

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Webhook hostname is invalid") from exc

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port or 443,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ValueError("Webhook hostname could not be resolved") from exc
    addresses = {str(info[4][0]) for info in infos if info and info[4]}
    if not addresses or any(not _public_address(address) for address in addresses):
        raise ValueError("Webhook URL must resolve only to public IP addresses")
    request_target = quote(
        parsed.path or "/",
        safe="/%:@!$&'()*+,;=-._~",
    )
    if parsed.params:
        request_target += ";" + quote(parsed.params, safe="!$&'()*+,;=:@-._~")
    if parsed.query:
        request_target += "?" + quote(
            parsed.query,
            safe="=&?/:;+,%@[]-._~!$'()*",
        )
    authority = f"[{hostname}]" if ":" in hostname else hostname
    return ResolvedWebhookTarget(
        url=value,
        hostname=hostname,
        authority=authority,
        port=443,
        request_target=request_target,
        addresses=tuple(sorted(addresses)),
    )
