"""Pixel Gemini Activation Tool Handler (Admin-Only).

Allows admins to trigger Pixel Gemini account activations directly by
selecting a task mode and submitting Google account credentials (email, password, 2FA secret).
"""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.models import get_user_lang
from services.supplier_registry import purchase_supplier_product, _provider_config
from services.supplier_multi_api import _request
from utils.helpers import escape_html, is_admin
from utils.keyboards import make_button
from utils.locales import t
from utils.telegram import safe_edit_message_text
from services.pixel_worker import record_pixel_task

logger = logging.getLogger(__name__)


async def _get_lang(user_id: int) -> str:
    try:
        return await get_user_lang(user_id) or "fr"
    except Exception:
        return "fr"

async def pixel_activation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_activation_start' callback — prompt admin to choose activation mode."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    context.user_data.pop("pixel_awaiting_creds", None)
    lang = await _get_lang(user_id)

    text = t("pixel_title", lang)

    markup = InlineKeyboardMarkup([
        [make_button("pixel_mode_fast_sub", lang, callback_data="pixel_mode:extract_link_fast")],
        [make_button("pixel_mode_normal_sub", lang, callback_data="pixel_mode:extract_link_normal")],
        [make_button("btn_back", lang, callback_data="back_main")],
    ])

    if query:
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def pixel_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_mode:{mode}' callback — set selected mode and prompt for credentials."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    mode_id = query.data.split(":", 1)[1]
    context.user_data["pixel_selected_mode"] = mode_id
    context.user_data["pixel_awaiting_creds"] = True

    mode_key = "pixel_mode_fast_sub" if mode_id == "extract_link_fast" else "pixel_mode_normal_sub"
    mode_title = t(mode_key, lang)

    text = t("pixel_prompt_creds", lang).format(mode=escape_html(mode_title))

    change_mode_lbl = t("btn_change_mode", lang)
    if change_mode_lbl == "btn_change_mode":
        change_mode_lbl = "🔄 Change Mode"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(change_mode_lbl, callback_data="pixel_activation_start")],
        [make_button("btn_cancel", lang, callback_data="back_main")],
    ])

    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)


async def receive_pixel_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler receiving the email|password|2fa_secret text input."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return False

    if not context.user_data.get("pixel_awaiting_creds"):
        return False

    lang = await _get_lang(user_id)
    raw_text = (update.message.text or "").strip()
    parts = [p.strip() for p in raw_text.replace("|", "\n").splitlines() if p.strip()]

    if len(parts) < 3 or "@" not in parts[0]:
        await update.message.reply_text(
            t("pixel_invalid_format", lang),
            parse_mode="HTML",
        )
        return True

    email, password, twofa_secret = parts[0], parts[1], parts[2]
    mode_id = context.user_data.get("pixel_selected_mode", "extract_link_fast")
    context.user_data.pop("pixel_awaiting_creds", None)

    loading_msg = await update.message.reply_text(
        t("pixel_submitting", lang),
        parse_mode="HTML",
    )

    try:
        buyer_info = f"{email}|{password}|{twofa_secret}"
        result = await purchase_supplier_product("pixel", mode_id, 1, buyer_info=buyer_info)
        task_id = str(result.get("order_id") or "1")
        try:
            await record_pixel_task(int(task_id), user_id, email, mode_id)
        except Exception:
            pass

        success_text = t("pixel_submit_success", lang).format(
            task_id=escape_html(task_id),
            email=escape_html(email),
            mode_id=escape_html(mode_id),
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_query_btn", lang), callback_data=f"pixel_query:{task_id}")],
            [InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")],
            [make_button("btn_back", lang, callback_data="back_main")],
        ])

        await loading_msg.edit_text(success_text, parse_mode="HTML", reply_markup=markup)
        return True
    except Exception as exc:
        logger.error("Pixel activation submission failed: %s", exc, exc_info=True)
        err_text = t("pixel_submit_error", lang).format(error=escape_html(str(exc)))
        await loading_msg.edit_text(
            err_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")],
                [make_button("btn_back", lang, callback_data="back_main")],
            ]),
        )
        return True


async def pixel_query_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_query:{task_id}' callback — query task status via API."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    task_id_str = query.data.split(":", 1)[1]
    try:
        provider = _provider_config("pixel")
        payload = await _request(
            provider,
            "POST",
            "/api/v1/query",
            json={"task_id": int(task_id_str)},
        )

        task_data = payload.get("task") or {}
        if not task_data and isinstance(payload.get("tasks"), list) and payload["tasks"]:
            task_data = payload["tasks"][0].get("task") or {}

        status = str(task_data.get("status") or "inconnu").lower()
        result_link = str(task_data.get("result_link") or "")
        error_msg = str(task_data.get("error_message") or "")
        display_id = str(task_data.get("display_id") or f"#{task_id_str}")

        status_emoji = "✅" if status == "success" else ("❌" if status in ("failed", "error") else "⏳")

        text = t("pixel_status_title", lang).format(
            emoji=status_emoji,
            display_id=escape_html(display_id),
            status=escape_html(status.upper()),
        ) + "\n"

        if result_link:
            text += f"🔗 <b>Link:</b> <code>{escape_html(result_link)}</code>\n"
        if error_msg:
            text += f"⚠️ <b>Error:</b> <code>{escape_html(error_msg)}</code>\n"

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_refresh_btn", lang), callback_data=f"pixel_query:{task_id_str}")],
            [InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")],
            [make_button("btn_back", lang, callback_data="back_main")],
        ])

        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    except Exception as exc:
        logger.error("Pixel task query failed: %s", exc)
        await safe_edit_message_text(
            query,
            f"⚠️ <b>Error querying #{escape_html(task_id_str)}:</b>\n<code>{escape_html(str(exc))}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("pixel_refresh_btn", lang), callback_data=f"pixel_query:{task_id_str}")],
                [make_button("btn_back", lang, callback_data="back_main")],
            ]),
        )
