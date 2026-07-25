"""Persistent shared HTTP connection pools with keep-alive limits."""

from __future__ import annotations

import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

_SHARED_CLIENT: httpx.AsyncClient | None = None
_LOCK = asyncio.Lock()


async def get_shared_http_client(
    *,
    timeout: float = 20.0,
    max_connections: int = 50,
    max_keepalive: int = 25,
    keepalive_expiry: float = 90.0,
) -> httpx.AsyncClient:
    """Return an application-wide HTTP client for suppliers and APIs with persistent keep-alive."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        async with _LOCK:
            if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
                _SHARED_CLIENT = httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout, connect=6.0),
                    limits=httpx.Limits(
                        max_connections=max_connections,
                        max_keepalive_connections=max_keepalive,
                        keepalive_expiry=keepalive_expiry,
                    ),
                    follow_redirects=True,
                )
    return _SHARED_CLIENT


async def close_http_pools() -> None:
    """Shutdown helper to close open HTTP client pools cleanly."""
    global _SHARED_CLIENT
    async with _LOCK:
        if _SHARED_CLIENT and not _SHARED_CLIENT.is_closed:
            try:
                await _SHARED_CLIENT.aclose()
            except Exception as exc:
                logger.warning("Error closing HTTP client pool: %s", exc)
            _SHARED_CLIENT = None
