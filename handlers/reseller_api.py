"""
Self-service reseller API menu for Telegram users.
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_active_reseller_api_key_info,
    get_or_create_user,
    get_user_lang,
    get_wallet_balance,
    rotate_reseller_api_key,
)
from utils.helpers import escape_html, format_price
from utils.keyboards import reseller_api_confirm_keyboard, reseller_api_keyboard
from utils.locales import t

logger = logging.getLogger(__name__)


def _api_docs_url() -> str | None:
    base_url = (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("WEBHOOK_URL")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or ""
    ).strip().rstrip("/")
    if not base_url:
        return None
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return f"{base_url}/api/swagger/"


async def reseller_api_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    lang = await get_user_lang(user.id)
    docs_url = _api_docs_url()
    key_info = await get_active_reseller_api_key_info(user.id)
    balance = await get_wallet_balance(user.id)

    lines = [
        t("api_menu_title", lang),
        "",
        t("api_menu_body", lang),
        "",
        f"{t('wallet_balance_lbl', lang)} <b>{format_price(balance)}</b>",
        t("api_wallet_required", lang),
        "",
    ]
    if key_info:
        lines.append(
            t("api_existing_key", lang).format(
                prefix=escape_html(key_info.get("key_prefix") or ""),
                created_at=escape_html(str(key_info.get("created_at") or "-")),
            )
        )
    else:
        lines.append(t("api_no_key", lang))
    if docs_url:
        lines.extend(["", t("api_docs_line", lang).format(docs_url=escape_html(docs_url))])

    text = "\n".join(lines)
    markup = reseller_api_keyboard(lang, docs_url=docs_url)

    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)


async def generate_reseller_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    lang = await get_user_lang(user.id)

    if update.effective_chat.type != "private":
        await query.edit_message_text(
            t("api_private_only", lang),
            reply_markup=reseller_api_keyboard(lang, docs_url=_api_docs_url()),
        )
        return

    await query.edit_message_text(
        t("api_generate_confirm", lang),
        parse_mode="HTML",
        reply_markup=reseller_api_confirm_keyboard(lang),
    )


async def confirm_generate_reseller_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    lang = await get_user_lang(user.id)

    if update.effective_chat.type != "private":
        await query.edit_message_text(
            t("api_private_only", lang),
            reply_markup=reseller_api_keyboard(lang, docs_url=_api_docs_url()),
        )
        return

    try:
        await get_or_create_user(user.id, user.username, user.first_name or "")
        key = await rotate_reseller_api_key(user.id, "Self-service Telegram")
        docs_url = _api_docs_url()
        parts = [
            t("api_key_generated", lang).format(api_key=escape_html(key["api_key"])),
            "",
            t("api_key_warning", lang),
            t("api_wallet_required", lang),
        ]
        if docs_url:
            parts.extend(["", t("api_docs_line", lang).format(docs_url=escape_html(docs_url))])
        await query.edit_message_text(
            "\n".join(parts),
            parse_mode="HTML",
            reply_markup=reseller_api_keyboard(lang, docs_url=docs_url),
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.error("Error generating reseller API key for %s: %s", user.id, exc, exc_info=True)
        await query.edit_message_text(
            t("api_generate_error", lang),
            reply_markup=reseller_api_keyboard(lang, docs_url=_api_docs_url()),
        )
