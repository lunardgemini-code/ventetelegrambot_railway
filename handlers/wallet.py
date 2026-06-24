"""
Wallet handler — View balance, top up via Binance Pay, view transaction history.
Uses ConversationHandler with states WALLET_MENU, WALLET_TOPUP_AMOUNT, WALLET_TOPUP_VERIFY.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BINANCE_PAY_ID
from database.models import (
    get_user_lang,
    get_wallet_balance,
    get_wallet_transactions,
    topup_wallet,
)
from services.binance_verify import verify_payment
from utils.helpers import format_price
from utils.keyboards import back_keyboard, main_menu_keyboard, wallet_topup_method_keyboard
from utils.locales import t

logger = logging.getLogger(__name__)

WALLET_MENU = 299
WALLET_TOPUP_AMOUNT = 300
WALLET_TOPUP_METHOD = 301
WALLET_TOPUP_VERIFY = 302
WALLET_TOPUP_BEP20_TX = 303
WALLET_TOPUP_TRC20_TX = 304


def wallet_menu_keyboard(balance: float, lang: str = "fr") -> InlineKeyboardMarkup:
    """Wallet menu with balance, top-up, and history buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{t('wallet_balance_lbl', lang)} {format_price(balance)}", callback_data="wallet_noop")],
        [
            InlineKeyboardButton(t("wallet_topup", lang), callback_data="wallet_topup"),
            InlineKeyboardButton(t("wallet_history", lang), callback_data="wallet_history"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")],
    ])


def wallet_topup_amounts_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Back button only — user types custom amount as free text."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back_wallet")],
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
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=wallet_menu_keyboard(balance, lang))
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

    await query.edit_message_text(
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
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

    return WALLET_TOPUP_VERIFY


async def wallet_topup_method_binance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    amount = context.user_data.get("wallet_topup_amount", 0)
    return await _start_binance_topup(update, context, amount, lang, is_callback=True)


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

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
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
            if not tx_hash.startswith("0x") or len(tx_hash) != 66:
                await update.message.reply_text(t("bep20_invalid_tx_hash", lang))
                return WALLET_TOPUP_BEP20_TX
            
            if await is_bep20_transaction_used(tx_hash):
                await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                return ConversationHandler.END
            
            bep20_address = await get_setting("bep20_address")
            from services.blockchain_verify import verify_bep20_payment
            result = await verify_bep20_payment(tx_hash, amount, bep20_address)
            
            if result.get("verified"):
                if not await record_used_bep20_transaction(tx_hash, None, telegram_id, amount):
                    await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                    return ConversationHandler.END
            else:
                error_msg = result.get("error", "Payment not verified")
                await update.message.reply_text(f"❌ {error_msg}\n\n👉 {t('bep20_send_tx_hash', lang)}")
                return WALLET_TOPUP_BEP20_TX

        elif crypto_type == "TRC20":
            tx_hash_clean = tx_hash
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
            result = await verify_trc20_payment(tx_hash_clean, amount, trc20_address)
            
            if result.get("verified"):
                if not await record_used_trc20_transaction(tx_hash_clean, None, telegram_id, amount):
                    await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                    return ConversationHandler.END
            else:
                error_msg = result.get("error", "Payment not verified")
                await update.message.reply_text(f"❌ {error_msg}\n\n👉 {t('trc20_send_tx_hash', lang)}")
                return WALLET_TOPUP_TRC20_TX

        # If verified, credit wallet
        new_balance = await topup_wallet(telegram_id, amount, f"Topup via {crypto_type}")
        
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

        result = await verify_payment(client_order_id, amount, api_key=api_key_to_use, api_secret=api_secret_to_use)

        if result.get("verified"):
            # Anti-replay: check if this transaction was already used
            tx = result.get("transaction", {})
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
            new_balance = await topup_wallet(telegram_id, amount, f"Binance Pay: {desc_id}")

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
        await query.edit_message_text(
            t("wallet_no_transactions", lang),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_back", lang), callback_data="back_wallet")],
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

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_back", lang), callback_data="back_wallet")],
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
        },
        fallbacks=[
            CallbackQueryHandler(wallet_back, pattern=r"^back_wallet$"),
            CallbackQueryHandler(wallet_back_main, pattern=r"^back_main$"),
        ],
        per_message=False,
        allow_reentry=True,
        name="wallet_conv",
    )
