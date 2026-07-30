"""Admin-only Pixel activation conversation.

Only this ConversationHandler reads credential messages.  It never registers a
catch-all text handler, so support, orders and reseller traffic stay isolated.
"""

from __future__ import annotations

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import KeyboardButtonStyle
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config import PIXEL_ADMIN_ONLY, PIXEL_ENABLED
from database.models import (
    create_pixel_activation_draft,
    create_pixel_activation_batch_drafts,
    get_pixel_activation_settings,
    get_pixel_activation_task,
    get_pixel_credit_balance,
    get_pixel_credit_packs,
    get_user_lang,
    get_wallet_balance,
    list_pixel_activation_tasks,
    purchase_pixel_credit_pack,
    reserve_pixel_activation_task,
    reserve_pixel_activation_batch,
    signal_pixel_reconciliation,
)
from services.pixel_worker import process_pixel_activation_cycle
from utils.helpers import escape_html, is_admin
from utils.keyboards import make_button
from utils.locales import t
from utils.telegram import safe_edit_message_text


logger = logging.getLogger(__name__)
PIXEL_CREDENTIALS = 310
PIXEL_CONFIRM = 311
PIXEL_BATCH_MAX_SIZE = 20
_PIXEL_TWOFA_SECRET_RE = re.compile(r"[A-Z2-7]{32}")


def _format_pixel_credits(value: object) -> str:
    """Keep customer-facing credit amounts compact while preserving decimals."""
    try:
        return f"{float(value):.3f}".rstrip("0").rstrip(".") or "0"
    except (TypeError, ValueError):
        return "0"


def parse_pixel_credentials_message(text: str) -> list[dict[str, str]]:
    """Parse one legacy three-line record or a pipe-delimited batch.

    The provider requires a raw 32-character Base32 secret. In particular,
    ``otpauth://`` URLs are not a supported substitute.
    """
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        raise ValueError("No Pixel credentials were supplied")

    pipe_mode = any("|" in line for line in lines)
    if pipe_mode:
        if len(lines) > PIXEL_BATCH_MAX_SIZE or any("|" not in line for line in lines):
            raise ValueError("Invalid Pixel batch")
        raw_entries = []
        for line in lines:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 3:
                raise ValueError("Invalid Pixel batch entry")
            raw_entries.append(parts)
    else:
        if len(lines) != 3:
            raise ValueError("Invalid Pixel credentials")
        raw_entries = [lines]

    entries: list[dict[str, str]] = []
    seen_emails: set[str] = set()
    for email, password, raw_secret in raw_entries:
        normalized_email = str(email or "").strip().lower()
        normalized_password = str(password or "").strip()
        secret_text = str(raw_secret or "").strip()
        normalized_secret = re.sub(r"[\s-]+", "", secret_text).upper()
        if (
            "@" not in normalized_email
            or len(normalized_email) > 254
            or not normalized_password
            or "otpauth://" in secret_text.lower()
            or "://" in secret_text
            or not _PIXEL_TWOFA_SECRET_RE.fullmatch(normalized_secret)
            or normalized_email in seen_emails
        ):
            raise ValueError("Invalid Pixel credentials")
        seen_emails.add(normalized_email)
        entries.append({
            "email": normalized_email,
            "password": normalized_password,
            "twofa_secret": normalized_secret,
        })
    return entries


async def pixel_activation_available_for_user(user_id: int) -> bool:
    if not PIXEL_ENABLED:
        return False
    settings = await get_pixel_activation_settings()
    if not settings.get("is_enabled"):
        return False
    if PIXEL_ADMIN_ONLY or settings.get("admin_only"):
        return is_admin(int(user_id))
    return True


async def _lang(user_id: int) -> str:
    try:
        return await get_user_lang(int(user_id)) or "fr"
    except Exception:
        return "fr"


async def _guard(update: Update) -> tuple[bool, str]:
    user_id = int(update.effective_user.id)
    lang = await _lang(user_id)
    if await pixel_activation_available_for_user(user_id):
        return True, lang
    query = update.callback_query
    if query:
        try:
            await query.answer(t("pixel_unavailable", lang), show_alert=True)
        except Exception:
            pass
    return False, lang


def _main_markup(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t("pixel_mode_fast_button", lang),
            callback_data="pixel:mode:fast",
            style=KeyboardButtonStyle.PRIMARY,
        )],
        # Telegram only supports blue, green, and red button backgrounds. The
        # purple marker keeps the Standard option visually distinct without
        # misrepresenting a color that the Telegram API cannot render.
        [InlineKeyboardButton(
            t("pixel_mode_normal_button", lang),
            callback_data="pixel:mode:normal",
        )],
        [InlineKeyboardButton(
            t("pixel_buy_credits", lang),
            callback_data="pixel:credits",
            style=KeyboardButtonStyle.SUCCESS,
        )],
        [InlineKeyboardButton(t("pixel_my_tasks", lang), callback_data="pixel:tasks")],
        [make_button("btn_back", lang, callback_data="back_main")],
    ])


async def pixel_activation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    user_id = int(update.effective_user.id)
    credits = await get_pixel_credit_balance(user_id)
    settings = await get_pixel_activation_settings()
    text = t("pixel_menu", lang).format(
        credits=_format_pixel_credits(credits),
        fast_credits=_format_pixel_credits(settings["fast_credits"]),
        normal_credits=_format_pixel_credits(settings["normal_credits"]),
    )
    if query:
        await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=_main_markup(lang))
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=_main_markup(lang))


async def pixel_credit_packs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    credits = await get_pixel_credit_balance(int(update.effective_user.id))
    packs = await get_pixel_credit_packs(active_only=True)
    rows = []
    for pack in packs:
        label = str(pack.get("label") or "").strip()
        credits_label = _format_pixel_credits(pack["credits"])
        title = label or t("pixel_credit_pack", lang).format(credits=credits_label)
        rows.append([
            InlineKeyboardButton(
                f"{title} - {credits_label} {t('pixel_credits_short', lang)} (${pack['price_usd']:.2f})",
                callback_data=f"pixel:credit-pack:{int(pack['id'])}",
            )
        ])
    if not rows:
        rows.append([InlineKeyboardButton(t("pixel_no_credit_packs", lang), callback_data="pixel:menu")])
    rows.append([InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")])
    text = t("pixel_credit_packs", lang).format(credits=_format_pixel_credits(credits))
    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def pixel_credit_pack_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    try:
        pack_id = int(str(query.data).rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    pack = next((item for item in await get_pixel_credit_packs(active_only=True) if int(item["id"]) == pack_id), None)
    if not pack:
        await safe_edit_message_text(query, t("pixel_pack_unavailable", lang), reply_markup=_main_markup(lang))
        return
    wallet_balance = await get_wallet_balance(int(update.effective_user.id))
    enough = wallet_balance >= float(pack["price_usd"])
    text = t("pixel_credit_confirm", lang).format(
        credits=_format_pixel_credits(pack["credits"]),
        price=f"{pack['price_usd']:.2f}",
        wallet=f"{wallet_balance:.2f}",
    )
    rows = []
    if enough:
        rows.append([InlineKeyboardButton(t("pixel_confirm_credit_purchase", lang), callback_data=f"pixel:credit-buy:{pack_id}")])
    else:
        text += "\n\n" + t("pixel_wallet_insufficient", lang)
        rows.append([make_button("btn_wallet", lang, callback_data="menu_wallet")])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="pixel:credits")])
    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def pixel_credit_pack_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    try:
        pack_id = int(str(query.data).rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    message = query.message
    reference_key = f"pixel-topup:{update.effective_user.id}:{pack_id}:{message.chat_id}:{message.message_id}"
    try:
        result = await purchase_pixel_credit_pack(
            int(update.effective_user.id), pack_id, reference_key=reference_key
        )
    except ValueError as exc:
        if str(exc) == "INSUFFICIENT_WALLET_BALANCE":
            await safe_edit_message_text(
                query,
                t("pixel_wallet_insufficient", lang),
                reply_markup=InlineKeyboardMarkup([
                    [make_button("btn_wallet", lang, callback_data="menu_wallet")],
                    [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
                ]),
            )
            return
        logger.warning("Pixel credit purchase rejected: %s", exc)
        await safe_edit_message_text(query, t("pixel_credit_purchase_failed", lang), reply_markup=_main_markup(lang))
        return
    text = t("pixel_credit_purchase_success", lang).format(
        credits=_format_pixel_credits(result["credits_added"]),
        balance=_format_pixel_credits(result["credit_balance"]),
        wallet=f"{result['wallet_balance']:.2f}",
    )
    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=_main_markup(lang))


async def pixel_select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return ConversationHandler.END
    channel = "fast" if str(query.data).endswith(":fast") else "normal"
    settings = await get_pixel_activation_settings()
    credits = settings["fast_credits"] if channel == "fast" else settings["normal_credits"]
    context.user_data["pixel_channel"] = channel
    text = t("pixel_credentials_prompt", lang).format(
        channel=escape_html(t(f"pixel_channel_{channel}", lang)),
        credits=_format_pixel_credits(credits),
        max_accounts=PIXEL_BATCH_MAX_SIZE,
    )
    await safe_edit_message_text(
        query,
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_cancel", lang), callback_data="pixel:cancel")],
        ]),
    )
    return PIXEL_CREDENTIALS


async def pixel_receive_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    allowed, lang = await _guard(update)
    if not allowed:
        return ConversationHandler.END
    try:
        entries = parse_pixel_credentials_message(str(update.effective_message.text or ""))
    except ValueError:
        await update.effective_message.reply_text(
            t("pixel_credentials_invalid", lang).format(max_accounts=PIXEL_BATCH_MAX_SIZE),
            parse_mode="HTML",
        )
        return PIXEL_CREDENTIALS
    channel = "fast" if context.user_data.get("pixel_channel") == "fast" else "normal"
    user = update.effective_user
    display_name = " ".join(part for part in (user.first_name, user.last_name) if part).strip() or (user.username or str(user.id))
    try:
        if len(entries) == 1:
            entry = entries[0]
            draft = await create_pixel_activation_draft(
                user_telegram_id=int(user.id),
                user_display_name=display_name,
                email=entry["email"],
                password=entry["password"],
                twofa_secret=entry["twofa_secret"],
                channel=channel,
                request_key=f"pixel-draft:{user.id}:{update.effective_message.message_id}",
            )
            batch = None
        else:
            batch_result = await create_pixel_activation_batch_drafts(
                user_telegram_id=int(user.id),
                user_display_name=display_name,
                credentials=entries,
                channel=channel,
                request_key=f"pixel-batch:{user.id}:{update.effective_message.message_id}",
            )
            batch = batch_result["batch"]
            draft = None
    except (ValueError, RuntimeError) as exc:
        logger.warning("Pixel draft could not be stored: %s", exc)
        await update.effective_message.reply_text(t("pixel_credentials_store_failed", lang), parse_mode="HTML")
        return ConversationHandler.END
    finally:
        context.user_data.pop("pixel_channel", None)

    # The trace is now encrypted in Turso. Delete Telegram's plaintext copy as
    # soon as possible, without treating a deletion failure as a task failure.
    try:
        await update.effective_message.delete()
    except Exception:
        pass
    settings = await get_pixel_activation_settings()
    cost = settings["fast_credits"] if channel == "fast" else settings["normal_credits"]
    if batch:
        count = len(entries)
        confirmation = t("pixel_batch_confirm", lang).format(
            count=count,
            channel=escape_html(t(f"pixel_channel_{channel}", lang)),
            credits=_format_pixel_credits(cost * count),
        )
        await update.effective_chat.send_message(
            confirmation,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    t("pixel_confirm_batch", lang).format(count=count),
                    callback_data=f"pixel:batch-confirm:{batch['public_id']}",
                )],
                [InlineKeyboardButton(t("btn_cancel", lang), callback_data="pixel:cancel")],
            ]),
        )
        return PIXEL_CONFIRM

    entry = entries[0]
    confirmation = t("pixel_task_confirm", lang).format(
        email=escape_html(entry["email"]),
        channel=escape_html(t(f"pixel_channel_{channel}", lang)),
        credits=_format_pixel_credits(cost),
    )
    await update.effective_chat.send_message(
        confirmation,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_confirm_task", lang), callback_data=f"pixel:confirm:{draft['public_id']}")],
            [InlineKeyboardButton(t("btn_cancel", lang), callback_data="pixel:cancel")],
        ]),
    )
    return PIXEL_CONFIRM


async def pixel_confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return ConversationHandler.END
    try:
        public_id = str(query.data).rsplit(":", 1)[1]
    except IndexError:
        return ConversationHandler.END
    try:
        task = await reserve_pixel_activation_task(public_id, int(update.effective_user.id))
    except ValueError as exc:
        if str(exc) == "INSUFFICIENT_PIXEL_CREDITS":
            await safe_edit_message_text(
                query,
                t("pixel_credits_insufficient", lang),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("pixel_buy_credits", lang), callback_data="pixel:credits")],
                    [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
                ]),
            )
            return ConversationHandler.END
        await safe_edit_message_text(query, t("pixel_task_not_found", lang), reply_markup=_main_markup(lang))
        return ConversationHandler.END

    # The task is durable and reserved first. The external calls deliberately
    # run outside the callback so Telegram stays responsive under supplier lag.
    if task.get("newly_reserved"):
        context.application.create_task(
            process_pixel_activation_cycle(context.bot, busy=False),
            update=update,
            name="pixel-confirm-cycle",
        )
    await safe_edit_message_text(
        query,
        t("pixel_task_queued", lang).format(task_id=escape_html(public_id)),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_view_task", lang), callback_data=f"pixel:task:{public_id}")],
            [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
        ]),
    )
    return ConversationHandler.END


async def pixel_confirm_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return ConversationHandler.END
    try:
        batch_public_id = str(query.data).rsplit(":", 1)[1]
    except IndexError:
        return ConversationHandler.END
    try:
        result = await reserve_pixel_activation_batch(batch_public_id, int(update.effective_user.id))
    except ValueError as exc:
        if str(exc) == "INSUFFICIENT_PIXEL_CREDITS":
            await safe_edit_message_text(
                query,
                t("pixel_credits_insufficient", lang),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("pixel_buy_credits", lang), callback_data="pixel:credits")],
                    [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
                ]),
            )
            return ConversationHandler.END
        await safe_edit_message_text(query, t("pixel_task_not_found", lang), reply_markup=_main_markup(lang))
        return ConversationHandler.END

    tasks = result.get("tasks") or []
    if result.get("newly_reserved"):
        context.application.create_task(
            process_pixel_activation_cycle(context.bot, busy=False),
            update=update,
            name="pixel-batch-confirm-cycle",
        )
    await safe_edit_message_text(
        query,
        t("pixel_batch_queued", lang).format(
            count=len(tasks),
            credits=_format_pixel_credits((result.get("batch") or {}).get("credits_reserved")),
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_my_tasks", lang), callback_data="pixel:tasks")],
            [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
        ]),
    )
    return ConversationHandler.END


async def pixel_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        lang = await _lang(int(update.effective_user.id))
        await safe_edit_message_text(query, t("pixel_cancelled", lang), reply_markup=_main_markup(lang))
    context.user_data.pop("pixel_channel", None)
    return ConversationHandler.END


async def pixel_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    tasks = await list_pixel_activation_tasks(user_telegram_id=int(update.effective_user.id), limit=8)
    if not tasks:
        text = t("pixel_tasks_empty", lang)
    else:
        chunks = [t("pixel_tasks_title", lang)]
        for task in tasks:
            status = escape_html(str(task.get("status") or "-"))
            chunks.append(
                t("pixel_task_line", lang).format(
                    task_id=escape_html(str(task["public_id"])),
                    email=escape_html(str(task.get("email") or "")),
                    status=status,
                    credits=_format_pixel_credits(task.get("credits_reserved")),
                )
            )
        text = "\n\n".join(chunks)
    rows = [
        [InlineKeyboardButton(t("pixel_refresh_tasks", lang), callback_data="pixel:tasks")],
        [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:menu")],
    ]
    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def pixel_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    allowed, lang = await _guard(update)
    if not allowed:
        return
    try:
        public_id = str(query.data).rsplit(":", 1)[1]
    except IndexError:
        return
    task = await get_pixel_activation_task(public_id, user_telegram_id=int(update.effective_user.id))
    if not task:
        await safe_edit_message_text(query, t("pixel_task_not_found", lang), reply_markup=_main_markup(lang))
        return
    await signal_pixel_reconciliation(public_id)
    text = t("pixel_task_detail", lang).format(
        task_id=escape_html(public_id),
        email=escape_html(str(task.get("email") or "")),
        status=escape_html(str(task.get("status") or "")),
        credits=_format_pixel_credits(task.get("credits_reserved")),
        result_link=escape_html(str(task.get("result_link") or "-")),
        error=escape_html(str(task.get("error_message") or "-")),
    )
    await safe_edit_message_text(
        query,
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("pixel_refresh_tasks", lang), callback_data=f"pixel:task:{public_id}")],
            [InlineKeyboardButton(t("pixel_back_activation", lang), callback_data="pixel:tasks")],
        ]),
    )


def pixel_activation_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(pixel_select_channel, pattern=r"^pixel:mode:(fast|normal)$")],
        states={
            PIXEL_CREDENTIALS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pixel_receive_credentials),
            ],
            PIXEL_CONFIRM: [
                CallbackQueryHandler(pixel_confirm_task, pattern=r"^pixel:confirm:[A-Za-z0-9_-]{8,32}$"),
                CallbackQueryHandler(pixel_confirm_batch, pattern=r"^pixel:batch-confirm:[A-Za-z0-9_-]{8,32}$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(pixel_cancel, pattern=r"^pixel:(cancel|menu)$")],
        allow_reentry=True,
        per_message=False,
        name="pixel_activation_conv",
    )
