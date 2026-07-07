"""
Start command & language selection handlers.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_or_create_user, get_user_lang, set_user_language, is_user_banned
from utils.helpers import is_admin
from utils.keyboards import language_keyboard, main_menu_keyboard, reply_menu_keyboard
from utils.locales import t

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — cancel everything, reset state, show fresh main menu."""
    user = update.effective_user

    # ── Cancel all pending/awaiting orders and clear conversation state ──
    try:
        from database.models import cancel_all_pending_orders
        cancelled = await cancel_all_pending_orders(user.id)
        if cancelled:
            logger.info("Auto-cancelled %d pending order(s) for user %s on /start", cancelled, user.id)
    except Exception as exc:
        logger.error("Error cancelling pending orders on /start: %s", exc)

    # Clear ALL conversation-related user_data
    for key in list(context.user_data.keys()):
        context.user_data.pop(key, None)

    referred_by = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referred_by = int(arg.split("_")[1])
            except (ValueError, IndexError):
                pass

    db_user = await get_or_create_user(user.id, user.username, user.first_name, referred_by=referred_by)

    if await is_user_banned(user.id):
        return

    lang = db_user.get("language") or "fr"

    # If new user (no language set yet), show language picker
    if not db_user.get("language"):
        await update.message.reply_text(
            t("choose_language", "en") + "\n"
            + t("choose_language", "fr") + "\n"
            + t("choose_language", "ar"),
            reply_markup=language_keyboard(),
        )
        return

    await update.message.reply_text(
        t("welcome", lang),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )
    # Activate the persistent reply keyboard
    try:
        await update.message.reply_text(
            "⬇️ Menu :",
            reply_markup=reply_menu_keyboard(lang),
        )
    except Exception:
        pass


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'change_lang' callback or reply button — show language picker."""
    text = (
        t("choose_language", "en") + "\n"
        + t("choose_language", "fr") + "\n"
        + t("choose_language", "ar")
    )
    markup = language_keyboard()

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'lang:{code}' callback — set language and show main menu."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split(":")[1]

    # Validate language code against allowed values
    if lang_code not in ("en", "fr", "ar", "zh", "vi", "ru"):
        lang_code = "fr"

    telegram_id = update.effective_user.id

    # Ensure user exists
    user = update.effective_user
    await get_or_create_user(telegram_id, user.username, user.first_name)
    await set_user_language(telegram_id, lang_code)

    await query.edit_message_text(
        t("language_set", lang_code) + "\n\n" + t("welcome", lang_code),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang_code),
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'back_main' callback — return to main menu."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    text = t("welcome", lang) or t("welcome", "fr")
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        pass  # Message already shows this content


async def callback_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for verifying Telegram channel membership."""
    query = update.callback_query
    user_id = query.from_user.id

    from config import REQUIRED_CHANNEL
    is_subscribed = False
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            is_subscribed = True
    except Exception as e:
        # Fallback to True if bot is not admin or configured incorrectly
        err_msg = str(e).lower()
        if "chat not found" in err_msg or "not enough rights" in err_msg or "admin" in err_msg:
            is_subscribed = True

    referred_by = context.user_data.get("referred_by") if context.user_data else None
    db_user = await get_or_create_user(user_id, query.from_user.username, query.from_user.first_name, referred_by=referred_by)
    lang = db_user.get("language") or "fr"

    if is_subscribed:
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass

        # Send start menu
        await query.message.reply_text(
            t("welcome", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        try:
            await query.message.reply_text(
                "⬇️ Menu :",
                reply_markup=reply_menu_keyboard(lang),
            )
        except Exception:
            pass
    else:
        # Send an alert to the user that they are still not subscribed
        alert_msg = {
            "fr": "❌ Vous n'avez pas encore rejoint le canal.",
            "en": "❌ You have not joined the channel yet.",
            "ar": "❌ لم تنضم إلى القناة بعد."
        }
        await query.answer(alert_msg.get(lang, alert_msg["fr"]), show_alert=True)
