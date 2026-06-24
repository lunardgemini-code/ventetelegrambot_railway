"""
History handler — paginated order history + order detail with account data re-delivery.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_order,
    get_product,
    get_user_lang,
    get_user_order_count,
    get_user_orders,
)
from utils.helpers import format_date, format_price, escape_html
from utils.keyboards import back_keyboard, history_keyboard
from utils.locales import t

logger = logging.getLogger(__name__)

ORDERS_PER_PAGE = 5


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'menu_history' / 'hist_page:{page}' callback — show order history."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    try:
        page = 0
        if "hist_page:" in query.data:
            page = max(0, int(query.data.split(":")[1]))

        total = await get_user_order_count(telegram_id)
        total_pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
        offset = page * ORDERS_PER_PAGE

        orders = await get_user_orders(telegram_id, limit=ORDERS_PER_PAGE, offset=offset)

        if not orders:
            await query.edit_message_text(
                f"{t('history_title', lang)}\n\n{t('no_orders', lang)}",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_main", lang),
            )
            return

        text = f"{t('history_title', lang)}\n\n"
        for o in orders:
            product = await get_product(o.get("product_id"))
            pname = product["name"] if product else "?"
            pemoji = product["emoji"] if product else "📦"
            status_key = f"s_{o.get('status', 'PENDING').lower()}"
            status = t(status_key, lang)
            order_no = o.get("merchant_trade_no", "")
            text += f"📦 #{o['id']} ({order_no}) — {pemoji} {pname}\n   {format_price(o['amount_usd'])} — {status}\n\n"

        text += f"📄 {page + 1}/{total_pages}"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=history_keyboard(orders, page, total_pages, lang),
        )
    except Exception as exc:
        logger.error("show_history: %s", exc, exc_info=True)
        await query.edit_message_text(t("error_generic", lang))


async def show_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'order:{id}' callback — show full order details + account data."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)

        if not order:
            await query.edit_message_text(
                t("product_not_found", lang),
                reply_markup=back_keyboard("menu_history", lang),
            )
            return

        telegram_id = update.effective_user.id
        if order.get("user_telegram_id") != telegram_id:
            logger.warning("User %s tried to view order #%s which belongs to %s", telegram_id, order_id, order.get("user_telegram_id"))
            await query.edit_message_text(
                "❌ Access Denied: This order does not belong to you.",
                reply_markup=back_keyboard("menu_history", lang),
            )
            return

        product = await get_product(order.get("product_id"))
        prod_name = product["name"] if product else "?"
        prod_emoji = product["emoji"] if product else "📦"
        warranty_days = product.get("warranty_days", 0) if product else 0

        status_key = f"s_{order.get('status', 'PENDING').lower()}"
        status = t(status_key, lang)

        order_no = order.get("merchant_trade_no", "—")

        text = (
            f"{t('order_detail', lang).format(id=order_id)}\n\n"
            f"🔢 N°: <code>{order_no}</code>\n"
            f"{t('product_lbl', lang)} {prod_emoji} {prod_name}\n"
            f"{t('quantity_lbl', lang).format(qty=order.get('quantity', 1))}\n"
            f"{t('total_lbl', lang)} {format_price(order['amount_usd'])}\n"
            f"{t('status_lbl', lang)} {status}\n"
            f"{t('date_lbl', lang)} {format_date(order.get('created_at'))}\n"
        )

        if warranty_days:
            text += f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"

        # Show account data if order is completed
        if order.get("status") == "COMPLETED":
            from database.models import get_stock_items_for_order
            items = await get_stock_items_for_order(order_id)
            if items:
                text += f"\n{'━' * 20}\n"
                text += f"{t('your_account', lang)}\n"
                for item in items:
                    text += f"🔑 <code>{escape_html(item['account_data'])}</code>\n"
                text += f"\n{t('save_info', lang)}"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_keyboard("menu_history", lang),
        )
    except Exception as exc:
        logger.error("show_order_detail: %s", exc, exc_info=True)
        await query.edit_message_text(t("error_generic", lang))
