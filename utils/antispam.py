# utils/antispam.py — Rate limiter & anti-spam protection for the Telegram bot
# Tracks per-user message timestamps and blocks excessive requests.

from __future__ import annotations

import time
import logging
from collections import defaultdict
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
MAX_MESSAGES = 8          # Max messages allowed in the time window
TIME_WINDOW = 10          # Time window in seconds
COOLDOWN_SECONDS = 30     # How long a spammer is muted
WARN_THRESHOLD = 6        # After this many msgs, send a warning

# ── State ──────────────────────────────────────────────────────────
_user_timestamps: dict[int, list[float]] = defaultdict(list)
_user_cooldown: dict[int, float] = {}
_warned: set[int] = set()
_cooldown_warned: set[int] = set()


def _cleanup(user_id: int, now: float) -> None:
    """Remove timestamps older than TIME_WINDOW."""
    cutoff = now - TIME_WINDOW
    _user_timestamps[user_id] = [
        ts for ts in _user_timestamps[user_id] if ts > cutoff
    ]


def is_spam(user_id: int) -> bool:
    """Check if a user is currently rate-limited or spamming.

    Returns True if the message should be blocked.
    """
    # Admins are never rate-limited
    if user_id in ADMIN_IDS:
        return False

    now = time.time()

    # Check if user is in cooldown
    if user_id in _user_cooldown:
        if now < _user_cooldown[user_id]:
            return True
        else:
            # Cooldown expired
            del _user_cooldown[user_id]
            _user_timestamps[user_id].clear()
            _warned.discard(user_id)
            _cooldown_warned.discard(user_id)

    # Record this message
    _cleanup(user_id, now)
    _user_timestamps[user_id].append(now)
    count = len(_user_timestamps[user_id])

    # Check if over limit
    if count >= MAX_MESSAGES:
        _user_cooldown[user_id] = now + COOLDOWN_SECONDS
        logger.warning(
            "Anti-spam: user %d rate-limited for %ds (%d msgs in %ds)",
            user_id, COOLDOWN_SECONDS, count, TIME_WINDOW,
        )
        return True

    return False


def should_warn(user_id: int) -> bool:
    """Check if we should send a warning (approaching limit)."""
    if user_id in ADMIN_IDS:
        return False
    if user_id in _warned:
        return False
    count = len(_user_timestamps.get(user_id, []))
    if count >= WARN_THRESHOLD:
        _warned.add(user_id)
        return True
    return False


def get_cooldown_remaining(user_id: int) -> int:
    """Return seconds remaining in cooldown, or 0."""
    if user_id not in _user_cooldown:
        return 0
    remaining = _user_cooldown[user_id] - time.time()
    return max(0, int(remaining))


def check_and_mark_cooldown_warned(user_id: int) -> bool:
    """Check if the user has been warned about the current cooldown.
    If not, mark them as warned and return False.
    If already warned, return True.
    """
    if user_id in _cooldown_warned:
        return True
    _cooldown_warned.add(user_id)
    return False


# ── Decorator for handlers ────────────────────────────────────────

SPAM_MESSAGES = {
    "en": "⚠️ You are sending messages too fast. Please wait {sec}s.",
    "fr": "⚠️ Vous envoyez des messages trop vite. Patientez {sec}s.",
    "ar": "⚠️ أنت ترسل الرسائل بسرعة كبيرة. انتظر {sec} ثانية.",
}

WARN_MESSAGES = {
    "en": "⏳ Slow down! You're approaching the message limit.",
    "fr": "⏳ Ralentissez ! Vous approchez la limite de messages.",
    "ar": "⏳ تمهل! أنت تقترب من حد الرسائل.",
}


def rate_limit(func):
    """Decorator that adds anti-spam protection to any handler."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return await func(update, context, *args, **kwargs)

        user_id = user.id

        if is_spam(user_id):
            if not check_and_mark_cooldown_warned(user_id):
                remaining = get_cooldown_remaining(user_id)
                lang = context.user_data.get("lang", "fr")
                msg = SPAM_MESSAGES.get(lang, SPAM_MESSAGES["fr"]).format(sec=remaining)

                try:
                    if update.callback_query:
                        await update.callback_query.answer(msg, show_alert=True)
                    elif update.message:
                        sent = await update.message.reply_text(msg)
                        # Auto-delete spam warning after a few seconds
                        try:
                            import asyncio
                            await asyncio.sleep(5)
                            await sent.delete()
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                try:
                    if update.callback_query:
                        await update.callback_query.answer()
                except Exception:
                    pass
            return None

        # Warn if approaching limit
        if should_warn(user_id):
            lang = context.user_data.get("lang", "fr")
            msg = WARN_MESSAGES.get(lang, WARN_MESSAGES["fr"])
            try:
                if update.callback_query:
                    await update.callback_query.answer(msg, show_alert=False)
                elif update.message:
                    await update.message.reply_text(msg)
            except Exception:
                pass

        return await func(update, context, *args, **kwargs)

    return wrapper
