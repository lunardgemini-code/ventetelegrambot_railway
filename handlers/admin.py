"""
Admin panel handlers.

A single ConversationHandler manages all admin multi-step flows:
  - Category management  (add category)
  - Product management   (add / toggle / delete product)
  - Stock management      (add stock items)
  - Broadcast             (send message to all users)
  - Ticket management     (reply / close tickets)
  - Order management      (view pending, manually confirm)
  - Statistics dashboard

All routes are restricted to ADMIN_IDS.
"""

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS
from database.models import (
    add_category,
    add_product,
    add_stock_items,
    close_ticket,
    delete_product,
    get_all_products,
    get_all_users,
    get_activation_orders,
    get_categories,
    get_category,
    get_open_tickets,
    get_order,
    get_pending_orders,
    get_product,
    get_products_by_category,
    get_stats,
    get_stock_count,
    get_ticket,
    get_user_lang,
    reply_ticket,
    toggle_product,
    update_order_status,
)
from services.delivery import deliver_order
from utils.helpers import format_price, is_admin, escape_html
from utils.locales import t
from utils.keyboards import (
    admin_categories_keyboard,
    admin_category_detail_keyboard,
    admin_menu_keyboard,
    admin_orders_keyboard,
    admin_product_detail_keyboard,
    admin_products_keyboard,
    admin_stock_keyboard,
    admin_ticket_detail_keyboard,
    admin_tickets_keyboard,
    back_keyboard,
)

logger = logging.getLogger(__name__)

# ── Conversation states ──
ADMIN_ADD_CAT_NAME = 100
ADMIN_ADD_CAT_EMOJI = 101
ADMIN_ADD_PROD_NAME = 110
ADMIN_ADD_PROD_DESC = 111
ADMIN_ADD_PROD_PRICE = 112
ADMIN_ADD_PROD_WARRANTY = 113
ADMIN_ADD_PROD_EMOJI = 114
ADMIN_ADD_PROD_BINANCE = 115
ADMIN_ADD_PROD_BROADCAST_DECISION = 116
ADMIN_ADD_STOCK = 120
ADMIN_ADD_STOCK_BROADCAST_DECISION = 121
ADMIN_BROADCAST = 130
ADMIN_BROADCAST_BTN_TYPE = 131
ADMIN_BROADCAST_BTN_PRODUCT = 132
ADMIN_BROADCAST_BTN_URL = 133
ADMIN_REPLY_TICKET = 140


# ──────────────────────────────────────────────
#  Guard helper
# ──────────────────────────────────────────────

def _admin_check(update: Update) -> bool:
    """Return True if the effective user is an admin."""
    return is_admin(update.effective_user.id)


async def _not_admin(update: Update):
    """Send an access-denied message."""
    lang = await get_user_lang(update.effective_user.id)
    text = t("admin_access_denied", lang)
    if update.callback_query:
        await update.callback_query.answer(text, show_alert=True)
    elif update.message:
        await update.message.reply_text(text)


# ──────────────────────────────────────────────
#  /admin command & menu
# ──────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin — show admin dashboard."""
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END

    lang = await get_user_lang(update.effective_user.id)
    await update.message.reply_text(
        t("admin_panel", lang),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(lang),
    )
    return ConversationHandler.END


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_menu' callback — return to admin dashboard."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END

    lang = await get_user_lang(update.effective_user.id)
    await query.answer()
    await query.edit_message_text(
        t("admin_panel", lang),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(lang),
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════

async def admin_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_cats' callback — list categories."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)

    try:
        cats = await get_categories()
        await query.edit_message_text(
            t("admin_categories_title", lang).format(count=len(cats)),
            parse_mode="HTML",
            reply_markup=admin_categories_keyboard(cats),
        )
    except Exception as exc:
        logger.error("admin_categories: %s", exc, exc_info=True)
        await query.edit_message_text(t("admin_error", lang))


async def admin_category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_cat:{id}' callback — show category detail."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        cat_id = int(query.data.split(":")[1])
        cat = await get_category(cat_id)
        if not cat:
            await query.edit_message_text("❌ Catégorie introuvable.")
            return

        prods = await get_products_by_category(cat_id)
        cat_name = escape_html(cat['name'])
        cat_desc = escape_html(cat.get('description', 'Pas de description') or 'Pas de description')
        text = (
            f"{cat['emoji']} <b>{cat_name}</b>\n\n"
            f"📝 {cat_desc}\n"
            f"📦 Produits : {len(prods)}"
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_category_detail_keyboard(cat),
        )
    except Exception as exc:
        logger.error("admin_category_detail: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_add_cat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_add_cat' callback — start add-category flow."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END
    await query.answer()

    await query.edit_message_text(
        "➕ <b>Ajouter une catégorie</b>\n\n"
        "📝 Envoyez le <b>nom</b> de la catégorie :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_CAT_NAME


async def admin_add_cat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive category name, ask for emoji."""
    context.user_data["new_cat_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Nom : <b>{context.user_data['new_cat_name']}</b>\n\n"
        "🎨 Envoyez un <b>emoji</b> pour cette catégorie :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_CAT_EMOJI


async def admin_add_cat_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive emoji, create category."""
    emoji = update.message.text.strip()
    name = context.user_data.pop("new_cat_name", "Sans nom")

    try:
        cat_id = await add_category(name, emoji, "")
        await update.message.reply_text(
            f"✅ <b>Catégorie créée !</b>\n\n"
            f"{emoji} {name} (ID: {cat_id})",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("admin_add_cat_emoji: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Erreur lors de la création.")

    return ConversationHandler.END


# ══════════════════════════════════════════════
#  PRODUCTS
# ══════════════════════════════════════════════

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_prods' callback — list all products."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        prods = await get_all_products()
        await query.edit_message_text(
            "📦 <b>Gestion des produits</b>\n\n"
            f"Total : {len(prods)} produit(s)",
            parse_mode="HTML",
            reply_markup=admin_products_keyboard(prods),
        )
    except Exception as exc:
        logger.error("admin_products: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_prod:{id}' callback — show product detail with admin actions."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        prod_id = int(query.data.split(":")[1])
        product = await get_product(prod_id)
        if not product:
            await query.edit_message_text("❌ Produit introuvable.")
            return

        stock = await get_stock_count(prod_id)
        active_label = "✅ Actif" if product.get("is_active", True) else "❌ Inactif"
        prod_name = escape_html(product['name'])
        prod_desc = escape_html(product.get('description', 'N/A') or 'N/A')

        text = (
            f"{product['emoji']} <b>{prod_name}</b>\n\n"
            f"📝 {prod_desc}\n"
            f"💰 Prix : {format_price(product['price_usd'])}\n"
            f"🛡️ Garantie : {product.get('warranty_days', 0)} jours\n"
            f"📦 Stock : {stock}\n"
            f"📊 Statut : {active_label}"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_product_detail_keyboard(product),
        )
    except Exception as exc:
        logger.error("admin_product_detail: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_add_prod_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_add_prod:{cat_id}' callback — start add-product flow."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END
    await query.answer()

    cat_id = int(query.data.split(":")[1])
    context.user_data["new_prod_cat_id"] = cat_id

    await query.edit_message_text(
        "➕ <b>Ajouter un produit</b>\n\n"
        "📝 Envoyez le <b>nom</b> du produit :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_PROD_NAME


async def admin_add_prod_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive product name, ask for description."""
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Nom : <b>{context.user_data['new_prod_name']}</b>\n\n"
        "📝 Envoyez la <b>description</b> du produit :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_PROD_DESC


async def admin_add_prod_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive description, ask for price."""
    context.user_data["new_prod_desc"] = update.message.text.strip()
    await update.message.reply_text(
        "💰 Envoyez le <b>prix en USD</b> (ex: 5.99) :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_PROD_PRICE


async def admin_add_prod_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive price, ask for warranty days."""
    try:
        price = float(update.message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
        context.user_data["new_prod_price"] = price
    except ValueError:
        await update.message.reply_text("❌ Prix invalide. Envoyez un nombre valide (ex: 5.99) :")
        return ADMIN_ADD_PROD_PRICE

    await update.message.reply_text(
        f"✅ Prix : {format_price(price)}\n\n"
        "🛡️ Envoyez le nombre de <b>jours de garantie</b> (0 si aucune) :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_PROD_WARRANTY


async def admin_add_prod_warranty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive warranty days, ask for emoji."""
    try:
        days = int(update.message.text.strip())
        if days < 0:
            raise ValueError
        context.user_data["new_prod_warranty"] = days
    except ValueError:
        await update.message.reply_text("❌ Nombre invalide. Envoyez un entier positif :")
        return ADMIN_ADD_PROD_WARRANTY

    await update.message.reply_text(
        f"✅ Garantie : {days} jours\n\n"
        "🎨 Envoyez un <b>emoji</b> pour ce produit :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_PROD_EMOJI


async def admin_add_prod_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive emoji, then ask which Binance account to use."""
    emoji = update.message.text.strip()
    context.user_data["new_prod_emoji"] = emoji

    # Fetch available Binance accounts
    from database.models import get_binance_accounts
    accounts = await get_binance_accounts()

    if not accounts:
        # No Binance accounts configured — create product without one
        return await _create_product_and_ask_broadcast(update, context, binance_account_id=None)

    if len(accounts) == 1:
        # Only one account — use it automatically
        return await _create_product_and_ask_broadcast(update, context, binance_account_id=accounts[0]["id"])

    # Multiple accounts — let admin choose
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for acc in accounts:
        default_tag = " ⭐" if acc.get("is_default") else ""
        uid_short = acc["uid"][:8] + "..." if len(acc["uid"]) > 8 else acc["uid"]
        buttons.append([InlineKeyboardButton(
            f"💳 {acc['label']} ({uid_short}){default_tag}",
            callback_data=f"prod_binance:{acc['id']}",
        )])

    await update.message.reply_text(
        "🔗 <b>Choisissez le compte Binance</b> pour ce produit :",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ADMIN_ADD_PROD_BINANCE


async def admin_add_prod_binance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'prod_binance:{account_id}' callback — select Binance account, then create product."""
    query = update.callback_query
    await query.answer()

    try:
        account_id = int(query.data.split(":")[1])
    except (ValueError, IndexError):
        account_id = None

    return await _create_product_and_ask_broadcast(update, context, binance_account_id=account_id)


async def _create_product_and_ask_broadcast(update, context, binance_account_id=None):
    """Shared helper: create the product and ask about broadcast."""
    ud = context.user_data

    try:
        cat_id = ud.pop("new_prod_cat_id")
        name = ud.pop("new_prod_name", "Sans nom")
        desc = ud.pop("new_prod_desc", "")
        price = ud.pop("new_prod_price", 0)
        warranty = ud.pop("new_prod_warranty", 0)
        emoji = ud.pop("new_prod_emoji", "📦")

        prod_id = await add_product(
            category_id=cat_id,
            name=name,
            description=desc,
            price_usd=price,
            warranty_days=warranty,
            emoji=emoji,
            binance_account_id=binance_account_id,
        )

        # Store created product info in context for potential broadcast
        ud["broadcast_prod_id"] = prod_id
        ud["broadcast_prod_name"] = name
        ud["broadcast_prod_desc"] = desc
        ud["broadcast_prod_price"] = price
        ud["broadcast_prod_emoji"] = emoji

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Diffuser le produit", callback_data="prod_bc_yes")],
            [InlineKeyboardButton("❌ Ne pas diffuser / Terminer", callback_data="prod_bc_no")]
        ])

        msg_text = (
            f"\u2705 <b>Produit cr\u00e9\u00e9 !</b> (ID: {prod_id})\n\n"
            "Voulez-vous <b>diffuser (broadcast)</b> ce nouveau produit \u00e0 tous les utilisateurs avec un bouton d'achat ?"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg_text, parse_mode="HTML", reply_markup=markup)
        else:
            await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=markup)
        return ADMIN_ADD_PROD_BROADCAST_DECISION
    except Exception as exc:
        logger.error("_create_product_and_ask_broadcast: %s", exc, exc_info=True)
        err_msg = "\u26a0\ufe0f Erreur lors de la cr\u00e9ation du produit."
        if update.callback_query:
            await update.callback_query.edit_message_text(err_msg)
        else:
            await update.message.reply_text(err_msg)
        return ConversationHandler.END


async def admin_toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_toggle_prod:{id}' callback — toggle product active status."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        prod_id = int(query.data.split(":")[1])
        await toggle_product(prod_id)
        product = await get_product(prod_id)
        status = "✅ activé" if product and product.get("is_active") else "❌ désactivé"
        await query.answer(f"Produit {status}", show_alert=True)

        # Refresh product detail
        if product:
            stock = await get_stock_count(prod_id)
            active_label = "✅ Actif" if product.get("is_active", True) else "❌ Inactif"
            prod_name = escape_html(product['name'])
            prod_desc = escape_html(product.get('description', 'N/A') or 'N/A')
            text = (
                f"{product['emoji']} <b>{prod_name}</b>\n\n"
                f"📝 {prod_desc}\n"
                f"💰 Prix : {format_price(product['price_usd'])}\n"
                f"🛡️ Garantie : {product.get('warranty_days', 0)} jours\n"
                f"📦 Stock : {stock}\n"
                f"📊 Statut : {active_label}"
            )
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=admin_product_detail_keyboard(product),
            )
    except Exception as exc:
        logger.error("admin_toggle_product: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_del_prod:{id}' callback — delete product."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        prod_id = int(query.data.split(":")[1])
        await delete_product(prod_id)
        await query.edit_message_text(
            "🗑️ <b>Produit supprimé !</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("admin_delete_product: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur lors de la suppression.")


# ══════════════════════════════════════════════
#  STOCK
# ══════════════════════════════════════════════

async def admin_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_stock' callback — show product list to add stock."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        prods = await get_all_products()
        await query.edit_message_text(
            "📥 <b>Gestion du stock</b>\n\n"
            "Sélectionnez un produit pour ajouter du stock :",
            parse_mode="HTML",
            reply_markup=admin_stock_keyboard(prods),
        )
    except Exception as exc:
        logger.error("admin_stock_menu: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_add_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_add_stock:{prod_id}' callback — prompt for stock items."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END
    await query.answer()

    prod_id = int(query.data.split(":")[1])
    product = await get_product(prod_id)
    if not product:
        await query.edit_message_text("❌ Produit introuvable.")
        return ConversationHandler.END

    context.user_data["stock_product_id"] = prod_id
    current_stock = await get_stock_count(prod_id)

    await query.edit_message_text(
        f"📥 <b>Ajouter du stock</b>\n\n"
        f"📦 Produit : {product['emoji']} {product['name']}\n"
        f"📊 Stock actuel : {current_stock}\n\n"
        "Envoyez les comptes/items à ajouter,\n"
        "<b>un par ligne</b> :",
        parse_mode="HTML",
    )
    return ADMIN_ADD_STOCK


async def admin_add_stock_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive stock items (one per line) and add to database."""
    try:
        prod_id = context.user_data.pop("stock_product_id", None)
        if not prod_id:
            await update.message.reply_text("⚠️ Aucun produit sélectionné.")
            return ConversationHandler.END

        raw = update.message.text.strip()
        items = [line.strip() for line in raw.split("\n") if line.strip()]

        if not items:
            await update.message.reply_text("❌ Aucun item détecté. Envoyez un item par ligne.")
            context.user_data["stock_product_id"] = prod_id
            return ADMIN_ADD_STOCK

        count = await add_stock_items(prod_id, items)
        new_stock = await get_stock_count(prod_id)

        # Store stock info in user_data for potential broadcast
        ud = context.user_data
        ud["stock_bc_prod_id"] = prod_id
        ud["stock_bc_count"] = count

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Diffuser l'alerte de restock", callback_data="stock_bc_yes")],
            [InlineKeyboardButton("❌ Ne pas diffuser / Terminer", callback_data="stock_bc_no")]
        ])

        await update.message.reply_text(
            f"✅ <b>{count} item(s) ajouté(s) !</b>\n\n"
            f"📦 Stock total : {new_stock}\n\n"
            "Voulez-vous <b>diffuser (broadcast)</b> une alerte de restockage à tous les utilisateurs ?",
            parse_mode="HTML",
            reply_markup=markup,
        )
        return ADMIN_ADD_STOCK_BROADCAST_DECISION
    except Exception as exc:
        logger.error("admin_add_stock_receive: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Erreur lors de l'ajout du stock.")
        return ConversationHandler.END


async def admin_stock_broadcast_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'stock_bc_yes' callback — broadcast product restock with purchase button."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    prod_id = ud.pop("stock_bc_prod_id", None)
    count = ud.pop("stock_bc_count", 0)

    if not prod_id:
        await query.edit_message_text("❌ Produit introuvable.", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END

    product = await get_product(prod_id)
    if not product:
        await query.edit_message_text("❌ Produit introuvable.", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("📢 Diffusion de l'alerte en cours...")

    from utils.helpers import format_price
    broadcast_text = (
        "🔔 <b>Product Restocked!</b>\n\n"
        f"{product['emoji']} <b>{escape_html(product['name'])}</b> is back in stock!\n"
        f"💰 Price: <b>{format_price(product['price_usd'])}</b>\n\n"
        f"{escape_html(product.get('description', ''))}"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Buy now", callback_data=f"buy:{prod_id}")
    ]])

    sent, failed = await _execute_broadcast(context.bot, broadcast_text, reply_markup=markup)

    await query.edit_message_text(
        f"📢 <b>Alerte de restock diffusée !</b>\n\n"
        f"✅ Envoyé : {sent}\n"
        f"❌ Échoué : {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    return ConversationHandler.END


async def admin_stock_broadcast_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'stock_bc_no' callback — finish stock updates without broadcast."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    ud.pop("stock_bc_prod_id", None)
    ud.pop("stock_bc_count", None)

    await query.edit_message_text(
        "✅ Stock mis à jour sans diffusion.",
        reply_markup=admin_menu_keyboard()
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_stats' callback — show sales stats."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        stats = await get_stats(days=30)
        all_users = await get_all_users()

        text = (
            "📊 <b>Statistiques (30 derniers jours)</b>\n"
            "\n"
            f"👥 <b>Utilisateurs :</b> {len(all_users)}\n"
            f"📦 <b>Commandes totales :</b> {stats.get('total_orders', 0)}\n"
            f"✅ <b>Commandes complétées :</b> {stats.get('completed_orders', 0)}\n"
            f"⏳ <b>Commandes en attente :</b> {stats.get('pending_orders', 0)}\n"
            f"💰 <b>Revenus :</b> {format_price(stats.get('total_revenue', 0))}\n"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_keyboard("adm_menu"),
        )
    except Exception as exc:
        logger.error("admin_stats: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur lors du chargement des statistiques.")


# Helper to execute broadcast to all users (rich media: text/photo and button)
async def _execute_broadcast(bot, text, photo_file_id=None, reply_markup=None):
    from database.models import get_all_users
    users = await get_all_users()
    sent = 0
    failed = 0
    for user in users:
        if user.get("is_banned"):
            continue
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=user["telegram_id"],
                    photo=photo_file_id,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            sent += 1
        except Exception:
            failed += 1
    return sent, failed


# Decision handlers for broadcasting a newly created product
async def admin_prod_broadcast_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'prod_bc_yes' callback — broadcast product with purchase button."""
    query = update.callback_query
    await query.answer()
    lang = await get_user_lang(update.effective_user.id)
    ud = context.user_data

    prod_id = ud.get("broadcast_prod_id")
    name = escape_html(ud.get("broadcast_prod_name", "Sans nom"))
    desc = escape_html(ud.get("broadcast_prod_desc", ""))
    price = ud.get("broadcast_prod_price")
    emoji = ud.get("broadcast_prod_emoji")

    if not prod_id:
        await query.edit_message_text("❌ Produit introuvable.", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("📢 Diffusion en cours...")

    broadcast_text = (
        "🔔 <b>Nouveau produit disponible !</b>\n\n"
        f"{emoji} <b>{name}</b>\n"
        f"💰 Prix : <b>{format_price(price)}</b>\n\n"
        f"📝 {desc}"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f"buy:{prod_id}")
    ]])

    sent, failed = await _execute_broadcast(context.bot, broadcast_text, reply_markup=markup)

    # Clean up
    for key in ["broadcast_prod_id", "broadcast_prod_name", "broadcast_prod_desc", "broadcast_prod_price", "broadcast_prod_emoji"]:
        ud.pop(key, None)

    await query.edit_message_text(
        f"📢 <b>Broadcast terminé !</b>\n\n"
        f"✅ Envoyé : {sent}\n"
        f"❌ Échoué : {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    return ConversationHandler.END


async def admin_prod_broadcast_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'prod_bc_no' callback — finish product creation without broadcast."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    # Clean up
    for key in ["broadcast_prod_id", "broadcast_prod_name", "broadcast_prod_desc", "broadcast_prod_price", "broadcast_prod_emoji"]:
        ud.pop(key, None)

    await query.edit_message_text(
        "✅ Produit créé sans diffusion.",
        reply_markup=admin_menu_keyboard()
    )
    return ConversationHandler.END


#  BROADCAST (Riche)
# ══════════════════════════════════════════════

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_broadcast' callback — start broadcast flow."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END
    await query.answer()

    await query.edit_message_text(
        "📢 <b>Broadcast (Médias Riches)</b>\n\n"
        "Envoyez votre message de diffusion (texte seul, ou photo avec légende) :",
        parse_mode="HTML",
    )
    return ADMIN_BROADCAST


async def admin_broadcast_receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive text or photo for the broadcast and ask for button type."""
    ud = context.user_data

    if update.message.photo:
        ud["bc_photo_file_id"] = update.message.photo[-1].file_id
        ud["bc_text"] = update.message.caption_html or ""
    else:
        ud["bc_photo_file_id"] = None
        ud["bc_text"] = update.message.text_html if update.message.text else ""

    if not ud["bc_text"] and not ud["bc_photo_file_id"]:
        await update.message.reply_text(
            "❌ Le message de diffusion ne peut pas être vide. Veuillez envoyer du texte ou une photo :",
            parse_mode="HTML"
        )
        return ADMIN_BROADCAST

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Bouton d'Achat (Produit)", callback_data="bc_btn:buy")],
        [InlineKeyboardButton("🌐 Bouton de Lien Web", callback_data="bc_btn:url")],
        [InlineKeyboardButton("❌ Aucun bouton", callback_data="bc_btn:none")],
    ])

    await update.message.reply_text(
        "🎨 <b>Bouton Interactif</b>\n\n"
        "Voulez-vous ajouter un bouton interactif sous ce message ?",
        parse_mode="HTML",
        reply_markup=markup
    )
    return ADMIN_BROADCAST_BTN_TYPE


async def admin_broadcast_btn_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process selection of button type."""
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":")[1]
    ud = context.user_data

    if choice == "none":
        # Broadcast immediately
        await query.edit_message_text("📢 Diffusion en cours...")
        sent, failed = await _execute_broadcast(
            context.bot,
            ud["bc_text"],
            photo_file_id=ud.get("bc_photo_file_id")
        )
        await query.edit_message_text(
            f"📢 <b>Broadcast terminé !</b>\n\n"
            f"✅ Envoyé : {sent}\n"
            f"❌ Échoué : {failed}",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return ConversationHandler.END

    elif choice == "buy":
        # List active products
        from database.models import get_all_products
        products = await get_all_products()
        buttons = []
        for p in products:
            if p.get("is_active", 1):
                buttons.append([InlineKeyboardButton(f"{p['emoji']} {p['name']}", callback_data=f"bc_buy_prod:{p['id']}")])
        buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="adm_menu")])

        await query.edit_message_text(
            "🛒 <b>Sélectionner le produit</b>\n\n"
            "Choisissez le produit à lier au bouton d'achat :",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return ADMIN_BROADCAST_BTN_PRODUCT

    elif choice == "url":
        # Prompt for URL formatting
        await query.edit_message_text(
            "🌐 <b>Bouton de Lien Web</b>\n\n"
            "Veuillez envoyer le texte du bouton et l'URL sous la forme :\n"
            "<code>Texte du Bouton | URL</code>\n\n"
            "<i>Exemple : Rejoindre le canal | https://t.me/mychannel</i>",
            parse_mode="HTML"
        )
        return ADMIN_BROADCAST_BTN_URL


async def admin_broadcast_btn_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product selection, add buy button and broadcast."""
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split(":")[1])
    ud = context.user_data

    await query.edit_message_text("📢 Diffusion en cours...")

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f"buy:{prod_id}")
    ]])

    sent, failed = await _execute_broadcast(
        context.bot,
        ud["bc_text"],
        photo_file_id=ud.get("bc_photo_file_id"),
        reply_markup=markup
    )

    await query.edit_message_text(
        f"📢 <b>Broadcast terminé !</b>\n\n"
        f"✅ Envoyé : {sent}\n"
        f"❌ Échoué : {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    return ConversationHandler.END


async def admin_broadcast_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URL input, add link button and broadcast."""
    text_input = update.message.text.strip()
    parts = text_input.split("|")
    ud = context.user_data

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ Format invalide. Veuillez réessayer sous la forme :\n"
            "<code>Texte du Bouton | URL</code>",
            parse_mode="HTML"
        )
        return ADMIN_BROADCAST_BTN_URL

    btn_label = parts[0].strip()
    url_target = parts[1].strip()

    if not btn_label or not url_target:
        await update.message.reply_text(
            "❌ Le texte du bouton et l'URL ne peuvent pas être vides. Veuillez réessayer sous la forme :\n"
            "<code>Texte du Bouton | URL</code>",
            parse_mode="HTML"
        )
        return ADMIN_BROADCAST_BTN_URL

    if not url_target.startswith(("http://", "https://")):
        url_target = "https://" + url_target

    await update.message.reply_text("📢 Diffusion en cours...")

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(btn_label, url=url_target)
    ]])

    sent, failed = await _execute_broadcast(
        context.bot,
        ud["bc_text"],
        photo_file_id=ud.get("bc_photo_file_id"),
        reply_markup=markup
    )

    await update.message.reply_text(
        f"📢 <b>Broadcast terminé !</b>\n\n"
        f"✅ Envoyé : {sent}\n"
        f"❌ Échoué : {failed}",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════
#  TICKETS (admin view)
# ══════════════════════════════════════════════

async def admin_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_tickets' callback — list open tickets."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        tickets = await get_open_tickets()
        if not tickets:
            await query.edit_message_text(
                "🎫 <b>Tickets</b>\n\n"
                "📭 Aucun ticket ouvert.",
                parse_mode="HTML",
                reply_markup=back_keyboard("adm_menu"),
            )
            return

        await query.edit_message_text(
            f"🎫 <b>Tickets ouverts ({len(tickets)})</b>\n\n"
            "Sélectionnez un ticket :",
            parse_mode="HTML",
            reply_markup=admin_tickets_keyboard(tickets),
        )
    except Exception as exc:
        logger.error("admin_tickets: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin ticket detail with reply/close buttons (re-uses 'ticket:{id}')."""
    query = update.callback_query
    if not _admin_check(update):
        # Non-admins see user-side ticket detail (handled in support.py)
        return
    await query.answer()

    try:
        ticket_id = int(query.data.split(":")[1])
        ticket = await get_ticket(ticket_id)
        if not ticket:
            await query.edit_message_text("❌ Ticket introuvable.")
            return

        status_map = {"OPEN": "🟢 Ouvert", "REPLIED": "💬 Répondu", "CLOSED": "🔴 Fermé"}
        status = status_map.get(ticket.get("status", "OPEN"), "❓")

        text = (
            f"🎫 <b>Ticket #{ticket['id']}</b>\n\n"
            f"👤 User : <code>{ticket.get('user_telegram_id', '?')}</code>\n"
            f"📊 Statut : {status}\n"
            f"📝 Message :\n{escape_html(ticket.get('message', 'N/A'))}\n"
        )
        if ticket.get("admin_reply"):
            text += f"\n💬 Réponse :\n{escape_html(ticket['admin_reply'])}\n"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_ticket_detail_keyboard(ticket),
        )
    except Exception as exc:
        logger.error("admin_ticket_detail: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_reply_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_reply_ticket:{id}' callback — ask for reply text."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return ConversationHandler.END
    await query.answer()

    ticket_id = int(query.data.split(":")[1])
    context.user_data["reply_ticket_id"] = ticket_id

    await query.edit_message_text(
        f"💬 <b>Répondre au ticket #{ticket_id}</b>\n\n"
        "Envoyez votre réponse :",
        parse_mode="HTML",
    )
    return ADMIN_REPLY_TICKET


async def admin_reply_ticket_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive admin reply and send to user."""
    try:
        ticket_id = context.user_data.pop("reply_ticket_id", None)
        if not ticket_id:
            await update.message.reply_text("⚠️ Aucun ticket sélectionné.")
            return ConversationHandler.END

        reply_text = update.message.text.strip()
        await reply_ticket(ticket_id, reply_text)

        ticket = await get_ticket(ticket_id)

        # Notify user
        if ticket:
            try:
                user_lang = await get_user_lang(ticket["user_telegram_id"])
                await context.bot.send_message(
                    ticket["user_telegram_id"],
                    f"{t('ticket_replied', user_lang).format(id=ticket_id)}\n\n"
                    f"{escape_html(reply_text)}",
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Could not notify user: %s", exc)

        await update.message.reply_text(
            f"✅ Réponse envoyée au ticket #{ticket_id}",
            reply_markup=admin_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("admin_reply_ticket_send: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Erreur.")

    return ConversationHandler.END


async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_close_ticket:{id}' callback — close ticket."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        ticket_id = int(query.data.split(":")[1])
        await close_ticket(ticket_id)

        ticket = await get_ticket(ticket_id)
        if ticket:
            try:
                user_lang = await get_user_lang(ticket["user_telegram_id"])
                await context.bot.send_message(
                    ticket["user_telegram_id"],
                    t("ticket_closed", user_lang).format(id=ticket_id),
                )
            except Exception:
                pass

        await query.edit_message_text(
            f"🔒 <b>Ticket #{ticket_id} fermé.</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("admin_close_ticket: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


# ══════════════════════════════════════════════
#  ORDERS (admin view)
# ══════════════════════════════════════════════

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_orders' callback — list pending orders."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        orders = await get_pending_orders()
        if not orders:
            await query.edit_message_text(
                "📋 <b>Commandes</b>\n\n"
                "📭 Aucune commande en attente.",
                parse_mode="HTML",
                reply_markup=back_keyboard("adm_menu"),
            )
            return

        await query.edit_message_text(
            f"📋 <b>Commandes en attente ({len(orders)})</b>\n\n"
            "Cliquez pour confirmer manuellement :",
            parse_mode="HTML",
            reply_markup=admin_orders_keyboard(orders),
        )
    except Exception as exc:
        logger.error("admin_orders: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur.")


async def admin_activations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_activations' callback - list pending manual activations."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()
    admin_lang = await get_user_lang(update.effective_user.id)

    try:
        activations, _total = await get_activation_orders(limit=100, offset=0)
        if not activations:
            await query.edit_message_text(
                t("admin_activation_empty", admin_lang),
                parse_mode="HTML",
                reply_markup=back_keyboard("adm_menu"),
            )
            return

        buttons = []
        for order in activations:
            username = order.get("username")
            client = f"@{username}" if username else (order.get("user_first_name") or str(order.get("user_telegram_id")))
            product_name = order.get("product_name") or f"Produit #{order.get('product_id')}"
            status_icon = "✅" if order.get("status") == "AWAITING_ACTIVATION" else "⏳"
            buttons.append([
                InlineKeyboardButton(
                    f"{status_icon} {client} - {product_name} #{order['id']}",
                    callback_data=f"adm_activation:{order['id']}",
                )
            ])

        buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_menu")])
        await query.edit_message_text(
            t("admin_activation_list", admin_lang).format(count=len(activations)),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as exc:
        logger.error("admin_activations: %s", exc, exc_info=True)
        await query.edit_message_text(t("admin_activation_load_error", admin_lang))


async def admin_activation_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show one manual activation request with accept button."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()
    admin_lang = await get_user_lang(update.effective_user.id)

    try:
        order_id = int(query.data.split(":")[1])
        activations, _total = await get_activation_orders(limit=200, offset=0)
        order = next((o for o in activations if int(o["id"]) == order_id), None)
        if not order:
            raw_order = await get_order(order_id)
            if not raw_order:
                await query.edit_message_text(t("admin_activation_not_found", admin_lang), reply_markup=back_keyboard("adm_activations"))
                return
            order = raw_order

        product = await get_product(order.get("product_id"))
        product_name = order.get("product_name") or (product["name"] if product else f"Produit #{order.get('product_id')}")
        username = order.get("username")
        first_name = order.get("user_first_name") or ""
        client_line = f"@{username}" if username else (first_name or str(order.get("user_telegram_id")))
        activation_identifier = order.get("activation_identifier")
        status = order.get("status")

        text = (
            f"⚡ <b>Activation #{order_id}</b>\n\n"
            f"Client: <b>{escape_html(client_line)}</b>\n"
            f"ID Telegram: <code>{order.get('user_telegram_id')}</code>\n"
            f"Produit: <b>{escape_html(product_name)}</b>\n"
            f"Quantité: {order.get('quantity', 1)}\n"
            f"Montant: {format_price(order.get('amount_usd', 0))}\n"
            f"Statut: <code>{escape_html(status or '')}</code>\n\n"
            "Identifiant à activer:\n"
            f"<code>{escape_html(activation_identifier or 'Le client ne l’a pas encore envoyé.')}</code>"
        )

        buttons = []
        if status == "AWAITING_ACTIVATION" and activation_identifier:
            buttons.append([InlineKeyboardButton(f"✅ {t('activation_admin_button', admin_lang)}", callback_data=f"adm_activate_order:{order_id}")])
        buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="adm_activations")])

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as exc:
        logger.error("admin_activation_detail: %s", exc, exc_info=True)
        await query.edit_message_text(t("admin_activation_load_error", admin_lang))


async def admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'adm_confirm_pay:{order_id}' callback — manually confirm payment."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)
        admin_lang = await get_user_lang(update.effective_user.id)

        if not order:
            await query.edit_message_text("❌ Commande introuvable.")
            return

        product = await get_product(order.get("product_id"))
        if product and product.get("delivery_type") == "activation":
            await update_order_status(order_id, "AWAITING_ACTIVATION_INFO", payment_method=order.get("payment_method") or "manual", binance_order_id="MANUAL")
            try:
                user_lang = await get_user_lang(order["user_telegram_id"])
                await context.bot.send_message(
                    order["user_telegram_id"],
                    t("activation_manual_payment_prompt", user_lang).format(product=escape_html(product["name"])),
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Could not notify activation user: %s", exc)

            await query.edit_message_text(
                t("admin_activation_user_must_send", admin_lang).format(order_id=order_id),
                reply_markup=admin_menu_keyboard(admin_lang),
            )
            return

        # Mark as completed
        await update_order_status(order_id, "COMPLETED", binance_order_id="MANUAL")

        # Deliver product
        delivered = await deliver_order(order_id, order.get("product_id"))

        if delivered:
            product = await get_product(order.get("product_id"))
            warranty_days = product.get("warranty_days", 0) if product else 0

            # Notify user
            try:
                user_lang = await get_user_lang(order["user_telegram_id"])
                accounts_text = "\n".join(f"🔑 <code>{escape_html(item['account_data'])}</code>" for item in delivered)
                await context.bot.send_message(
                    order["user_telegram_id"],
                    f"{t('payment_confirmed', user_lang)}\n\n"
                    f"{t('your_account', user_lang)}\n"
                    f"{accounts_text}\n\n"
                    f"{t('warranty_lbl', user_lang).format(days=warranty_days)}\n"
                    f"{t('save_info', user_lang)}\n\n"
                    f"{t('thank_you', user_lang)}",
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Could not notify user: %s", exc)

            await query.edit_message_text(
                f"✅ <b>Commande #{order_id} confirmée et livrée !</b>",
                parse_mode="HTML",
                reply_markup=admin_menu_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"✅ Commande #{order_id} confirmée.\n"
                "⚠️ Livraison automatique impossible (stock vide ?).",
                reply_markup=admin_menu_keyboard(),
            )
    except Exception as exc:
        logger.error("admin_confirm_payment: %s", exc, exc_info=True)
        await query.edit_message_text("⚠️ Erreur lors de la confirmation.")


# ══════════════════════════════════════════════
#  Fallback
# ══════════════════════════════════════════════

async def admin_complete_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete a manual activation order from an admin Telegram button."""
    query = update.callback_query
    if not _admin_check(update):
        await _not_admin(update)
        return
    await query.answer()

    try:
        order_id = int(query.data.split(":")[1])
        order = await get_order(order_id)
        if not order:
            await query.edit_message_text("Commande introuvable.")
            return
        if order.get("status") == "COMPLETED":
            admin_lang = await get_user_lang(update.effective_user.id)
            await query.edit_message_text(t("admin_activation_already_done", admin_lang).format(order_id=order_id))
            return
        if order.get("status") != "AWAITING_ACTIVATION":
            admin_lang = await get_user_lang(update.effective_user.id)
            await query.edit_message_text(t("admin_activation_wrong_status", admin_lang))
            return

        await update_order_status(
            order_id,
            "COMPLETED",
            activation_status="done",
            activated_at=datetime.utcnow().isoformat(),
        )

        product = await get_product(order.get("product_id"))
        product_name = product["name"] if product else f"#{order.get('product_id')}"
        try:
            user_lang = await get_user_lang(order["user_telegram_id"])
            await context.bot.send_message(
                order["user_telegram_id"],
                t("activation_completed_user", user_lang).format(
                    product=escape_html(product_name),
                    order_id=order_id,
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Could not notify activated user: %s", exc)

        admin_lang = await get_user_lang(update.effective_user.id)
        await query.edit_message_text(
            t("admin_activation_done_admin", admin_lang).format(order_id=order_id),
            reply_markup=back_keyboard("adm_activations"),
        )
    except Exception as exc:
        logger.error("admin_complete_activation: %s", exc, exc_info=True)
        admin_lang = await get_user_lang(update.effective_user.id)
        await query.edit_message_text(t("admin_activation_error", admin_lang))


async def _admin_start_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback: end admin conversation and go to /start."""
    from handlers.start import start_command
    await start_command(update, context)
    return ConversationHandler.END


# ══════════════════════════════════════════════
#  ConversationHandler factory
# ══════════════════════════════════════════════

def get_admin_conversation_handler() -> ConversationHandler:
    """Build and return the admin ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_command),
            CallbackQueryHandler(admin_menu, pattern=r"^adm_menu$"),
            # Allow entering from any admin callback
            CallbackQueryHandler(admin_categories, pattern=r"^adm_cats$"),
            CallbackQueryHandler(admin_products, pattern=r"^adm_prods$"),
            CallbackQueryHandler(admin_stock_menu, pattern=r"^adm_stock$"),
            CallbackQueryHandler(admin_stats, pattern=r"^adm_stats$"),
            CallbackQueryHandler(admin_orders, pattern=r"^adm_orders$"),
            CallbackQueryHandler(admin_activations, pattern=r"^adm_activations$"),
            CallbackQueryHandler(admin_activation_detail, pattern=r"^adm_activation:"),
            CallbackQueryHandler(admin_tickets, pattern=r"^adm_tickets$"),
            CallbackQueryHandler(admin_category_detail, pattern=r"^adm_cat:"),
            CallbackQueryHandler(admin_product_detail, pattern=r"^adm_prod:\d+$"),
            CallbackQueryHandler(admin_toggle_product, pattern=r"^adm_toggle_prod:"),
            CallbackQueryHandler(admin_delete_product, pattern=r"^adm_del_prod:"),
            CallbackQueryHandler(admin_close_ticket, pattern=r"^adm_close_ticket:"),
            CallbackQueryHandler(admin_confirm_payment, pattern=r"^adm_confirm_pay:"),
            CallbackQueryHandler(admin_complete_activation, pattern=r"^adm_activate_order:"),
            # Multi-step entry points
            CallbackQueryHandler(admin_add_cat_start, pattern=r"^adm_add_cat$"),
            CallbackQueryHandler(admin_add_prod_start, pattern=r"^adm_add_prod:"),
            CallbackQueryHandler(admin_add_stock_start, pattern=r"^adm_add_stock:"),
            CallbackQueryHandler(admin_broadcast_start, pattern=r"^adm_broadcast$"),
            CallbackQueryHandler(admin_reply_ticket_start, pattern=r"^adm_reply_ticket:"),
            # Ticket detail from admin view
            CallbackQueryHandler(admin_ticket_detail, pattern=r"^ticket:"),
        ],
        states={
            ADMIN_ADD_CAT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_cat_name),
            ],
            ADMIN_ADD_CAT_EMOJI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_cat_emoji),
            ],
            ADMIN_ADD_PROD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prod_name),
            ],
            ADMIN_ADD_PROD_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prod_desc),
            ],
            ADMIN_ADD_PROD_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prod_price),
            ],
            ADMIN_ADD_PROD_WARRANTY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prod_warranty),
            ],
            ADMIN_ADD_PROD_EMOJI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prod_emoji),
            ],
            ADMIN_ADD_PROD_BINANCE: [
                CallbackQueryHandler(admin_add_prod_binance, pattern=r"^prod_binance:"),
            ],
            ADMIN_ADD_PROD_BROADCAST_DECISION: [
                CallbackQueryHandler(admin_prod_broadcast_yes, pattern=r"^prod_bc_yes$"),
                CallbackQueryHandler(admin_prod_broadcast_no, pattern=r"^prod_bc_no$"),
            ],
            ADMIN_ADD_STOCK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_stock_receive),
            ],
            ADMIN_ADD_STOCK_BROADCAST_DECISION: [
                CallbackQueryHandler(admin_stock_broadcast_yes, pattern=r"^stock_bc_yes$"),
                CallbackQueryHandler(admin_stock_broadcast_no, pattern=r"^stock_bc_no$"),
            ],
            ADMIN_BROADCAST: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, admin_broadcast_receive_content),
            ],
            ADMIN_BROADCAST_BTN_TYPE: [
                CallbackQueryHandler(admin_broadcast_btn_type, pattern=r"^bc_btn:"),
            ],
            ADMIN_BROADCAST_BTN_PRODUCT: [
                CallbackQueryHandler(admin_broadcast_btn_product, pattern=r"^bc_buy_prod:"),
                CallbackQueryHandler(admin_menu, pattern=r"^adm_menu$"),
            ],
            ADMIN_BROADCAST_BTN_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_btn_url),
            ],
            ADMIN_REPLY_TICKET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_ticket_send),
            ],
        },
        fallbacks=[
            CommandHandler("start", _admin_start_fallback),
            CommandHandler("admin", admin_command),
            CallbackQueryHandler(admin_menu, pattern=r"^adm_menu$"),
        ],
        per_message=False,
        allow_reentry=True,
        name="admin_conversation",
    )
