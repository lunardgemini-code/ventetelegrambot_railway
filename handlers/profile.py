"""
Profile handler — display user information.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_user, get_user_lang, get_user_order_count, generate_reseller_api_key
from utils.helpers import format_date, format_price, escape_html
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

        is_reseller = bool(user.get('is_reseller', 0))

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=profile_keyboard(lang, is_reseller=is_reseller),
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


async def show_reseller_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'show_reseller_api' callback — show reseller API key and docs."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    try:
        user = await get_user(telegram_id)
        if not user:
            await query.edit_message_text(t("error_generic", lang))
            return

        if not user.get("is_reseller"):
            # Not a reseller -> show "contact support" message
            text_map_no_access = {
                "fr": "⚙️ <b>API Revendeur</b>\n\nVous n'avez pas encore accès à l'API.\n\nPour activer votre accès revendeur, veuillez contacter le support.",
                "en": "⚙️ <b>Reseller API</b>\n\nYou don't have API access yet.\n\nTo activate your reseller access, please contact support.",
                "ar": "⚙️ <b>API الموزع</b>\n\nليس لديك وصول إلى API بعد.\n\nلتفعيل وصول الموزع الخاص بك، يرجى الاتصال بالدعم."
            }
            text_no_access = text_map_no_access.get(lang, text_map_no_access["fr"])
            await query.edit_message_text(
                text_no_access,
                parse_mode="HTML",
                reply_markup=back_keyboard("menu_profile", lang),
            )
            return

        # Generate API key if the reseller doesn't have one yet
        api_key = user.get("reseller_api_key")
        if not api_key:
            api_key = await generate_reseller_api_key(telegram_id)

        balance = user.get("wallet_balance", 0)

        # Build the API docs URL from the bot's webhook URL or a known base
        import os
        base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
        if base_url and not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        docs_url = f"{base_url}/docs" if base_url else "https://your-bot-url.up.railway.app/docs"

        text_map = {
            "fr": (
                "⚙️ <b>API Revendeur</b>\n\n"
                "🔑 <b>Votre clé API :</b>\n<code>{key}</code>\n\n"
                "💰 <b>Solde :</b> ${balance:.2f}\n"
                "<i>⚠️ Vous devez recharger votre solde sur le bot pour pouvoir acheter via l'API.</i>\n\n"
                "📖 <b>Documentation :</b>\n{docs}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 <b>Guide rapide :</b>\n"
                "1️⃣ Ajoutez le header <code>X-Reseller-Key</code> avec votre clé\n"
                "2️⃣ <code>GET /api/b2b/products</code> — Voir le catalogue\n"
                "3️⃣ <code>POST /api/b2b/buy</code> — Acheter des comptes\n"
                "4️⃣ <code>GET /api/b2b/balance</code> — Voir votre solde"
            ),
            "en": (
                "⚙️ <b>Reseller API</b>\n\n"
                "🔑 <b>Your API Key:</b>\n<code>{key}</code>\n\n"
                "💰 <b>Balance:</b> ${balance:.2f}\n"
                "<i>⚠️ You must top up your bot wallet balance to make API purchases.</i>\n\n"
                "📖 <b>Documentation:</b>\n{docs}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 <b>Quick Guide:</b>\n"
                "1️⃣ Add header <code>X-Reseller-Key</code> with your key\n"
                "2️⃣ <code>GET /api/b2b/products</code> — View catalog\n"
                "3️⃣ <code>POST /api/b2b/buy</code> — Buy accounts\n"
                "4️⃣ <code>GET /api/b2b/balance</code> — Check balance"
            ),
            "ar": (
                "⚙️ <b>API الموزع</b>\n\n"
                "🔑 <b>مفتاح API الخاص بك:</b>\n<code>{key}</code>\n\n"
                "💰 <b>الرصيد:</b> ${balance:.2f}\n"
                "<i>⚠️ يجب عليك شحن رصيدك في البوت لتتمكن من الشراء عبر API.</i>\n\n"
                "📖 <b>التوثيق:</b>\n{docs}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 <b>دليل سريع:</b>\n"
                "1️⃣ أضف header <code>X-Reseller-Key</code> مع مفتاحك\n"
                "2️⃣ <code>GET /api/b2b/products</code> — عرض المنتجات\n"
                "3️⃣ <code>POST /api/b2b/buy</code> — شراء حسابات\n"
                "4️⃣ <code>GET /api/b2b/balance</code> — التحقق من الرصيد"
            ),
        }
        template = text_map.get(lang, text_map["fr"])
        text = template.format(key=api_key, balance=balance, docs=docs_url)

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_keyboard("menu_profile", lang),
        )
    except Exception as exc:
        logger.error("show_reseller_api: %s", exc, exc_info=True)
        await query.edit_message_text(t("error_generic", lang))
