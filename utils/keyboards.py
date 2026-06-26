"""
Keyboard builders for the Telegram bot.
Provides InlineKeyboardMarkup and ReplyKeyboardMarkup factories
for all menus, product listings, payment flows, and admin panels.
Multi-language support via lang parameter.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from utils.locales import t


# ──────────────────────────────────────────────
#  Language selection
# ──────────────────────────────────────────────

def language_keyboard() -> InlineKeyboardMarkup:
    """Language selection buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang:fr")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar")],
    ])


# ──────────────────────────────────────────────
#  Main / Navigation keyboards
# ──────────────────────────────────────────────

def main_menu_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Main menu shown after /start and on 'back_main'."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_buy", lang), callback_data="menu_buy")],
        [InlineKeyboardButton(t("btn_wallet", lang), callback_data="menu_wallet")],
        [
            InlineKeyboardButton(t("btn_profile", lang), callback_data="menu_profile"),
            InlineKeyboardButton(t("btn_history", lang), callback_data="menu_history"),
        ],
        [
            InlineKeyboardButton(t("btn_support", lang), callback_data="menu_support"),
            InlineKeyboardButton(t("btn_referral", lang), callback_data="show_referrals"),
        ],
        [InlineKeyboardButton(t("btn_language", lang), callback_data="change_lang")],
    ])


def reply_menu_keyboard(lang: str = "fr") -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard with quick-access buttons in a 2x2 layout."""
    return ReplyKeyboardMarkup(
        [
            [t("btn_start", lang), t("btn_products", lang)],
            [t("btn_support", lang), t("btn_language", lang)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def back_keyboard(callback_data: str, lang: str = "fr") -> InlineKeyboardMarkup:
    """Single back button pointing to *callback_data*."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data=callback_data)],
    ])


def profile_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Profile menu with Referral Program button."""
    ref_btn = {"fr": "👥 Programme de Parrainage", "en": "👥 Referral Program", "ar": "👥 برنامج الإحالة"}.get(lang, "👥 Programme de Parrainage")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ref_btn, callback_data="show_referrals")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")],
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
    buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list[dict], stock_counts: dict, lang: str = "fr") -> InlineKeyboardMarkup:
    """One button per product showing name, price and stock count or ❌."""
    buttons = []
    for prod in products:
        stock = stock_counts.get(prod["id"], 0)
        custom_id = prod.get("custom_emoji_id")
        
        if stock > 0:
            base_label = f"{prod['name']} | ${prod['price_usd']:.2f} | 📦 {stock}"
            fallback_label = f"{prod['emoji']} {base_label}"
        else:
            rupture_txt = {"en": "Out of stock", "fr": "Rupture", "ar": "نفذت الكمية"}.get(lang, "Rupture")
            base_label = f"{prod['name']} | ${prod['price_usd']:.2f} | {rupture_txt}"
            fallback_label = f"❌ {base_label}"
            
        btn = None
        if custom_id and stock > 0:
            try:
                # Try to use the new icon_custom_emoji_id if python-telegram-bot supports it
                btn = InlineKeyboardButton(base_label, callback_data=f"prod:{prod['id']}", icon_custom_emoji_id=str(custom_id))
            except TypeError:
                pass
                
        if btn is None:
            btn = InlineKeyboardButton(fallback_label, callback_data=f"prod:{prod['id']}")
            
        buttons.append([btn])

    buttons.append([
        InlineKeyboardButton(t("btn_refresh", lang), callback_data="refresh_prods"),
        InlineKeyboardButton(t("btn_back", lang), callback_data="back_main"),
    ])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Buy now + back to product list."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_buy_now", lang), callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back_products")],
    ])


def quantity_keyboard(product_id: int, stock: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Back button only — user types quantity as free text."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back", lang), callback_data=f"prod:{product_id}")],
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
    buttons.append([InlineKeyboardButton(label, callback_data=f"pay_wallet:{order_id}")])
    
    # Always show binance pay button
    buttons.append([InlineKeyboardButton(t("btn_pay_binance", lang), callback_data=f"pay_binance:{order_id}")])

    # Dynamic BEP20 button
    bep20_addr = await get_setting("bep20_address")
    if bep20_addr:
        bep20_btn_text = {
            "fr": "◇ Payer avec BEP20 (USDT)",
            "en": "◇ Pay with BEP20 (USDT)",
            "ar": "◇ الدفع عبر BEP20 (USDT)"
        }.get(lang, "◇ Payer avec BEP20 (USDT)")
        buttons.append([InlineKeyboardButton(bep20_btn_text, callback_data=f"pay_bep20:{order_id}")])

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

    buttons.append([InlineKeyboardButton(t("btn_cancel", lang), callback_data=f"cancel_order:{order_id}")])
    return InlineKeyboardMarkup(buttons)


async def wallet_topup_method_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Choose wallet top-up method or cancel."""
    from database.models import get_setting
    buttons = []
    
    # Always show binance pay button
    buttons.append([InlineKeyboardButton(t("btn_pay_binance", lang), callback_data="topup_binance")])

    # Dynamic BEP20 button
    bep20_addr = await get_setting("bep20_address")
    if bep20_addr:
        bep20_btn_text = {
            "fr": "◇ Payer avec BEP20 (USDT)",
            "en": "◇ Pay with BEP20 (USDT)",
            "ar": "◇ الدفع عبر BEP20 (USDT)"
        }.get(lang, "◇ Payer avec BEP20 (USDT)")
        buttons.append([InlineKeyboardButton(bep20_btn_text, callback_data="topup_bep20")])

    # Dynamic TRC20 button
    trc20_addr = await get_setting("trc20_address")
    if trc20_addr:
        trc20_btn_text = {
            "fr": "◇ Payer avec TRC20 (USDT)",
            "en": "◇ Pay with TRC20 (USDT)",
            "ar": "◇ الدفع عبر TRC20 (USDT)"
        }.get(lang, "◇ Payer avec TRC20 (USDT)")
        buttons.append([InlineKeyboardButton(trc20_btn_text, callback_data="topup_trc20")])

    buttons.append([InlineKeyboardButton(t("btn_cancel", lang), callback_data="back_wallet")])
    return InlineKeyboardMarkup(buttons)


def bep20_payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Check payment or cancel buttons for BEP20."""
    btn_paid = {"fr": "✅ J'ai payé (Saisir Tx Hash)", "en": "✅ I paid (Enter Tx Hash)", "ar": "✅ لقد دفعت (أدخل Hash)"}.get(lang, "✅ J'ai payé")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_paid, callback_data=f"check_bep20:{order_id}")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data=f"cancel_order:{order_id}")],
    ])


def trc20_payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Check payment or cancel buttons for TRC20."""
    btn_paid = {"fr": "✅ J'ai payé (Saisir Tx Hash)", "en": "✅ I paid (Enter Tx Hash)", "ar": "✅ لقد دفعت (أدخل Hash)"}.get(lang, "✅ J'ai payé")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_paid, callback_data=f"check_trc20:{order_id}")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data=f"cancel_order:{order_id}")],
    ])


def payment_check_keyboard(order_id: int, lang: str = "fr") -> InlineKeyboardMarkup:
    """Cancel order during payment."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data=f"cancel_order:{order_id}")],
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

    buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="back_main")])
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
    buttons.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu_support")])
    return InlineKeyboardMarkup(buttons)


# ──────────────────────────────────────────────
#  Admin keyboards (no lang parameter needed)
# ──────────────────────────────────────────────

def admin_menu_keyboard(lang: str = "fr") -> InlineKeyboardMarkup:
    """Admin dashboard."""
    from utils.locales import t as _t
    # Short labels with icons — using simple inline translations
    _prods = {"fr": "📦 Produits", "en": "📦 Products", "ar": "📦 المنتجات"}.get(lang, "📦 Produits")
    _cats = {"fr": "📂 Catégories", "en": "📂 Categories", "ar": "📂 الفئات"}.get(lang, "📂 Catégories")
    _stock = {"fr": "📥 Stock", "en": "📥 Stock", "ar": "📥 المخزون"}.get(lang, "📥 Stock")
    _stats = {"fr": "📊 Stats", "en": "📊 Stats", "ar": "📊 إحصائيات"}.get(lang, "📊 Stats")
    _bcast = "📢 Broadcast"
    _tickets = {"fr": "🎫 Tickets", "en": "🎫 Tickets", "ar": "🎫 التذاكر"}.get(lang, "🎫 Tickets")
    _orders = {"fr": "📋 Commandes", "en": "📋 Orders", "ar": "📋 الطلبات"}.get(lang, "📋 Commandes")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_prods, callback_data="adm_prods"), InlineKeyboardButton(_cats, callback_data="adm_cats")],
        [InlineKeyboardButton(_stock, callback_data="adm_stock"), InlineKeyboardButton(_stats, callback_data="adm_stats")],
        [InlineKeyboardButton(_bcast, callback_data="adm_broadcast"), InlineKeyboardButton(_tickets, callback_data="adm_tickets")],
        [InlineKeyboardButton(_orders, callback_data="adm_orders")],
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
