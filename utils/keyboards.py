"""
Keyboard builders for the Telegram bot.
Provides InlineKeyboardMarkup and ReplyKeyboardMarkup factories
for all menus, product listings, payment flows, and admin panels.
Multi-language support via lang parameter.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import KeyboardButtonStyle
from utils.locales import t
import re

CUSTOM_EMOJIS = {
    "btn_buy": "5309801015015405183",
    "btn_wallet": "5443127283898405358",
    "btn_profile": "5373012449597335010",
    "btn_history": "5305265301917549162",
    "btn_support": "5443038326535759644",
    "btn_referral": "5456140674028019486",
    "btn_language": "6053275839821257175",
    "btn_refresh": "5312361253610475399",
    "btn_cancel": "5271934564699226262",
    "btn_back": "5332348837405145999",
    "btn_buy_now": "5312361253610475399",
    "btn_pay_wallet": "5278223861404421915",
    "btn_start": "5463156928307801722",
    "wallet_topup": "5361656830944624968",
    "wallet_history": "5305265301917549162",
}

def clean_standard_emoji(text: str) -> str:
    """Removes standard leading emojis and spaces from button label."""
    return re.sub(r'^[🛒💳👤📜💬👥🌐↩️❌🔄⚡💸➕🎫🚀✅🪙💰◀️\s]+', '', text)

def make_button(text_key: str, lang: str = "fr", callback_data: str | None = None, url: str | None = None, style = None, custom_text: str | None = None) -> InlineKeyboardButton:
    """Creates an InlineKeyboardButton with automatic animated emoji if configured."""
    emoji_id = CUSTOM_EMOJIS.get(text_key)
    label = custom_text if custom_text is not None else t(text_key, lang)
    btn_kwargs = {}
    if emoji_id:
        btn_kwargs["icon_custom_emoji_id"] = emoji_id
        label = clean_standard_emoji(label)
    if style is not None:
        btn_kwargs["style"] = style
    if callback_data is not None:
        return InlineKeyboardButton(label, callback_data=callback_data, **btn_kwargs)
    elif url is not None:
        return InlineKeyboardButton(label, url=url, **btn_kwargs)
    else:
        return InlineKeyboardButton(label, **btn_kwargs)

def make_reply_button(text_key: str, lang: str = "fr") -> KeyboardButton:
    """Creates a KeyboardButton with automatic animated emoji if configured."""
    emoji_id = CUSTOM_EMOJIS.get(text_key)
    label = t(text_key, lang)
    btn_kwargs = {}
    if emoji_id:
        btn_kwargs["icon_custom_emoji_id"] = emoji_id
        label = clean_standard_emoji(label)
    return KeyboardButton(label, **btn_kwargs)


# ──────────────────────────────────────────────
#  Language selection
# ──────────────────────────────────────────────

def language_keyboard() -> InlineKeyboardMarkup:
    """Language selection buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang:fr")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar")],
        [InlineKeyboardButton("🇨🇳 简体中文", callback_data="lang:zh")],
        [InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang:vi")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru")],
    ])


# ──────────────────────────────────────────────
#  Main / Navigation keyboards
# ──────────────────────────────────────────────

def main_menu_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Main menu shown after /start and on 'back_main'."""
    return InlineKeyboardMarkup([
        [make_button("btn_buy", lang, callback_data="menu_buy", style=KeyboardButtonStyle.SUCCESS)],
        [make_button("btn_wallet", lang, callback_data="menu_wallet")],
        [
            make_button("btn_profile", lang, callback_data="menu_profile"),
            make_button("btn_history", lang, callback_data="menu_history"),
        ],
        [
            make_button("btn_support", lang, callback_data="menu_support"),
            make_button("btn_referral", lang, callback_data="show_referrals"),
        ],
        [make_button("btn_api", lang, callback_data="menu_api")],
        [make_button("btn_language", lang, callback_data="change_lang")],
    ])


def reply_menu_keyboard(lang: str = "fr") -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard with quick-access buttons in a 2x2 layout."""
    return ReplyKeyboardMarkup(
        [
            [make_reply_button("btn_start", lang), make_reply_button("btn_products", lang)],
            [make_reply_button("btn_support", lang), make_reply_button("btn_language", lang)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def back_keyboard(callback_data: str, lang: str = "fr") -> InlineKeyboardMarkup:
    """Single back button pointing to *callback_data*."""
    return InlineKeyboardMarkup([
        [make_button("btn_back", lang, callback_data=callback_data)],
    ])


def profile_keyboard(lang: str = "fr", is_reseller: bool = False) -> InlineKeyboardMarkup:
    """Profile menu with Referral Program button and API for resellers."""
    ref_btn = {"fr": "👥 Programme de Parrainage", "en": "👥 Referral Program", "ar": "👥 برنامج الإحالة", "zh": "👥 推荐计划", "vi": "👥 Chương trình giới thiệu", "ru": "👥 Реферальная программа"}.get(lang, "👥 Programme de Parrainage")
    api_btn = {"fr": "🔌 Mon API Revendeur", "en": "🔌 My Reseller API", "ar": "🔌 واجهة برمجة تطبيقات الموزع الخاص بي", "zh": "🔌 我的经销商 API", "vi": "🔌 API đại lý của tôi", "ru": "🔌 Мой API реселлера"}.get(lang, "🔌 Mon API Revendeur")
    
    buttons = [
        [make_button("btn_referral", lang, callback_data="show_referrals", custom_text=ref_btn)]
    ]
    
    if is_reseller:
        buttons.append([make_button("btn_api", lang, callback_data="menu_api", custom_text=api_btn)])
        
    buttons.append([make_button("btn_back", lang, callback_data="back_main")])
    
    return InlineKeyboardMarkup(buttons)


def reseller_api_keyboard(lang: str = "fr", docs_url: str | None = None) -> InlineKeyboardMarkup:
    """Self-service reseller API menu."""
    buttons = [
        [make_button("btn_generate_api_key", lang, callback_data="api_generate_key")],
    ]
    if docs_url:
        buttons.append([make_button("btn_api_docs", lang, url=docs_url)])
    buttons.append([make_button("btn_back", lang, callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def reseller_api_confirm_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Confirmation before rotating a reseller API key."""
    return InlineKeyboardMarkup([
        [make_button("btn_confirm_generate_api_key", lang, callback_data="api_confirm_generate_key")],
        [make_button("btn_back", lang, callback_data="menu_api")],
    ])


# ──────────────────────────────────────────────
#  Product browsing keyboards
# ──────────────────────────────────────────────

def categories_keyboard(categories: list[dict], lang: str = "fr") -> InlineKeyboardMarkup:
    """One button per category, plus a back button."""
    buttons = [
        [InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat:{cat['id']}",
        )]
        for cat in categories
    ]
    buttons.append([make_button("btn_back", lang, callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list[dict], stock_counts: dict, lang: str = "fr") -> InlineKeyboardMarkup:
    """One button per product showing name, price and stock count or ❌."""
    from utils.helpers import format_price
    buttons = []
    for prod in products:
        stock = stock_counts.get(prod["id"], 0)
        is_activation = prod.get("delivery_type") == "activation"
        price_lbl = format_price(prod.get("price_usd")).lstrip("$")
        name = prod.get("name") or "?"
        emoji = prod.get("emoji") or "📦"
        
        custom_id = (prod.get("custom_emoji_id") or "").strip()
        # icon_custom_emoji_id must be numeric; invalid IDs break the whole keyboard
        if custom_id and not custom_id.isdigit():
            custom_id = ""

        if is_activation:
            activation_txt = {"en": "Activation", "fr": "Activation", "ar": "تفعيل", "zh": "激活", "vi": "Kích hoạt", "ru": "Активация"}.get(lang, "Activation")
            if custom_id:
                label = f"{name} | ${price_lbl} | {activation_txt}"
            else:
                label = f"{emoji} {name} | ${price_lbl} | {activation_txt}"
        elif stock > 0:
            if custom_id:
                label = f"{name} | ${price_lbl} | 📦 {stock}"
            else:
                label = f"{emoji} {name} | ${price_lbl} | 📦 {stock}"
        else:
            rupture_txt = {"en": "Out of stock", "fr": "Rupture", "ar": "نفذت الكمية", "zh": "缺货", "vi": "Hết hàng", "ru": "Нет в наличии"}.get(lang, "Rupture")
            if custom_id:
                label = f"{name} | ${price_lbl} | {rupture_txt}"
            else:
                label = f"⚠️ {name} | ${price_lbl} | {rupture_txt}"
            
        btn_kwargs = {}
        if custom_id:
            btn_kwargs["icon_custom_emoji_id"] = custom_id

        if is_activation or stock > 0:
            btn_kwargs["style"] = KeyboardButtonStyle.SUCCESS
        else:
            btn_kwargs["style"] = KeyboardButtonStyle.DANGER

        # Telegram button text max ~64 chars
        if len(label) > 64:
            label = label[:61] + "…"

        buttons.append([InlineKeyboardButton(label, callback_data=f"prod:{prod['id']}", **btn_kwargs)])

    buttons.append([
        make_button("btn_refresh", lang, callback_data="refresh_prods"),
        make_button("btn_back", lang, callback_data="back_main"),
    ])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: int, lang: str = "fr", can_buy: bool = True) -> InlineKeyboardMarkup:
    """Buy/notify + back to product list."""
    buttons = []
    if can_buy:
        buttons.append([make_button("btn_buy_now", lang, callback_data=f"buy:{product_id}", style=KeyboardButtonStyle.SUCCESS)])
    else:
        buttons.append([make_button("btn_notify_restock", lang, callback_data=f"notify_stock:{product_id}")])
    buttons.append([make_button("btn_back", lang, callback_data="back_products")])
    return InlineKeyboardMarkup(buttons)


def quantity_keyboard(product_id: int, stock: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Back button only — user types quantity as free text."""
    return InlineKeyboardMarkup([
        [make_button("btn_back", lang, callback_data=f"prod:{product_id}")],
    ])


# ──────────────────────────────────────────────
#  Payment keyboards
# ──────────────────────────────────────────────

async def payment_method_keyboard(order_id: int, lang: str = "fr", wallet_balance: float = 0.0, has_promo: bool = False) -> InlineKeyboardMarkup:
    """Choose payment method or cancel."""
    from utils.helpers import format_price
    from database.models import get_setting
    buttons = []
    
    # Always show wallet button
    label = t("btn_pay_wallet", lang).replace("${balance}", format_price(wallet_balance))
    buttons.append([make_button("btn_pay_wallet", lang, callback_data=f"pay_wallet:{order_id}", custom_text=label)])
    
    # Always show binance pay button
    binance_label = t("btn_pay_binance", lang).lstrip("◇ ").strip()
    buttons.append([InlineKeyboardButton(
        binance_label, 
        callback_data=f"pay_binance:{order_id}", 
        icon_custom_emoji_id="5388622778817589921"
    )])

    # Automated USDT/BEP20 checkout through NOWPayments.
    from services.nowpayments import is_nowpayments_configured
    if is_nowpayments_configured():
        buttons.append([InlineKeyboardButton(
            t("btn_pay_nowpayments", lang),
            callback_data=f"pay_nowpayments:{order_id}",
        )])

    # Dynamic BEP20 button
    bep20_addr = await get_setting("bep20_address")
    if bep20_addr:
        bep20_btn_text = {
            "fr": "Payer avec BEP20 (USDT)",
            "en": "Pay with BEP20 (USDT)",
            "ar": "دفع عبر BEP20 (USDT)"
        }.get(lang, "Payer avec BEP20 (USDT)")
        buttons.append([InlineKeyboardButton(
            bep20_btn_text, 
            callback_data=f"pay_bep20:{order_id}", 
            icon_custom_emoji_id="5413589900450625318"
        )])

    # Dynamic TRC20 button
    trc20_addr = await get_setting("trc20_address")
    if trc20_addr:
        trc20_btn_text = {
            "fr": "◇ Payer avec TRC20 (USDT)",
            "en": "◇ Pay with TRC20 (USDT)",
            "ar": "◇ الدفع عبر TRC20 (USDT)"
        }.get(lang, "◇ Payer avec TRC20 (USDT)")
        buttons.append([InlineKeyboardButton(trc20_btn_text, callback_data=f"pay_trc20:{order_id}")])

    if not has_promo:
        promo_btn_text = {"fr": "🎫 Code Promo", "en": "🎫 Promo Code", "ar": "🎫 كود الخصم"}.get(lang, "🎫 Code Promo")
        buttons.append([InlineKeyboardButton(promo_btn_text, callback_data=f"apply_promo:{order_id}")])

    buttons.append([make_button("btn_cancel", lang, callback_data=f"cancel_order:{order_id}")])
    return InlineKeyboardMarkup(buttons)


def nowpayments_payment_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_check_nowpayments", lang), callback_data=f"check_nowpayments:{order_id}")],
        [make_button("btn_cancel", lang, callback_data=f"cancel_order:{order_id}")],
    ])


async def wallet_topup_method_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Choose wallet top-up method or cancel."""
    from database.models import get_setting
    buttons = []
    
    # Always show binance pay button
    binance_label = t("btn_pay_binance", lang).lstrip("◇ ").strip()
    buttons.append([InlineKeyboardButton(
        binance_label, 
        callback_data="topup_binance", 
        icon_custom_emoji_id="5388622778817589921"
    )])

    # Dynamic BEP20 button
    bep20_addr = await get_setting("bep20_address")
    if bep20_addr:
        bep20_btn_text = {
            "fr": "Payer avec BEP20 (USDT)",
            "en": "Pay with BEP20 (USDT)",
            "ar": "دفع عبر BEP20 (USDT)"
        }.get(lang, "Payer avec BEP20 (USDT)")
        buttons.append([InlineKeyboardButton(
            bep20_btn_text, 
            callback_data="topup_bep20", 
            icon_custom_emoji_id="5413589900450625318"
        )])

    # Dynamic TRC20 button
    trc20_addr = await get_setting("trc20_address")
    if trc20_addr:
        trc20_btn_text = {
            "fr": "◇ Payer avec TRC20 (USDT)",
            "en": "◇ Pay with TRC20 (USDT)",
            "ar": "◇ الدفع عبر TRC20 (USDT)"
        }.get(lang, "◇ Payer avec TRC20 (USDT)")
        buttons.append([InlineKeyboardButton(trc20_btn_text, callback_data="topup_trc20")])

    buttons.append([make_button("btn_cancel", lang, callback_data="back_wallet")])
    return InlineKeyboardMarkup(buttons)


def bep20_payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Check payment or cancel buttons for BEP20."""
    btn_paid = {"fr": "✅ J'ai payé (Saisir Tx Hash)", "en": "✅ I paid (Enter Tx Hash)", "ar": "✅ لقد دفعت (أدخل Hash)"}.get(lang, "✅ J'ai payé")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_paid, callback_data=f"check_bep20:{order_id}")],
        [make_button("btn_cancel", lang, callback_data=f"cancel_order:{order_id}")],
    ])


def trc20_payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Check payment or cancel buttons for TRC20."""
    btn_paid = {"fr": "✅ J'ai payé (Saisir Tx Hash)", "en": "✅ I paid (Enter Tx Hash)", "ar": "✅ لقد دفعت (أدخل Hash)"}.get(lang, "✅ J'ai payé")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_paid, callback_data=f"check_trc20:{order_id}")],
        [make_button("btn_cancel", lang, callback_data=f"cancel_order:{order_id}")],
    ])


def payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Cancel order during payment."""
    return InlineKeyboardMarkup([
        [make_button("btn_cancel", lang, callback_data=f"cancel_order:{order_id}")],
    ])


# ──────────────────────────────────────────────
#  History / Orders keyboards
# ──────────────────────────────────────────────

def history_keyboard(orders: list[dict], page: int, total_pages: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Order list with detail buttons and pagination."""
    buttons = [
        [InlineKeyboardButton(
            f"📦 #{o['id']} — ${o['amount_usd']:.2f}",
            callback_data=f"order:{o['id']}",
        )]
        for o in orders
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"hist_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"hist_page:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([make_button("btn_back", lang, callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────────────
#  Support keyboards
# ──────────────────────────────────────────────

def support_menu_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Support sub-menu with direct link to admin."""
    btn_label = {
        "fr": "💬 Contacter l'Admin",
        "en": "💬 Contact Admin",
        "ar": "💬 الاتصال بالمسؤول"
    }
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_label.get(lang, btn_label["fr"]), url="https://t.me/Drbatman2")],
    ])


def tickets_keyboard(tickets: list[dict], lang: str = "fr") -> InlineKeyboardMarkup:
    """List of user tickets."""
    status_emojis = {"OPEN": "🟢", "REPLIED": "💬", "CLOSED": "🔴"}
    buttons = [
        [InlineKeyboardButton(
            f"{status_emojis.get(t_item.get('status', 'OPEN'), '❓')} Ticket #{t_item['id']}",
            callback_data=f"ticket:{t_item['id']}",
        )]
        for t_item in tickets
    ]
    buttons.append([make_button("btn_back", lang, callback_data="menu_support")])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────────────
#  Admin keyboards (no lang parameter needed)
# ──────────────────────────────────────────────

def admin_menu_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Admin dashboard."""
    from utils.locales import t as _t
    # Short labels with icons — using simple inline translations
    _prods = {"fr": "📦 Produits", "en": "📦 Products", "ar": "📦 المنتجات", "zh": "📦 产品", "vi": "📦 Sản phẩm", "ru": "📦 Товары"}.get(lang, "📦 Produits")
    _cats = {"fr": "📂 Catégories", "en": "📂 Categories", "ar": "📂 الفئات", "zh": "📂 分类", "vi": "📂 Danh mục", "ru": "📂 Категории"}.get(lang, "📂 Catégories")
    _stock = {"fr": "📥 Stock", "en": "📥 Stock", "ar": "📥 المخزون", "zh": "📥 库存", "vi": "📥 Kho", "ru": "📥 Склад"}.get(lang, "📥 Stock")
    _stats = {"fr": "📊 Stats", "en": "📊 Stats", "ar": "📊 إحصائيات", "zh": "📊 统计", "vi": "📊 Thống kê", "ru": "📊 Статистика"}.get(lang, "📊 Stats")
    _bcast = "📢 Broadcast"
    _tickets = {"fr": "🎫 Tickets", "en": "🎫 Tickets", "ar": "🎫 التذاكر", "zh": "🎫 工单", "vi": "🎫 Ticket", "ru": "🎫 Тикеты"}.get(lang, "🎫 Tickets")
    _orders = {"fr": "📋 Commandes", "en": "📋 Orders", "ar": "📋 الطلبات", "zh": "📋 订单", "vi": "📋 Đơn hàng", "ru": "📋 Заказы"}.get(lang, "📋 Commandes")
    _activations = {"fr": "⚡ Activations", "en": "⚡ Activations", "ar": "⚡ التفعيلات", "zh": "⚡ 激活", "vi": "⚡ Kích hoạt", "ru": "⚡ Активации"}.get(lang, "⚡ Activations")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_prods, callback_data="adm_prods"), InlineKeyboardButton(_cats, callback_data="adm_cats")],
        [InlineKeyboardButton(_stock, callback_data="adm_stock"), InlineKeyboardButton(_stats, callback_data="adm_stats")],
        [InlineKeyboardButton(_bcast, callback_data="adm_broadcast"), InlineKeyboardButton(_tickets, callback_data="adm_tickets")],
        [InlineKeyboardButton(_orders, callback_data="adm_orders"), InlineKeyboardButton(_activations, callback_data="adm_activations")],
    ])


def admin_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    """Admin category list with add + back."""
    buttons = [
        [InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"adm_cat:{cat['id']}",
        )]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("➕ Ajouter", callback_data="adm_add_cat")])
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
    return InlineKeyboardMarkup(buttons)


def admin_category_detail_keyboard(category: dict) -> InlineKeyboardMarkup:
    """Detail view for a single category with add product option."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Ajouter un produit", callback_data=f"adm_add_prod:{category['id']}")],
        [InlineKeyboardButton("◀️ Retour", callback_data="adm_cats")],
    ])


def admin_products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    """Admin product list."""
    buttons = [
        [InlineKeyboardButton(
            f"{p['emoji']} {p['name']} {'✅' if p.get('is_active', True) else '❌'}",
            callback_data=f"adm_prod:{p['id']}",
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
    return InlineKeyboardMarkup(buttons)


def admin_product_detail_keyboard(product: dict) -> InlineKeyboardMarkup:
    """Admin single product actions."""
    toggle_label = "❌ Désactiver" if product.get("is_active", True) else "✅ Activer"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"adm_toggle_prod:{product['id']}")],
        [InlineKeyboardButton("📥 Ajouter stock", callback_data=f"adm_add_stock:{product['id']}")],
        [InlineKeyboardButton("🗑️ Supprimer", callback_data=f"adm_del_prod:{product['id']}")],
        [InlineKeyboardButton("◀️ Retour", callback_data="adm_prods")],
    ])


def admin_stock_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    """Select a product to add stock to."""
    buttons = [
        [InlineKeyboardButton(
            f"{p['emoji']} {p['name']}",
            callback_data=f"adm_add_stock:{p['id']}",
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
    return InlineKeyboardMarkup(buttons)


def admin_tickets_keyboard(tickets: list[dict]) -> InlineKeyboardMarkup:
    """Admin list of open tickets."""
    buttons = [
        [InlineKeyboardButton(
            f"🎫 Ticket #{t_item['id']} — User {t_item.get('user_telegram_id', '?')}",
            callback_data=f"ticket:{t_item['id']}",
        )]
        for t_item in tickets
    ]
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
    return InlineKeyboardMarkup(buttons)


def admin_ticket_detail_keyboard(ticket: dict) -> InlineKeyboardMarkup:
    """Admin actions for a single ticket."""
    buttons = [
        [InlineKeyboardButton("💬 Répondre", callback_data=f"adm_reply_ticket:{ticket['id']}")],
        [InlineKeyboardButton("🔒 Fermer", callback_data=f"adm_close_ticket:{ticket['id']}")],
        [InlineKeyboardButton("◀️ Retour", callback_data="adm_tickets")],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_orders_keyboard(orders: list[dict]) -> InlineKeyboardMarkup:
    """Admin pending orders list."""
    buttons = [
        [InlineKeyboardButton(
            f"📦 #{o['id']} — ${o['amount_usd']:.2f}",
            callback_data=f"adm_confirm_pay:{o['id']}",
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
    return InlineKeyboardMarkup(buttons)


def referral_dashboard_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for the referral dashboard."""
    from utils.locales import t
    btn_text = {"fr": "👥 Voir mes filleuls", "en": "👥 View my referrals", "ar": "👥 عرض الإحالات الخاصة بي"}.get(lang, "👥 Voir mes filleuls")
    buttons = [
        [InlineKeyboardButton(btn_text, callback_data="view_referrals_list")],
        [make_button("btn_back", lang, callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(buttons)
