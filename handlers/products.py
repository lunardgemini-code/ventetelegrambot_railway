"""
Product browsing handlers — direct product list (no categories), product detail.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_all_products,
    get_product,
    get_stock_count,
    get_user_lang,
    get_all_stock_counts,
)
from utils.helpers import format_price, escape_html
from utils.keyboards import (
    back_keyboard,
    product_detail_keyboard,
    products_keyboard,
)
from utils.locales import t

logger = logging.getLogger(__name__)


async def show_products_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'menu_buy' / 'back_products' / 'refresh_prods' / 'cat:{id}' — list products directly."""
    lang = await get_user_lang(update.effective_user.id)
    query = update.callback_query

    category_id = None
    if query and query.data.startswith("cat:"):
        try:
            category_id = int(query.data.split(":")[1])
        except (ValueError, IndexError):
            pass

    try:
        if category_id is not None:
            from database.models import get_products_by_category
            products = await get_products_by_category(category_id)
        else:
            products = await get_all_products()
            # Only show active products
            products = [p for p in products if p.get("is_active", 1)]

        all_stocks = await get_all_stock_counts()
        stock_counts = {p["id"]: all_stocks.get(p["id"], 0) for p in products}

        if not products:
            text = t("no_categories", lang)
            if update.callback_query:
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass
                await update.callback_query.edit_message_text(
                    text, reply_markup=back_keyboard("back_main", lang)
                )
            else:
                await update.message.reply_text(text, reply_markup=back_keyboard("back_main", lang))
            return

        text = t("categories_title", lang)  # reuse "choose" title
        markup = products_keyboard(products, stock_counts, lang)

        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            try:
                await update.callback_query.edit_message_text(
                    text, parse_mode="HTML", reply_markup=markup
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    # Fallback for photo messages or other edit failures
                    try:
                        await update.callback_query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_message(
                        chat_id=update.callback_query.message.chat_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
        else:
            await update.message.reply_text(
                text, parse_mode="HTML", reply_markup=markup
            )
    except Exception as exc:
        logger.error("show_products_list: %s", exc, exc_info=True)
        if update.callback_query:
            await update.callback_query.edit_message_text(t("error_generic", lang))
        else:
            await update.message.reply_text(t("error_generic", lang))


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'prod:{id}' callback — show product details."""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    lang = await get_user_lang(update.effective_user.id)

    try:
        product_id = int(query.data.split(":")[1])
        from database.models import get_product_full_details
        product, stock, tiers, sold_count = await get_product_full_details(product_id)

        if not product:
            await query.edit_message_text(
                t("product_not_found", lang),
                reply_markup=back_keyboard("back_products", lang),
            )
            return

        p_emoji = product["emoji"]
        if product.get("custom_emoji_id"):
            p_emoji = f'<tg-emoji emoji-id="{product["custom_emoji_id"]}">{p_emoji}</tg-emoji>'

        text = t("product_detail", lang).format(
            emoji=p_emoji,
            name=escape_html(product["name"]),
            description=escape_html(product.get("description", "N/A") or "N/A"),
            price=format_price(product["price_usd"]),
            warranty=product.get("warranty_days", 0),
            stock=stock,
            sold=sold_count,
        )

        # Append tier pricing if available
        if tiers:
            tier_lines = []
            for tier in tiers:
                tier_lines.append(
                    f"  📦 {tier['min_qty']}–{tier['max_qty']} → {format_price(tier['price_usd'])}/u"
                )
            tiers_label = {"fr": "💰 <b>Tarifs par quantité :</b>", "en": "💰 <b>Bulk pricing:</b>", "ar": "💰 <b>:تسعير بالجملة</b>"}.get(lang, "💰 <b>Tarifs par quantité :</b>")
            text += f"\n\n{tiers_label}\n" + "\n".join(tier_lines)

        markup = product_detail_keyboard(product_id, lang)
        image_url = product.get("image_url")

        if image_url:
            # Auto-fix common imgur links (https://imgur.com/RYDsqu1 -> https://i.imgur.com/RYDsqu1.png)
            if "imgur.com" in image_url and "i.imgur.com" not in image_url:
                image_url = image_url.replace("imgur.com", "i.imgur.com") + ".png"

            try:
                await query.message.delete()
            except Exception:
                pass
            
            try:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=image_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception as e:
                logger.warning(f"Failed to send photo for product {product_id} with url {image_url}: {e}")
                # Fallback to text message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
        else:
            try:
                await query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    # Fallback if editing fails (e.g., coming from a photo message)
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
    except Exception as exc:
        logger.error("show_product_detail: %s", exc, exc_info=True)
        await query.edit_message_text(t("error_generic", lang))


async def refresh_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'refresh_prods' callback — reload product list."""
    return await show_products_list(update, context)
