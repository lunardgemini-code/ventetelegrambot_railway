"""Durable, signed webhook delivery for reseller deposit events."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

import httpx

from database.jobs import create_background_job_once
from database.models import (
    get_reseller_api_security,
    get_reseller_deposit_by_payment_id,
    public_reseller_deposit,
)
from services.reseller_security import (
    canonical_webhook_body,
    derive_webhook_secret,
    sign_webhook_body,
    validate_webhook_url,
)
from services.runtime_metrics import dependency_call


logger = logging.getLogger(__name__)
_HTTP_CLIENT: httpx.AsyncClient | None = None


async def _client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            headers={"User-Agent": "VenteBot-Reseller-Webhook/1.0"},
        )
    return _HTTP_CLIENT


async def close_reseller_webhook_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


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
    webhook_url = await validate_webhook_url(str(security.get("webhook_url") or ""))
    if not webhook_url:
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
        response = await (await _client()).post(webhook_url, content=body, headers=headers)
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Reseller webhook returned HTTP {response.status_code}")
