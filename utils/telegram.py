"""Small safety helpers for Telegram callback message updates."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from telegram.error import BadRequest


logger = logging.getLogger(__name__)

_UNCHANGED_ERRORS = (
    "message is not modified",
)
_UNEDITABLE_ERRORS = (
    "message to edit not found",
    "message can't be edited",
    "message can not be edited",
    "there is no text in the message to edit",
)
_FALLBACK_DEDUPE_SECONDS = 10.0
_FALLBACK_SENT: dict[tuple[int, int, str], float] = {}


def _fallback_key(query: Any, text: str) -> tuple[int, int, str]:
    message = getattr(query, "message", None)
    chat_id = int(getattr(message, "chat_id", 0) or 0)
    message_id = int(getattr(message, "message_id", 0) or 0)
    digest = hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]
    return chat_id, message_id, digest


def _claim_fallback(key: tuple[int, int, str]) -> bool:
    now = time.monotonic()
    if len(_FALLBACK_SENT) >= 512:
        expired = [
            item_key for item_key, sent_at in _FALLBACK_SENT.items()
            if now - sent_at >= _FALLBACK_DEDUPE_SECONDS
        ]
        for item_key in expired:
            _FALLBACK_SENT.pop(item_key, None)
        while len(_FALLBACK_SENT) >= 512:
            _FALLBACK_SENT.pop(next(iter(_FALLBACK_SENT)))
    previous = _FALLBACK_SENT.get(key, 0.0)
    if now - previous < _FALLBACK_DEDUPE_SECONDS:
        return False
    _FALLBACK_SENT[key] = now
    return True


async def safe_edit_message_text(
    query: Any,
    text: str,
    *,
    fallback_to_new_message: bool = True,
    **kwargs: Any,
) -> Any:
    """Edit a callback message without turning benign Telegram races into failures.

    Repeated callbacks can target a message that was already changed or removed.
    An unchanged edit is treated as success; an uneditable message falls back to a
    new reply in the same chat. Other Telegram errors still propagate.
    """
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        error_text = str(exc).lower()
        if any(marker in error_text for marker in _UNCHANGED_ERRORS):
            return None
        if not fallback_to_new_message or not any(
            marker in error_text for marker in _UNEDITABLE_ERRORS
        ):
            raise

        message = getattr(query, "message", None)
        reply_text = getattr(message, "reply_text", None)
        if not callable(reply_text):
            raise

        fallback_key = _fallback_key(query, text)
        if not _claim_fallback(fallback_key):
            return None
        logger.debug("Callback message could not be edited; sending a fresh message")
        try:
            return await reply_text(text, **kwargs)
        except Exception:
            _FALLBACK_SENT.pop(fallback_key, None)
            raise
