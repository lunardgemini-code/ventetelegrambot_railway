"""Small, bounded client for the Pixel activation provider API.

The provider has no documented idempotency key or signed callback.  This
module deliberately never retries ``POST /submit``: after an ambiguous timeout
the caller must reconcile the task instead of risking a second paid task.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import (
    PIXEL_API_BASE_URL,
    PIXEL_API_KEY,
    PIXEL_ENABLED,
    PIXEL_HTTP_TIMEOUT_SECONDS,
)
from services.runtime_metrics import DependencyCircuitOpen, dependency_call


logger = logging.getLogger(__name__)
_HTTP_CLIENT: httpx.AsyncClient | None = None


class PixelAPIError(RuntimeError):
    """A provider failure with enough context for safe retry decisions."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.outcome_unknown = outcome_unknown


def is_pixel_configured() -> bool:
    return bool(PIXEL_ENABLED and PIXEL_API_KEY and PIXEL_API_BASE_URL)


async def _client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            base_url=PIXEL_API_BASE_URL,
            timeout=httpx.Timeout(PIXEL_HTTP_TIMEOUT_SECONDS, connect=5.0),
            headers={
                "Authorization": f"Bearer {PIXEL_API_KEY}",
                "Accept": "application/json",
            },
            limits=httpx.Limits(
                max_connections=4,
                max_keepalive_connections=2,
                keepalive_expiry=90.0,
            ),
        )
    return _HTTP_CLIENT


async def close_pixel_api_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


def _provider_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("message") or payload.get("detail")
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("code") or detail
        if detail:
            return str(detail)
    return response.text.strip()[:300] or f"HTTP {response.status_code}"


async def _request(
    method: str,
    path: str,
    *,
    retry_read: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    if not is_pixel_configured():
        raise PixelAPIError("Pixel activation is not configured")

    method = method.upper()
    attempts = 2 if method == "GET" and retry_read else 1
    last_error: PixelAPIError | None = None
    for attempt in range(attempts):
        try:
            async with dependency_call("pixel_activation"):
                response = await (await _client()).request(method, path, **kwargs)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                error = PixelAPIError(
                    _provider_error(response),
                    status_code=response.status_code,
                    retryable=retryable,
                    # The supplier has no idempotency guarantee. A 5xx after
                    # POST can still mean it accepted the task before its
                    # response failed, so preserve the reservation for human
                    # review rather than risk charging twice on a retry.
                    outcome_unknown=method == "POST" and response.status_code >= 500,
                )
                if retryable and method == "GET" and attempt + 1 < attempts:
                    last_error = error
                    await asyncio.sleep(0.4)
                    continue
                raise error

            try:
                payload = response.json()
            except ValueError as exc:
                raise PixelAPIError("Pixel returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise PixelAPIError("Pixel returned an invalid response")
            return payload
        except PixelAPIError:
            raise
        except DependencyCircuitOpen as exc:
            raise PixelAPIError("Pixel is temporarily unavailable", retryable=True) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            # POST may have reached the provider after the TCP connection was
            # opened. Never auto-retry a submission in that situation.
            unknown = method == "POST"
            error = PixelAPIError(
                "Pixel request timed out or lost its connection",
                retryable=method == "GET",
                outcome_unknown=unknown,
            )
            if method == "GET" and attempt + 1 < attempts:
                last_error = error
                await asyncio.sleep(0.4)
                continue
            raise error from exc

    raise last_error or PixelAPIError("Pixel request failed")


async def get_pixel_balance() -> dict[str, Any]:
    payload = await _request("GET", "/balance", retry_read=True)
    balance = payload.get("balance")
    if not isinstance(balance, dict):
        raise PixelAPIError("Pixel balance response is missing its balance object")
    try:
        balance_points = float(balance["balance_points"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PixelAPIError("Pixel balance response has no valid balance_points") from exc
    return {
        "balance_points": balance_points,
        "total_success_count": int(balance.get("total_success_count") or 0),
        "today_success_count": int(balance.get("today_success_count") or 0),
        "pending_task_count": int(balance.get("pending_task_count") or 0),
        "daily_success_cap": balance.get("daily_success_cap"),
        "generated_at": payload.get("generated_at"),
    }


async def submit_pixel_task(
    *,
    email: str,
    password: str,
    twofa_secret: str,
    task_mode: str,
    channel: str,
    callback_url: str,
) -> dict[str, Any]:
    """Submit exactly once and validate the documented task response."""

    payload = await _request(
        "POST",
        "/submit",
        json={
            "email": email,
            "password": password,
            "twofa_url": twofa_secret,
            "task_mode": task_mode,
            "channel": channel,
            "callback_url": callback_url,
        },
    )
    task = payload.get("task")
    if not isinstance(task, dict):
        raise PixelAPIError("Pixel submit response is missing its task object")
    try:
        task_id = int(task["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PixelAPIError("Pixel submit response has no valid task id") from exc
    if task_id <= 0:
        raise PixelAPIError("Pixel submit response has an invalid task id")
    return {"task": task, "balance": payload.get("balance") or {}}


async def query_pixel_tasks(task_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Return provider task data keyed by the task IDs owned by this API key."""

    ids: list[int] = []
    for raw_task_id in task_ids:
        try:
            task_id = int(raw_task_id)
        except (TypeError, ValueError):
            continue
        if task_id > 0:
            ids.append(task_id)
    ids = sorted(set(ids))
    if not ids:
        return {}
    payload = await _request("POST", "/query", json={"task_ids": ids})
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raise PixelAPIError("Pixel query response is missing its tasks list")

    found: dict[int, dict[str, Any]] = {}
    for entry in raw_tasks:
        task = entry.get("task") if isinstance(entry, dict) else None
        if not isinstance(task, dict):
            continue
        try:
            task_id = int(task["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if task_id in ids:
            found[task_id] = task
    return found
