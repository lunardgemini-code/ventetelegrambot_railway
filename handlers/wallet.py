"""
Wallet handler — View balance, top up via Binance Pay, view transaction history.
Uses ConversationHandler with states WALLET_MENU, WALLET_TOPUP_AMOUNT, WALLET_TOPUP_VERIFY.
"""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BINANCE_PAY_ID, PAYMENT_TIMEOUT_SECONDS
from database.models import (
    get_user_lang,
    get_wallet_balance,
    get_wallet_transactions,
    topup_wallet,
)
from services.binance_verify import verify_payment
from utils.helpers import escape_html, format_price
from utils.keyboards import (
    back_keyboard,
    main_menu_keyboard,
    make_button,
    nowpayments_wallet_topup_keyboard,
    wallet_topup_method_keyboard,
)
from utils.locales import t
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)

WALLET_MENU = 299
WALLET_TOPUP_AMOUNT = 300
WALLET_TOPUP_METHOD = 301
WALLET_TOPUP_VERIFY = 302
WALLET_TOPUP_BEP20_TX = 303
WALLET_TOPUP_TRC20_TX = 304
WALLET_TOPUP_NOWPAYMENTS = 305

_nowpayments_topup_locks = [asyncio.Lock() for _ in range(64)]
_nowpayments_topup_timeout_tasks: dict[int, asyncio.Task] = {}


def wallet_menu_keyboard(balance: float, lang: str = "fr") -> InlineKeyboardMarkup:
    """Wallet menu with balance, top-up, and history buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{t('wallet_balance_lbl', lang)} {format_price(balance)}", callback_data="wallet_noop")],
        [
            make_button("wallet_topup", lang, callback_data="wallet_topup"),
            make_button("wallet_history", lang, callback_data="wallet_history"),
        ],
        [make_button("btn_back", lang, callback_data="back_main")],
    ])


def wallet_topup_amounts_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Back button only — user types custom amount as free text."""
    return InlineKeyboardMarkup([
        [make_button("btn_back", lang, callback_data="back_wallet")],
    ])


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show wallet balance and options."""
    query = update.callback_query
    if query:
        await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    balance = await get_wallet_balance(update.effective_user.id)

    text = (
        f"{t('wallet_title', lang)}\n\n"
        f"{t('wallet_balance_lbl', lang)} <b>{format_price(balance)}</b>"
    )

    if query:
        try:
            await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=wallet_menu_keyboard(balance, lang))
        except Exception:
            pass  # Message already shows this content
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=wallet_menu_keyboard(balance, lang))


async def wallet_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance button click (no-op)."""
    await update.callback_query.answer()


async def wallet_topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top-up amount selection."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    await safe_edit_message_text(query, 
        t("wallet_topup_title", lang),
        parse_mode="HTML",
        reply_markup=wallet_topup_amounts_keyboard(lang),
    )
    return WALLET_TOPUP_AMOUNT


async def wallet_topup_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom text amount input."""
    lang = await get_user_lang(update.effective_user.id)
    text = update.message.text.strip()

    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            raise ValueError()
        if amount > 10000:
            await update.message.reply_text(t("max_topup", lang))
            return WALLET_TOPUP_AMOUNT
    except ValueError:
        await update.message.reply_text(t("wallet_invalid_amount", lang))
        return WALLET_TOPUP_AMOUNT

    context.user_data["wallet_topup_amount"] = amount

    try:
        kb = await wallet_topup_method_keyboard(lang)
        await update.message.reply_text(
            f"💰 {t('amount_lbl', lang)} {format_price(amount)}\n\n"
            f"Veuillez choisir votre méthode de paiement pour recharger :",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return WALLET_TOPUP_METHOD
    except Exception as exc:
        logger.error("Error in wallet_topup_text: %s", exc, exc_info=True)
        await update.message.reply_text(t("pay_error", lang))
        return ConversationHandler.END


async def _start_binance_topup(update, context, amount, lang, is_callback=True):
    """Create Binance Pay instructions for wallet top-up."""
    telegram_id = update.effective_user.id
    context.user_data["wallet_topup_amount"] = amount

    uid_to_show = BINANCE_PAY_ID
    from database.models import get_default_binance_account
    def_acc = await get_default_binance_account()
    if def_acc and def_acc.get("uid"):
        uid_to_show = def_acc["uid"]

    text = (
        f"\U0001f4b0 <b>{t('wallet_topup', lang)}: {format_price(amount)}</b>\n\n"
        f"\U0001f4f2 Binance Pay ID:\n"
        f"<code>{uid_to_show}</code>\n\n"
        f"💵 {t('amount_lbl', lang)} {format_price(amount)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('pay_instructions', lang)}\n"
        f"{t('pay_step1', lang)}\n"
        f"{t('pay_step2', lang)}\n\n"
        f"{t('waiting_payment', lang)}"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="back_wallet")],
    ])

    if is_callback:
        await safe_edit_message_text(update.callback_query, text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

    return WALLET_TOPUP_VERIFY


async def wallet_topup_method_binance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    amount = context.user_data.get("wallet_topup_amount", 0)
    return await _start_binance_topup(update, context, amount, lang, is_callback=True)


def _format_topup_crypto_amount(value) -> str:
    rendered = f"{float(value or 0):.8f}".rstrip("0").rstrip(".")
    return rendered or "0"


async def _render_nowpayments_topup_checkout(
    query,
    topup: dict,
    lang: str,
    status_text: str | None = None,
) -> None:
    from services.nowpayments import calculate_customer_pay_amount

    payment_id = str(topup.get("payment_id") or "")
    address = str(topup.get("pay_address") or "")
    wallet_amount = float(topup.get("wallet_amount") or 0)
    customer_pay_amount = calculate_customer_pay_amount(
        topup.get("pay_amount"),
        provider_price_amount=topup.get("price_amount"),
        original_price_amount=wallet_amount,
    )
    pay_amount = _format_topup_crypto_amount(customer_pay_amount)
    text = (
        f"{t('nowpayments_title', lang)}\n\n"
        f"{t('nowpayments_address', lang)}\n"
        f"<code>{escape_html(address)}</code>\n\n"
        f"{t('nowpayments_amount', lang).format(amount=pay_amount)}\n"
        f"{t('nowpayments_network', lang)}\n"
        f"{t('nowpayments_reference', lang).format(payment_id=escape_html(payment_id))}\n\n"
        f"{t('nowpayments_instructions', lang)}\n\n"
        f"{t('nowpayments_fee_warning', lang)}\n\n"
        f"{status_text or t('nowpayments_waiting', lang)}"
    )
    await safe_edit_message_text(query, 
        text,
        parse_mode="HTML",
        reply_markup=nowpayments_wallet_topup_keyboard(int(topup["id"]), pay_amount, lang),
    )


async def process_nowpayments_wallet_topup_notification(
    bot,
    payment_id: str | int,
    *,
    finalized_result: dict | None = None,
    force_notification: bool = False,
) -> dict:
    """Finalize and notify a NOWPayments wallet credit exactly once."""
    from database.models import (
        claim_nowpayments_wallet_topup_notification,
        finalize_nowpayments_wallet_topup,
        mark_nowpayments_wallet_topup_notified,
        release_nowpayments_wallet_topup_notification,
    )

    result = finalized_result or await finalize_nowpayments_wallet_topup(payment_id)
    action = result.get("action")
    payment = result.get("payment") or {}
    try:
        from services.reseller_webhooks import (
            enqueue_reseller_deposit_webhook_for_payment,
        )

        await enqueue_reseller_deposit_webhook_for_payment(payment_id)
    except Exception as exc:
        logger.warning(
            "Could not enqueue reseller deposit webhook for %s: %s",
            payment_id,
            exc,
        )
    if not payment or (payment.get("notified_at") and not force_notification):
        return result
    notifiable = {
        "wallet_credited",
        "review_required",
        "partially_paid",
        "expired",
        "failed",
        "refunded",
    }
    if action not in notifiable:
        return result
    if not await claim_nowpayments_wallet_topup_notification(payment_id):
        return result

    user_id = int(payment.get("user_telegram_id") or 0)
    lang = await get_user_lang(user_id) if user_id else "en"
    notified = False
    try:
        if action == "wallet_credited" and user_id:
            wallet_amount = float(payment.get("wallet_amount") or 0)
            new_balance = float(payment.get("new_balance") or await get_wallet_balance(user_id))
            text = t("wallet_credited", lang) \
                .replace("${amount}", format_price(wallet_amount)) \
                .replace("${balance}", format_price(new_balance))
            try:
                await bot.send_message(
                    user_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=wallet_menu_keyboard(new_balance, lang),
                )
            except Exception as exc:
                logger.warning("Could not notify wallet top-up user %s: %s", user_id, exc)
            try:
                from bot import notify_admins
                await notify_admins(
                    "<b>NOWPayments wallet top-up confirmed</b>\n\n"
                    f"Client: <code>{user_id}</code>\n"
                    f"Wallet credit: {format_price(wallet_amount)}\n"
                    f"Payment: <code>{escape_html(str(payment_id))}</code>"
                )
            except Exception as exc:
                logger.warning("Could not notify admins about wallet top-up %s: %s", payment_id, exc)
            notified = True
        elif action == "review_required":
            if user_id:
                try:
                    await bot.send_message(user_id, t("nowpayments_review", lang), reply_markup=main_menu_keyboard(lang))
                except Exception:
                    pass
            try:
                from bot import notify_admins
                await notify_admins(
                    "<b>NOWPayments wallet top-up review</b>\n\n"
                    f"Client: <code>{user_id}</code>\n"
                    f"Payment: <code>{escape_html(str(payment_id))}</code>\n"
                    f"Reason: {escape_html(str(payment.get('processing_error') or 'Validation mismatch'))}"
                )
            except Exception:
                pass
            notified = True
        elif action == "partially_paid" and user_id:
            try:
                await bot.send_message(user_id, t("nowpayments_partial", lang))
            except Exception:
                pass
            notified = True
        elif action in ("expired", "failed", "refunded") and user_id:
            try:
                await bot.send_message(
                    user_id,
                    t("nowpayments_expired", lang),
                    reply_markup=main_menu_keyboard(lang),
                )
            except Exception:
                pass
            notified = True

        if notified:
            await mark_nowpayments_wallet_topup_notified(payment_id)
        else:
            await release_nowpayments_wallet_topup_notification(payment_id)
        return result
    except Exception:
        await release_nowpayments_wallet_topup_notification(payment_id)
        raise


async def expire_nowpayments_wallet_topup_after_timeout(
    bot,
    topup_id: int,
    timeout_seconds: int = PAYMENT_TIMEOUT_SECONDS,
    delay_seconds: float | None = None,
) -> None:
    await asyncio.sleep(timeout_seconds if delay_seconds is None else max(0, delay_seconds))
    try:
        from database.models import expire_stale_nowpayments_wallet_topups
        payment_ids = await expire_stale_nowpayments_wallet_topups(
            timeout_seconds=timeout_seconds,
            topup_id=topup_id,
        )
        for payment_id in payment_ids:
            await process_nowpayments_wallet_topup_notification(bot, payment_id)
    except Exception as exc:
        logger.error("Error expiring NOWPayments wallet top-up #%s: %s", topup_id, exc, exc_info=True)
    finally:
        current = asyncio.current_task()
        if _nowpayments_topup_timeout_tasks.get(topup_id) is current:
            _nowpayments_topup_timeout_tasks.pop(topup_id, None)


async def restore_nowpayments_wallet_topup_timeout_tasks(bot) -> int:
    from database.models import list_active_nowpayments_wallet_topup_timeouts

    restored = 0
    for topup in await list_active_nowpayments_wallet_topup_timeouts(
        timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
    ):
        topup_id = int(topup["topup_id"])
        previous = _nowpayments_topup_timeout_tasks.pop(topup_id, None)
        if previous and not previous.done():
            previous.cancel()
        _nowpayments_topup_timeout_tasks[topup_id] = asyncio.create_task(
            expire_nowpayments_wallet_topup_after_timeout(
                bot,
                topup_id,
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
                delay_seconds=float(topup.get("remaining_seconds") or 0),
            )
        )
        restored += 1
    return restored


async def wallet_topup_method_nowpayments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    user_id = update.effective_user.id
    amount = round(float(context.user_data.get("wallet_topup_amount") or 0), 2)
    if amount <= 0:
        await safe_edit_message_text(query, t("wallet_invalid_amount", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END

    lock = _nowpayments_topup_locks[user_id % len(_nowpayments_topup_locks)]
    async with lock:
        from handlers.payment import _nowpayments_callback_url
        from database.models import (
            attach_nowpayments_wallet_topup,
            mark_nowpayments_wallet_topup_creation_failed,
            prepare_nowpayments_wallet_topup,
        )
        from services.nowpayments import (
            NowPaymentsError,
            create_payment,
            get_minimum_amount,
            is_nowpayments_configured,
        )

        callback_url = _nowpayments_callback_url()
        if not is_nowpayments_configured() or not callback_url.startswith("https://"):
            logger.error("NOWPayments wallet top-up callback URL is missing or not HTTPS")
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END

        provider_price = amount
        try:
            minimum = await get_minimum_amount()
            minimum_usd = float(minimum.get("fiat_equivalent") or minimum.get("min_amount") or 0)
            if minimum_usd > 0 and provider_price + 0.000001 < minimum_usd:
                await safe_edit_message_text(query, 
                    t("nowpayments_below_minimum", lang).format(minimum=_format_topup_crypto_amount(minimum_usd)),
                    reply_markup=main_menu_keyboard(lang),
                )
                return ConversationHandler.END
        except NowPaymentsError as exc:
            logger.warning("Could not read NOWPayments top-up minimum amount: %s", exc)
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid NOWPayments top-up minimum response: %s", exc)

        try:
            attempt = await prepare_nowpayments_wallet_topup(user_id, amount, provider_price)
        except Exception as exc:
            logger.error("Could not prepare NOWPayments wallet top-up for user %s: %s", user_id, exc, exc_info=True)
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END
        if not attempt.get("created"):
            if attempt.get("payment_id"):
                await _render_nowpayments_topup_checkout(query, attempt, lang)
                return WALLET_TOPUP_NOWPAYMENTS
            await safe_edit_message_text(query, 
                t("nowpayments_creation_unknown", lang).format(order_id=f"W{attempt['id']}"),
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        try:
            provider_payment = await create_payment(
                price_amount=provider_price,
                order_id=attempt["request_key"],
                order_description=f"Wallet top-up {amount:.2f} USD",
                callback_url=callback_url,
            )
            topup = await attach_nowpayments_wallet_topup(attempt["request_key"], provider_payment)
        except Exception as exc:
            try:
                await mark_nowpayments_wallet_topup_creation_failed(
                    attempt["request_key"],
                    uncertain=bool(isinstance(exc, NowPaymentsError) and exc.retryable),
                    error=str(exc),
                )
            except Exception as mark_exc:
                logger.error("Could not record failed NOWPayments top-up creation: %s", mark_exc)
            logger.warning("NOWPayments wallet top-up creation failed for user %s: %s", user_id, exc)
            text = (
                t("nowpayments_creation_unknown", lang).format(order_id=f"W{attempt['id']}")
                if isinstance(exc, NowPaymentsError) and exc.retryable
                else t("nowpayments_unavailable", lang)
            )
            await safe_edit_message_text(query, text, reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END

        context.user_data["wallet_topup_id"] = int(topup["id"])
        await _render_nowpayments_topup_checkout(query, topup, lang)
        previous = _nowpayments_topup_timeout_tasks.pop(int(topup["id"]), None)
        if previous and not previous.done():
            previous.cancel()
        _nowpayments_topup_timeout_tasks[int(topup["id"])] = asyncio.create_task(
            expire_nowpayments_wallet_topup_after_timeout(
                context.bot,
                int(topup["id"]),
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
        )
        return WALLET_TOPUP_NOWPAYMENTS


async def check_nowpayments_wallet_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await get_user_lang(update.effective_user.id)
    await query.answer(t("nowpayments_checking_short", lang))
    topup_id = int(query.data.split(":", 1)[1])
    from database.models import (
        get_nowpayments_wallet_topup,
        save_nowpayments_update,
    )
    from services.nowpayments import NowPaymentsError, get_payment_status

    topup = await get_nowpayments_wallet_topup(topup_id)
    if not topup or int(topup.get("user_telegram_id") or 0) != update.effective_user.id:
        await safe_edit_message_text(query, t("access_denied", lang))
        return ConversationHandler.END
    if not topup.get("payment_id"):
        await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END

    await _render_nowpayments_topup_checkout(query, topup, lang, t("nowpayments_checking", lang))
    try:
        provider_payment = await get_payment_status(topup["payment_id"])
        topup = await save_nowpayments_update(provider_payment) or topup
        result = await process_nowpayments_wallet_topup_notification(context.bot, topup["payment_id"])
    except (NowPaymentsError, TypeError, ValueError):
        await _render_nowpayments_topup_checkout(query, topup, lang, t("nowpayments_unavailable", lang))
        return WALLET_TOPUP_NOWPAYMENTS

    action = result.get("action")
    if action == "wallet_credited":
        payment = result.get("payment") or topup
        balance = float(payment.get("new_balance") or await get_wallet_balance(update.effective_user.id))
        text = t("wallet_credited", lang) \
            .replace("${amount}", format_price(float(payment.get("wallet_amount") or 0))) \
            .replace("${balance}", format_price(balance))
        await safe_edit_message_text(query, 
            text,
            parse_mode="HTML",
            reply_markup=wallet_menu_keyboard(balance, lang),
        )
        context.user_data.pop("wallet_topup_amount", None)
        context.user_data.pop("wallet_topup_id", None)
        task = _nowpayments_topup_timeout_tasks.pop(topup_id, None)
        if task and not task.done():
            task.cancel()
        return ConversationHandler.END
    if action == "review_required":
        await safe_edit_message_text(query, t("nowpayments_review", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END
    if action == "partially_paid":
        status_text = t("nowpayments_partial", lang)
    elif action in ("confirming", "confirmed", "sending", "spending"):
        status_text = t("nowpayments_confirming", lang)
    elif action in ("expired", "failed", "refunded"):
        await safe_edit_message_text(query, t("nowpayments_expired", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END
    else:
        status_text = t("nowpayments_waiting", lang)
    await _render_nowpayments_topup_checkout(query, topup, lang, status_text)
    return WALLET_TOPUP_NOWPAYMENTS


async def cancel_nowpayments_wallet_topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    topup_id = int(query.data.split(":", 1)[1])
    from database.models import cancel_nowpayments_wallet_topup, get_nowpayments_wallet_topup

    topup = await get_nowpayments_wallet_topup(topup_id)
    if not topup or int(topup.get("user_telegram_id") or 0) != update.effective_user.id:
        await safe_edit_message_text(query, t("access_denied", lang))
        return ConversationHandler.END
    cancelled = await cancel_nowpayments_wallet_topup(topup_id, update.effective_user.id)
    if not cancelled and (
        topup.get("processed_at") is not None
        or str(topup.get("provider_status") or "").lower() == "finished"
    ):
        result = await process_nowpayments_wallet_topup_notification(
            context.bot,
            topup.get("payment_id"),
        )
        if result.get("action") == "wallet_credited":
            payment = result.get("payment") or topup
            balance = float(payment.get("new_balance") or await get_wallet_balance(update.effective_user.id))
            text = t("wallet_credited", lang) \
                .replace("${amount}", format_price(float(payment.get("wallet_amount") or 0))) \
                .replace("${balance}", format_price(balance))
            await safe_edit_message_text(query, 
                text,
                parse_mode="HTML",
                reply_markup=wallet_menu_keyboard(balance, lang),
            )
            return ConversationHandler.END
    task = _nowpayments_topup_timeout_tasks.pop(topup_id, None)
    if task and not task.done():
        task.cancel()
    context.user_data.pop("wallet_topup_amount", None)
    context.user_data.pop("wallet_topup_id", None)
    balance = await get_wallet_balance(update.effective_user.id)
    await safe_edit_message_text(query, 
        t("nowpayments_expired", lang),
        reply_markup=wallet_menu_keyboard(balance, lang),
    )
    return ConversationHandler.END


async def _start_crypto_topup(update, context, crypto_type: str, setting_key: str, state_to_return: int):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    amount = context.user_data.get("wallet_topup_amount", 0)
    from database.models import get_setting
    addr = await get_setting(setting_key)

    instructions = t("bep20_instructions", lang) if "BEP20" in crypto_type else t("trc20_instructions", lang)
    address_lbl = t("bep20_address_lbl", lang) if "BEP20" in crypto_type else t("trc20_address_lbl", lang)
    send_lbl = t("bep20_send_tx_hash", lang) if "BEP20" in crypto_type else t("trc20_send_tx_hash", lang)

    text = (
        f"💳 <b>{t('btn_wallet', lang)} — {crypto_type}</b>\n\n"
        f"💰 <b>{format_price(amount)}</b>\n\n"
        f"{address_lbl}\n"
        f"<code>{addr}</code>\n\n"
        f"{instructions}\n\n"
        f"👉 <b>{send_lbl}</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="back_wallet")],
    ])

    await safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)
    return state_to_return


async def wallet_topup_method_bep20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _start_crypto_topup(update, context, "BEP20 (USDT)", "bep20_address", WALLET_TOPUP_BEP20_TX)


async def wallet_topup_method_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _start_crypto_topup(update, context, "TRC20 (USDT)", "trc20_address", WALLET_TOPUP_TRC20_TX)


async def _verify_crypto_topup(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_type: str):
    tx_hash = update.message.text.strip()
    lang = await get_user_lang(update.effective_user.id)
    amount = context.user_data.get("wallet_topup_amount", 0)
    telegram_id = update.effective_user.id
    
    if not amount:
        await update.message.reply_text(t("order_error", lang))
        return ConversationHandler.END

    await update.message.reply_text(t("verifying", lang))
    
    from database.models import get_setting, record_used_bep20_transaction, record_used_trc20_transaction, is_bep20_transaction_used, is_trc20_transaction_used, topup_wallet
    
    try:
        if crypto_type == "BEP20":
            is_on_chain = tx_hash.startswith("0x") and len(tx_hash) == 66
            is_off_chain = tx_hash.isdigit() or "off-chain" in tx_hash.lower() or (not tx_hash.startswith("0x") and len(tx_hash) > 5)

            if not is_on_chain and not is_off_chain:
                await update.message.reply_text(t("bep20_invalid_tx_hash", lang))
                return WALLET_TOPUP_BEP20_TX
            
            if await is_bep20_transaction_used(tx_hash):
                await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                return ConversationHandler.END
            
            bep20_address = await get_setting("bep20_address")
            from services.blockchain_verify import verify_bep20_payment
            from services.binance_verify import verify_internal_transfer

            result = {"verified": False, "error": "Type de transaction non pris en charge."}

            if is_on_chain:
                result = await verify_bep20_payment(tx_hash, amount, bep20_address)
            else:
                from database.models import get_default_binance_account
                acc = await get_default_binance_account()
                api_key = acc.get("api_key") if acc else None
                api_secret = acc.get("api_secret") if acc else None
                result = await verify_internal_transfer(tx_hash, amount, api_key=api_key, api_secret=api_secret, lang=lang)
            
            if result.get("verified"):
                amount = float(result.get("transaction", {}).get("amount", amount))
                if not await record_used_bep20_transaction(tx_hash, None, telegram_id, amount):
                    await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                    return ConversationHandler.END
            else:
                error_msg = result.get("error", "Payment not verified")
                await update.message.reply_text(f"❌ {error_msg}\n\n👉 {t('bep20_send_tx_hash', lang)}")
                return WALLET_TOPUP_BEP20_TX

        elif crypto_type == "TRC20":
            is_off_chain = tx_hash.isdigit() or "off-chain" in tx_hash.lower() or len(tx_hash) < 64
            is_on_chain = not is_off_chain
            
            tx_hash_clean = tx_hash
            if is_on_chain:
                if tx_hash_clean.lower().startswith("0x"):
                    tx_hash_clean = tx_hash_clean[2:]
                
                import re
                if not re.match(r"^[a-fA-F0-9]{64}$", tx_hash_clean):
                    await update.message.reply_text(t("trc20_invalid_tx_hash", lang))
                    return WALLET_TOPUP_TRC20_TX
            
            if await is_trc20_transaction_used(tx_hash_clean):
                await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                return ConversationHandler.END
            
            trc20_address = await get_setting("trc20_address")
            from services.trc20_verify import verify_trc20_payment
            from services.binance_verify import verify_internal_transfer

            result = {"verified": False, "error": "Type de transaction non pris en charge."}
            if is_on_chain:
                result = await verify_trc20_payment(tx_hash_clean, amount, trc20_address)
            else:
                from database.models import get_default_binance_account
                acc = await get_default_binance_account()
                api_key = acc.get("api_key") if acc else None
                api_secret = acc.get("api_secret") if acc else None
                result = await verify_internal_transfer(tx_hash_clean, amount, api_key=api_key, api_secret=api_secret, lang=lang)
            
            if result.get("verified"):
                amount = float(result.get("transaction", {}).get("amount", amount))
                if not await record_used_trc20_transaction(tx_hash_clean, None, telegram_id, amount):
                    await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                    return ConversationHandler.END
            else:
                error_msg = result.get("error", "Payment not verified")
                await update.message.reply_text(f"❌ {error_msg}\n\n👉 {t('trc20_send_tx_hash', lang)}")
                return WALLET_TOPUP_TRC20_TX

        # If verified, credit wallet
        final_hash = tx_hash_clean if crypto_type == "TRC20" else tx_hash
        new_balance = await topup_wallet(telegram_id, amount, f"Topup via {crypto_type}", tx_hash=final_hash)
        
        await update.message.reply_text(
            f"✅ <b>Rechargement réussi !</b>\n\n"
            f"💵 Montant ajouté : {format_price(amount)}\n"
            f"💰 Nouveau solde : {format_price(new_balance)}\n\n"
            f"Merci pour votre confiance !",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang)
        )
        
        from bot import notify_admins
        user = update.effective_user
        user_name = f"@{user.username}" if user.username else "Aucun"
        msg = (
            f"💰 <b>Wallet Rechargé ({crypto_type})</b>\n\n"
            f"👤 Utilisateur : {user.first_name} ({user_name})\n"
            f"💵 Montant : {format_price(amount)}\n"
            f"🔗 Tx Hash :\n<code>{tx_hash}</code>"
        )
        try:
            await notify_admins(msg)
        except Exception:
            pass

        context.user_data.pop("wallet_topup_amount", None)
        return ConversationHandler.END

    except Exception as exc:
        logger.error("_verify_crypto_topup: %s", exc, exc_info=True)
        await update.message.reply_text(t("verify_error", lang))
        return WALLET_TOPUP_BEP20_TX if crypto_type == "BEP20" else WALLET_TOPUP_TRC20_TX


async def wallet_verify_bep20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _verify_crypto_topup(update, context, "BEP20")


async def wallet_verify_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _verify_crypto_topup(update, context, "TRC20")


async def wallet_verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify Binance payment for wallet top-up."""
    client_order_id = update.message.text.strip()
    lang = await get_user_lang(update.effective_user.id)
    amount = context.user_data.get("wallet_topup_amount", 0)

    if not amount:
        await update.message.reply_text(t("order_error", lang))
        return ConversationHandler.END

    try:
        await update.message.reply_text(t("verifying", lang))

        api_key_to_use = None
        api_secret_to_use = None
        from database.models import get_default_binance_account
        def_acc = await get_default_binance_account()
        if def_acc:
            api_key_to_use = def_acc.get("api_key")
            api_secret_to_use = def_acc.get("api_secret")

        result = await verify_payment(client_order_id, amount, api_key=api_key_to_use, api_secret=api_secret_to_use, lang=lang)

        if result.get("verified"):
            # Anti-replay: check if this transaction was already used
            tx = result.get("transaction", {})
            amount = float(tx.get("amount", amount))
            tx_id = str(tx.get("transactionId", "")) or str(tx.get("orderId", "")) or client_order_id
            from database.models import record_used_transaction
            telegram_id = update.effective_user.id
            if not await record_used_transaction(tx_id, order_id=None, user_telegram_id=telegram_id, amount=amount):
                logger.warning("WALLET REPLAY BLOCKED: User %s tried to reuse transaction %s",
                             telegram_id, tx_id)
                await update.message.reply_text(
                    t("tx_used", lang),
                    reply_markup=main_menu_keyboard(lang),
                )
                context.user_data.pop("wallet_topup_amount", None)
                return ConversationHandler.END

            binance_order_id_val = tx.get("orderId", "")
            desc_id = binance_order_id_val or tx_id or client_order_id
            new_balance = await topup_wallet(telegram_id, amount, f"Binance Pay: {desc_id}", tx_hash=tx_id)

            text = t("wallet_credited", lang) \
                .replace("${amount}", format_price(amount)) \
                .replace("${balance}", format_price(new_balance))

            balance = await get_wallet_balance(telegram_id)
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=wallet_menu_keyboard(balance, lang),
            )
            context.user_data.pop("wallet_topup_amount", None)
            return ConversationHandler.END
        else:
            reason = result.get("error", "Unknown")
            await update.message.reply_text(
                f"{t('payment_not_found', lang)}\n\n💡 {reason}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("btn_cancel", lang), callback_data="back_wallet")],
                ]),
            )
            return WALLET_TOPUP_VERIFY

    except Exception as exc:
        logger.error("wallet_verify_payment: %s", exc, exc_info=True)
        await update.message.reply_text(t("pay_error", lang))
        return ConversationHandler.END


async def wallet_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to wallet menu from any sub-state."""
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.pop("wallet_topup_amount", None)
    await wallet_menu(update, context)
    return ConversationHandler.END


async def wallet_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exit wallet and go back to main menu."""
    context.user_data.pop("wallet_topup_amount", None)
    from handlers.start import main_menu_callback
    await main_menu_callback(update, context)
    return ConversationHandler.END


async def wallet_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent wallet transactions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    txs = await get_wallet_transactions(update.effective_user.id, limit=10)

    if not txs:
        await safe_edit_message_text(query, 
            t("wallet_no_transactions", lang),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [make_button("btn_back", lang, callback_data="back_wallet")],
            ]),
        )
        return

    lines = [f"{t('wallet_title', lang)}\n📜 {t('wallet_history', lang)}\n"]
    for tx in txs:
        icon = "➕" if tx["type"] == "topup" else "🛒"
        sign = "+" if tx["type"] == "topup" else "-"
        label = t("wallet_tx_topup", lang) if tx["type"] == "topup" else t("wallet_tx_purchase", lang)
        date_str = tx.get("created_at", "")[:16].replace("T", " ")
        lines.append(f"{icon} {sign}{format_price(tx['amount'])} — {label}\n   💰 {format_price(tx['balance_after'])} | {date_str}")

    await safe_edit_message_text(query, 
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [make_button("btn_back", lang, callback_data="back_wallet")],
        ]),
    )


def wallet_conversation_handler() -> ConversationHandler:
    """Build and return the wallet ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(wallet_topup_start, pattern=r"^wallet_topup$"),
        ],
        states={
            WALLET_TOPUP_AMOUNT: [
                CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_topup_text),
            ],
            WALLET_TOPUP_METHOD: [
                CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
                CallbackQueryHandler(wallet_topup_method_binance, pattern=r"^topup_binance$"),
                CallbackQueryHandler(wallet_topup_method_nowpayments, pattern=r"^topup_nowpayments$"),
                CallbackQueryHandler(wallet_topup_method_bep20, pattern=r"^topup_bep20$"),
                CallbackQueryHandler(wallet_topup_method_trc20, pattern=r"^topup_trc20$"),
            ],
            WALLET_TOPUP_VERIFY: [
                CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_verify_payment),
            ],
            WALLET_TOPUP_BEP20_TX: [
                CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_verify_bep20),
            ],
            WALLET_TOPUP_TRC20_TX: [
                CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_verify_trc20),
            ],
            WALLET_TOPUP_NOWPAYMENTS: [
                CallbackQueryHandler(check_nowpayments_wallet_topup, pattern=r"^check_topup_nowpayments:"),
                CallbackQueryHandler(cancel_nowpayments_wallet_topup_callback, pattern=r"^cancel_topup_nowpayments:"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
            CallbackQueryHandler(wallet_back_main, pattern=r"^back_main$"),
        ],
        per_message=False,
        allow_reentry=True,
        name="wallet_conv",
    )
