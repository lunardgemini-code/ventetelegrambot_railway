"""Pixel Gemini Activation Tool Handler (Admin-Only).

Allows admins to trigger Pixel Gemini account activations directly by
selecting a task mode and submitting Google account credentials (email, password, 2FA secret).
"""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.models import (
    get_user_lang,
    get_user_pixel_points,
    deduct_user_pixel_points,
    get_pixel_point_packs,
    get_pixel_settings,
)
from services.pixel_payment import topup_pixel_points_via_wallet
from services.supplier_registry import purchase_supplier_product, _provider_config
from services.supplier_multi_api import _request
from utils.helpers import escape_html, is_admin
from utils.keyboards import make_button
from utils.locales import t
from utils.telegram import safe_edit_message_text
from services.pixel_worker import record_pixel_task, get_user_pixel_tasks

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
    user_points = await get_user_pixel_points(user_id)

    balance_text = t("pixel_balance_header", lang).format(points=user_points)
    text = f"{balance_text}\n\n" + t("pixel_title", lang)

    markup = InlineKeyboardMarkup([
        [make_button("pixel_mode_fast_sub", lang, callback_data="pixel_mode:extract_link_fast")],
        [make_button("pixel_mode_normal_sub", lang, callback_data="pixel_mode:extract_link_normal")],
        [InlineKeyboardButton(t("btn_pixel_topup", lang), callback_data="pixel_topup_start")],
        [InlineKeyboardButton(t("pixel_my_activations_btn", lang), callback_data="pixel_my_activations")],
        [make_button("btn_back", lang, callback_data="back_main")],
    ])

    if query:
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def pixel_topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_topup_start' callback — display available Point Packs for purchase."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    user_points = await get_user_pixel_points(user_id)
    packs = await get_pixel_point_packs()

    text = t("pixel_balance_header", lang).format(points=user_points) + "\n\n" + t("pixel_topup_title", lang)

    buttons = []
    for pack in packs:
        if not pack.get("is_active", 1):
            continue
        pid = pack["id"]
        pts = pack["points"]
        price = pack["price_usd"]
        disc = pack.get("discount_percent", 0)

        label = f"🎁 {pts} PTS — ${price:.2f} USD"
        if disc > 0:
            label += f" ({disc:.0f}% OFF🔥)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"pixel_topup_buy:{pid}")])

    buttons.append([InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")])
    buttons.append([make_button("btn_back", lang, callback_data="pixel_activation_start")])

    markup = InlineKeyboardMarkup(buttons)
    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)


async def pixel_topup_select_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_topup_buy:{pack_id}' callback — show confirmation and payment method choice."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    pack_id_str = query.data.split(":", 1)[1]
    pack_id = int(pack_id_str)

    packs = await get_pixel_point_packs()
    pack = next((p for p in packs if p["id"] == pack_id), None)
    if not pack:
        await safe_edit_message_text(query, "Pack introuvable.", parse_mode="HTML")
        return

    from database.db import get_db
    db = await get_db()
    cursor = await db.execute("SELECT wallet_balance FROM users WHERE telegram_id = ?", (int(user_id),))
    row = await cursor.fetchone()
    wallet_bal = float(row[0] or 0) if row else 0.0

    cost_usd = float(pack["price_usd"])
    points = int(pack["points"])

    text = (
        f"🎁 <b>Pack Sélectionné : {points} PTS</b>\n"
        f"💵 <b>Prix :</b> ${cost_usd:.2f} USD\n\n"
        f"💼 <b>Votre Solde Wallet :</b> ${wallet_bal:.2f} USD\n\n"
    )

    if wallet_bal >= cost_usd:
        text += "✅ Vous avez suffisamment de fonds. Veuillez confirmer l'achat avec votre Wallet :"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Confirmer l'achat (Wallet)", callback_data=f"pixel_topup_exec:{pack_id}")],
            [make_button("btn_back", lang, callback_data="pixel_topup_start")],
        ])
    else:
        text += "⚠️ <b>Solde insuffisant.</b>\nVous devez d'abord recharger votre Wallet via Binance ou Crypto Pay pour acheter ce pack."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Recharger mon Wallet (Binance/Crypto)", callback_data="menu_wallet")],
            [make_button("btn_back", lang, callback_data="pixel_topup_start")],
        ])

    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)

async def pixel_topup_execute_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_topup_exec:{pack_id}' callback — execute wallet top-up."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    pack_id_str = query.data.split(":", 1)[1]
    pack_id = int(pack_id_str)

    res = await topup_pixel_points_via_wallet(user_id, pack_id)
    if res["success"]:
        text = t("pixel_topup_success", lang).format(
            points=res["points_added"],
            cost=f"{res['cost_usd']:.2f}",
            new_balance=res["new_points_balance"],
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")],
            [make_button("btn_back", lang, callback_data="pixel_activation_start")],
        ])
    else:
        text = t("pixel_topup_wallet_fail", lang).format(
            cost=f"{res.get('cost_usd', 0):.2f}",
            current=f"{res.get('current_balance', 0):.2f}",
        )
        markup = InlineKeyboardMarkup([
            [make_button("btn_wallet", lang, callback_data="menu_wallet")],
            [InlineKeyboardButton(t("btn_pixel_topup", lang), callback_data="pixel_topup_start")],
            [make_button("btn_back", lang, callback_data="pixel_activation_start")],
        ])

    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)

async def pixel_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_mode:{mode}' callback — set selected mode and prompt for credentials."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    mode_id = query.data.split(":", 1)[1]

    settings = await get_pixel_settings()
    required_points = settings["fast_mode_points"] if mode_id == "extract_link_fast" else settings["normal_mode_points"]
    user_points = await get_user_pixel_points(user_id)

    if user_points < required_points:
        text = t("pixel_insufficient_points", lang).format(
            required=required_points,
            current=user_points,
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_pixel_topup", lang), callback_data="pixel_topup_start")],
            [InlineKeyboardButton(t("btn_change_mode", lang) if t("btn_change_mode", lang) != "btn_change_mode" else "🔄 Change Mode", callback_data="pixel_activation_start")],
            [make_button("btn_back", lang, callback_data="pixel_activation_start")],
        ])
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
        return

    context.user_data["pixel_selected_mode"] = mode_id
    context.user_data["pixel_awaiting_creds"] = True

    mode_key = "pixel_mode_fast_sub" if mode_id == "extract_link_fast" else "pixel_mode_normal_sub"
    mode_title = t(mode_key, lang)

    balance_hdr = t("pixel_balance_header", lang).format(points=user_points)
    text = f"{balance_hdr}\n\n" + t("pixel_prompt_creds", lang).format(mode=escape_html(mode_title))

    change_mode_lbl = t("btn_change_mode", lang)
    if change_mode_lbl == "btn_change_mode":
        change_mode_lbl = "🔄 Change Mode"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(change_mode_lbl, callback_data="pixel_activation_start")],
        [make_button("btn_cancel", lang, callback_data="pixel_activation_start")],
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
        settings = await get_pixel_settings()
        cost_points = settings["fast_mode_points"] if mode_id == "extract_link_fast" else settings["normal_mode_points"]

        deducted = await deduct_user_pixel_points(user_id, cost_points, ref_id="task_submit")
        if not deducted:
            user_pts = await get_user_pixel_points(user_id)
            await loading_msg.edit_text(
                t("pixel_insufficient_points", lang).format(required=cost_points, current=user_pts),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("btn_pixel_topup", lang), callback_data="pixel_topup_start")],
                    [make_button("btn_back", lang, callback_data="pixel_activation_start")],
                ])
            )
            return True

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
            [make_button("btn_back", lang, callback_data="pixel_activation_start")],
        ])

        await loading_msg.edit_text(success_text, parse_mode="HTML", reply_markup=markup)
        return True
    except Exception as exc:
        logger.error("Pixel activation submission failed: %s", exc, exc_info=True)
        if 'cost_points' in locals() and 'deducted' in locals() and deducted:
            try:
                from database.models import add_user_pixel_points
                await add_user_pixel_points(user_id, cost_points, 0, "refund_submit_fail", "submit_failed")
            except Exception as ref_exc:
                logger.error("Failed to refund points on submission error: %s", ref_exc)
        err_text = t("pixel_submit_error", lang).format(error=escape_html(str(exc)))
        await loading_msg.edit_text(
            err_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("pixel_new_btn", lang), callback_data="pixel_activation_start")],
                [make_button("btn_back", lang, callback_data="pixel_activation_start")],
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
            [make_button("btn_back", lang, callback_data="pixel_activation_start")],
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
                [make_button("btn_back", lang, callback_data="pixel_activation_start")],
            ]),
        )

async def pixel_my_activations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_my_activations' callback — show user's recent/active activation tasks."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    lang = await _get_lang(user_id)
    tasks = await get_user_pixel_tasks(user_id)

    if not tasks:
        text = t("pixel_my_activations_empty", lang)
    else:
        text = t("pixel_my_activations_title", lang)
        for task in tasks:
            task_id = task["task_id"]
            email = task["email"]
            mode = task["task_mode"]
            status = (task["status"] or "pending").lower()
            status_emoji = "✅" if status == "success" else ("❌" if status in ("failed", "error") else "⏳")
            link = task.get("result_link", "")
            err = task.get("error_message", "")

            text += (
                f"⚡ <b>Tâche #{task_id}</b>\n"
                f"📧 <b>Account:</b> <code>{escape_html(email)}</code>\n"
                f"⚙️ <b>Mode:</b> <code>{escape_html(mode)}</code>\n"
                f"📊 <b>Status:</b> {status_emoji} <code>{escape_html(status.upper())}</code>\n"
            )
            if link:
                text += f"🔗 <b>Link:</b> <code>{escape_html(link)}</code>\n"
            if err:
                text += f"⚠️ <b>Error:</b> <code>{escape_html(err)}</code>\n"
            text += "\n"

    refresh_lbl = t("pixel_refresh_btn", lang)
    if refresh_lbl == "pixel_refresh_btn":
        refresh_lbl = "🔄 Refresh"
    new_lbl = t("pixel_new_btn", lang)
    if new_lbl == "pixel_new_btn":
        new_lbl = "✨ New Activation"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(refresh_lbl, callback_data="pixel_my_activations")],
        [InlineKeyboardButton(new_lbl, callback_data="pixel_activation_start")],
        [make_button("btn_back", lang, callback_data="pixel_activation_start")],
    ])

    if query:
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
