"""Reliable Telegram broadcast delivery shared by dashboard and bot admin."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable

from telegram import Bot
from telegram.error import BadRequest, RetryAfter
from telegram.request import HTTPXRequest

from database.models import get_all_users


logger = logging.getLogger(__name__)
_BROADCAST_LOCK = asyncio.Lock()
_DEFAULT_BATCH_SIZE = 8
_MAX_BATCH_SIZE = 10
_DEFAULT_POOL_SIZE = 8


def _bounded_env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _broadcast_batch_size() -> int:
    return _bounded_env_int(
        "BROADCAST_BATCH_SIZE",
        _DEFAULT_BATCH_SIZE,
        minimum=1,
        maximum=_MAX_BATCH_SIZE,
    )


def _build_isolated_broadcast_bot(main_bot) -> Bot | None:
    """Create a Bot whose HTTP pool is never shared with interactive traffic."""
    token = str(getattr(main_bot, "token", "") or "").strip()
    if not token:
        # Lightweight test doubles do not expose a token.
        return None
    pool_size = _bounded_env_int(
        "BROADCAST_CONNECTION_POOL_SIZE",
        _DEFAULT_POOL_SIZE,
        minimum=2,
        maximum=12,
    )
    request = HTTPXRequest(
        connection_pool_size=pool_size,
        connect_timeout=10.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=5.0,
        media_write_timeout=30.0,
    )
    return Bot(token=token, request=request)


@asynccontextmanager
async def _isolated_broadcast_transport(main_bot):
    dedicated_bot = _build_isolated_broadcast_bot(main_bot)
    if dedicated_bot is None:
        yield main_bot
        return
    await dedicated_bot.initialize()
    try:
        yield dedicated_bot
    finally:
        await dedicated_bot.shutdown()


def validate_broadcast_content(text: str, photo: str | None = None) -> None:
    if not text and not photo:
        raise ValueError("EMPTY_BROADCAST")
    if len(text) > 4096:
        raise ValueError("BROADCAST_TEXT_TOO_LONG")


async def _telegram_call_with_html_fallback(method, **kwargs):
    try:
        return await method(**kwargs)
    except BadRequest as exc:
        # Invalid or unsupported HTML should not make every delivery fail.
        if kwargs.get("parse_mode") and any(
            marker in str(exc).lower()
            for marker in ("parse entities", "can't parse", "unsupported start tag")
        ):
            fallback = dict(kwargs)
            fallback["parse_mode"] = None
            return await method(**fallback)
        raise


async def _send_one(bot, user_id: int, text: str, photo: str | None, reply_markup) -> bool:
    async def send() -> None:
        if photo and text and len(text) > 1024:
            await bot.send_photo(chat_id=user_id, photo=photo)
            await _telegram_call_with_html_fallback(
                bot.send_message,
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        elif photo:
            await _telegram_call_with_html_fallback(
                bot.send_photo,
                chat_id=user_id,
                photo=photo,
                caption=text or None,
                parse_mode="HTML" if text else None,
                reply_markup=reply_markup,
            )
        else:
            await _telegram_call_with_html_fallback(
                bot.send_message,
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    try:
        await send()
        return True
    except RetryAfter as exc:
        await asyncio.sleep(min(float(exc.retry_after), 10.0) + 0.1)
        try:
            await send()
            return True
        except Exception as retry_exc:
            logger.debug("Broadcast retry failed for %s: %s", user_id, retry_exc)
            return False
    except Exception as exc:
        logger.debug("Broadcast failed for %s: %s", user_id, exc)
        return False


async def execute_broadcast(
    bot,
    text: str,
    *,
    photo: str | None = None,
    reply_markup=None,
    progress: Callable[[int, int, int], Awaitable[None] | None] | None = None,
    checkpoint: Callable[[int, int, int, int], Awaitable[None] | None] | None = None,
    start_offset: int = 0,
    max_user_id: int | None = None,
    initial_sent: int = 0,
    initial_failed: int = 0,
) -> tuple[int, int, int]:
    """Send a rate-controlled broadcast through an isolated Telegram pool."""
    text = str(text or "")
    photo = str(photo or "").strip() or None
    validate_broadcast_content(text, photo)
    users = [user for user in await get_all_users() if not user.get("is_banned")]
    users.sort(key=lambda user: int(user.get("id") or user.get("telegram_id") or 0))
    if max_user_id is not None:
        users = [
            user for user in users
            if int(user.get("id") or user.get("telegram_id") or 0) <= int(max_user_id)
        ]
    total = len(users)
    start_offset = min(total, max(0, int(start_offset)))
    sent = max(0, int(initial_sent))
    failed = max(0, int(initial_failed))

    batch_size = _broadcast_batch_size()
    async with _BROADCAST_LOCK:
        async with _isolated_broadcast_transport(bot) as broadcast_bot:
            logger.info(
                "Broadcast transport started: recipients=%d batch_size=%d isolated=%s",
                total - start_offset,
                batch_size,
                broadcast_bot is not bot,
            )
            for offset in range(start_offset, total, batch_size):
                batch = users[offset:offset + batch_size]
                results = await asyncio.gather(*(
                    _send_one(
                        broadcast_bot,
                        int(user["telegram_id"]),
                        text,
                        photo,
                        reply_markup,
                    )
                    for user in batch
                ))
                sent += sum(1 for result in results if result)
                failed += sum(1 for result in results if not result)
                if progress:
                    progress_result = progress(sent, failed, total)
                    if asyncio.iscoroutine(progress_result):
                        await progress_result
                next_offset = min(total, offset + len(batch))
                if checkpoint:
                    checkpoint_result = checkpoint(sent, failed, total, next_offset)
                    if asyncio.iscoroutine(checkpoint_result):
                        await checkpoint_result
                if offset + batch_size < total:
                    await asyncio.sleep(1.0)

    logger.info("Broadcast completed: sent=%d failed=%d total=%d", sent, failed, total)
    return sent, failed, total
