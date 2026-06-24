"""
Profile handler — display user information.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_user, get_user_lang, get_user_order_count
from utils.helpers import format_date, format_price
from utils.keyboards import back_keyboard, profile_keyboard
from utils.locales import t

logger = logging.getLogger(__name__)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'menu_profile' callback — show user profile."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    try:
        user = await get_user(telegram_id)
        if not user:
            await query.edit_message_text(t("error_generic", lang))
            return

        order_count = await get_user_order_count(telegram_id)

        text = (
            f"{t('profile_title', lang)}\n\n"
            f"{t('id_lbl', lang)} <code>{telegram_id}</code>\n"
            f"{t('name_lbl', lang)} {user.get('first_name', 'N/A')}\n"
            f"{t('joined_lbl', lang)} {format_date(user.get('created_at'))}\n"
            f"{t('purchases_lbl', lang)} {order_count}\n"
            f"{t('spent_lbl', lang)} {format_price(user.get('total_spent', 0))}"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(lang),
        )
    except Exception as exc:
        logger.error("show_profile: %s", exc, exc_info=True)
        await query.edit_message_text(t("error_generic", lang))


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'show_referrals' callback — show referral program dashboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    try:
        user = await get_user(telegram_id)
        if not user:
            await query.edit_message_text(t("error_generic", lang))
            return

        # Get stats
        from database.models import get_referred_users_count
        ref_count = await get_referred_users_count(telegram_id)
        earnings = user.get("referral_earnings") or 0.0

        # Construct referral link using context.bot.username
        bot_username = getattr(context.bot, "username", None)
        if not bot_username:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username

        ref_link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"

        # Construct localized text
        text = (
            t("referral_title", lang)
            .replace("{link}", ref_link)
            .replace("{count}", str(ref_count))
            .replace("{earnings}", format_price(earnings))
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_keyboard("back_main", lang),
        )
    except Exception as exc:
        logger.error("show_referrals: %s", exc, exc_info=True)
        await query.edit_message_text(
            f"⚠️ An error occurred:\n<code>{str(exc)}</code>",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_main", lang),
        )
