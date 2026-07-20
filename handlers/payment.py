# -*- coding: utf-8 -*-
"""
Payment flow handlers â€” purchase â†’ Binance Pay instructions â†’ Order ID â†’ verify â†’ deliver.
Uses ConversationHandler with state WAITING_ORDER_ID = 200.
"""

import asyncio
import logging
import os

from telegram import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS, BINANCE_PAY_ID, PAYMENT_TIMEOUT_SECONDS
from database.models import (
    create_order,
    get_pending_activation_order_for_user,
    get_order,
    get_product,
    get_sale_notification_details,
    get_stock_count,
    get_telegram_order_pricing,
    get_user_lang,
    purchase_order_with_wallet,
    record_product_buy_click,
    submit_activation_identifier,
    update_order_status,
    record_used_transaction,
)
from services.binance_verify import verify_payment
from services.delivery import check_low_stock, deliver_order
from services.supplier_api import SupplierAPIError
from services.supplier_sync import refresh_supplier_product_stock
from utils.helpers import escape_html, format_price
from utils.keyboards import (
    back_keyboard,
    main_menu_keyboard,
    payment_check_keyboard,
    payment_method_keyboard,
    nowpayments_payment_keyboard,
    quantity_keyboard,
)
from utils.locales import t, get_confirmation_message
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)

WAITING_ORDER_ID = 200
WAITING_QUANTITY = 201
WAITING_PAYMENT_METHOD = 202
WAITING_PROMO_CODE = 203
WAITING_BEP20_TX_HASH = 204
WAITING_TRC20_TX_HASH = 205
WAITING_ACTIVATION_IDENTIFIER = 206
WAITING_NOWPAYMENTS = 207

_timeout_tasks = {}
_nowpayments_locks = [asyncio.Lock() for _ in range(64)]


def _nowpayments_callback_url() -> str:
    explicit = os.environ.get("NOWPAYMENTS_CALLBACK_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")

    for env_name in ("PUBLIC_BASE_URL", "WEBHOOK_URL"):
        public_base = os.environ.get(env_name, "").strip().rstrip("/")
        if public_base:
            return f"{public_base}/webhooks/nowpayments"

    # Railway injects this variable for services with a generated public domain.
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip().strip("/")
    if railway_domain:
        if railway_domain.startswith(("http://", "https://")):
            public_base = railway_domain.rstrip("/")
        else:
            public_base = f"https://{railway_domain}"
        return f"{public_base}/webhooks/nowpayments"
    return ""


def _format_crypto_amount(value) -> str:
    rendered = f"{float(value or 0):.8f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _is_activation_product(product: dict | None) -> bool:
    return bool(product and product.get("delivery_type") == "activation")


async def _get_current_purchase_stock(
    product: dict,
    *,
    reservation_order_id: int | None = None,
) -> int:
    product_id = int(product["id"])
    if product.get("delivery_type") != "supplier_api":
        return await get_stock_count(product_id)
    refreshed = await refresh_supplier_product_stock(
        product_id,
        reservation_order_id=reservation_order_id,
    )
    return max(0, int(refreshed or 0))


async def _ensure_supplier_stock_for_order(query, order: dict, lang: str) -> bool:
    """Fail closed before exposing payment instructions for supplier orders."""
    product = await get_product(int(order["product_id"]))
    if not product or product.get("delivery_type") != "supplier_api":
        return True

    try:
        available = await _get_current_purchase_stock(
            product,
            reservation_order_id=int(order["id"]),
        )
    except SupplierAPIError as exc:
        logger.warning(
            "Supplier stock verification failed for order #%s: %s",
            order.get("id"),
            exc,
        )
        await safe_edit_message_text(
            query,
            t("pay_error", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        return False

    quantity = max(1, int(order.get("quantity") or 1))
    if quantity <= available:
        return True

    await update_order_status(
        int(order["id"]),
        "CANCELLED",
        expected_statuses=("PENDING", "AWAITING_PAYMENT"),
    )
    await safe_edit_message_text(
        query,
        t("insufficient_stock", lang).format(stock=available),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )
    return False


def _clear_payment_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in ("paying_order_id", "paying_amount", "paying_product_id", "pending_order_id", "pending_product_id"):
        context.user_data.pop(key, None)


async def _prompt_activation_identifier(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, product: dict | None, lang: str, payment_method: str, payment_ref: str | None = None):
    kwargs = {"payment_method": payment_method}
    if payment_ref:
        kwargs["binance_order_id"] = payment_ref
    await update_order_status(
        order_id,
        "AWAITING_ACTIVATION_INFO",
        expected_statuses=("PENDING", "AWAITING_PAYMENT", "AWAITING_ACTIVATION_INFO"),
        **kwargs,
    )
    context.user_data["activation_order_id"] = order_id
    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_amount", None)
    context.user_data.pop("paying_product_id", None)

    product_name = product["name"] if product else f"#{order_id}"
    text = t("activation_prompt", lang).format(
        payment_confirmed=t("payment_confirmed", lang),
        product=escape_html(product_name),
    )
    if update.callback_query:
        await safe_edit_message_text(update.callback_query, text, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML")
    return WAITING_ACTIVATION_IDENTIFIER


async def receive_activation_identifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the identifier for a paid manual activation order."""
    if not update.message or not update.message.text:
        return ConversationHandler.END

    identifier = update.message.text.strip()
    order_id = context.user_data.get("activation_order_id")
    if len(identifier) < 2:
        if order_id:
            lang = await get_user_lang(update.effective_user.id)
            await update.message.reply_text(t("activation_identifier_too_short", lang))
            return WAITING_ACTIVATION_IDENTIFIER
        return ConversationHandler.END

    order = await get_order(order_id) if order_id else None
    if not order or order.get("user_telegram_id") != update.effective_user.id or order.get("status") != "AWAITING_ACTIVATION_INFO":
        order = await get_pending_activation_order_for_user(update.effective_user.id)
        if not order:
            return ConversationHandler.END
        order_id = order["id"]

    lang = await get_user_lang(update.effective_user.id)
    submitted = await submit_activation_identifier(order_id, identifier)
    if not submitted:
        context.user_data.pop("activation_order_id", None)
        return ConversationHandler.END
    context.user_data.pop("activation_order_id", None)

    product = await get_product(order["product_id"])
    product_name = product["name"] if product else f"#{order['product_id']}"
    username = f"@{update.effective_user.username}" if update.effective_user.username else escape_html(update.effective_user.first_name or str(update.effective_user.id))

    try:
        from bot import notify_admins
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(t("activation_admin_button", lang), callback_data=f"adm_activate_order:{order_id}")
        ]])
        await notify_admins(
            "<b>Nouvelle activation a faire</b>\n\n"
            f"Commande: #{order_id}\n"
            f"Client: {username} (<code>{update.effective_user.id}</code>)\n"
            f"Produit: {escape_html(product_name)} x{order.get('quantity', 1)}\n"
            f"Montant: {format_price(order.get('amount_usd', 0))}\n"
            f"Identifiant: <code>{escape_html(identifier)}</code>",
            reply_markup=markup,
        )
    except Exception:
        pass

    await update.message.reply_text(t("activation_request_sent", lang), reply_markup=main_menu_keyboard(lang))
    return ConversationHandler.END


def _build_txt_delivery(items: list) -> str:
    """Return raw account data separated by one blank line."""
    accounts = [str(item["account_data"]).strip() for item in items]
    return "\n\n".join(accounts) + "\n"


async def send_delivery_messages(bot, chat_id: int, header: str, items: list, footer: str, lang: str, order_id: int = None):
    """Sends delivery messages. Uses a single .txt document if the total delivery is very long."""
    import io
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    total_length = sum(len(item['account_data']) for item in items)
    your_acc_text = t("your_account", lang)
    
    base_markup = main_menu_keyboard(lang)
    if order_id and total_length <= 1500 and len(items) <= 10:
        new_kb = [[InlineKeyboardButton("📥 Download as TXT", callback_data=f"dl_txt:{order_id}")]] + list(base_markup.inline_keyboard)
        reply_markup = InlineKeyboardMarkup(new_kb)
    else:
        reply_markup = base_markup
    
    if total_length > 1500 or len(items) > 10:
        file_content = _build_txt_delivery(items)
        file_bytes = io.BytesIO(file_content.encode('utf-8'))
        file_bytes.name = "accounts.txt"
        
        await bot.send_message(chat_id=chat_id, text=header, parse_mode="HTML")
        await bot.send_document(chat_id=chat_id, document=file_bytes, caption=f"📁 {your_acc_text}")
        await bot.send_message(chat_id=chat_id, text=footer, parse_mode="HTML", reply_markup=reply_markup)
        return

    current_msg = f"{header}\n\n"
    if "your_account" in header or "votre compte" in header.lower() or "your account" in header.lower() or your_acc_text.lower() in header.lower():
        pass
    else:
        current_msg += f"{your_acc_text}\n"
        
    for item in items:
        line = f"🔑 <code>{escape_html(item['account_data'])}</code>\n"
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


async def safe_send_delivery_messages(bot, chat_id: int, header: str, items: list, footer: str, lang: str, order_id: int = None) -> bool:
    try:
        await send_delivery_messages(bot, chat_id, header, items, footer, lang, order_id=order_id)
        return True
    except Exception as exc:
        logger.error("Delivery message failed for order #%s: %s", order_id, exc, exc_info=True)
        alert = (
            "<b>Delivery message failed</b>\n\n"
            f"Order: #{order_id}\n"
            f"Client: <code>{chat_id}</code>\n"
            "Stock is reserved and the order is completed. Ask the client to open purchase history."
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=alert, parse_mode="HTML")
            except Exception:
                pass
        return False


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

        asyncio.create_task(record_product_buy_click(product_id, update.effective_user.id))

        is_activation = _is_activation_product(product)
        try:
            stock = await _get_current_purchase_stock(product)
        except SupplierAPIError as exc:
            logger.warning(
                "Supplier stock verification failed for product %s: %s",
                product_id,
                exc,
            )
            await safe_edit_message_text(
                query,
                t("pay_error", lang),
                parse_mode="HTML",
                reply_markup=back_keyboard(
                    f"back_prods:{product['category_id']}", lang
                ),
            )
            return ConversationHandler.END
        if not is_activation and stock <= 0:
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
                    await update_order_status(
                        old_order_id,
                        "CANCELLED",
                        expected_statuses=("PENDING",),
                    )
                    logger.info("Auto-cancelled stale order #%d (new purchase started)", old_order_id)
            except Exception:
                pass
            context.user_data.pop("pending_order_id", None)
            context.user_data.pop("pending_product_id", None)

        if is_activation:
            return await _process_quantity(update, context, product_id, 1, lang, is_callback=True)

        text = t("choose_quantity", lang).format(stock=stock)
        markup = quantity_keyboard(product_id, stock, lang)
        
        try:
            await safe_edit_message_text(query, 
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
            await safe_edit_message_text(update.callback_query, msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    is_activation = _is_activation_product(product)
    try:
        stock = await _get_current_purchase_stock(product)
    except SupplierAPIError as exc:
        logger.warning(
            "Supplier stock verification failed for product %s: %s",
            product_id,
            exc,
        )
        msg = t("pay_error", lang)
        if is_callback:
            await safe_edit_message_text(
                update.callback_query,
                msg,
                reply_markup=main_menu_keyboard(lang),
            )
        else:
            await update.message.reply_text(
                msg,
                reply_markup=main_menu_keyboard(lang),
            )
        return ConversationHandler.END
    if not is_activation and quantity > stock:
        msg = t("insufficient_stock", lang).format(stock=stock)
        if is_callback:
            try:
                await safe_edit_message_text(update.callback_query, 
                    msg,
                    reply_markup=quantity_keyboard(product_id, stock, lang),
                )
            except Exception as exc:
                if "Message is not modified" not in str(exc):
                    raise
        else:
            await update.message.reply_text(msg)
        return WAITING_QUANTITY

    telegram_id = update.effective_user.id
    try:
        pricing = await get_telegram_order_pricing(
            telegram_id, product_id, quantity
        )
    except ValueError as exc:
        logger.info(
            "Telegram special price unavailable for user %s product %s: %s",
            telegram_id,
            product_id,
            exc,
        )
        msg = t("pay_error", lang)
        if is_callback:
            await safe_edit_message_text(
                update.callback_query,
                msg,
                reply_markup=back_keyboard(
                    f"back_prods:{product['category_id']}", lang
                ),
            )
        else:
            await update.message.reply_text(
                msg,
                reply_markup=back_keyboard(
                    f"back_prods:{product['category_id']}", lang
                ),
            )
        return ConversationHandler.END
    unit_price = float(pricing["unit_price"])
    total_price = round(unit_price * quantity, 2)

    # â”€â”€ Prevent duplicate orders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Cancel any previous PENDING order for this user to avoid duplicates
    existing_order_id = context.user_data.get("pending_order_id")
    if existing_order_id:
        try:
            existing = await get_order(existing_order_id)
            if existing and existing.get("status") == "PENDING":
                await update_order_status(
                    existing_order_id,
                    "CANCELLED",
                    expected_statuses=("PENDING",),
                )
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
            await safe_edit_message_text(update.callback_query, msg)
        else:
            await update.effective_message.reply_text(msg)
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    if order.get("user_telegram_id") != telegram_id:
        msg = t("access_denied", lang)
        if is_callback and update.callback_query:
            await safe_edit_message_text(update.callback_query, msg)
        else:
            await update.effective_message.reply_text(msg)
        return ConversationHandler.END

    product = await get_product(order["product_id"])
    if not product:
        msg = t("product_not_found", lang)
        if is_callback and update.callback_query:
            await safe_edit_message_text(update.callback_query, msg)
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
        discount_label = {"fr": "💰 Prix unitaire (palier)", "en": "💰 Unit price (bulk)", "ar": "💰 Ø³Ø¹Ø± Ø§Ù„ÙˆØ­Ø¯Ø© (Ø¬Ù…Ù„Ø©)"}.get(lang, "💰 Prix unitaire (palier)")
        unit_price_line = f"{discount_label}: {format_price(unit_price)}\n"

    # Promo discount line
    promo_line = ""
    if has_promo:
        promo_discount = order.get("promo_discount", 0.0)
        promo_line = f"🎫 <b>Code Promo :</b> -{format_price(promo_discount)}\n"

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
        try:
            await safe_edit_message_text(update.callback_query, 
                summary,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception as exc:
            if "Message is not modified" not in str(exc):
                raise
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
        await safe_edit_message_text(query, t("access_denied", lang))
        return ConversationHandler.END

    # Store order_id in user_data so we know which order to apply it to
    context.user_data["promo_order_id"] = order_id

    await safe_edit_message_text(query, 
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
        
    from database.models import check_promo_usage
    can_use = await check_promo_usage(promo["id"], update.effective_user.id)
    if not can_use:
        await update.message.reply_text(
            t("promo_max_uses_reached", lang),
            parse_mode="HTML",
            reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
        )
        return WAITING_PROMO_CODE

    # Check applicable products
    from utils.promos import calculate_promo_price, parse_applicable_product_ids

    applicable_ids = parse_applicable_product_ids(promo.get("applicable_product_ids"))
    if applicable_ids:
        if order.get("product_id") not in applicable_ids:
            await update.message.reply_text(
                t("promo_product_invalid", lang),
                parse_mode="HTML",
                reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
            )
            return WAITING_PROMO_CODE
            
    # Check max quantity per order
    max_qty = promo.get("max_qty_per_order", 0)
    order_qty = order.get("quantity", 1)
    if max_qty > 0 and order_qty > max_qty:
        await update.message.reply_text(
            t("promo_qty_limit", lang).format(max_qty=max_qty),
            parse_mode="HTML",
            reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
        )
        return WAITING_PROMO_CODE

    # Calculate discount
    original_amount = order["amount_usd"]
    discount_type = promo.get("discount_type", "percent")
    discount_value = promo.get("discount_value", 0.0)
    if discount_type == "product_price" and len(applicable_ids) != 1:
        await update.message.reply_text(
            t("promo_product_invalid", lang),
            parse_mode="HTML",
            reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
        )
        return WAITING_PROMO_CODE

    try:
        discount, new_amount = calculate_promo_price(
            original_amount,
            order_qty,
            discount_type,
            discount_value,
        )
    except (TypeError, ValueError):
        await update.message.reply_text(
            t("promo_invalid", lang),
            parse_mode="HTML",
            reply_markup=back_keyboard(f"back_pay_method:{order_id}", lang),
        )
        return WAITING_PROMO_CODE

    # Update order with promo code info
    await update_order_status(
        order_id,
        "PENDING",
        expected_statuses=("PENDING",),
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
    """Handle an atomic wallet purchase."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return ConversationHandler.END

        amount = order["amount_usd"]
        product_id = order.get("product_id")

        # Verify order is still payable (prevent double-payment)
        if order.get("status") == "COMPLETED":
            await query.answer(t("payment_confirmed", lang), show_alert=True)
            return ConversationHandler.END
        elif order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            if order.get("status") == "PROCESSING":
                await query.answer(t("payment_processing", lang), show_alert=True)
                return ConversationHandler.END
            await safe_edit_message_text(query, 
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        if not await _ensure_supplier_stock_for_order(query, order, lang):
            return ConversationHandler.END

        from database.models import get_wallet_balance
        try:
            purchase = await purchase_order_with_wallet(order_id, telegram_id)
        except ValueError as exc:
            error_code = str(exc).split(":", 1)[0]
            balance = await get_wallet_balance(telegram_id)
            if error_code == "INSUFFICIENT_BALANCE":
                text = t("wallet_insufficient", lang) \
                    .replace("${balance}", format_price(balance)) \
                    .replace("${required}", format_price(amount))
            elif error_code in ("INSUFFICIENT_STOCK", "STOCK_CONFLICT"):
                text = t("delivery_failed", lang)
            elif error_code == "ORDER_NOT_PAYABLE":
                latest_order = await get_order(order_id)
                if latest_order and latest_order.get("status") == "COMPLETED":
                    await query.answer(t("payment_confirmed", lang), show_alert=True)
                    return ConversationHandler.END
                text = t("order_cancelled", lang)
            else:
                text = t("pay_error", lang)
            await safe_edit_message_text(query, 
                text,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        order = purchase["order"]
        amount = order["amount_usd"]
        product_id = order.get("product_id")
        new_balance = purchase["balance_after"]
        product = await get_product(product_id)
        if _is_activation_product(product):
            return await _prompt_activation_identifier(update, context, order_id, product, lang, "wallet")

        delivered = purchase["items"]
        if purchase.get("delivery_type") == "supplier_api":
            wallet_msg = t("wallet_paid", lang) \
                .replace("${amount}", format_price(amount)) \
                .replace("${balance}", format_price(new_balance))
            await safe_edit_message_text(query, 
                f"{wallet_msg}\n\n{t('supplier_delivery_processing', lang)}",
                parse_mode="HTML",
            )
            delivered = await deliver_order(order_id, product_id)
            if delivered:
                await update_order_status(
                    order_id,
                    "COMPLETED",
                    expected_statuses=("PAID_PENDING_DELIVERY",),
                    payment_method="wallet",
                )
            else:
                await safe_edit_message_text(query, 
                    t("supplier_paid_pending", lang).format(order_id=order_id),
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )
                try:
                    from bot import notify_admins
                    await notify_admins(
                        f"⚠️ <b>Supplier delivery pending</b>\n"
                        f"Order: #{order_id}\n"
                        f"Client: <code>{telegram_id}</code>\n"
                        f"Product: {escape_html((product or {}).get('name') or str(product_id))}\n"
                        "Check API Bot Management before retrying the supplier purchase."
                    )
                except Exception as notify_exc:
                    logger.warning("Could not notify admins about supplier order %s: %s", order_id, notify_exc)
                return ConversationHandler.END
        if delivered:
            warranty_days = product.get("warranty_days", 0) if product else 0

            wallet_msg = t("wallet_paid", lang) \
                .replace("${amount}", format_price(amount)) \
                .replace("${balance}", format_price(new_balance))

            await safe_edit_message_text(query, f"{wallet_msg}\n\n✅ Préparation de votre commande...", parse_mode="HTML")

            header = f"{wallet_msg}"
            conf_msg = get_confirmation_message(product, lang, order_id)
            footer = (
                f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                f"{t('save_info', lang)}\n\n"
                f"{conf_msg}"
            )
            await safe_send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang, order_id)

        await _notify_admins_sale(
            context,
            order_id,
            product_id,
            amount,
            payment_method="Wallet",
            user_id=telegram_id,
        )

        return ConversationHandler.END

    except Exception as exc:
        logger.error("pay_with_wallet: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("pay_error", lang))
        return ConversationHandler.END


async def pay_with_binance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_binance:{order_id}' callback — show Binance Pay instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via Binance which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return ConversationHandler.END

        if not await _ensure_supplier_stock_for_order(query, order, lang):
            return ConversationHandler.END

        await update_order_status(
            order_id,
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )

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

        await safe_edit_message_text(query, 
            f"{t('binance_title', lang)}\n\n"
            f"{t('binance_id_lbl', lang)}\n"
            f"<code>{uid_to_show}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
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
                context, chat_id, order_id, telegram_id, timeout_seconds=PAYMENT_TIMEOUT_SECONDS
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_ORDER_ID

    except Exception as exc:
        if "Message is not modified" in str(exc):
            return WAITING_ORDER_ID
        logger.error("pay_with_binance: %s", exc, exc_info=True)
        try:
            await safe_edit_message_text(query, t("pay_error", lang))
        except Exception:
            pass
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
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED", "PAID_PENDING_DELIVERY"):
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
            api_secret=api_secret_to_use,
            lang=lang
        )

        if result.get("verified"):
            # Anti-replay: check if transaction was already used
            tx = result.get("transaction", {})
            tx_id = str(tx.get("transactionId", "")) or str(tx.get("orderId", "")) or client_order_id
            if not await record_used_transaction(tx_id, order_id, update.effective_user.id, expected_amount):
                logger.warning("REPLAY ATTACK BLOCKED: User %s tried to reuse transaction %s for order %d",
                             update.effective_user.id, tx_id, order_id)
                await update.message.reply_text(
                    t("tx_already_used", lang),
                    reply_markup=main_menu_keyboard(lang),
                )
                return ConversationHandler.END

            # Cancel any pending timeout task for this order since it's paid
            task = _timeout_tasks.pop(order_id, None)
            if task and not task.done():
                task.cancel()
                
            # Reactivate order if it was cancelled by timeout but payment is confirmed
            if order_was_cancelled:
                await update_order_status(
                    order_id,
                    "PENDING",
                    expected_statuses=("CANCELLED",),
                    payment_method="binance",
                )
                logger.info("Order #%d reactivated: Binance payment confirmed after timeout", order_id)
            binance_tx_id = tx.get("transactionId", "")
            binance_order_id_val = tx.get("orderId", "")
            display_id = binance_order_id_val or binance_tx_id or client_order_id

            product = await get_product(product_id)
            if _is_activation_product(product):
                return await _prompt_activation_identifier(update, context, order_id, product, lang, "binance", display_id)

            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(
                    order_id,
                    "COMPLETED",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT", "PAID_PENDING_DELIVERY"),
                    payment_method="binance",
                    binance_order_id=display_id,
                )
                warranty_days = product.get("warranty_days", 0) if product else 0

                await update.message.reply_text(f"✅ {t('payment_confirmed', lang)}\n\nPréparation de votre commande...", parse_mode="HTML")

                header = f"{t('payment_confirmed', lang)}"
                conf_msg = get_confirmation_message(product, lang, order_id)
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{conf_msg}"
                )
                await safe_send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang, order_id)
            else:
                await update_order_status(
                    order_id,
                    "PAID_PENDING_DELIVERY",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT"),
                    payment_method="binance",
                    binance_order_id=display_id,
                )
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang).replace('{order_id}', str(order_id))}",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            await _notify_admins_sale(
                context,
                order_id,
                product_id,
                expected_amount,
                payment_method="Binance Pay",
                user_id=update.effective_user.id,
            )

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
                f"❌ {error_msg}\n\n"
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
            await safe_edit_message_text(query, t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return

        await safe_edit_message_text(query, 
            f"{t('check_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('send_order_id', lang)}",
            parse_mode="HTML",
            reply_markup=payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_payment: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("verify_error", lang))


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
            transitioned = await update_order_status(
                order_id,
                "CANCELLED",
                expected_statuses=("PENDING", "AWAITING_PAYMENT"),
            )
            if not transitioned:
                return
            lang = await get_user_lang(user_telegram_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=t("order_timeout", lang).format(id=order_id),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
    except Exception as exc:
        logger.error("Error in cancel_order_after_timeout: %s", exc, exc_info=True)


async def expire_nowpayments_order_after_timeout(
    bot,
    order_id: int,
    timeout_seconds: int = PAYMENT_TIMEOUT_SECONDS,
    delay_seconds: float | None = None,
):
    """Expire an unpaid provider checkout while preserving late IPN recovery."""
    await asyncio.sleep(timeout_seconds if delay_seconds is None else max(0, delay_seconds))
    try:
        from database.models import expire_stale_nowpayments_payments

        payment_ids = await expire_stale_nowpayments_payments(
            timeout_seconds=timeout_seconds,
            order_id=order_id,
        )
        for payment_id in payment_ids:
            await process_nowpayments_payment_notification(bot, payment_id)
    except Exception as exc:
        logger.error("Error expiring NOWPayments order #%s: %s", order_id, exc, exc_info=True)
    finally:
        current = asyncio.current_task()
        if _timeout_tasks.get(order_id) is current:
            _timeout_tasks.pop(order_id, None)


async def restore_nowpayments_timeout_tasks(bot) -> int:
    """Restore exact payment deadlines after a process restart."""
    from database.models import list_active_nowpayments_timeouts

    restored = 0
    for payment in await list_active_nowpayments_timeouts(
        timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
    ):
        order_id = int(payment["order_id"])
        previous_task = _timeout_tasks.pop(order_id, None)
        if previous_task and not previous_task.done():
            previous_task.cancel()
        _timeout_tasks[order_id] = asyncio.create_task(
            expire_nowpayments_order_after_timeout(
                bot,
                order_id,
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
                delay_seconds=float(payment.get("remaining_seconds") or 0),
            )
        )
        restored += 1
    return restored


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'cancel_order:{order_id}' callback â€” cancel the pending order."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)
        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to cancel order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return

        # Only allow cancelling PENDING or AWAITING_PAYMENT orders
        if order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            await safe_edit_message_text(query, 
                t("cannot_cancel", lang).format(status=order.get("status")),
                reply_markup=main_menu_keyboard(lang),
            )
            return

        # Cancel the background timeout task if it exists
        task = _timeout_tasks.pop(order_id, None)
        if task and not task.done():
            task.cancel()

        transitioned = await update_order_status(
            order_id,
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )
        if not transitioned:
            latest = await get_order(order_id)
            await safe_edit_message_text(query, 
                t("cannot_cancel", lang).format(status=(latest or {}).get("status", "?")),
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        context.user_data.pop("paying_order_id", None)
        context.user_data.pop("paying_amount", None)
        context.user_data.pop("paying_product_id", None)
        context.user_data.pop("pending_order_id", None)
        context.user_data.pop("pending_product_id", None)

        await safe_edit_message_text(query, 
            t("order_cancelled", lang),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception as exc:
        logger.error("cancel_order: %s", exc, exc_info=True)
        await safe_edit_message_text(query, 
            t("cancel_error", lang),
            reply_markup=main_menu_keyboard(lang),
        )

    return ConversationHandler.END


async def _start_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End payment state; the global /start handler renders the menu once."""
    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_amount", None)
    context.user_data.pop("paying_product_id", None)

    return ConversationHandler.END


# ── Admin notification helpers ──

def _sale_customer_label(user: dict | None, user_id: int | None) -> str:
    resolved_id = int(user_id or (user or {}).get("telegram_id") or 0)
    first_name = str((user or {}).get("first_name") or "").strip()
    username = str((user or {}).get("username") or "").strip().lstrip("@")
    display_name = first_name or (f"@{username}" if username else str(resolved_id or "?"))
    if username and first_name:
        display_name = f"{display_name} (@{username})"
    if resolved_id:
        return f"{escape_html(display_name)} (<code>{resolved_id}</code>)"
    return escape_html(display_name)


async def _notify_admins_sale_with_bot(
    bot,
    order_id,
    product_id,
    amount,
    *,
    payment_method: str,
    user_id: int | None = None,
):
    details = None
    try:
        details = await get_sale_notification_details(order_id)
    except Exception as exc:
        logger.warning("Could not load sale notification details for order %s: %s", order_id, exc)

    details = details or {}
    resolved_user_id = int(user_id or details.get("telegram_id") or 0)
    prod_name = escape_html(str(details.get("product_name") or "?"))
    quantity = max(1, int(details.get("quantity") or 1))
    customer = _sale_customer_label(details, resolved_user_id)
    text = (
        "🔔 <b>Nouvelle vente !</b>\n"
        f"👤 Client : {customer}\n"
        f"💳 Paiement : {escape_html(payment_method)}\n"
        f"📦 Produit : {prod_name} x{quantity}\n"
        f"💰 Montant : {format_price(amount)}\n"
        f"🔖 Commande : #{order_id}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _notify_admins_sale(
    context,
    order_id,
    product_id,
    amount,
    *,
    payment_method: str = "Paiement direct",
    user_id: int | None = None,
):
    await _notify_admins_sale_with_bot(
        context.bot,
        order_id,
        product_id,
        amount,
        payment_method=payment_method,
        user_id=user_id,
    )


async def _notify_admins_low_stock(context, product_id):
    product = await get_product(product_id)
    prod_name = escape_html(product["name"]) if product else f"ID {product_id}"
    stock = await get_stock_count(product_id)
    text = (
        "⚠️ <b>Stock faible !</b>\n"
        f"📦 {prod_name}\n"
        f"📉 Restant : {stock}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _notify_admins_manual_check(context, order_id, client_order_id):
    text = (
        "🔔 <b>Vérification manuelle requise</b>\n"
        f"🔖 Commande : #{order_id}\n"
        f"📝 Order ID soumis : <code>{client_order_id}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


async def _render_nowpayments_checkout(
    query,
    payment: dict,
    lang: str,
    status_text: str | None = None,
    *,
    order_amount: float | None = None,
):
    from services.nowpayments import calculate_customer_pay_amount

    payment_id = str(payment.get("payment_id") or "")
    address = str(payment.get("pay_address") or "")
    customer_pay_amount = calculate_customer_pay_amount(
        payment.get("pay_amount"),
        provider_price_amount=payment.get("price_amount"),
        original_price_amount=(
            payment.get("price_amount") if order_amount is None else order_amount
        ),
    )
    amount = _format_crypto_amount(customer_pay_amount)
    text = (
        f"{t('nowpayments_title', lang)}\n\n"
        f"{t('nowpayments_address', lang)}\n"
        f"<code>{escape_html(address)}</code>\n\n"
        f"{t('nowpayments_amount', lang).format(amount=amount)}\n"
        f"{t('nowpayments_network', lang)}\n"
        f"{t('nowpayments_reference', lang).format(payment_id=escape_html(payment_id))}\n\n"
        f"{t('nowpayments_instructions', lang)}\n\n"
        f"{t('nowpayments_fee_warning', lang)}\n\n"
        f"{status_text or t('nowpayments_waiting', lang)}"
    )
    await safe_edit_message_text(query, 
        text,
        parse_mode="HTML",
        reply_markup=nowpayments_payment_keyboard(int(payment["order_id"]), amount, lang),
    )


async def process_nowpayments_payment_notification(
    bot,
    payment_id: str | int,
    *,
    finalized_result: dict | None = None,
    force_notification: bool = False,
) -> dict:
    """Finalize and notify a NOWPayments status update without requiring a Telegram Update."""
    from database.models import (
        claim_nowpayments_notification,
        finalize_nowpayments_payment,
        get_product,
        get_user_lang,
        mark_nowpayments_notified,
        release_nowpayments_notification,
        update_order_status,
    )

    result = finalized_result or await finalize_nowpayments_payment(payment_id)
    action = result.get("action")
    payment = result.get("payment") or {}
    if action == "paid_pending_delivery" and payment.get("product_id"):
        supplier_product = await get_product(int(payment["product_id"]))
        if (supplier_product or {}).get("delivery_type") == "supplier_api":
            delivered = await deliver_order(int(payment["order_id"]), int(payment["product_id"]))
            if delivered:
                await update_order_status(
                    int(payment["order_id"]),
                    "COMPLETED",
                    expected_statuses=("PAID_PENDING_DELIVERY",),
                    payment_method="nowpayments_bep20",
                    binance_order_id=str(payment_id),
                )
                result["action"] = action = "completed"
                result["items"] = delivered
    if not payment or (payment.get("notified_at") and not force_notification):
        return result

    notifiable_actions = {
        "completed", "activation", "paid_pending_delivery", "review_required",
        "partially_paid", "expired", "failed", "refunded",
    }
    if action not in notifiable_actions:
        return result
    if not await claim_nowpayments_notification(payment_id):
        return result

    user_id = int(payment.get("user_telegram_id") or 0)
    order_id = int(payment.get("order_id") or 0)
    product_id = int(payment.get("product_id") or 0)
    lang = await get_user_lang(user_id) if user_id else "en"
    notified = False

    if action == "completed" and user_id:
        product = await get_product(product_id)
        warranty_days = int((product or {}).get("warranty_days") or 0)
        footer = (
            f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
            f"{t('save_info', lang)}\n\n"
            f"{get_confirmation_message(product, lang, order_id)}"
        )
        notified = await safe_send_delivery_messages(
            bot,
            user_id,
            t("payment_confirmed", lang),
            result.get("items") or [],
            footer,
            lang,
            order_id,
        )
    elif action == "activation" and user_id:
        product = await get_product(product_id)
        product_name = escape_html((product or {}).get("name") or f"#{order_id}")
        text = t("activation_prompt", lang).format(
            payment_confirmed=t("payment_confirmed", lang),
            product=product_name,
        )
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(t("btn_enter_activation", lang), callback_data=f"activation_info:{order_id}")
        ]])
        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)
        notified = True
    elif action == "paid_pending_delivery" and user_id:
        await bot.send_message(
            user_id,
            t("nowpayments_paid_pending", lang).format(order_id=order_id),
            reply_markup=main_menu_keyboard(lang),
        )
        notified = True
    elif action == "review_required":
        if user_id:
            await bot.send_message(user_id, t("nowpayments_review", lang), reply_markup=main_menu_keyboard(lang))
        error = escape_html(str(payment.get("processing_error") or "Payment validation mismatch"))
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"<b>NOWPayments security review</b>\nOrder: #{order_id}\nPayment: <code>{escape_html(str(payment_id))}</code>\nReason: {error}",
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Could not notify admin %s about NOWPayments review: %s", admin_id, exc)
        notified = True
    elif action == "partially_paid" and user_id:
        await bot.send_message(user_id, t("nowpayments_partial", lang))
        notified = True
    elif action in ("expired", "failed", "refunded") and user_id:
        await update_order_status(
            order_id,
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )
        await bot.send_message(user_id, t("nowpayments_expired", lang), reply_markup=main_menu_keyboard(lang))
        notified = True

    if notified:
        await mark_nowpayments_notified(payment_id)
        if action in ("completed", "activation", "paid_pending_delivery"):
            await _notify_admins_sale_with_bot(
                bot,
                order_id,
                product_id,
                float(payment.get("actually_paid") or payment.get("price_amount") or 0),
                payment_method="BEP20 (NOWPayments)",
                user_id=user_id,
            )
    else:
        await release_nowpayments_notification(payment_id)
    return result


async def pay_with_nowpayments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    order_id = int(query.data.split(":")[1])
    lock = _nowpayments_locks[order_id % len(_nowpayments_locks)]

    async with lock:
        order = await get_order(order_id)
        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return ConversationHandler.END
        if int(order.get("user_telegram_id") or 0) != update.effective_user.id:
            await safe_edit_message_text(query, t("access_denied", lang))
            return ConversationHandler.END
        if order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            if order.get("status") == "COMPLETED":
                await safe_edit_message_text(query, t("payment_confirmed", lang), reply_markup=main_menu_keyboard(lang))
            else:
                await safe_edit_message_text(query, t("order_cancelled", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END

        if not await _ensure_supplier_stock_for_order(query, order, lang):
            return ConversationHandler.END

        callback_url = _nowpayments_callback_url()
        if not callback_url.startswith("https://"):
            logger.error("NOWPayments callback URL is missing or not HTTPS")
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END

        from database.models import (
            attach_nowpayments_payment,
            mark_nowpayments_creation_failed,
            prepare_nowpayments_attempt,
        )
        from services.nowpayments import (
            NowPaymentsError,
            create_payment,
            get_minimum_amount,
            is_nowpayments_configured,
        )

        if not is_nowpayments_configured():
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END

        provider_price = round(float(order["amount_usd"]), 2)

        try:
            minimum = await get_minimum_amount()
            minimum_usd = float(minimum.get("fiat_equivalent") or minimum.get("min_amount") or 0)
            if minimum_usd > 0 and provider_price + 0.000001 < minimum_usd:
                await safe_edit_message_text(query, 
                    t("nowpayments_below_minimum", lang).format(minimum=_format_crypto_amount(minimum_usd)),
                    reply_markup=main_menu_keyboard(lang),
                )
                return ConversationHandler.END
        except NowPaymentsError as exc:
            logger.warning("Could not read NOWPayments minimum amount: %s", exc)
            await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
            return ConversationHandler.END
        except (ValueError, TypeError) as exc:
            logger.warning("Invalid NOWPayments minimum response: %s", exc)

        attempt = await prepare_nowpayments_attempt(order_id, provider_price)
        if not attempt.get("created"):
            if attempt.get("payment_id"):
                await _render_nowpayments_checkout(
                    query, attempt, lang, order_amount=order["amount_usd"]
                )
                return WAITING_NOWPAYMENTS
            await safe_edit_message_text(query, 
                t("nowpayments_creation_unknown", lang).format(order_id=order_id),
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        await update_order_status(
            order_id,
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
            payment_method="nowpayments_bep20",
        )
        product = await get_product(order.get("product_id"))
        description = f"{(product or {}).get('name') or 'Product'} x{int(order.get('quantity') or 1)}"

        try:
            provider_payment = await create_payment(
                price_amount=provider_price,
                order_id=order_id,
                order_description=description,
                callback_url=callback_url,
            )
            payment = await attach_nowpayments_payment(attempt["request_key"], provider_payment)
        except (NowPaymentsError, ValueError, TypeError) as exc:
            provider_status = exc.status_code if isinstance(exc, NowPaymentsError) else None
            logger.warning(
                "NOWPayments creation failed for order %s (HTTP %s): %s",
                order_id,
                provider_status or "n/a",
                exc,
            )
            await mark_nowpayments_creation_failed(
                attempt["request_key"],
                uncertain=bool(isinstance(exc, NowPaymentsError) and exc.retryable),
                error=str(exc),
            )
            text = (
                t("nowpayments_creation_unknown", lang).format(order_id=order_id)
                if isinstance(exc, NowPaymentsError) and exc.retryable
                else t("nowpayments_unavailable", lang)
            )
            await safe_edit_message_text(query, text, reply_markup=main_menu_keyboard(lang))
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"NOWPayments creation failed for order #{order_id}. HTTP: {provider_status or 'n/a'}. Check Railway logs and NOWPayments settings.",
                    )
                except Exception:
                    pass
            return ConversationHandler.END

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_product_id"] = order.get("product_id")
        await _render_nowpayments_checkout(
            query, payment, lang, order_amount=order["amount_usd"]
        )
        previous_task = _timeout_tasks.pop(order_id, None)
        if previous_task and not previous_task.done():
            previous_task.cancel()
        _timeout_tasks[order_id] = asyncio.create_task(
            expire_nowpayments_order_after_timeout(
                context.bot,
                order_id,
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
        )
        return WAITING_NOWPAYMENTS


async def check_nowpayments_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await get_user_lang(update.effective_user.id)
    await query.answer(t("nowpayments_checking_short", lang))
    order_id = int(query.data.split(":")[1])
    order = await get_order(order_id)
    if not order or int(order.get("user_telegram_id") or 0) != update.effective_user.id:
        await safe_edit_message_text(query, t("access_denied", lang))
        return ConversationHandler.END

    from database.models import get_nowpayments_payment_for_order, save_nowpayments_update
    from services.nowpayments import NowPaymentsError, get_payment_status

    payment = await get_nowpayments_payment_for_order(order_id)
    if not payment or not payment.get("payment_id"):
        await safe_edit_message_text(query, t("nowpayments_unavailable", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END
    await _render_nowpayments_checkout(
        query,
        payment,
        lang,
        t("nowpayments_checking", lang),
        order_amount=order["amount_usd"],
    )
    try:
        provider_payment = await get_payment_status(payment["payment_id"])
        payment = await save_nowpayments_update(provider_payment) or payment
        result = await process_nowpayments_payment_notification(context.bot, payment["payment_id"])
    except (NowPaymentsError, ValueError, TypeError):
        await _render_nowpayments_checkout(
            query,
            payment,
            lang,
            t("nowpayments_unavailable", lang),
            order_amount=order["amount_usd"],
        )
        return WAITING_NOWPAYMENTS

    action = result.get("action")
    if action in ("completed", "activation", "paid_pending_delivery"):
        await safe_edit_message_text(query, t("payment_confirmed", lang), parse_mode="HTML", reply_markup=main_menu_keyboard(lang))
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
    await _render_nowpayments_checkout(
        query, payment, lang, status_text, order_amount=order["amount_usd"]
    )
    return WAITING_NOWPAYMENTS


async def start_activation_identifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    order_id = int(query.data.split(":")[1])
    order = await get_order(order_id)
    if not order or int(order.get("user_telegram_id") or 0) != update.effective_user.id:
        await safe_edit_message_text(query, t("access_denied", lang))
        return ConversationHandler.END
    if order.get("status") != "AWAITING_ACTIVATION_INFO":
        await safe_edit_message_text(query, t("order_cancelled", lang), reply_markup=main_menu_keyboard(lang))
        return ConversationHandler.END
    product = await get_product(order.get("product_id"))
    context.user_data["activation_order_id"] = order_id
    text = t("activation_prompt", lang).format(
        payment_confirmed=t("payment_confirmed", lang),
        product=escape_html((product or {}).get("name") or f"#{order_id}"),
    )
    await safe_edit_message_text(query, text, parse_mode="HTML")
    return WAITING_ACTIVATION_IDENTIFIER


async def pay_with_bep20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'pay_bep20:{order_id}' callback â€” show BEP20 deposit instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via BEP20 which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return ConversationHandler.END

        if not await _ensure_supplier_stock_for_order(query, order, lang):
            return ConversationHandler.END

        from database.models import get_setting
        bep20_address = await get_setting("bep20_address")
        if not bep20_address:
            await safe_edit_message_text(query, "❌ BEP20 USDT payment is not configured by admin.")
            return ConversationHandler.END

        await update_order_status(
            order_id,
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_amount"] = order["amount_usd"]
        context.user_data["paying_product_id"] = order.get("product_id")

        from utils.keyboards import payment_check_keyboard
        
        await safe_edit_message_text(query, 
            f"{t('bep20_title', lang)}\n\n"
            f"{t('bep20_address_lbl', lang)}\n"
            f"<code>{bep20_address}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('bep20_instructions', lang)}\n\n"
            f"👉 <b>{t('bep20_send_tx_hash', lang)}</b>",
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
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_BEP20_TX_HASH

    except Exception as exc:
        if "Message is not modified" in str(exc):
            return WAITING_BEP20_TX_HASH
        logger.error("pay_with_bep20: %s", exc, exc_info=True)
        try:
            await safe_edit_message_text(query, t("pay_error", lang))
        except Exception:
            pass
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
            await safe_edit_message_text(query, t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check BEP20 payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return

        from utils.keyboards import bep20_payment_check_keyboard
        
        await safe_edit_message_text(query, 
            f"{t('bep20_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('bep20_send_tx_hash', lang)}",
            parse_mode="HTML",
            reply_markup=bep20_payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_bep20_payment: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("verify_error", lang))


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
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED", "PAID_PENDING_DELIVERY"):
            await update.message.reply_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        from database.models import record_used_bep20_transaction, get_setting

        bep20_address = await get_setting("bep20_address")
        if not bep20_address:
            await update.message.reply_text("❌ BEP20 payment address is not configured by the administrator.")
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
            
            result = await verify_internal_transfer(tx_hash, expected_amount, api_key=api_key, api_secret=api_secret, lang=lang)

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
                await update_order_status(
                    order_id,
                    "PENDING",
                    expected_statuses=("CANCELLED",),
                    payment_method="bep20",
                )
                logger.info("Order #%d reactivated: BEP20 payment confirmed on-chain after timeout", order_id)

            product = await get_product(product_id)
            if _is_activation_product(product):
                return await _prompt_activation_identifier(update, context, order_id, product, lang, "bep20", tx_hash)

            # Deliver order
            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(
                    order_id,
                    "COMPLETED",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT", "PAID_PENDING_DELIVERY"),
                    payment_method="bep20",
                    binance_order_id=tx_hash,
                )
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
                await update_order_status(
                    order_id,
                    "PAID_PENDING_DELIVERY",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT"),
                    payment_method="bep20",
                    binance_order_id=tx_hash,
                )
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang).replace('{order_id}', str(order_id))}",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            # Notify admins of BSC BEP20 sale
            await _notify_admins_sale(
                context,
                order_id,
                product_id,
                expected_amount,
                payment_method="BEP20",
                user_id=update.effective_user.id,
            )
            return ConversationHandler.END

        else:
            error_msg = result.get("error", t("payment_not_detected", lang))
            await update.message.reply_text(
                f"{t('payment_not_detected', lang)}\n\n"
                f"⚠️ {error_msg}\n\n"
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
    """Handle 'pay_trc20:{order_id}' callback — show TRC20 deposit instructions."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to pay order #%s via TRC20 which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return ConversationHandler.END

        if not await _ensure_supplier_stock_for_order(query, order, lang):
            return ConversationHandler.END

        from database.models import get_setting
        trc20_address = await get_setting("trc20_address")
        if not trc20_address:
            await safe_edit_message_text(query, "⚠️ TRC20 USDT payment is not configured by admin.")
            return ConversationHandler.END

        await update_order_status(
            order_id,
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )

        context.user_data["paying_order_id"] = order_id
        context.user_data["paying_amount"] = order["amount_usd"]
        context.user_data["paying_product_id"] = order.get("product_id")

        from utils.keyboards import payment_check_keyboard
        
        await safe_edit_message_text(query, 
            f"{t('trc20_title', lang)}\n\n"
            f"{t('trc20_address_lbl', lang)}\n"
            f"<code>{trc20_address}</code>\n\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('trc20_instructions', lang)}\n\n"
            f"📥 <b>{t('trc20_send_tx_hash', lang)}</b>",
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
                timeout_seconds=PAYMENT_TIMEOUT_SECONDS,
            )
        )
        _timeout_tasks[order_id] = task

        return WAITING_TRC20_TX_HASH

    except Exception as exc:
        if "Message is not modified" in str(exc):
            return WAITING_TRC20_TX_HASH
        logger.error("pay_with_trc20: %s", exc, exc_info=True)
        try:
            await safe_edit_message_text(query, t("pay_error", lang))
        except Exception:
            pass
        return ConversationHandler.END


async def check_trc20_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'check_trc20:{order_id}' callback — prompt user to send Tx Hash."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await safe_edit_message_text(query, t("product_not_found", lang))
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to check TRC20 payment of order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await safe_edit_message_text(query, t("access_denied", lang))
            return

        from utils.keyboards import trc20_payment_check_keyboard
        
        await safe_edit_message_text(query, 
            f"{t('trc20_title', lang)}\n\n"
            f"{t('order_lbl', lang)} #{order_id}\n"
            f"{t('amount_lbl', lang)} {format_price(order['amount_usd'])}\n\n"
            f"{t('trc20_send_tx_hash', lang)}",
            parse_mode="HTML",
            reply_markup=trc20_payment_check_keyboard(order_id, lang),
        )
    except Exception as exc:
        logger.error("check_trc20_payment: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("verify_error", lang))


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

    # Validation: on-chain TRON hashes are 64 hex characters.
    # Off-chain Binance transfers are usually digits, contain "off-chain", or are shorter.
    is_off_chain = tx_hash.isdigit() or "off-chain" in tx_hash.lower() or len(tx_hash) < 64

    tx_hash_clean = tx_hash
    if not is_off_chain:
        if tx_hash_clean.lower().startswith("0x"):
            tx_hash_clean = tx_hash_clean[2:]
        import re
        if not re.match(r"^[a-fA-F0-9]{64}$", tx_hash_clean):
            await update.message.reply_text(t("trc20_invalid_tx_hash", lang))
            return WAITING_TRC20_TX_HASH
            
    is_on_chain = not is_off_chain

    # Track if order was cancelled by timeout (we still verify on-chain)
    order_was_cancelled = db_order.get("status") == "CANCELLED"

    try:
        await update.message.reply_text(t("verifying", lang))

        if db_order.get("status") == "COMPLETED":
            await update.message.reply_text(t("payment_confirmed", lang))
            return ConversationHandler.END
        elif db_order.get("status") not in ("PENDING", "AWAITING_PAYMENT", "CANCELLED", "PAID_PENDING_DELIVERY"):
            await update.message.reply_text(
                t("order_cancelled", lang),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(lang),
            )
            return ConversationHandler.END

        from database.models import record_used_trc20_transaction, get_setting

        trc20_address = await get_setting("trc20_address")
        if not trc20_address:
            await update.message.reply_text("TRC20 payment address is not configured by the administrator.")
            return ConversationHandler.END

        from services.trc20_verify import verify_trc20_payment
        from services.binance_verify import verify_internal_transfer

        result = {"verified": False, "error": "Type de transaction non pris en charge."}

        if is_on_chain:
            # On-chain verification
            result = await verify_trc20_payment(tx_hash_clean, expected_amount, trc20_address)
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
            
            result = await verify_internal_transfer(tx_hash_clean, expected_amount, api_key=api_key, api_secret=api_secret, lang=lang)

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
                await update_order_status(
                    order_id,
                    "PENDING",
                    expected_statuses=("CANCELLED",),
                    payment_method="trc20",
                )
                logger.info("Order #%d reactivated: TRC20 payment confirmed on-chain after timeout", order_id)

            product = await get_product(product_id)
            if _is_activation_product(product):
                return await _prompt_activation_identifier(update, context, order_id, product, lang, "trc20", tx_hash_clean)

            delivered = await deliver_order(order_id, product_id)

            if delivered:
                await update_order_status(
                    order_id,
                    "COMPLETED",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT", "PAID_PENDING_DELIVERY"),
                    payment_method="trc20",
                    binance_order_id=tx_hash_clean,
                )
                warranty_days = product.get("warranty_days", 0) if product else 0
                await update.message.reply_text(f"✅ {t('payment_confirmed', lang)}\n\nPréparation de votre commande...", parse_mode="HTML")
                header = f"{t('payment_confirmed', lang)}"
                conf_msg = get_confirmation_message(product, lang, order_id)
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{conf_msg}"
                )
                await safe_send_delivery_messages(context.bot, update.effective_user.id, header, delivered, footer, lang, order_id)
            else:
                await update_order_status(
                    order_id,
                    "PAID_PENDING_DELIVERY",
                    expected_statuses=("PENDING", "AWAITING_PAYMENT"),
                    payment_method="trc20",
                    binance_order_id=tx_hash_clean,
                )
                await update.message.reply_text(
                    f"{t('payment_confirmed', lang)}\n\n"
                    f"{t('delivery_error', lang).replace('{order_id}', str(order_id))}",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(lang),
                )

            try:
                from bot import notify_admins
                product = await get_product(product_id)
                pname = product["name"] if product else "?"
                await notify_admins(
                    f"💸 <b>TRC20 Sale!</b>\n"
                    f"👤 {escape_html(update.effective_user.first_name)}\n"
                    f"📦 {pname} x{db_order.get('quantity', 1)}\n"
                    f"💰 {format_price(expected_amount)}"
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
            CallbackQueryHandler(pay_with_nowpayments, pattern=r"^pay_nowpayments:"),
            CallbackQueryHandler(check_nowpayments_payment, pattern=r"^check_nowpayments:"),
            CallbackQueryHandler(start_activation_identifier, pattern=r"^activation_info:"),
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
                CallbackQueryHandler(pay_with_nowpayments, pattern=r"^pay_nowpayments:"),
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
            WAITING_NOWPAYMENTS: [
                CallbackQueryHandler(check_nowpayments_payment, pattern=r"^check_nowpayments:"),
                CallbackQueryHandler(start_activation_identifier, pattern=r"^activation_info:"),
            ],
            WAITING_ACTIVATION_IDENTIFIER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_activation_identifier),
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

        file_content = _build_txt_delivery(items)
        file_bytes = io.BytesIO(file_content.encode('utf-8'))
        file_bytes.name = f"Order_{order_id}_accounts.txt"
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_bytes,
            caption=f"📁 Order #{order_id} Accounts",
        )
    except Exception as exc:
        logger.error("download_txt_delivery error: %s", exc, exc_info=True)
        await query.answer("Error generating file.", show_alert=True)
