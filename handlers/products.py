"""
Product browsing handlers — direct product list (no categories), product detail.
"""

import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from database.models import (
    apply_telegram_special_prices_to_products,
    get_all_products,
    get_catalog_cache_generation,
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
from utils.locales import LANGUAGES, t
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)

_PRODUCT_VIEW_CACHE_GENERATION = -1
_PRODUCT_LIST_VIEW_CACHE: dict[tuple, tuple[str, InlineKeyboardMarkup]] = {}
_PRODUCT_DETAIL_VIEW_CACHE: dict[tuple, tuple[str, InlineKeyboardMarkup]] = {}


def _ensure_product_view_generation(generation: int) -> None:
    global _PRODUCT_VIEW_CACHE_GENERATION
    if generation == _PRODUCT_VIEW_CACHE_GENERATION:
        return
    _PRODUCT_LIST_VIEW_CACHE.clear()
    _PRODUCT_DETAIL_VIEW_CACHE.clear()
    _PRODUCT_VIEW_CACHE_GENERATION = generation


def _product_list_signature(
    products: list[dict],
    stock_counts: dict[int, int],
) -> tuple:
    return tuple(
        (
            int(product["id"]),
            str(product.get("name") or ""),
            str(product.get("emoji") or ""),
            str(product.get("custom_emoji_id") or ""),
            round(float(product.get("price_usd") or 0), 4),
            str(product.get("delivery_type") or "stock"),
            int(stock_counts.get(int(product["id"]), 0)),
        )
        for product in products
    )


def _precomputed_product_list_view(
    products: list[dict],
    stock_counts: dict[int, int],
    lang: str,
    category_id: int | None,
) -> tuple[str, InlineKeyboardMarkup]:
    generation = get_catalog_cache_generation()
    _ensure_product_view_generation(generation)
    signature = _product_list_signature(products, stock_counts)
    for language in LANGUAGES:
        key = (category_id, language, signature)
        if key not in _PRODUCT_LIST_VIEW_CACHE:
            _PRODUCT_LIST_VIEW_CACHE[key] = (
                t("categories_title", language),
                products_keyboard(products, stock_counts, language),
            )
    key = (category_id, lang, signature)
    if key not in _PRODUCT_LIST_VIEW_CACHE:
        _PRODUCT_LIST_VIEW_CACHE[key] = (
            t("categories_title", lang),
            products_keyboard(products, stock_counts, lang),
        )
    return _PRODUCT_LIST_VIEW_CACHE[key]


def _log_background_task(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Background product analytics task failed", exc_info=True)

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


def _precomputed_product_detail_view(
    product: dict,
    stock: int,
    tiers: list[dict],
    sold_count: int,
    lang: str,
) -> tuple[str, InlineKeyboardMarkup]:
    generation = get_catalog_cache_generation()
    _ensure_product_view_generation(generation)
    tier_signature = tuple(
        (
            int(tier.get("min_qty") or 0),
            int(tier.get("max_qty") or 0),
            round(float(tier.get("price_usd") or 0), 4),
        )
        for tier in tiers
    )
    can_buy = product.get("delivery_type") == "activation" or int(stock or 0) > 0
    base_key = (
        int(product["id"]),
        int(stock or 0),
        int(sold_count or 0),
        tier_signature,
        can_buy,
    )
    for language in LANGUAGES:
        key = (*base_key, language)
        if key not in _PRODUCT_DETAIL_VIEW_CACHE:
            _PRODUCT_DETAIL_VIEW_CACHE[key] = (
                _build_product_detail_text(
                    product,
                    stock,
                    tiers,
                    sold_count,
                    language,
                    use_custom_emoji=True,
                ),
                product_detail_keyboard(
                    int(product["id"]),
                    language,
                    can_buy=can_buy,
                ),
            )
    key = (*base_key, lang)
    if key not in _PRODUCT_DETAIL_VIEW_CACHE:
        _PRODUCT_DETAIL_VIEW_CACHE[key] = (
            _build_product_detail_text(
                product,
                stock,
                tiers,
                sold_count,
                lang,
                use_custom_emoji=True,
            ),
            product_detail_keyboard(
                int(product["id"]),
                lang,
                can_buy=can_buy,
            ),
        )
    return _PRODUCT_DETAIL_VIEW_CACHE[key]


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
    telegram_file_id: str | None = None,
    product_id: int | None = None,
    query=None,
) -> None:
    """Send or edit product detail, with photo caption length + HTML fallbacks."""
    stored_image_url = image_url
    image_url = _normalize_image_url(image_url)

    async def _edit_or_send(body: str, parse_mode: str | None = "HTML"):
        if query is not None:
            try:
                await safe_edit_message_text(query, 
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

    media_references = []
    if telegram_file_id:
        media_references.append(telegram_file_id)
    if image_url and image_url not in media_references:
        media_references.append(image_url)

    if media_references:
        # Telegram photo captions max 1024 chars
        caption = text if len(text) <= 1024 else (text[:1000].rstrip() + "…")
        for media_reference in media_references:
            try:
                if query is not None:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                sent_message = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=media_reference,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup if len(text) <= 1024 else None,
                )
                if (
                    product_id is not None
                    and stored_image_url
                    and media_reference == image_url
                    and getattr(sent_message, "photo", None)
                ):
                    from database.models import cache_product_telegram_file_id

                    cache_task = asyncio.create_task(cache_product_telegram_file_id(
                        product_id,
                        stored_image_url,
                        sent_message.photo[-1].file_id,
                    ))
                    cache_task.add_done_callback(_log_background_task)
                if len(text) > 1024:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                return
            except Exception as e:
                logger.warning("Failed to send product photo (%s): %s", media_reference, e)
            # A stale file_id falls through to the original URL, then to text.

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
        products = await get_all_products()
        products = [
            product for product in products
            if product.get("is_active", 1)
            and (
                category_id is None
                or int(product.get("category_id") or 0) == category_id
            )
        ]

        all_stocks = await get_all_stock_counts()
        stock_counts = {p["id"]: all_stocks.get(p["id"], 0) for p in products}
        products = [
            product for product in products
            if product.get("delivery_type") != "supplier_api" or stock_counts.get(product["id"], 0) > 0
        ]
        standard_products = products
        products = await apply_telegram_special_prices_to_products(
            standard_products, update.effective_user.id
        )

        if not products:
            text = t("no_categories", lang)
            if update.callback_query:
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass
                await safe_edit_message_text(update.callback_query, 
                    text, reply_markup=back_keyboard("back_main", lang)
                )
            else:
                await update.message.reply_text(text, reply_markup=back_keyboard("back_main", lang))
            return

        if products is standard_products:
            text, markup = _precomputed_product_list_view(
                products,
                stock_counts,
                lang,
                category_id,
            )
        else:
            text = t("categories_title", lang)
            markup = products_keyboard(products, stock_counts, lang)

        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            try:
                await safe_edit_message_text(update.callback_query, 
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
                await safe_edit_message_text(update.callback_query, t("error_generic", lang))
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
            await safe_edit_message_text(query, t("product_not_found", lang))
        except Exception:
            pass
        return

    try:
        from database.models import get_product_full_details
        product, stock, tiers, sold_count = await get_product_full_details(product_id)

        if not product:
            await safe_edit_message_text(query, 
                t("product_not_found", lang),
                reply_markup=back_keyboard("back_products", lang),
            )
            return

        standard_products = [product]
        priced_products = await apply_telegram_special_prices_to_products(
            standard_products, update.effective_user.id
        )
        if not priced_products:
            await safe_edit_message_text(
                query,
                t("product_not_found", lang),
                reply_markup=back_keyboard("back_products", lang),
            )
            return
        product = priced_products[0]
        if product.get("pricing_type") == "reseller_special":
            tiers = []

        # Analytics is deliberately off the response path.
        view_task = asyncio.create_task(record_product_view(product_id, update.effective_user.id))
        view_task.add_done_callback(_log_background_task)

        can_buy = product.get("delivery_type") == "activation" or (stock or 0) > 0
        chat_id = query.message.chat_id
        image_url = product.get("image_url")

        if priced_products is standard_products:
            text, markup = _precomputed_product_detail_view(
                product,
                stock,
                tiers,
                sold_count,
                lang,
            )
        else:
            markup = product_detail_keyboard(product_id, lang, can_buy=can_buy)
            text = _build_product_detail_text(
                product,
                stock,
                tiers,
                sold_count,
                lang,
                use_custom_emoji=True,
            )
        try:
            await _send_product_detail_message(
                context,
                chat_id,
                text,
                markup,
                image_url,
                telegram_file_id=product.get("telegram_file_id"),
                product_id=product_id,
                query=query,
            )
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
                context,
                chat_id,
                text_plain,
                markup,
                image_url,
                telegram_file_id=product.get("telegram_file_id"),
                product_id=product_id,
                query=query,
            )

    except Exception as exc:
        logger.error("show_product_detail: %s", exc, exc_info=True)
        err = t("error_generic", lang)
        try:
            await safe_edit_message_text(query, err, reply_markup=back_keyboard("back_products", lang))
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
    completed_user_ids: list[int] = []
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
            user_id = int(alert["user_telegram_id"])
            sent_user_ids.append(user_id)
            completed_user_ids.append(user_id)
        except Forbidden:
            # A blocked bot cannot ever deliver this one-shot alert.
            completed_user_ids.append(int(alert["user_telegram_id"]))
            logger.info(
                "Removed unreachable restock subscriber %s",
                alert["user_telegram_id"],
            )
        except Exception as exc:
            logger.warning("Could not notify restock subscriber %s: %s", alert["user_telegram_id"], exc)

    await mark_stock_alerts_notified(product_id, completed_user_ids)
    return len(sent_user_ids)
