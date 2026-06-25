"""
Payment flow handlers â€” purchase â†’ Binance Pay instructions â†’ Order ID â†’ verify â†’ deliver.
Uses ConversationHandler with state WAITING_ORDER_ID = 200.
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS, BINANCE_PAY_ID
from database.models import (
    create_order,
    get_order,
    get_product,
    get_stock_count,
    get_user_lang,
    update_order_status,
    record_used_transaction,
)
from services.binance_verify import verify_payment
from services.delivery import check_low_stock, deliver_order
from utils.helpers import escape_html, format_price
from utils.keyboards import (
    back_keyboard,
    main_menu_keyboard,
    payment_check_keyboard,
    payment_method_keyboard,
    quantity_keyboard,
)
from utils.locales import t

logger = logging.getLogger(__name__)

WAITING_ORDER_ID = 200
WAITING_QUANTITY = 201
WAITING_PAYMENT_METHOD = 202
WAITING_PROMO_CODE = 203
WAITING_BEP20_TX_HASH = 204
WAITING_TRC20_TX_HASH = 205

_timeout_tasks = {}

async def send_delivery_messages(bot, chat_id: int, header: str, items: list, footer: str, lang: str, order_id: int = None):
    """Sends delivery messages. Uses a single .txt document if the total delivery is very long."""
    import io
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    total_length = sum(len(item['account_data']) for item in items)
    your_acc_text = t("your_account", lang)
    
    base_markup = main_menu_keyboard(lang)
    if order_id and total_length <= 1500 and len(items) <= 10:
        new_kb = [[InlineKeyboardButton("ðŸ“¥ Download as TXT", callback_data=f"dl_txt:{order_id}")]] + base_markup.inline_keyboard
        reply_markup = InlineKeyboardMarkup(new_kb)
    else:
        reply_markup = base_markup
    
    if total_length > 1500 or len(items) > 10:
        file_content = ""
        for i, item in enumerate(items):
            file_content += f"--- Product nÂ°{i+1} ---\n{item['account_data']}\n\n"
            
        file_bytes = io.BytesIO(file_content.encode('utf-8'))
        file_bytes.name = "accounts.txt"
        
        await bot.send_message(chat_id=chat_id, text=header, parse_mode="HTML")
        await bot.send_document(chat_id=chat_id, document=file_bytes, caption=f"ðŸ“ {your_acc_text}")
        await bot.send_message(chat_id=chat_id, text=footer, parse_mode="HTML", reply_markup=reply_markup)
        return

    current_msg = f"{header}\n\n"
    if "your_account" in header or "votre compte" in header.lower() or "your account" in header.lower() or your_acc_text.lower() in header.lower():
        pass
    else:
        current_msg += f"{your_acc_text}\n"
        
    for item in items:
        line = f"ðŸ”‘ <code>{escape_html(item['account_data'])}</code>\n"
        if len(current_msg) + len(line) > 3800:
            await bot.send_message(chat_id=chat_id, text=current_msg, parse_mode="HTML")
            current_msg = ""
        current_msg += line
        
    if current_msg.strip():
        if len(current_msg + "\n" + footer) > 3800:
            await bot.send_message(chat_id=chat_id, text=current_msg, parse_mode="HTML")
            await bot.send_message(chat_id=chat_id, text=footer, parse_mode="HTML", reply_markup=reply_markup)
        else:
            current_msg += "\n" + footer
            await bot.send_message(chat_id=chat_id, text=current_msg, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=chat_id, text=footer, parse_mode="HTML", reply_markup=reply_markup)

async def initiate_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'buy:{product_id}' callback â€” entry point for purchase conversation. Ask for quantity."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        product_id = int(query.data.split(":")[1])
        product = await get_product(product_id)

        if not product:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=t("product_not_found", lang),
                reply_markup=back_keyboard("back_cats", lang),
            )
            return ConversationHandler.END

        stock = await get_stock_count(product_id)
        if stock <= 0:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"{product['emoji']} <b>{product['name']}</b>\n\n" + t("out_of_stock", lang),
                parse_mode="HTML",
                reply_markup=back_keyboard(f"back_prods:{product['category_id']}", lang),
            )
            return ConversationHandler.END

        context.user_data["buying_product_id"] = product_id
        context.user_data["buying_unit_price"] = product["price_usd"]

        # Cancel any stale PENDING order from a previous purchase attempt
        old_order_id = context.user_data.get("pending_order_id")
        if old_order_id:
            try:
                old_order = await get_order(old_order_id)
                if old_order and old_order.get("status") == "PENDING":
                    await update_order_status(old_order_id, "CANCELLED")
                    logger.info("Auto-cancelled stale order #%d (new purchase started)", old_order_id)
            except Exception:
                pass
            context.user_data.pop("pending_order_id", None)
            context.user_data.pop("pending_product_id", None)

        text = t("choose_quantity", lang).format(stock=stock)
        markup = quantity_keyboard(product_id, stock, lang)
        
        try:
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
        return WAITING_QUANTITY
    except Exception as exc:
        logger.error("initiate_purchase: %s", exc, exc_info=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=t("order_error", lang),
            reply_markup=back_keyboard("back_main", lang),
        )
        return ConversationHandler.END



async def receive_quantity_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle raw text quantity inputs."""
    lang = await get_user_lang(update.effective_user.id)
    product_id = context.user_data.get("buying_product_id")

    if not product_id:
        await update.message.reply_text(t("no_pending_order", lang))
        return ConversationHandler.END

    try:
        text = update.message.text.strip()
        if not text.isdigit():
            await update.message.reply_text(t("invalid_quantity", lang))
            return WAITING_QUANTITY

        quantity = int(text)
        if quantity <= 0:
            await update.message.reply_text(t("invalid_quantity", lang))
            return WAITING_QUANTITY

        return await _process_quantity(update, context, product_id, quantity, lang, is_callback=False)
    except Exception as exc:
        logger.error("receive_quantity_text: %s", exc, exc_info=True)
        await update.message.reply_text(t("order_error", lang))
        return ConversationHandler.END


async def _process_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_id: int,
    quantity: int,
    lang: str,
    is_callback: bool = False,
) -> int:
    """Helper to validate stock, create order, and prompt for payment method."""
    product = await get_product(product_id)
    if not product:
        msg = t("product_not_found", lang)
        if is_callback:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    stock = await get_stock_count(product_id)
    if quantity > stock:
        msg = t("insufficient_stock", lang).format(stock=stock)
        if is_callback:
            await update.callback_query.edit_message_text(
                msg,
                reply_markup=quantity_keyboard(product_id, stock, lang),
            )
        else:
            await update.message.reply_text(msg)
        return WAITING_QUANTITY

    # Calculate total price using batch pricing tiers
    from database.models import get_effective_price
    unit_price = await get_effective_price(product_id, quantity)
    total_price = unit_price * quantity
    telegram_id = update.effective_user.id

    # â”€â”€ Prevent duplicate orders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Cancel any previous PENDING order for this user to avoid duplicates
    existing_order_id = context.user_data.get("pending_order_id")
    if existing_order_id:
        try:
            existing = await get_order(existing_order_id)
            if existing and existing.get("status") == "PENDING":
                await update_order_status(existing_order_id, "CANCELLED")
                logger.info("Auto-cancelled stale PENDING order #%d for user %d",
                            existing_order_id, telegram_id)
        except Exception:
            pass

    order = await create_order(telegram_id, product_id, total_price, quantity)

    context.user_data["pending_order_id"] = order["id"]
    context.user_data["pending_product_id"] = product_id

    # Get wallet balance for payment options
    from database.models import get_wallet_balance
    wallet_balance = await get_wallet_balance(telegram_id)

    return await show_payment_method_screen(update, context, order["id"], lang, is_callback=is_callback)


async def show_payment_method_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    order_id: int,
    lang: str,
    is_callback: bool = True
):
    """Helper to display the payment method selection screen for an order."""
    order = await get_order(order_id)
    if not order:
        msg = t("product_not_found", lang)
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.effective_message.reply_text(msg)
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    if order.get("user_telegram_id") != telegram_id:
        msg = t("access_denied", lang)
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.effective_message.reply_text(msg)
        return ConversationHandler.END

    product = await get_product(order["product_id"])
    if not product:
        msg = t("product_not_found", lang)
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.effective_message.reply_text(msg)
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    from database.models import get_wallet_balance
    wallet_balance = await get_wallet_balance(telegram_id)

    # Check if a promo code is already applied
    promo_code_id = order.get("promo_code_id")
    has_promo = bool(promo_code_id)

    # Base price and price tiers line
    from database.models import get_effective_price
    unit_price = await get_effective_price(order["product_id"], order["quantity"])
    base_price = product["price_usd"]
    unit_price_line = ""
    if abs(unit_price - base_price) > 0.001:
        discount_label = {"fr": "ðŸ’° Prix unitaire (palier)", "en": "ðŸ’° Unit price (bulk)", "ar": "ðŸ’° Ø³Ø¹Ø± Ø§Ù„ÙˆØ­Ø¯Ø© (Ø¬Ù…Ù„Ø©)"}.get(lang, "ðŸ’° Prix unitaire (palier)")
        unit_price_line = f"{discount_label}: {format_price(unit_price)}\n"

    # Promo discount line
    promo_line = ""
    if has_promo:
        promo_discount = order.get("promo_discount", 0.0)
        promo_line = f"ðŸŽ« <b>Code Promo :</b> -{format_price(promo_discount)}\n"

    summary = (
        f"{t('new_order', lang)}\n\n"
        f"{t('product_lbl', lang)} {product['emoji']} {product['name']}\n"
        f"{t('quantity_lbl', lang).format(qty=order['quantity'])}\n"
        f"{unit_price_line}"
        f"{promo_line}"
        f"{t('total_lbl', lang)} {format_price(order['amount_usd'])}\n"
        f"{t('ref_lbl', lang)} <code>{order.get('merchant_trade_no', order['id'])}</code>\n\n"
        f"{t('choose_payment', lang)}"
    )

    markup = await payment_method_keyboard(order["id"], lang, wallet_balance=wallet_balance, has_promo=has_promo)

    if is_callback and update.callback_query:
        await update.callback_query.edit_message_text(
            summary,
            parse_mode="HTML",
            reply_markup=markup,
        )
    else:
        await update.effective_message.reply_text(
            summary,
            parse_mode="HTML",
            reply_markup=markup,
        )
    return WAITING_PAYMENT_METHOD


async def start_apply_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'apply_promo:{order_id}' callback â€” prompt for promo code."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    order_id = int(query.data.split(":")[1])

    # Verify order ownership
    order = await get_order(order_id)
    if not order or order.get("user_telegram_id") != update.effective_user.id:
        await query.edit_message_text(t("access_denied", lang))
        return ConversationHandler.END

    # Store order_id in user_data so we know which order to apply it to
    context.user_data["promo_order_id"] = order_id

    await query.edit_message_text(
        t("promo_prompt", lang),
        parse_mode="HTML",
        reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
    )
    return WAITING_PROMO_CODE


async def back_to_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'back_pay_method:{order_id}' callback â€” return to payment method selection."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    order_id = int(query.data.split(":")[1])
    return await show_payment_method_screen(update, context, order_id, lang, is_callback=True)


async def receive_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message in WAITING_PROMO_CODE state â€” apply promo code."""
    lang = await get_user_lang(update.effective_user.id)
    order_id = context.user_data.get("promo_order_id")
    promo_code_text = update.message.text.strip().upper()

    if not order_id:
        await update.message.reply_text(t("no_pending_order", lang))
        return ConversationHandler.END

    order = await get_order(order_id)
    if not order or order.get("status") != "PENDING":
        await update.message.reply_text(
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        return ConversationHandler.END

    # Verify order ownership
    if order.get("user_telegram_id") != update.effective_user.id:
        await update.message.reply_text(t("access_denied", lang))
        return ConversationHandler.END

    # Check if promo code already applied
    if order.get("promo_code_id"):
        await update.message.reply_text(
            t("promo_already_applied", lang),
            reply_markup=main_menu_keyboard(lang),
        )
        return ConversationHandler.END

    # Retrieve promo code
    from database.models import get_promo_by_code
    promo = await get_promo_by_code(promo_code_text)
    if not promo:
        await update.message.reply_text(
            t("promo_invalid", lang),
            parse_mode="HTML",
            reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
        )
        return WAITING_PROMO_CODE

    # Calculate discount
    original_amount = order["amount_usd"]
    discount_type = promo.get("discount_type", "percent")
    discount_value = promo.get("discount_value", 0.0)

    if discount_type == "percent":
        discount = original_amount * (discount_value / 100.0)
    else:  # fixed
        discount = discount_value

    # Clamp discount to not exceed original amount
    discount = min(discount, original_amount)
    new_amount = max(original_amount - discount, 0.0)

    # Update order with promo code info
    await update_order_status(
        order_id,
        "PENDING",
        amount_usd=new_amount,
        promo_code_id=promo["id"],
        promo_discount=discount
    )

    # Show success message and payment menu again
    success_text = t("promo_success", lang).format(
        discount=format_price(discount),
        total=format_price(new_amount)
    )
    await update.message.reply_text(success_text, parse_mode="HTML")

    return await show_payment_method_screen(update, context, order_id, lang, is_callback=False)


async def pay_with_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_wallet:{order_id}' callback â€” instant payment from wallet balance."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return ConversationHandler.END

        amount = order["amount_usd"]
        product_id = order.get("product_id")

        # Verify order is still payable (prevent double-payment)
        if order.get("status") == "COMPLETED":
            await query.answer(t("payment_confirmed", lang), show_alert=True)
            return ConversationHandler.END
        elif order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            await query.edit_message_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        # Try to deduct from wallet
        from database.models import deduct_wallet, get_wallet_balance
        try:
            new_balance = await deduct_wallet(
                telegram_id, amount,
                f"Order #{order_id}"
            )
        except ValueError:
            # Insufficient balance
            balance = await get_wallet_balance(telegram_id)
            text = t("wallet_insufficient", lang) \
                .replace("${balance}", format_price(balance)) \
                .replace("${required}", format_price(amount))
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        # Payment successful â€” deliver first, then complete
        delivered = await deliver_order(order_id, product_id)

        if delivered:
            await update_order_status(order_id, "COMPLETED", payment_method="wallet")
            product = await get_product(product_id)
            warranty_days = product.get("warranty_days", 0) if product else 0

            wallet_msg = t("wallet_paid", lang) \
                .replace("${amount}", format_price(amount)) \
                .replace("${balance}", format_price(new_balance))

            await query.edit_message_text(f"{wallet_msg}\n\nâœ… PrÃ©paration de votre commande...", parse_mode="HTML")

            header = f"{wallet_msg}"
            footer = (
                f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                f"{t('save_info', lang)}\n\n"
                f"{t('thank_you', lang)}"
            )
            await send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang)
        else:
            # Refund: delivery failed, return funds to wallet
            from database.models import topup_wallet as _topup_refund
            await _topup_refund(telegram_id, amount, f"Refund: delivery failed for order #{order_id}")
            refund_balance = await get_wallet_balance(telegram_id)
            await query.edit_message_text(
                t("delivery_failed", lang) + f"\n\nðŸ’° {format_price(amount)} refunded.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )

        # Notify admins
        try:
            from bot import notify_admins
            product = await get_product(product_id)
            pname = product["name"] if product else "?"
            await notify_admins(
                f"ðŸ’° <b>Wallet Purchase!</b>\n"
                f"ðŸ‘¤ {escape_html(update.effective_user.first_name)}\n"
                f"ðŸ“¦ {pname} x{order.get('quantity', 1)}\n"
                f"ðŸ’µ {format_price(amount)}"
            )
        except Exception:
            pass

        return ConversationHandler.END

    except Exception as exc:
        logger.error("pay_with_wallet: %s", exc, exc_info=True)
        await query.edit_message_text(t("pay_error", lang))
        return ConversationHandler.END


async def pay_with_binance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_binance:{order_id}' callback â€” show Binance Pay instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via Binance which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return ConversationHandler.END

        await update_order_status(order_id, "AWAITING_PAYMENT")

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_amount"] = order["amount_usd"]
        context.user_data["paying_product_id"] = order.get("product_id")

        # Determine which Binance UID to use
        uid_to_show = BINANCE_PAY_ID
        product_id = order.get("product_id")
        if product_id:
            product = await get_product(product_id)
            if product and product.get("binance_account_id"):
                from database.models import get_binance_account
                acc = await get_binance_account(product["binance_account_id"])
                if acc and acc.get("uid"):
                    uid_to_show = acc["uid"]

        await query.edit_message_text(
            f"{t('binance_title', lang)}\n\n"
            f"{t('binance_id_lbl', lang)}\n"
            f"<code>{uid_to_show}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            f"{t('pay_instructions', lang)}\n"
            f"{t('pay_step1', lang)}\n"
            f"{t('pay_step2', lang)}\n\n"
            f"{t('waiting_payment', lang)}",
            parse_mode="HTML",
            reply_markup=payment_check_keyboard(order_id, lang),
        )

        telegram_id = update.effective_user.id
        chat_id = query.message.chat_id if query.message else telegram_id
        task = asyncio.create_task(
            cancel_order_after_timeout(
                context, chat_id, order_id, telegram_id, timeout_seconds=300
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_ORDER_ID

    except Exception as exc:
        logger.error("pay_with_binance: %s", exc, exc_info=True)
        await query.edit_message_text(t("pay_error", lang))
        return ConversationHandler.END


async def receive_order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message in WAITING_ORDER_ID state â€” verify payment."""
    client_order_id = update.message.text.strip()
    order_id = context.user_data.get("paying_order_id")
    expected_amount = context.user_data.get("paying_amount", 0)
    product_id = context.user_data.get("paying_product_id")
    lang = await get_user_lang(update.effective_user.id)

    if not order_id:
        await update.message.reply_text(t("no_pending_order", lang))
        return ConversationHandler.END

    db_order = await get_order(order_id)
    if not db_order:
        await update.message.reply_text(
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        context.user_data.pop("paying_order_id", None)
        context.user_data.pop("paying_amount", None)
        context.user_data.pop("paying_product_id", None)
        return ConversationHandler.END

    # Track if order was cancelled by timeout (we still verify on-chain)
    order_was_cancelled = db_order.get("status") == "CANCELLED"

    try:
        await update.message.reply_text(t("verifying", lang))

        # Verify order is still in a payable status
        if db_order.get("status") == "COMPLETED":
            await update.message.reply_text(t("payment_confirmed", lang))
            return ConversationHandler.END
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED"):
            await update.message.reply_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        # Determine which API credentials to use based on the product
        api_key_to_use = None
        api_secret_to_use = None
        if product_id:
            product = await get_product(product_id)
            if product and product.get("binance_account_id"):
                from database.models import get_binance_account
                acc = await get_binance_account(product["binance_account_id"])
                if acc:
                    api_key_to_use = acc.get("api_key")
                    api_secret_to_use = acc.get("api_secret")

        result = await verify_payment(
            client_order_id, 
            expected_amount, 
            api_key=api_key_to_use, 
            api_secret=api_secret_to_use
        )

        if result.get("verified"):
            # Anti-replay: check if transaction was already used
            tx = result.get("transaction", {})
            tx_id = str(tx.get("transactionId", "")) or str(tx.get("orderId", "")) or client_order_id
            if not await record_used_transaction(tx_id, order_id, update.effective_user.id, expected_amount):
                logger.warning("REPLAY ATTACK BLOCKED: User %s tried to reuse transaction %s for order %d",
                             update.effective_user.id, tx_id, order_id)
                await update.message.reply_text(
                    "âŒ This transaction has already been used for another order.",
                    reply_markup=main_menu_keyboard(lang),
                )
                return ConversationHandler.END

            # Cancel any pending timeout task for this order since it's paid
            task = _timeout_tasks.pop(order_id, None)
            if task and not task.done():
                task.cancel()
                
            # Reactivate order if it was cancelled by timeout but payment is confirmed
            if order_was_cancelled:
                await update_order_status(order_id, "PENDING", payment_method="binance")
                logger.info("Order #%d reactivated: Binance payment confirmed after timeout", order_id)
            binance_tx_id = tx.get("transactionId", "")
            binance_order_id_val = tx.get("orderId", "")
            display_id = binance_order_id_val or binance_tx_id or client_order_id

            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(order_id, "COMPLETED", payment_method="binance", binance_order_id=display_id)
                product = await get_product(product_id)
                warranty_days = product.get("warranty_days", 0) if product else 0

                await update.message.reply_text(f"âœ… {t('payment_confirmed', lang)}\n\nPrÃ©paration de votre commande...", parse_mode="HTML")

                header = f"{t('payment_confirmed', lang)}"
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{t('thank_you', lang)}"
                )
                await send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang)
            else:
                await update_order_status(order_id, "FAILED", payment_method="binance", binance_order_id=display_id)
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang)}\n\n"
                    f"âš ï¸ <b>Action requise :</b> Veuillez contacter le support technique avec l'ID de commande <b>#{order_id}</b> pour obtenir un remboursement manuel.",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            await _notify_admins_sale(context, order_id, product_id, expected_amount)

            if product_id:
                low = await check_low_stock(product_id)
                if low:
                    await _notify_admins_low_stock(context, product_id)

            context.user_data.pop("paying_order_id", None)
            context.user_data.pop("paying_amount", None)
            context.user_data.pop("paying_product_id", None)
            return ConversationHandler.END

        else:
            error_msg = result.get("error", t("payment_not_detected", lang))
            await update.message.reply_text(
                f"{t('payment_not_detected', lang)}\n\n"
                f"âŒ {error_msg}\n\n"
                f"{t('retry_order_id', lang)}\n\n"
                f"{t('contact_support', lang)}",
                parse_mode="HTML",
            )
            await _notify_admins_manual_check(context, order_id, client_order_id)
            return WAITING_ORDER_ID

    except Exception as exc:
        logger.error("receive_order_id: %s", exc, exc_info=True)
        await update.message.reply_text(t("verify_error", lang))
        return WAITING_ORDER_ID


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'check_pay:{order_id}' callback â€” prompt user to send Order ID."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return

        await query.edit_message_text(
            f"{t('check_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('send_order_id', lang)}",
            parse_mode="HTML",
            reply_markup=payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_payment: %s", exc, exc_info=True)
        await query.edit_message_text(t("verify_error", lang))


async def cancel_order_after_timeout(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    order_id: int,
    user_telegram_id: int,
    timeout_seconds: int = 300,
):
    """Wait for timeout_seconds, then cancel order if it is still unpaid."""
    await asyncio.sleep(timeout_seconds)
    try:
        order = await get_order(order_id)
        if order and order.get("status") in ("PENDING", "AWAITING_PAYMENT"):
            await update_order_status(order_id, "CANCELLED")
            lang = await get_user_lang(user_telegram_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=t("order_timeout", lang).format(id=order_id),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
    except Exception as exc:
        logger.error("Error in cancel_order_after_timeout: %s", exc, exc_info=True)


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'cancel_order:{order_id}' callback â€” cancel the pending order."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)
        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to cancel order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return

        # Only allow cancelling PENDING or AWAITING_PAYMENT orders
        if order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            await query.edit_message_text(
                t("cannot_cancel", lang).format(status=order.get("status")),
                reply_markup=main_menu_keyboard(lang),
            )
            return

        # Cancel the background timeout task if it exists
        task = _timeout_tasks.pop(order_id, None)
        if task and not task.done():
            task.cancel()

        await update_order_status(order_id, "CANCELLED")

        context.user_data.pop("paying_order_id", None)
        context.user_data.pop("paying_amount", None)
        context.user_data.pop("paying_product_id", None)
        context.user_data.pop("pending_order_id", None)
        context.user_data.pop("pending_product_id", None)

        await query.edit_message_text(
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception as exc:
        logger.error("cancel_order: %s", exc, exc_info=True)
        await query.edit_message_text(
            t("cancel_error", lang),
            reply_markup=main_menu_keyboard(lang),
        )

    return ConversationHandler.END


async def _start_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback: end conversation and redirect to /start."""
    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_amount", None)
    context.user_data.pop("paying_product_id", None)

    from handlers.start import start_command
    await start_command(update, context)
    return ConversationHandler.END


# â”€â”€ Admin notification helpers â”€â”€

async def _notify_admins_sale(context, order_id, product_id, amount):
    product = await get_product(product_id) if product_id else None
    prod_name = escape_html(product["name"]) if product else "?"
    text = (
        "ðŸ”” <b>Nouvelle vente !</b>\n"
        f"ðŸ“¦ Produit : {prod_name}\n"
        f"ðŸ’° Montant : {format_price(amount)}\n"
        f"ðŸ”– Commande : #{order_id}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _notify_admins_low_stock(context, product_id):
    product = await get_product(product_id)
    prod_name = escape_html(product["name"]) if product else f"ID {product_id}"
    stock = await get_stock_count(product_id)
    text = (
        "âš ï¸ <b>Stock faible !</b>\n"
        f"ðŸ“¦ {prod_name}\n"
        f"ðŸ“‰ Restant : {stock}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _notify_admins_manual_check(context, order_id, client_order_id):
    text = (
        "ðŸ”” <b>VÃ©rification manuelle requise</b>\n"
        f"ðŸ”– Commande : #{order_id}\n"
        f"ðŸ“ Order ID soumis : <code>{client_order_id}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def pay_with_bep20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_bep20:{order_id}' callback â€” show BEP20 deposit instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via BEP20 which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return ConversationHandler.END

        from database.models import get_setting
        bep20_address = await get_setting("bep20_address")
        if not bep20_address:
            await query.edit_message_text("âŒ BEP20 USDT payment is not configured by admin.")
            return ConversationHandler.END

        await update_order_status(order_id, "AWAITING_PAYMENT")

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_amount"] = order["amount_usd"]
        context.user_data["paying_product_id"] = order.get("product_id")

        from utils.keyboards import payment_check_keyboard
        
        await query.edit_message_text(
            f"{t('bep20_title', lang)}\n\n"
            f"{t('bep20_address_lbl', lang)}\n"
            f"<code>{bep20_address}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            f"{t('bep20_instructions', lang)}\n\n"
            f"ðŸ‘‰ <b>{t('bep20_send_tx_hash', lang)}</b>",
            parse_mode="HTML",
            reply_markup=payment_check_keyboard(order_id, lang),
        )

        # Launch a background task to auto-cancel the order if not paid in 5 mins
        task = asyncio.create_task(
            cancel_order_after_timeout(
                context,
                chat_id=update.effective_chat.id,
                order_id=order_id,
                user_telegram_id=update.effective_user.id,
                timeout_seconds=300,
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_BEP20_TX_HASH

    except Exception as exc:
        logger.error("pay_with_bep20: %s", exc, exc_info=True)
        await query.edit_message_text(t("pay_error", lang))
        return ConversationHandler.END


async def check_bep20_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'check_bep20:{order_id}' callback â€” prompt user to send Tx Hash."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check BEP20 payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return

        from utils.keyboards import bep20_payment_check_keyboard
        
        await query.edit_message_text(
            f"{t('bep20_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('bep20_send_tx_hash', lang)}",
            parse_mode="HTML",
            reply_markup=bep20_payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_bep20_payment: %s", exc, exc_info=True)
        await query.edit_message_text(t("verify_error", lang))


async def receive_bep20_tx_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message in WAITING_BEP20_TX_HASH state â€” verify BEP20 payment."""
    tx_hash = update.message.text.strip()
    order_id = context.user_data.get("paying_order_id")
    expected_amount = context.user_data.get("paying_amount", 0)
    product_id = context.user_data.get("paying_product_id")
    lang = await get_user_lang(update.effective_user.id)

    if not order_id:
        await update.message.reply_text(t("no_pending_order", lang))
        return ConversationHandler.END

    db_order = await get_order(order_id)
    if not db_order:
        await update.message.reply_text(
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        context.user_data.pop("paying_order_id", None)
        context.user_data.pop("paying_amount", None)
        context.user_data.pop("paying_product_id", None)
        return ConversationHandler.END

    # Validation: on-chain hashes start with "0x" and are 66 chars.
    # Off-chain Binance transfers can be an ID (often digits) or "Off-chain transfer <ID>"
    is_on_chain = tx_hash.startswith("0x") and len(tx_hash) == 66
    is_off_chain = tx_hash.isdigit() or "off-chain" in tx_hash.lower() or (not tx_hash.startswith("0x") and len(tx_hash) > 5)

    if not is_on_chain and not is_off_chain:
        await update.message.reply_text(t("bep20_invalid_tx_hash", lang))
        return WAITING_BEP20_TX_HASH

    # Track if order was cancelled by timeout (we still verify on-chain)
    order_was_cancelled = db_order.get("status") == "CANCELLED"

    try:
        await update.message.reply_text(t("verifying", lang))

        if db_order.get("status") == "COMPLETED":
            await update.message.reply_text(t("payment_confirmed", lang))
            return ConversationHandler.END
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED"):
            await update.message.reply_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        # Anti-replay check
        from database.models import is_bep20_transaction_used, record_used_bep20_transaction, get_setting
        if await is_bep20_transaction_used(tx_hash):
            logger.warning("REPLAY ATTACK BLOCKED (BEP20): User %s tried to reuse tx %s for order %d",
                           update.effective_user.id, tx_hash, order_id)
            await update.message.reply_text(
                t("tx_already_used", lang),
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        bep20_address = await get_setting("bep20_address")
        if not bep20_address:
            await update.message.reply_text("âŒ BEP20 payment address is not configured by the administrator.")
            return ConversationHandler.END

        from services.blockchain_verify import verify_bep20_payment
        from services.binance_verify import verify_internal_transfer

        result = {"verified": False, "error": "Type de transaction non pris en charge."}

        if is_on_chain:
            # On-chain verification
            result = await verify_bep20_payment(tx_hash, expected_amount, bep20_address)
        else:
            # Off-chain Binance internal verification
            api_key = None
            api_secret = None
            if product_id:
                product = await get_product(product_id)
                if product and product.get("binance_account_id"):
                    from database.models import get_binance_account
                    acc = await get_binance_account(product["binance_account_id"])
                    if acc:
                        api_key = acc.get("api_key")
                        api_secret = acc.get("api_secret")
            
            result = await verify_internal_transfer(tx_hash, expected_amount, api_key=api_key, api_secret=api_secret)

        if result.get("verified"):
            # Record hash to prevent double spending
            if not await record_used_bep20_transaction(tx_hash, order_id, update.effective_user.id, expected_amount):
                logger.warning("REPLAY ATTACK BLOCKED (BEP20 DB constraint): User %s tried to reuse tx %s for order %d",
                               update.effective_user.id, tx_hash, order_id)
                await update.message.reply_text(
                    t("tx_already_used", lang),
                    reply_markup=main_menu_keyboard(lang),
                )
                return ConversationHandler.END

            # Cancel any pending timeout task for this order since it's paid
            task = _timeout_tasks.pop(order_id, None)
            if task and not task.done():
                task.cancel()

            # Reactivate order if it was cancelled by timeout but payment is confirmed on-chain
            if order_was_cancelled:
                await update_order_status(order_id, "PENDING", payment_method="bep20")
                logger.info("Order #%d reactivated: BEP20 payment confirmed on-chain after timeout", order_id)

            # Deliver order
            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(order_id, "COMPLETED", payment_method="bep20", binance_order_id=tx_hash)
                product = await get_product(product_id)
                warranty_days = product.get("warranty_days", 0) if product else 0
                
                await update.message.reply_text(f"âœ… {t('payment_confirmed', lang)}\n\nPrÃ©paration de votre commande...", parse_mode="HTML")

                header = f"{t('payment_confirmed', lang)}"
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{t('thank_you', lang)}"
                )
                await send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang)
            else:
                await update_order_status(order_id, "FAILED", payment_method="bep20", binance_order_id=tx_hash)
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang)}\n\n"
                    f"âš ï¸ <b>Action requise :</b> Veuillez contacter le support technique avec l'ID de commande <b>#{order_id}</b> pour obtenir un remboursement manuel.",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            # Notify admins of BSC BEP20 sale
            try:
                from bot import notify_admins
                product = await get_product(product_id)
                pname = product["name"] if product else "?"
                await notify_admins(
                    f"ðŸª™ <b>BEP20 Sale!</b>\n"
                    f"ðŸ‘¤ {escape_html(update.effective_user.first_name)}\n"
                    f"ðŸ“¦ {pname} x{db_order.get('quantity', 1)}\n"
                    f"ðŸ’µ {format_price(expected_amount)}"
                )
            except Exception:
                pass

            if product_id:
                low = await check_low_stock(product_id)
                if low:
                    await _notify_admins_low_stock(context, product_id)

            context.user_data.pop("paying_order_id", None)
            context.user_data.pop("paying_amount", None)
            context.user_data.pop("paying_product_id", None)
            return ConversationHandler.END

        else:
            error_msg = result.get("error", t("payment_not_detected", lang))
            await update.message.reply_text(
                f"{t('payment_not_detected', lang)}\n\n"
                f"âŒ {error_msg}\n\n"
                f"{t('retry_order_id', lang)}\n\n"
                f"{t('support_hint', lang)}",
                parse_mode="HTML",
            )
            # Notify admins of manual verification need
            await _notify_admins_manual_check(context, order_id, tx_hash)
            return WAITING_BEP20_TX_HASH

    except Exception as exc:
        logger.error("receive_bep20_tx_hash: %s", exc, exc_info=True)
        await update.message.reply_text(t("verify_error", lang))
        return WAITING_BEP20_TX_HASH


async def pay_with_trc20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_trc20:{order_id}' callback â€” show TRC20 deposit instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via TRC20 which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return ConversationHandler.END

        from database.models import get_setting
        trc20_address = await get_setting("trc20_address")
        if not trc20_address:
            await query.edit_message_text("âŒ TRC20 USDT payment is not configured by admin.")
            return ConversationHandler.END

        await update_order_status(order_id, "AWAITING_PAYMENT")

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_amount"] = order["amount_usd"]
        context.user_data["paying_product_id"] = order.get("product_id")

        from utils.keyboards import payment_check_keyboard
        
        await query.edit_message_text(
            f"{t('trc20_title', lang)}\n\n"
            f"{t('trc20_address_lbl', lang)}\n"
            f"<code>{trc20_address}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            f"{t('trc20_instructions', lang)}\n\n"
            f"ðŸ‘‰ <b>{t('trc20_send_tx_hash', lang)}</b>",
            parse_mode="HTML",
            reply_markup=payment_check_keyboard(order_id, lang),
        )

        # Launch a background task to auto-cancel the order if not paid in 5 mins
        task = asyncio.create_task(
            cancel_order_after_timeout(
                context,
                chat_id=update.effective_chat.id,
                order_id=order_id,
                user_telegram_id=update.effective_user.id,
                timeout_seconds=300,
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_TRC20_TX_HASH

    except Exception as exc:
        logger.error("pay_with_trc20: %s", exc, exc_info=True)
        await query.edit_message_text(t("pay_error", lang))
        return ConversationHandler.END


async def check_trc20_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'check_trc20:{order_id}' callback â€” prompt user to send Tx Hash."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check TRC20 payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(t("access_denied", lang))
            return

        from utils.keyboards import trc20_payment_check_keyboard
        
        await query.edit_message_text(
            f"{t('trc20_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('trc20_send_tx_hash', lang)}",
            parse_mode="HTML",
            reply_markup=trc20_payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_trc20_payment: %s", exc, exc_info=True)
        await query.edit_message_text(t("verify_error", lang))


async def receive_trc20_tx_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message in WAITING_TRC20_TX_HASH state - verify TRC20 payment."""
    tx_hash = update.message.text.strip()
    order_id = context.user_data.get("paying_order_id")
    expected_amount = context.user_data.get("paying_amount", 0)
    product_id = context.user_data.get("paying_product_id")
    lang = await get_user_lang(update.effective_user.id)

    if not order_id:
        await update.message.reply_text(t("no_pending_order", lang))
        return ConversationHandler.END

    db_order = await get_order(order_id)
    if not db_order:
        await update.message.reply_text(
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        context.user_data.pop("paying_order_id", None)
        context.user_data.pop("paying_amount", None)
        context.user_data.pop("paying_product_id", None)
        return ConversationHandler.END

    # Clean the transaction hash for TRC20
    tx_hash_clean = tx_hash
    if tx_hash_clean.lower().startswith("0x"):
        tx_hash_clean = tx_hash_clean[2:]

    # Validate TRON Tx Hash length and character set
    import re
    if not re.match(r"^[a-fA-F0-9]{64}$", tx_hash_clean):
        await update.message.reply_text(t("trc20_invalid_tx_hash", lang))
        return WAITING_TRC20_TX_HASH

    # Track if order was cancelled by timeout (we still verify on-chain)
    order_was_cancelled = db_order.get("status") == "CANCELLED"

    try:
        await update.message.reply_text(t("verifying", lang))

        if db_order.get("status") == "COMPLETED":
            await update.message.reply_text(t("payment_confirmed", lang))
            return ConversationHandler.END
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED"):
            await update.message.reply_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        # Anti-replay check
        from database.models import is_trc20_transaction_used, record_used_trc20_transaction, get_setting
        if await is_trc20_transaction_used(tx_hash_clean):
            logger.warning("REPLAY ATTACK BLOCKED (TRC20): User %s tried to reuse tx %s for order %d",
                           update.effective_user.id, tx_hash_clean, order_id)
            await update.message.reply_text(
                t("tx_already_used", lang),
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        trc20_address = await get_setting("trc20_address")
        if not trc20_address:
            await update.message.reply_text("TRC20 payment address is not configured by the administrator.")
            return ConversationHandler.END

        from services.trc20_verify import verify_trc20_payment

        # On-chain verification
        result = await verify_trc20_payment(tx_hash_clean, expected_amount, trc20_address)

        if result.get("verified"):
            if not await record_used_trc20_transaction(tx_hash_clean, order_id, update.effective_user.id, expected_amount):
                logger.warning("REPLAY ATTACK BLOCKED (TRC20 DB): User %s reuse tx %s order %d",
                               update.effective_user.id, tx_hash_clean, order_id)
                await update.message.reply_text(t("tx_already_used", lang), reply_markup=main_menu_keyboard(lang))
                return ConversationHandler.END

            task = _timeout_tasks.pop(order_id, None)
            if task and not task.done():
                task.cancel()

            if order_was_cancelled:
                await update_order_status(order_id, "PENDING", payment_method="trc20")
                logger.info("Order #%d reactivated: TRC20 payment confirmed on-chain after timeout", order_id)

            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(order_id, "COMPLETED", payment_method="trc20", binance_order_id=tx_hash_clean)
                product = await get_product(product_id)
                warranty_days = product.get("warranty_days", 0) if product else 0
                await update.message.reply_text(f"✅ {t('payment_confirmed', lang)}\n\nPréparation de votre commande...", parse_mode="HTML")
                header = f"{t('payment_confirmed', lang)}"
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{t('thank_you', lang)}"
                )
                await send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang)
            else:
                await update_order_status(order_id, "FAILED", payment_method="trc20", binance_order_id=tx_hash_clean)
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang)}\n\n"
                    f"Action requise : Veuillez contacter le support avec l'ID de commande #{order_id}.",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            try:
                from bot import notify_admins
                product = await get_product(product_id)
                pname = product["name"] if product else "?"
                await notify_admins(
                    f"TRC20 Sale!\n"
                    f"User: {escape_html(update.effective_user.first_name)}\n"
                    f"Product: {pname} x{db_order.get('quantity', 1)}\n"
                    f"Amount: {format_price(expected_amount)}"
                )
            except Exception:
                pass

            if product_id:
                low = await check_low_stock(product_id)
                if low:
                    await _notify_admins_low_stock(context, product_id)

            context.user_data.pop("paying_order_id", None)
            context.user_data.pop("paying_amount", None)
            context.user_data.pop("paying_product_id", None)
            return ConversationHandler.END

        else:
            error_msg = result.get("error", t("payment_not_detected", lang))
            await update.message.reply_text(
                f"{t('payment_not_detected', lang)}\n\n{error_msg}\n\n{t('retry_order_id', lang)}\n\n{t('support_hint', lang)}",
                parse_mode="HTML",
            )
            await _notify_admins_manual_check(context, order_id, tx_hash)
            return WAITING_TRC20_TX_HASH

    except Exception as exc:
        logger.error("receive_trc20_tx_hash: %s", exc, exc_info=True)
        await update.message.reply_text(t("verify_error", lang))
        return WAITING_TRC20_TX_HASH

def get_payment_conversation_handler() -> ConversationHandler:
    """Build and return the payment ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(initiate_purchase, pattern=r"^buy:"),
            CallbackQueryHandler(pay_with_binance, pattern=r"^pay_binance:"),
            CallbackQueryHandler(pay_with_wallet, pattern=r"^pay_wallet:"),
            CallbackQueryHandler(pay_with_bep20, pattern=r"^pay_bep20:"),
            CallbackQueryHandler(pay_with_trc20, pattern=r"^pay_trc20:"),
            CallbackQueryHandler(start_apply_promo, pattern=r"^apply_promo:"),
        ],
        states={
            WAITING_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity_text),
            ],
            WAITING_PAYMENT_METHOD: [
                CallbackQueryHandler(pay_with_binance, pattern=r"^pay_binance:"),
                CallbackQueryHandler(pay_with_wallet, pattern=r"^pay_wallet:"),
                CallbackQueryHandler(pay_with_bep20, pattern=r"^pay_bep20:"),
                CallbackQueryHandler(pay_with_trc20, pattern=r"^pay_trc20:"),
                CallbackQueryHandler(start_apply_promo, pattern=r"^apply_promo:"),
            ],
            WAITING_PROMO_CODE: [
                CallbackQueryHandler(back_to_payment_method, pattern=r"^back_pay_method:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_code),
            ],
            WAITING_ORDER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_id),
            ],
            WAITING_BEP20_TX_HASH: [
                CallbackQueryHandler(check_bep20_payment, pattern=r"^check_bep20:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bep20_tx_hash),
            ],
            WAITING_TRC20_TX_HASH: [
                CallbackQueryHandler(check_trc20_payment, pattern=r"^check_trc20:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_trc20_tx_hash),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_order, pattern=r"^cancel_order:"),
            CommandHandler("start", _start_redirect),
        ],
        per_message=False,
        allow_reentry=True,
        name="payment_conversation",
    )

async def download_txt_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'dl_txt:{order_id}' callback - downloads order delivery as a TXT file."""
    import io
    from database.models import get_stock_items_for_order
    
    query = update.callback_query
    await query.answer()
    
    try:
        order_id = int(query.data.split(":")[1])
        items = await get_stock_items_for_order(order_id)
        
        if not items:
            await query.answer("Delivery not found or empty.", show_alert=True)
            return
            
        file_content = ""
        for i, item in enumerate(items):
            file_content += f"--- Product nÂ°{i+1} ---\n{item['account_data']}\n\n"
            
        file_bytes = io.BytesIO(file_content.encode('utf-8'))
        file_bytes.name = f"Order_{order_id}_accounts.txt"
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_bytes,
            caption=f"ðŸ“ Order #{order_id} Accounts",
        )
    except Exception as exc:
        logger.error("download_txt_delivery error: %s", exc, exc_info=True)
        await query.answer("Error generating file.", show_alert=True)
