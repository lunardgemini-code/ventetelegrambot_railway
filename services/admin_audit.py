"""Bounded, asynchronous persistence for low-volume admin mutations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from database.audit import insert_admin_audit_events


logger = logging.getLogger(__name__)

_AUDIT_QUEUE_MAX = 512
_AUDIT_BATCH_MAX = 50
_AUDIT_BATCH_WAIT_SECONDS = 0.25
_audit_queue: asyncio.Queue | None = None
_audit_queue_loop = None


def _get_audit_queue() -> asyncio.Queue:
    global _audit_queue, _audit_queue_loop
    loop = asyncio.get_running_loop()
    if _audit_queue is None or _audit_queue_loop is not loop:
        _audit_queue = asyncio.Queue(maxsize=_AUDIT_QUEUE_MAX)
        _audit_queue_loop = loop
    return _audit_queue


def enqueue_admin_audit_event(event: dict[str, Any]) -> bool:
    """Queue an event without adding database latency to the admin request."""
    queue = _get_audit_queue()
    try:
        queued = dict(event)
        queued.setdefault("event_uid", uuid.uuid4().hex)
        queue.put_nowait(queued)
        return True
    except asyncio.QueueFull:
        logger.error("Admin audit queue is full; dropping one audit event")
        return False


async def _persist_with_retry(events: list[dict[str, Any]]) -> None:
    for attempt in range(3):
        try:
            await insert_admin_audit_events(events)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if attempt == 2:
                logger.exception(
                    "Could not persist %d admin audit event(s): %s",
                    len(events),
                    exc,
                )
                return
            await asyncio.sleep(0.25 * (attempt + 1))


async def admin_audit_worker() -> None:
    queue = _get_audit_queue()
    pending: list[dict[str, Any]] = []
    try:
        while True:
            pending.append(await queue.get())
            deadline = asyncio.get_running_loop().time() + _AUDIT_BATCH_WAIT_SECONDS
            while len(pending) < _AUDIT_BATCH_MAX:
                timeout = deadline - asyncio.get_running_loop().time()
                if timeout <= 0:
                    break
                try:
                    pending.append(await asyncio.wait_for(queue.get(), timeout))
                except asyncio.TimeoutError:
                    break
            await _persist_with_retry(pending)
            for _ in pending:
                queue.task_done()
            pending.clear()
    except asyncio.CancelledError:
        while len(pending) < _AUDIT_BATCH_MAX:
            try:
                pending.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if pending:
            try:
                await asyncio.wait_for(
                    asyncio.shield(_persist_with_retry(pending)),
                    timeout=3.0,
                )
            except Exception as exc:
                logger.warning("Final admin audit flush failed: %s", exc)
            finally:
                for _ in pending:
                    queue.task_done()
        raise


def reset_admin_audit_state() -> None:
    global _audit_queue, _audit_queue_loop
    _audit_queue = None
    _audit_queue_loop = None
