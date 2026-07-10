"""
Product browsing handlers — direct product list (no categories), product detail.
"""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.models import (
    get_all_products,
    get_product,
    get_stock_count,
    get_user_lang,
    get_all_stock_counts,
    record_product_view,
)
from utils.helpers import format_price, escape_html, safe_format
from utils.keyboards import (
    back_keyboard,
    product_detail_keyboard,
    products_keyboard,
)
from utils.locales import t

logger = logging.getLogger(__name__)

_ACTIVATION_STOCK_LABEL = {
    "fr": "Activation manuelle",
    "en": "Manual activation",
    "ar": "تفعيل يدوي",
    "zh": "人工激活",
    "vi": "Kích hoạt thủ công",
    "ru": "Ручная активация",
}

_TIERS_LABEL = {
    "fr": "💰 <b>Tarifs par quantité :</b>",
    "en": "💰 <b>Bulk pricing:</b>",
    "ar": "💰 <b>تسعير بالجملة:</b>",
    "zh": "💰 <b>批量价格：</b>",
    "vi": "💰 <b>Giá theo số lượng:</b>",
    "ru": "💰 <b>Оптовые цены:</b>",
}


def _build_product_detail_text(product: dict, stock: int, tiers: list, sold_count: int, lang: str, use_custom_emoji: bool = True) -> str:
    """Build HTML product detail text. use_custom_emoji=False avoids <tg-emoji> (often rejected)."""
    p_emoji = product.get("emoji") or "📦"
    custom_id = (product.get("custom_emoji_id") or "").strip()
    if use_custom_emoji and custom_id and custom_id.isdigit():
        p_emoji = f'<tg-emoji emoji-id="{custom_id}">{escape_html(p_emoji)}</tg-emoji>'
    else:
        p_emoji = escape_html(p_emoji)

    translated_desc = product.get(f"description_{lang}")
    if translated_desc and str(translated_desc).strip():
        raw_desc = translated_desc
    else:
        raw_desc = product.get("description", "N/A") or "N/A"

    desc_escaped = escape_html(raw_desc)
    if use_custom_emoji:
        # Format 1: {emoji:ID:char}
        desc_parsed = re.sub(
            r"\{emoji:(\d+):(.*?)\}",
            r'<tg-emoji emoji-id="\1">\2</tg-emoji>',
            desc_escaped,
        )
        # Format 2: escaped <tg-emoji> tags restored
        desc_parsed = re.sub(
            r'&lt;tg-emoji emoji-id=(?:&quot;|")(\d+)(?:&quot;|")&gt;(.*?)&lt;/tg-emoji&gt;',
            r'<tg-emoji emoji-id="\1">\2</tg-emoji>',
            desc_parsed,
        )
    else:
        # Strip custom-emoji placeholders to plain fallback char
        desc_parsed = re.sub(r"\{emoji:(\d+):(.*?)\}", r"\2", desc_escaped)
        desc_parsed = re.sub(
            r'&lt;tg-emoji emoji-id=(?:&quot;|")(\d+)(?:&quot;|")&gt;(.*?)&lt;/tg-emoji&gt;',
            r"\2",
            desc_parsed,
        )

    if product.get("delivery_type") == "activation":
        display_stock = _ACTIVATION_STOCK_LABEL.get(lang, _ACTIVATION_STOCK_LABEL["en"])
    else:
        display_stock = stock

    warranty = product.get("warranty_days")
    if warranty is None:
        warranty = 0

    text = safe_format(
        t("product_detail", lang),
        emoji=p_emoji,
        name=escape_html(product.get("name") or "?"),
        description=desc_parsed,
        price=format_price(product.get("price_usd")),
        warranty=warranty,
        stock=display_stock,
        sold=sold_count if sold_count is not None else 0,
    )

    if tiers:
        tier_lines = []
        for tier in tiers:
            try:
                tier_lines.append(
                    f"  📦 {tier['min_qty']}–{tier['max_qty']} → {format_price(tier['price_usd'])}/u"
                )
            except Exception:
                continue
        if tier_lines:
            tiers_label = _TIERS_LABEL.get(lang, _TIERS_LABEL["en"])
            text += f"\n\n{tiers_label}\n" + "\n".join(tier_lines)

    return text


def _normalize_image_url(image_url: str | None) -> str | None:
    if not image_url:
        return None
    url = str(image_url).strip()
    if not url:
        return None
    if "imgur.com" in url and "i.imgur.com" not in url:
        url = url.replace("imgur.com", "i.imgur.com")
        if not re.search(r"\.(png|jpe?g|gif|webp)(\?|$)", url, re.I):
            url = url + ".png"
    return url


async def _send_product_detail_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    markup,
    image_url: str | None,
    query=None,
) -> None:
    """Send or edit product detail, with photo caption length + HTML fallbacks."""
    image_url = _normalize_image_url(image_url)

    async def _edit_or_send(body: str, parse_mode: str | None = "HTML"):
        if query is not None:
            try:
                await query.edit_message_text(
                    body,
                    parse_mode=parse_mode,
                    reply_markup=markup,
                )
                return
            except Exception as e:
                err = str(e).lower()
                if "message is not modified" in err:
                    return
                # Coming from a photo message or other uneditable content
                try:
                    await query.message.delete()
                except Exception:
                    pass
        await context.bot.send_message(
            chat_id=chat_id,
            text=body,
            parse_mode=parse_mode,
            reply_markup=markup,
        )

    if image_url:
        # Telegram photo captions max 1024 chars
        caption = text if len(text) <= 1024 else (text[:1000].rstrip() + "…")
        try:
            if query is not None:
                try:
                    await query.message.delete()
                except Exception:
                    pass
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup if len(text) <= 1024 else None,
            )
            # Full text as follow-up if caption was truncated
            if len(text) > 1024:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            return
        except Exception as e:
            logger.warning("Failed to send product photo (%s): %s", image_url, e)
            # Fall through to text-only

    try:
        await _edit_or_send(text, "HTML")
    except Exception as e:
        logger.warning("HTML product detail failed, retrying plain: %s", e)
        # Strip simple tags for plain fallback
        plain = re.sub(r"<[^>]+>", "", text)
        await _edit_or_send(plain, None)


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
            try:
                await update.callback_query.edit_message_text(t("error_generic", lang))
            except Exception:
                try:
                    await update.callback_query.message.reply_text(t("error_generic", lang))
                except Exception:
                    pass
        else:
            await update.message.reply_text(t("error_generic", lang))


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'prod:{id}' callback — show product details."""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    lang = "en"
    try:
        lang = await get_user_lang(update.effective_user.id)
    except Exception:
        pass

    try:
        parts = (query.data or "").split(":")
        product_id = int(parts[1])
    except (ValueError, IndexError, AttributeError):
        try:
            await query.edit_message_text(t("product_not_found", lang))
        except Exception:
            pass
        return

    try:
        from database.models import get_product_full_details
        product, stock, tiers, sold_count = await get_product_full_details(product_id)

        if not product:
            await query.edit_message_text(
                t("product_not_found", lang),
                reply_markup=back_keyboard("back_products", lang),
            )
            return

        # Best-effort analytics (must never break the UI)
        try:
            await record_product_view(product_id, update.effective_user.id)
        except Exception as view_exc:
            logger.debug("record_product_view failed: %s", view_exc)

        can_buy = product.get("delivery_type") == "activation" or (stock or 0) > 0
        markup = product_detail_keyboard(product_id, lang, can_buy=can_buy)
        chat_id = query.message.chat_id
        image_url = product.get("image_url")

        # Prefer plain emoji first if custom emoji often fails; try with custom, then without
        text = _build_product_detail_text(product, stock, tiers, sold_count, lang, use_custom_emoji=True)
        try:
            await _send_product_detail_message(context, chat_id, text, markup, image_url, query=query)
        except Exception as send_exc:
            logger.warning(
                "Product detail send with custom emoji failed (product %s): %s — retrying plain emoji",
                product_id,
                send_exc,
            )
            text_plain = _build_product_detail_text(
                product, stock, tiers, sold_count, lang, use_custom_emoji=False
            )
            await _send_product_detail_message(
                context, chat_id, text_plain, markup, image_url, query=query
            )

    except Exception as exc:
        logger.error("show_product_detail: %s", exc, exc_info=True)
        err = t("error_generic", lang)
        try:
            await query.edit_message_text(err, reply_markup=back_keyboard("back_products", lang))
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=err,
                    reply_markup=back_keyboard("back_products", lang),
                )
            except Exception:
                try:
                    await query.answer(err, show_alert=True)
                except Exception:
                    pass


async def refresh_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'refresh_prods' callback — reload product list."""
    return await show_products_list(update, context)


async def notify_product_restock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe the user to a one-time restock notification."""
    query = update.callback_query
    lang = await get_user_lang(update.effective_user.id)

    try:
        product_id = int(query.data.split(":")[1])
        product = await get_product(product_id)
        if not product:
            await query.answer(t("product_not_found", lang), show_alert=True)
            return

        stock = await get_stock_count(product_id)
        if product.get("delivery_type") == "activation" or stock > 0:
            await query.answer(t("restock_notification", lang).format(
                product=product["name"],
                stock=stock,
            ), show_alert=True)
            return

        from database.models import add_product_stock_alert
        added = await add_product_stock_alert(update.effective_user.id, product_id)
        await query.answer(
            t("restock_alert_saved" if added else "restock_alert_existing", lang),
            show_alert=True,
        )
    except Exception as exc:
        logger.error("notify_product_restock: %s", exc, exc_info=True)
        await query.answer(t("error_generic", lang), show_alert=True)


async def notify_restock_subscribers(bot, product_id: int) -> int:
    """Notify users who asked to be alerted when a product is restocked."""
    from database.models import get_pending_stock_alerts, mark_stock_alerts_notified

    product = await get_product(product_id)
    if not product:
        return 0
    stock = await get_stock_count(product_id)
    if stock <= 0:
        return 0

    alerts = await get_pending_stock_alerts(product_id)
    sent_user_ids: list[int] = []
    for alert in alerts:
        lang = alert.get("language") or "fr"
        product_label = f"{product.get('emoji') or '📦'} <b>{escape_html(product['name'])}</b>"
        text = t("restock_notification", lang).format(
            product=product_label,
            stock=stock,
        )
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(t("btn_buy_now", lang), callback_data=f"buy:{product_id}")
        ]])
        try:
            await bot.send_message(
                chat_id=alert["user_telegram_id"],
                text=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            sent_user_ids.append(int(alert["user_telegram_id"]))
        except Exception as exc:
            logger.warning("Could not notify restock subscriber %s: %s", alert["user_telegram_id"], exc)

    await mark_stock_alerts_notified(product_id, sent_user_ids)
    return len(sent_user_ids)
