"""Read-only verification of incoming Bybit internal transfers."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import re
import time
from urllib.parse import urlencode

import httpx

from config import (
    BYBIT_API_BASE_URL,
    BYBIT_API_KEY,
    BYBIT_API_SECRET,
    BYBIT_RECV_WINDOW,
    BYBIT_TRANSFER_ENABLED,
    BYBIT_UID,
)
from services.runtime_metrics import dependency_call

logger = logging.getLogger(__name__)

AMOUNT_TOLERANCE = 0.01
MAX_PAYMENT_AGE_SECONDS = 48 * 60 * 60
MAX_FUTURE_SKEW_SECONDS = 5 * 60
_TX_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,128}$")
_HTTP_CLIENT: httpx.AsyncClient | None = None
_TIME_OFFSET_MS = 0
_TIME_SYNCED_AT = 0.0
_TIME_SYNC_LOCK: asyncio.Lock | None = None
_VERIFY_CACHE: dict[str, tuple[float, dict]] = {}
_VERIFY_TASKS: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Task]] = {}


class BybitTransferError(RuntimeError):
    """Safe integration error with an optional Bybit return code."""

    def __init__(self, message: str, *, code: int | None = None):
        super().__init__(message)
        self.code = code


def is_bybit_transfer_configured() -> bool:
    return bool(
        BYBIT_TRANSFER_ENABLED
        and BYBIT_API_KEY
        and BYBIT_API_SECRET
        and BYBIT_UID
    )


async def _get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            base_url=BYBIT_API_BASE_URL,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=120.0,
            ),
        )
    return _HTTP_CLIENT


async def close_bybit_transfer_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


def _time_sync_lock() -> asyncio.Lock:
    global _TIME_SYNC_LOCK
    if _TIME_SYNC_LOCK is None:
        _TIME_SYNC_LOCK = asyncio.Lock()
    return _TIME_SYNC_LOCK


async def _sync_server_time(*, force: bool = False) -> None:
    global _TIME_OFFSET_MS, _TIME_SYNCED_AT
    now = time.monotonic()
    if not force and _TIME_SYNCED_AT and now - _TIME_SYNCED_AT < 300:
        return
    async with _time_sync_lock():
        now = time.monotonic()
        if not force and _TIME_SYNCED_AT and now - _TIME_SYNCED_AT < 300:
            return
        client = await _get_http_client()
        local_before = int(time.time() * 1000)
        async with dependency_call("bybit", circuit_breaker=False):
            response = await client.get("/v5/market/time")
        response.raise_for_status()
        payload = response.json()
        server_ms = int(payload.get("time") or 0)
        if not server_ms:
            server_ms = int((payload.get("result") or {}).get("timeNano") or 0) // 1_000_000
        if not server_ms:
            raise BybitTransferError("BYBIT_TIME_UNAVAILABLE")
        local_after = int(time.time() * 1000)
        _TIME_OFFSET_MS = server_ms - ((local_before + local_after) // 2)
        _TIME_SYNCED_AT = time.monotonic()


def _timestamp_ms() -> int:
    return int(time.time() * 1000) + _TIME_OFFSET_MS


async def _get_internal_deposit(tx_id: str) -> list[dict]:
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        raise BybitTransferError("BYBIT_NOT_CONFIGURED")

    await _sync_server_time()
    params = [("txID", tx_id), ("coin", "USDT"), ("limit", "50")]
    query = urlencode(params)
    client = await _get_http_client()

    for attempt in range(2):
        timestamp = str(_timestamp_ms())
        plain = f"{timestamp}{BYBIT_API_KEY}{BYBIT_RECV_WINDOW}{query}"
        signature = hmac.new(
            BYBIT_API_SECRET.encode("utf-8"),
            plain.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-BAPI-API-KEY": BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": str(BYBIT_RECV_WINDOW),
            "X-BAPI-SIGN": signature,
        }
        async with dependency_call("bybit", circuit_breaker=False):
            response = await client.get(
                "/v5/asset/deposit/query-internal-record",
                params=params,
                headers=headers,
            )
        response.raise_for_status()
        payload = response.json()
        code = int(payload.get("retCode") or 0)
        if code == 10002 and attempt == 0:
            await _sync_server_time(force=True)
            continue
        if code != 0:
            raise BybitTransferError(
                str(payload.get("retMsg") or "BYBIT_API_ERROR"),
                code=code,
            )
        return list((payload.get("result") or {}).get("rows") or [])
    raise BybitTransferError("BYBIT_TIME_SYNC_FAILED", code=10002)


def _created_at_seconds(value: object) -> float:
    try:
        timestamp = float(value or 0)
    except (TypeError, ValueError):
        return 0
    return timestamp / 1000 if timestamp >= 1_000_000_000_000 else timestamp


async def _verify_uncached(tx_id: str, expected_amount: float) -> dict:
    if not is_bybit_transfer_configured():
        return {"verified": False, "error_key": "bybit_transfer_unavailable"}
    if not _TX_ID_RE.fullmatch(tx_id):
        return {"verified": False, "error_key": "bybit_transfer_invalid_id"}

    try:
        rows = await _get_internal_deposit(tx_id)
    except (httpx.HTTPError, BybitTransferError, ValueError) as exc:
        logger.warning("Bybit transfer verification failed: %s", exc)
        return {"verified": False, "error_key": "bybit_transfer_unavailable"}

    matching = next(
        (
            row for row in rows
            if str(row.get("txID") or "").strip().casefold() == tx_id.casefold()
        ),
        None,
    )
    if not matching:
        return {
            "verified": False,
            "error_key": "bybit_transfer_not_found",
            "_cacheable_miss": True,
        }
    if int(matching.get("status") or 0) != 2:
        return {"verified": False, "error_key": "bybit_transfer_pending"}
    if str(matching.get("coin") or "").upper() != "USDT":
        return {"verified": False, "error_key": "bybit_transfer_wrong_coin"}

    try:
        received = float(matching.get("amount") or 0)
    except (TypeError, ValueError):
        received = 0
    if received + AMOUNT_TOLERANCE < float(expected_amount):
        return {
            "verified": False,
            "error_key": "bybit_transfer_underpaid",
            "error_params": {
                "received": f"{received:.8f}".rstrip("0").rstrip("."),
                "expected": f"{float(expected_amount):.8f}".rstrip("0").rstrip("."),
            },
        }

    created_at = _created_at_seconds(matching.get("createdTime"))
    now = time.time() + (_TIME_OFFSET_MS / 1000)
    if not created_at or created_at < now - MAX_PAYMENT_AGE_SECONDS:
        return {"verified": False, "error_key": "bybit_transfer_too_old"}
    if created_at > now + MAX_FUTURE_SKEW_SECONDS:
        return {"verified": False, "error_key": "bybit_transfer_invalid_time"}

    normalized = dict(matching)
    normalized["transactionId"] = str(matching.get("txID") or tx_id)
    normalized["orderId"] = normalized["transactionId"]
    normalized["amount"] = received
    return {"verified": True, "transaction": normalized}


async def verify_payment(tx_id: str, expected_amount: float) -> dict:
    cleaned_id = str(tx_id or "").strip()
    cache_key = f"{cleaned_id.casefold()}:{float(expected_amount):.8f}"
    now = time.monotonic()
    expired = [key for key, value in _VERIFY_CACHE.items() if value[0] <= now]
    for key in expired:
        _VERIFY_CACHE.pop(key, None)
    cached = _VERIFY_CACHE.get(cache_key)
    if cached:
        return dict(cached[1])

    loop = asyncio.get_running_loop()
    current = _VERIFY_TASKS.get(cache_key)
    if current is None or current[0] is not loop or current[1].done():
        task = asyncio.create_task(_verify_uncached(cleaned_id, expected_amount))
        _VERIFY_TASKS[cache_key] = (loop, task)
    else:
        task = current[1]
    try:
        raw = await asyncio.shield(task)
    finally:
        registered = _VERIFY_TASKS.get(cache_key)
        if registered and registered[1] is task and task.done():
            _VERIFY_TASKS.pop(cache_key, None)

    result = dict(raw)
    cacheable_miss = bool(result.pop("_cacheable_miss", False))
    ttl = 300.0 if result.get("verified") else (5.0 if cacheable_miss else 0.0)
    if ttl:
        _VERIFY_CACHE[cache_key] = (time.monotonic() + ttl, dict(result))
    return result


def reset_bybit_transfer_cache() -> None:
    global _TIME_OFFSET_MS, _TIME_SYNCED_AT, _TIME_SYNC_LOCK
    _VERIFY_CACHE.clear()
    _VERIFY_TASKS.clear()
    _TIME_OFFSET_MS = 0
    _TIME_SYNCED_AT = 0.0
    _TIME_SYNC_LOCK = None
