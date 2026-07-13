"""Reliable Telegram broadcast delivery shared by dashboard and bot admin."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from telegram.error import BadRequest, RetryAfter

from database.models import get_all_users


logger = logging.getLogger(__name__)
_BROADCAST_LOCK = asyncio.Lock()
_BATCH_SIZE = 20


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
    """Send a rate-controlled broadcast and return sent, failed, total."""
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

    async with _BROADCAST_LOCK:
        for offset in range(start_offset, total, _BATCH_SIZE):
            batch = users[offset:offset + _BATCH_SIZE]
            results = await asyncio.gather(*(
                _send_one(bot, int(user["telegram_id"]), text, photo, reply_markup)
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
            if offset + _BATCH_SIZE < total:
                await asyncio.sleep(1.0)

    logger.info("Broadcast completed: sent=%d failed=%d total=%d", sent, failed, total)
    return sent, failed, total
