"""Durable, signed webhook delivery for reseller deposit events."""

from __future__ import annotations

import hashlib
import asyncio
import logging
import ssl
import time
from datetime import datetime, timezone

from database.jobs import create_background_job_once
from database.models import (
    get_reseller_api_security,
    get_reseller_deposit_by_payment_id,
    public_reseller_deposit,
)
from services.reseller_security import (
    canonical_webhook_body,
    derive_webhook_secret,
    resolve_webhook_target,
    sign_webhook_body,
)
from services.runtime_metrics import dependency_call


logger = logging.getLogger(__name__)
async def close_reseller_webhook_client() -> None:
    return None


async def _post_pinned_webhook(target, body: bytes, headers: dict[str, str]) -> int:
    """POST to a validated IP while preserving TLS SNI and the HTTP Host."""
    ssl_context = ssl.create_default_context()
    safe_headers = {
        str(name): str(value)
        for name, value in headers.items()
        if "\r" not in str(name) + str(value) and "\n" not in str(name) + str(value)
    }
    request_headers = {
        "Host": target.authority,
        "User-Agent": "VenteBot-Reseller-Webhook/1.0",
        "Accept": "application/json",
        "Connection": "close",
        "Content-Length": str(len(body)),
        **safe_headers,
    }
    request = (
        f"POST {target.request_target} HTTP/1.1\r\n"
        + "".join(f"{name}: {value}\r\n" for name, value in request_headers.items())
        + "\r\n"
    ).encode("ascii") + body

    last_error: Exception | None = None
    for address in target.addresses:
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    address,
                    target.port,
                    ssl=ssl_context,
                    server_hostname=target.hostname,
                ),
                timeout=5.0,
            )
            writer.write(request)
            await asyncio.wait_for(writer.drain(), timeout=5.0)
            response_head = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"),
                timeout=10.0,
            )
            status_line = response_head.split(b"\r\n", 1)[0].decode("ascii", "replace")
            parts = status_line.split(" ", 2)
            if len(parts) < 2 or not parts[1].isdigit():
                raise RuntimeError("Reseller webhook returned an invalid HTTP response")
            return int(parts[1])
        except (
            OSError,
            asyncio.TimeoutError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ) as exc:
            last_error = exc
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
    raise RuntimeError("Reseller webhook connection failed") from last_error


def _event_type(status: str) -> str:
    return f"deposit.{str(status or 'creating').strip().lower()}"


async def enqueue_reseller_deposit_webhook(deposit: dict | None) -> bool:
    public = public_reseller_deposit(deposit)
    if not deposit or not public:
        return False
    security = await get_reseller_api_security(
        int(deposit["reseller_api_key_id"]),
        active_only=True,
    )
    if not security or not security.get("webhook_enabled") or not security.get("webhook_url"):
        return False

    event_type = _event_type(public["status"])
    event_key = f"{public['deposit_id']}:{event_type}"
    event_id = "evt_" + hashlib.sha256(event_key.encode("utf-8")).hexdigest()[:24]
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reseller_api_key_id": int(deposit["reseller_api_key_id"]),
        "data": {"deposit": public},
    }
    job_id = f"reseller-webhook-{event_id}"
    _, created = await create_background_job_once(
        job_id,
        "reseller_webhook",
        payload,
        max_attempts=6,
    )
    return created


async def enqueue_reseller_deposit_webhook_for_payment(
    payment_id: str | int,
) -> bool:
    deposit = await get_reseller_deposit_by_payment_id(payment_id)
    return await enqueue_reseller_deposit_webhook(deposit)


async def deliver_reseller_webhook(payload: dict) -> None:
    key_id = int(payload.get("reseller_api_key_id") or 0)
    security = await get_reseller_api_security(key_id, active_only=True)
    if not security or not security.get("webhook_enabled"):
        return
    target = await resolve_webhook_target(str(security.get("webhook_url") or ""))
    if not target:
        return

    signing_secret = derive_webhook_secret(
        str(security.get("key_prefix") or ""),
        str(security.get("webhook_secret_salt") or ""),
    )
    body = canonical_webhook_body({
        "event_id": payload.get("event_id"),
        "event_type": payload.get("event_type"),
        "created_at": payload.get("created_at"),
        "data": payload.get("data") or {},
    })
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "X-Vente-Event-Id": str(payload.get("event_id") or ""),
        "X-Vente-Event": str(payload.get("event_type") or ""),
        "X-Vente-Timestamp": str(timestamp),
        "X-Vente-Signature": sign_webhook_body(signing_secret, timestamp, body),
    }
    async with dependency_call("reseller_webhook", circuit_breaker=False):
        response_status = await _post_pinned_webhook(target, body, headers)
    if response_status < 200 or response_status >= 300:
        raise RuntimeError(f"Reseller webhook returned HTTP {response_status}")
