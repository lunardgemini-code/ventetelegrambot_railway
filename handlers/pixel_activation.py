"""Pixel Gemini Activation Tool Handler (Admin-Only).

Allows admins to trigger Pixel Gemini account activations directly by
selecting a task mode and submitting Google account credentials (email, password, 2FA secret).
"""

import logging
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.supplier_registry import purchase_supplier_product, _provider_config
from services.supplier_multi_api import _request
from utils.helpers import escape_html
from utils.helpers import is_admin
from utils.keyboards import main_menu_keyboard
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "extract_link_fast": "⚡ Extract Link (Fast — 6 PTS)",
    "extract_link_normal": "🐢 Extract Link (Normal — 5 PTS)",
    "direct_subscription_fast": "⚡ Direct Subscription (Fast — 6 PTS)",
    "direct_subscription_normal": "🐢 Direct Subscription (Normal — 5 PTS)",
}


async def pixel_activation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pixel_activation_start' callback — prompt admin to choose activation mode."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    context.user_data.pop("pixel_awaiting_creds", None)

    text = (
        "✨ <b>Outil d'Activation Pixel Gemini v1 (Admin)</b>\n\n"
        "Choisissez le mode de tâche à exécuter pour l'activation du compte Google :"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Extract Link (Fast - 6 PTS)", callback_data="pixel_mode:extract_link_fast")],
        [InlineKeyboardButton("🐢 Extract Link (Normal - 5 PTS)", callback_data="pixel_mode:extract_link_normal")],
        [InlineKeyboardButton("⚡ Direct Subscription (Fast - 6 PTS)", callback_data="pixel_mode:direct_subscription_fast")],
        [InlineKeyboardButton("🐢 Direct Subscription (Normal - 5 PTS)", callback_data="pixel_mode:direct_subscription_normal")],
        [InlineKeyboardButton("↩️ Retour Menu Principal", callback_data="back_main")],
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

    mode_id = query.data.split(":", 1)[1]
    context.user_data["pixel_selected_mode"] = mode_id
    context.user_data["pixel_awaiting_creds"] = True

    mode_title = MODE_LABELS.get(mode_id, mode_id)

    text = (
        f"✨ <b>Activation Pixel Gemini</b>\n"
        f"⚙️ <b>Mode Sélectionné :</b> <code>{escape_html(mode_title)}</code>\n\n"
        f"Veuillez envoyer les identifiants du compte Google sous le format :\n\n"
        f"<code>email|mot_de_passe|secret_2FA_32_caracteres</code>\n\n"
        f"<i>Exemple :</i>\n"
        f"<code>testuser@gmail.com|monmotdepasse123|JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Changer de Mode", callback_data="pixel_activation_start")],
        [InlineKeyboardButton("↩️ Annuler", callback_data="back_main")],
    ])

    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)


async def receive_pixel_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler receiving the email|password|2fa_secret text input."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return False

    if not context.user_data.get("pixel_awaiting_creds"):
        return False

    raw_text = (update.message.text or "").strip()
    parts = [p.strip() for p in raw_text.replace("|", "\n").splitlines() if p.strip()]

    if len(parts) < 3 or "@" not in parts[0]:
        await update.message.reply_text(
            "⚠️ <b>Format d'identifiants invalide.</b>\n\n"
            "Veuillez envoyer sous le format exact :\n"
            "<code>email|mot_de_passe|secret_2FA_32_caracteres</code>",
            parse_mode="HTML",
        )
        return True

    email, password, twofa_secret = parts[0], parts[1], parts[2]
    mode_id = context.user_data.get("pixel_selected_mode", "extract_link_fast")
    context.user_data.pop("pixel_awaiting_creds", None)

    loading_msg = await update.message.reply_text(
        "⏳ <b>Soumission de l'activation Pixel Gemini en cours...</b>",
        parse_mode="HTML",
    )

    try:
        buyer_info = f"{email}|{password}|{twofa_secret}"
        result = await purchase_supplier_product("pixel", mode_id, 1, buyer_info=buyer_info)
        task_id = str(result.get("order_id") or "1")

        success_text = (
            f"✅ <b>Tâche d'Activation Soumise avec Succès !</b>\n\n"
            f"⚡ <b>ID Tâche :</b> <code>#{escape_html(task_id)}</code>\n"
            f"📧 <b>Compte :</b> <code>{escape_html(email)}</code>\n"
            f"⚙️ <b>Mode :</b> <code>{escape_html(mode_id)}</code>\n"
            f"📊 <b>Statut Initial :</b> <code>pending</code>\n\n"
            f"<i>La promotion est en cours d'activation sur le bot Pixel Gemini.</i>"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Vérifier le Statut (Query)", callback_data=f"pixel_query:{task_id}")],
            [InlineKeyboardButton("✨ Nouvelle Activation", callback_data="pixel_activation_start")],
            [InlineKeyboardButton("↩️ Menu Principal", callback_data="back_main")],
        ])

        await loading_msg.edit_text(success_text, parse_mode="HTML", reply_markup=markup)
        return True
    except Exception as exc:
        logger.error("Pixel activation submission failed: %s", exc, exc_info=True)
        await loading_msg.edit_text(
            f"❌ <b>Échec de la soumission de l'activation Pixel :</b>\n\n"
            f"<code>{escape_html(str(exc))}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Réessayer", callback_data="pixel_activation_start")],
                [InlineKeyboardButton("↩️ Menu Principal", callback_data="back_main")],
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

        text = (
            f"{status_emoji} <b>Statut Tâche Pixel Gemini {escape_html(display_id)}</b>\n\n"
            f"📊 <b>Statut :</b> <code>{escape_html(status.upper())}</code>\n"
        )
        if result_link:
            text += f"🔗 <b>Lien Résultat :</b> <code>{escape_html(result_link)}</code>\n"
        if error_msg:
            text += f"⚠️ <b>Erreur :</b> <code>{escape_html(error_msg)}</code>\n"

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Rafraîchir le Statut", callback_data=f"pixel_query:{task_id_str}")],
            [InlineKeyboardButton("✨ Nouvelle Activation", callback_data="pixel_activation_start")],
            [InlineKeyboardButton("↩️ Menu Principal", callback_data="back_main")],
        ])

        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    except Exception as exc:
        logger.error("Pixel task query failed: %s", exc)
        await safe_edit_message_text(
            query,
            f"⚠️ <b>Impossible de récupérer le statut de la tâche #{escape_html(task_id_str)} :</b>\n"
            f"<code>{escape_html(str(exc))}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Réessayer", callback_data=f"pixel_query:{task_id_str}")],
                [InlineKeyboardButton("↩️ Menu Principal", callback_data="back_main")],
            ]),
        )
