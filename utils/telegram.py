"""Small safety helpers for Telegram callback message updates."""

from __future__ import annotations

import logging
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

        logger.info("Callback message could not be edited; sending a fresh message")
        return await reply_text(text, **kwargs)
