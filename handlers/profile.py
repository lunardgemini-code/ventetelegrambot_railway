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
from utils.telegram import safe_edit_message_text

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
            await safe_edit_message_text(query, t("error_generic", lang))
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

        is_reseller = bool(user.get('is_reseller', 0))

        await safe_edit_message_text(query, 
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(lang, is_reseller=is_reseller),
        )
    except Exception as exc:
        logger.error("show_profile: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("error_generic", lang))


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'show_referrals' callback — show referral program dashboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    try:
        user = await get_user(telegram_id)
        if not user:
            await safe_edit_message_text(query, t("error_generic", lang))
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

        from utils.keyboards import referral_dashboard_keyboard
        await safe_edit_message_text(query, 
            text,
            parse_mode="HTML",
            reply_markup=referral_dashboard_keyboard(lang),
        )
    except Exception as exc:
        logger.error("show_referrals: %s", exc, exc_info=True)
        await safe_edit_message_text(query, 
            f"⚠️ An error occurred:\n<code>{str(exc)}</code>",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_main", lang),
        )

async def view_referrals_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'view_referrals_list' callback - show list of invited users."""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)
    
    try:
        from database.models import get_referred_users_list
        refs = await get_referred_users_list(telegram_id)
        
        if not refs:
            from utils.locales import t
            msg = {"fr": "Vous n'avez pas encore de filleuls.", "en": "You don't have any referrals yet.", "ar": "ليس لديك أي إحالات بعد."}.get(lang, "Vous n'avez pas encore de filleuls.")
            from utils.keyboards import back_keyboard
            await safe_edit_message_text(query, msg, reply_markup=back_keyboard("show_referrals", lang))
            return
        
        title = {"fr": "👥 <b>Vos filleuls récents :</b>\n\n", "en": "👥 <b>Your recent referrals:</b>\n\n", "ar": "👥 <b>إحالاتك الأخيرة:</b>\n\n"}.get(lang, "👥 <b>Vos filleuls récents :</b>\n\n")
        lines = []
        import html
        for r in refs:
            name = r.get("first_name") or r.get("username") or "Utilisateur"
            name = html.escape(name)
            lines.append(f"• {name}")
            
        text = title + "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "..."
            
        from utils.keyboards import back_keyboard
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=back_keyboard("show_referrals", lang))
    except Exception as exc:
        import logging
        logging.error("view_referrals_list: %s", exc, exc_info=True)
        from utils.keyboards import back_keyboard
        await safe_edit_message_text(query, "An error occurred.", reply_markup=back_keyboard("show_referrals", lang))
