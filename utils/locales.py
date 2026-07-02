# utils/locales.py — Traductions multilingues (EN / FR / AR)
# Utiliser: from utils.locales import t
#           t("welcome", "fr") → "🎉 Bienvenue ..."

from __future__ import annotations

LANGUAGES = {
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "ar": "🇸🇦 العربية",
    "zh": "🇨🇳 简体中文",
}

TRANSLATIONS: dict[str, dict[str, str]] = {

    # ═══════════════════════════════════════════
    #  ENGLISH
    # ═══════════════════════════════════════════
    "en": {
        # ── Start / Menu ──
        "choose_language": "🌐 Choose your language:",
        "language_set": "✅ Language set to English!",
        "welcome": (
            "🎉 <b>Welcome!</b>\n\n"
            "🎯 <b>Quick guide:</b>\n"
            "1. Tap \"🛒 Buy\"\n"
            "2. Choose the product you want\n"
            "3. Complete the payment\n"
            "4. After payment, send the Order ID for verification\n\n"
            "🎯 <b>Choose an option:</b>"
        ),
        "quick_menu_enabled": "🎯 Quick menu enabled below the chat bar.",

        # ── Buttons ──
        "btn_buy": "🛒 Buy",
        "btn_profile": "👤 Profile",
        "btn_history": "📋 Purchase history",
        "btn_support": "💬 Support",
        "btn_products": "🛍️ Products",
        "btn_back": "◀️ Back",
        "btn_cancel": "❌ Cancel",
        "btn_refresh": "🔄 Refresh products",
        "btn_buy_now": "🛒 Buy now",
        "btn_pay_binance": "◇ Pay with Binance",
        "btn_i_paid": "✅ I paid",
        "btn_new_ticket": "📝 New ticket",
        "btn_my_tickets": "📋 My tickets",
        "btn_language": "🌐 Language",
        "btn_start": "🚀 Start",
        "btn_wallet": "💰 Wallet",
        "btn_referral": "👥 Referral",

        # ── Wallet ──
        "wallet_title": "💰 <b>My Wallet</b>",
        "wallet_balance_lbl": "💵 Balance:",
        "wallet_topup": "➕ Top Up",
        "wallet_history": "📜 History",
        "wallet_topup_title": "💰 <b>Top Up Wallet</b>\n\n✏️ Send the amount in USD you want to add:\n(Example: 5, 10.50, 25)",
        "wallet_topup_preset": "Or choose a preset amount:",
        "wallet_invalid_amount": "❌ Invalid amount. Please enter a number (ex: 5, 10, 20).",
        "wallet_credited": "✅ <b>Wallet credited!</b>\n\n💵 +${amount} added\n💰 New balance: ${balance}",
        "wallet_insufficient": "❌ <b>Insufficient balance!</b>\n\n💰 Your balance: ${balance}\n💲 Required: ${required}\n\nPlease top up your wallet first.",
        "wallet_paid": "✅ <b>Paid with Wallet!</b>\n\n💲 Debited: ${amount}\n💰 Remaining: ${balance}",
        "wallet_no_transactions": "📭 No transactions yet.",
        "wallet_tx_topup": "➕ Top Up",
        "wallet_tx_purchase": "🛒 Purchase",
        "btn_pay_wallet": "💰 Pay with Wallet (${balance})",

        # ── Categories / Products ──
        "categories_title": "📂 <b>Categories</b>\n\nChoose a category:",
        "choose_quantity": "🔢 <b>Quantity</b>\n\n✏️ Send the number of items you want to buy:\n📦 Available stock: {stock}",
        "invalid_quantity": "❌ <b>Invalid quantity</b>\n\nPlease send a valid positive number.",
        "insufficient_stock": "❌ <b>Insufficient stock</b>\n\nWe only have {stock} items available. Please choose a lower quantity.",
        "quantity_lbl": "🔢 <b>Quantity:</b> {qty}",
        "no_categories": "📭 No categories available at the moment.",
        "product_not_found": "❌ Product not found.",
        "access_denied": "❌ Access Denied: This order does not belong to you.",
        "cannot_cancel": "❌ This order cannot be cancelled (status: {status})",
        "tx_used": "❌ This transaction has already been used.",
        "max_topup": "⚠️ Maximum top-up amount is $10,000.",
        "contact_support": "I paid / Contact Support",
        "banned_msg": "⛔ You have been banned from this bot.",
        "out_of_stock": "❌ <b>Out of stock!</b>\nThis product is currently unavailable.",
        "product_detail": (
            "{emoji} <b>{name}</b>\n"
            "💵 <b>Price:</b> {price}\n"
            "🛡️ <b>Warranty:</b> {warranty} days\n"
            "📦 <b>Stock:</b> {stock} accounts\n"
            "📊 <b>Sold:</b> {sold} accounts\n\n"
            "❞ <b>Description:</b>\n{description}"
        ),

        # ── Payment ──
        "new_order": "🛒 <b>New order</b>",
        "product_lbl": "📦 <b>Product:</b>",
        "total_lbl": "💰 <b>Total:</b>",
        "ref_lbl": "🔖 <b>Ref:</b>",
        "choose_payment": "💳 <b>Choose payment method:</b>",
        "binance_title": "◇ <b>Payment via Binance Pay</b>",
        "binance_id_lbl": "◇ <b>Binance ID</b> (tap to copy):",
        "amount_lbl": "💰 <b>Amount to transfer:</b>",
        "pay_instructions": "📝 <b>Instructions:</b>",
        "pay_step1": "1️⃣ Send the exact amount via Binance Pay",
        "pay_step2": "2️⃣ After payment, send the <b>Order ID</b> or\n   <b>transaction reference</b> here",
        "waiting_payment": "⏳ <i>Waiting for your payment…</i>",
        "verifying": "🔍 Verifying payment…",
        "payment_confirmed": "✅ <b>Payment confirmed!</b>",
        "your_account": "📧 <b>Here is your account:</b>",
        "warranty_lbl": "🛡️ <b>Warranty:</b> {days} days",
        "save_info": "📌 <b>Keep this information safe</b>",
        "thank_you": "Thank you for your purchase! 🙏",
        "delivery_error": "⚠️ <b>Stock unavailable!</b>\nIt seems you took too long to complete the payment and the stock was sold out.\n\n⚠️ <b>Action required:</b> Please contact support with Order ID <b>#{order_id}</b> to get a manual delivery or refund.",
        "payment_not_detected": "⏳ <b>Payment not detected</b>",
        "retry_order_id": "Please verify that you sent the payment,\nthen <b>try again by sending the Order ID</b>.",
        "support_hint": "💡 <i>If the problem persists, contact support.</i>",
        "no_pending_order": "⚠️ No pending order. Use /start to begin again.",
        "check_title": "📝 <b>Payment verification</b>",
        "order_lbl": "🔖 <b>Order:</b>",
        "send_order_id": "📩 Send the <b>Order ID</b> or <b>transaction reference</b>\nto verify your payment.",
        "promo_prompt": "🎫 <b>Apply Promo Code</b>\n\n✏️ Send your promo code:",
        "promo_success": "✅ <b>Promo code applied!</b>\n\n🎉 Discount: <b>{discount}</b>\n💰 New total: <b>{total}</b>",
        "promo_invalid": "❌ <b>Invalid or expired promo code!</b>\n\nPlease check the code and send it again, or cancel.",
        "promo_max_uses_reached": "❌ <b>Usage limit reached!</b>\n\nYou have already reached the maximum number of times you can use this promo code.",
        "promo_product_invalid": "❌ <b>Invalid Product!</b>\n\nThis promo code cannot be applied to this product.",
        "promo_qty_limit": "❌ <b>Quantity Limit!</b>\n\nThis promo code can only be used for orders of up to {max_qty} items.",
        "promo_already_applied": "❌ <b>A promo code has already been applied to this order.</b>",
        "order_expired_notification": "⏳ <b>Time expired!</b>\nYour order <b>#{order_id}</b> has been automatically cancelled because the payment was not received within the 5-minute time limit.\nIf you still wish to purchase or if you have already paid, please start a new order.",
        "order_cancelled": "❌ <b>Order cancelled</b>\n\nYour order has been cancelled.\nReturn to the main menu to continue.",
        "order_timeout": "❌ <b>Order expired</b>\n\nYour order #{id} has expired because payment was not received within 5 minutes.",
        "order_error": "⚠️ Error creating the order.",
        "pay_error": "⚠️ Error initializing payment.",
        "cancel_error": "⚠️ Error cancelling.",
        "verify_error": "⚠️ Verification error. Please try again.",

        # ── Profile ──
        "profile_title": "👤 <b>Your Profile</b>",
        "id_lbl": "🆔 <b>ID:</b>",
        "name_lbl": "👤 <b>Name:</b>",
        "joined_lbl": "📅 <b>Joined:</b>",
        "purchases_lbl": "🛒 <b>Total purchases:</b>",
        "spent_lbl": "💰 <b>Total spent:</b>",

        # ── History ──
        "history_title": "📋 <b>Purchase History</b>",
        "no_orders": "📭 You have no orders yet.",
        "order_detail": "📦 <b>Order #{id}</b>",
        "status_lbl": "📊 <b>Status:</b>",
        "date_lbl": "📅 <b>Date:</b>",
        "account_lbl": "📧 <b>Account:</b>",

        # ── Support ──
        "support_title": "💬 <b>Support</b>\n\nFor support, please contact the administrator on Telegram: @Drbatman2",
        "describe_problem": "📝 Describe your problem:",
        "ticket_created": "✅ Ticket #{id} created! We will respond shortly.",
        "no_tickets": "📭 No tickets.",
        "ticket_title": "🎫 <b>Ticket #{id}</b>",
        "message_lbl": "📝 <b>Message:</b>",
        "reply_lbl": "💬 <b>Reply:</b>",
        "ticket_replied": "💬 <b>Reply to your ticket #{id}</b>",
        "ticket_closed": "🔒 Your ticket #{id} has been closed.\nThank you for contacting us! 🙏",

        # ── Statuses ──
        "s_pending": "⏳ Pending",
        "s_completed": "✅ Completed",
        "s_cancelled": "❌ Cancelled",
        "s_awaiting": "⏳ Awaiting payment",
        "s_open": "🟢 Open",
        "s_replied": "💬 Replied",
        "s_closed": "🔴 Closed",

        # ── Notifications (admin) ──
        "notif_sale": "🔔 <b>New sale!</b>",
        "notif_low_stock": "⚠️ <b>Low stock!</b>",
        "notif_remaining": "📉 Remaining:",
        "notif_manual": "🔔 <b>Manual verification required</b>",
        "notif_order_id": "📝 Submitted Order ID:",

        # ── Errors ──
        "error_generic": "⚠️ An error occurred.",

        # ── Admin Panel ──
        "admin_panel": "🔧 <b>Admin Panel</b>\n\nSelect an option:",
        "admin_access_denied": "🚫 Access denied. Admins only.",
        "admin_categories_title": "📂 <b>Category Management</b>\n\nTotal: {count} category(ies)",
        "admin_products_title": "📦 <b>Product Management</b>",
        "admin_stock_title": "📦 <b>Stock Management</b>\n\nChoose a product to add stock:",
        "admin_enter_cat_name": "📝 Enter the category name:",
        "admin_enter_cat_emoji": "🎨 Send an emoji for this category (or /skip):",
        "admin_cat_created": "✅ Category created!",
        "admin_enter_prod_name": "📝 Enter the product name:",
        "admin_enter_prod_desc": "📝 Enter product description (or /skip):",
        "admin_enter_prod_price": "💰 Enter price in USD:",
        "admin_enter_prod_warranty": "🔒 Enter warranty days (or /skip for 0):",
        "admin_enter_prod_emoji": "🎨 Send an emoji (or /skip):",
        "admin_prod_created": "✅ Product created!",
        "admin_enter_stock": "📋 Send accounts (one per line):",
        "admin_stock_added": "✅ Added {count} account(s) to stock!",
        "admin_stats_title": "📊 <b>Statistics (30 days)</b>",
        "admin_stats_revenue": "💰 Revenue: ${revenue}",
        "admin_stats_orders": "📦 Orders: {orders}",
        "admin_stats_completed": "✅ Completed: {completed}",
        "admin_stats_users": "👥 Users: {users}",
        "admin_broadcast_prompt": "📢 Send the message to broadcast to all users:",
        "admin_broadcast_sent": "✅ Sent to {sent}/{total} users.",
        "admin_no_pending": "✅ No pending orders.",
        "admin_no_tickets": "✅ No open tickets.",
        "admin_order_confirmed": "✅ Order #{id} confirmed!",
        "admin_ticket_replied": "✅ Ticket #{id} replied!",
        "admin_not_found": "❌ Not found.",
        "admin_error": "⚠️ Error.",
        # ── Referral Program ──
        "referral_title": "👥 <b>Referral Program</b>\n\nInvite your friends using your referral link! For every <b>20 friends</b> you refer, you will receive a <b>free link</b>.\n\nTo claim your reward, simply open a support ticket and contact the admin.\n\n🔗 <b>Your referral link:</b>\n<code>{link}</code>\n\n📊 <b>Statistics:</b>\n- Friends referred: <b>{count}</b>",
        "referral_notif": "🎁 <b>Referral commission received!</b>\nYou have earned a commission of <b>{amount}</b> from the purchase of your friend {friend}.",
        # ── BEP20 USDT Payment ──
        "btn_pay_bep20": "🪙 Pay with USDT (BEP20)",
        "bep20_title": "🪙 <b>Payment via USDT (BEP20)</b>",
        "bep20_address_lbl": "🪙 <b>USDT Deposit Address (BSC/BEP20)</b> (tap to copy):",
        "bep20_instructions": "📝 <b>Instructions:</b>\n1️⃣ Send the exact USDT (BEP20) amount to the address above.\n2️⃣ Once done, send the <b>Transaction Hash (Tx Hash)</b> here for verification.",
        "bep20_waiting_payment": "⏳ <i>Waiting for your transaction hash…</i>",
        "bep20_send_tx_hash": "📩 Send the <b>Transaction Hash (Tx Hash)</b> to verify your payment.",
        "bep20_invalid_tx_hash": "❌ Invalid transaction hash. Please send a valid 66-character hash (starting with 0x...)",
        # ── TRC20 USDT Payment ──
        "btn_pay_trc20": "🪙 Pay with USDT (TRC20)",
        "trc20_title": "🪙 <b>Payment via USDT (TRC20)</b>",
        "trc20_address_lbl": "🪙 <b>USDT Deposit Address (TRON/TRC20)</b> (tap to copy):",
        "trc20_instructions": "📝 <b>Instructions:</b>\n1️⃣ Send the exact USDT (TRC20) amount to the address above.\n2️⃣ Once done, send the <b>Transaction Hash (Tx Hash)</b> here for verification.",
        "trc20_waiting_payment": "⏳ <i>Waiting for your transaction hash…</i>",
        "trc20_send_tx_hash": "📩 Send the <b>Transaction Hash (Tx Hash)</b> to verify your payment.",
        "trc20_invalid_tx_hash": "❌ Invalid transaction hash. Please send a valid 64-character TRON tx hash (no 0x prefix).",
        "tx_already_used": "❌ This transaction has already been used for another order.",
    },

    # ═══════════════════════════════════════════
    #  FRANÇAIS
    # ═══════════════════════════════════════════
    "fr": {
        "choose_language": "🌐 Choisissez votre langue :",
        "language_set": "✅ Langue définie sur Français !",
        "welcome": (
            "🎉 <b>Bienvenue !</b>\n\n"
            "🎯 <b>Guide rapide :</b>\n"
            "1. Appuyez sur \"🛒 Acheter\"\n"
            "2. Choisissez le produit souhaité\n"
            "3. Effectuez le paiement\n"
            "4. Après paiement, envoyez l'Order ID pour vérification\n\n"
            "🎯 <b>Choisissez une option :</b>"
        ),
        "quick_menu_enabled": "🎯 Menu rapide activé sous la barre de chat.",

        "btn_buy": "🛒 Acheter",
        "btn_profile": "👤 Profil",
        "btn_history": "📋 Historique",
        "btn_support": "💬 Support",
        "btn_products": "🛍️ Produits",
        "btn_back": "◀️ Retour",
        "btn_cancel": "❌ Annuler",
        "btn_refresh": "🔄 Rafraîchir",
        "btn_buy_now": "🛒 Acheter maintenant",
        "btn_pay_binance": "◇ Payer avec Binance",
        "btn_i_paid": "✅ J'ai payé",
        "btn_new_ticket": "📝 Nouveau ticket",
        "btn_my_tickets": "📋 Mes tickets",
        "btn_language": "🌐 Langue",
        "btn_start": "🚀 Commencer",
        "btn_wallet": "💰 Portefeuille",
        "btn_referral": "👥 Parrainage",

        # ── Wallet ──
        "wallet_title": "💰 <b>Mon Portefeuille</b>",
        "wallet_balance_lbl": "💵 Solde :",
        "wallet_topup": "➕ Recharger",
        "wallet_history": "📜 Historique",
        "wallet_topup_title": "💰 <b>Recharger le Portefeuille</b>\n\n✏️ Envoyez le montant en USD que vous souhaitez ajouter :\n(Exemple : 5, 10.50, 25)",
        "wallet_topup_preset": "Ou choisissez un montant :",
        "wallet_invalid_amount": "❌ Montant invalide. Entrez un nombre (ex: 5, 10, 20).",
        "wallet_credited": "✅ <b>Portefeuille crédité !</b>\n\n💵 +${amount} ajouté\n💰 Nouveau solde : ${balance}",
        "wallet_insufficient": "❌ <b>Solde insuffisant !</b>\n\n💰 Votre solde : ${balance}\n💲 Requis : ${required}\n\nVeuillez recharger votre portefeuille.",
        "wallet_paid": "✅ <b>Payé avec le Portefeuille !</b>\n\n💲 Débité : ${amount}\n💰 Restant : ${balance}",
        "wallet_no_transactions": "📭 Aucune transaction.",
        "wallet_tx_topup": "➕ Recharge",
        "wallet_tx_purchase": "🛒 Achat",
        "btn_pay_wallet": "💰 Wallet (${balance})",

        "categories_title": "📂 <b>Catégories</b>\n\nChoisissez une catégorie :",
        "choose_quantity": "🔢 <b>Quantité</b>\n\n✏️ Envoyez le nombre d'articles que vous voulez acheter :\n📦 Stock disponible : {stock}",
        "invalid_quantity": "❌ <b>Quantité invalide</b>\n\nVeuillez envoyer un nombre positif valide.",
        "insufficient_stock": "❌ <b>Stock insuffisant</b>\n\nNous n'avons que {stock} items disponibles. Veuillez choisir une quantité inférieure.",
        "quantity_lbl": "🔢 <b>Quantité :</b> {qty}",
        "no_categories": "📭 Aucune catégorie disponible pour le moment.",
        "product_not_found": "❌ Produit introuvable.",
        "access_denied": "❌ Accès refusé : Cette commande ne vous appartient pas.",
        "cannot_cancel": "❌ Cette commande ne peut pas être annulée (statut: {status})",
        "tx_used": "❌ Cette transaction a déjà été utilisée.",
        "max_topup": "⚠️ Le montant maximum de recharge est de 10 000 $.",
        "contact_support": "J'ai payé / Contacter le support",
        "banned_msg": "⛔ Vous avez été banni de ce bot.",
        "out_of_stock": "❌ <b>Rupture de stock !</b>\nCe produit n'est plus disponible.",
        "product_detail": (
            "{emoji} <b>{name}</b>\n"
            "💵 <b>Prix :</b> {price}\n"
            "🛡️ <b>Garantie :</b> {warranty} jours\n"
            "📦 <b>Stock :</b> {stock} comptes\n"
            "📊 <b>Vendus :</b> {sold} comptes\n\n"
            "❞ <b>Description :</b>\n{description}"
        ),

        "new_order": "🛒 <b>Nouvelle commande</b>",
        "product_lbl": "📦 <b>Produit :</b>",
        "total_lbl": "💰 <b>Total :</b>",
        "ref_lbl": "🔖 <b>Réf :</b>",
        "choose_payment": "💳 <b>Choisissez la méthode de paiement :</b>",
        "binance_title": "◇ <b>Paiement via Binance Pay</b>",
        "binance_id_lbl": "◇ <b>Binance ID</b> (appuyez pour copier) :",
        "amount_lbl": "💰 <b>Montant à transférer :</b>",
        "pay_instructions": "📝 <b>Instructions :</b>",
        "pay_step1": "1️⃣ Envoyez le montant exact via Binance Pay",
        "pay_step2": "2️⃣ Après le paiement, envoyez l'<b>Order ID</b> ou\n   la <b>référence de transaction</b> ici",
        "waiting_payment": "⏳ <i>En attente de votre paiement…</i>",
        "verifying": "🔍 Vérification du paiement en cours…",
        "payment_confirmed": "✅ <b>Paiement confirmé !</b>",
        "your_account": "📧 <b>Voici votre compte :</b>",
        "warranty_lbl": "🛡️ <b>Garantie :</b> {days} jours",
        "save_info": "📌 <b>Conservez ces informations en lieu sûr</b>",
        "thank_you": "Merci pour votre achat ! 🙏",
        "delivery_error": "⚠️ <b>Rupture de stock !</b>\nIl semble que vous ayez mis trop de temps à payer et le stock a été vendu.\n\n⚠️ <b>Action requise :</b> Veuillez contacter le support technique avec l'ID de commande <b>#{order_id}</b> pour obtenir un remboursement ou une livraison manuelle.",
        "payment_not_detected": "⏳ <b>Paiement non détecté</b>",
        "retry_order_id": "Veuillez vérifier que vous avez bien envoyé le paiement,\npuis <b>réessayez en envoyant l'Order ID</b>.",
        "support_hint": "💡 <i>Si le problème persiste, contactez le support.</i>",
        "no_pending_order": "⚠️ Aucune commande en attente. Utilisez /start pour recommencer.",
        "check_title": "📝 <b>Vérification du paiement</b>",
        "order_lbl": "🔖 <b>Commande :</b>",
        "send_order_id": "📩 Envoyez l'<b>Order ID</b> ou la <b>référence de transaction</b>\npour vérifier votre paiement.",
        "promo_prompt": "🎫 <b>Appliquer un code promo</b>\n\n✏️ Envoyez votre code promo :",
        "promo_success": "✅ <b>Code promo appliqué !</b>\n\n🎉 Réduction : <b>{discount}</b>\n💰 Nouveau total : <b>{total}</b>",
        "promo_invalid": "❌ <b>Code promo invalide ou expiré !</b>\n\nVeuillez vérifier le code et le renvoyer, ou annuler.",
        "promo_max_uses_reached": "❌ <b>Limite atteinte !</b>\n\nVous avez déjà atteint le nombre maximum d'utilisations autorisé pour ce code promo.",
        "promo_product_invalid": "❌ <b>Produit non éligible !</b>\n\nCe code promo ne peut pas être appliqué à ce produit.",
        "promo_qty_limit": "❌ <b>Limite de quantité !</b>\n\nCe code promo est valable uniquement pour les commandes de {max_qty} article(s) maximum.",
        "promo_already_applied": "❌ <b>Un code promo a déjà été appliqué à cette commande.</b>",
        "order_expired_notification": "⏳ <b>Temps écoulé !</b>\nVotre commande <b>#{order_id}</b> a été automatiquement annulée car le paiement n'a pas été reçu dans le délai imparti de 5 minutes.\nSi vous souhaitez toujours acheter ou si vous avez déjà payé, merci de repasser une nouvelle commande.",
        "order_cancelled": "❌ <b>Commande annulée</b>\n\nVotre commande a été annulée.\nRetournez au menu principal pour continuer.",
        "order_timeout": "❌ <b>Commande expirée</b>\n\nVotre commande #{id} a expiré car le paiement n'a pas été reçu dans les 5 minutes.",
        "order_error": "⚠️ Erreur lors de la création de la commande.",
        "pay_error": "⚠️ Erreur lors de l'initialisation du paiement.",
        "cancel_error": "⚠️ Erreur lors de l'annulation.",
        "verify_error": "⚠️ Erreur de vérification. Veuillez réessayer.",

        "profile_title": "👤 <b>Votre Profil</b>",
        "id_lbl": "🆔 <b>ID :</b>",
        "name_lbl": "👤 <b>Nom :</b>",
        "joined_lbl": "📅 <b>Inscrit le :</b>",
        "purchases_lbl": "🛒 <b>Total achats :</b>",
        "spent_lbl": "💰 <b>Total dépensé :</b>",

        "history_title": "📋 <b>Historique des achats</b>",
        "no_orders": "📭 Aucune commande pour le moment.",
        "order_detail": "📦 <b>Commande #{id}</b>",
        "status_lbl": "📊 <b>Statut :</b>",
        "date_lbl": "📅 <b>Date :</b>",
        "account_lbl": "📧 <b>Compte :</b>",

        "support_title": "💬 <b>Support</b>\n\nPour toute assistance, veuillez contacter directement notre support sur Telegram : @Drbatman2",
        "describe_problem": "📝 Décrivez votre problème :",
        "ticket_created": "✅ Ticket #{id} créé ! Nous vous répondrons bientôt.",
        "no_tickets": "📭 Aucun ticket.",
        "ticket_title": "🎫 <b>Ticket #{id}</b>",
        "message_lbl": "📝 <b>Message :</b>",
        "reply_lbl": "💬 <b>Réponse :</b>",
        "ticket_replied": "💬 <b>Réponse à votre ticket #{id}</b>",
        "ticket_closed": "🔒 Votre ticket #{id} a été fermé.\nMerci de nous avoir contacté ! 🙏",

        "s_pending": "⏳ En attente",
        "s_completed": "✅ Complétée",
        "s_cancelled": "❌ Annulée",
        "s_awaiting": "⏳ En attente de paiement",
        "s_open": "🟢 Ouvert",
        "s_replied": "💬 Répondu",
        "s_closed": "🔴 Fermé",

        "notif_sale": "🔔 <b>Nouvelle vente !</b>",
        "notif_low_stock": "⚠️ <b>Stock faible !</b>",
        "notif_remaining": "📉 Restant :",
        "notif_manual": "🔔 <b>Vérification manuelle requise</b>",
        "notif_order_id": "📝 Order ID soumis :",

        "error_generic": "⚠️ Une erreur s'est produite.",

        # ── Admin Panel ──
        "admin_panel": "🔧 <b>Panneau d'administration</b>\n\nSélectionnez une option :",
        "admin_access_denied": "🚫 Accès refusé. Réservé aux administrateurs.",
        "admin_categories_title": "📂 <b>Gestion des catégories</b>\n\nTotal : {count} catégorie(s)",
        "admin_products_title": "📦 <b>Gestion des produits</b>",
        "admin_stock_title": "📦 <b>Gestion du stock</b>\n\nChoisissez un produit pour ajouter du stock :",
        "admin_enter_cat_name": "📝 Entrez le nom de la catégorie :",
        "admin_enter_cat_emoji": "🎨 Envoyez un émoji pour cette catégorie (ou /skip) :",
        "admin_cat_created": "✅ Catégorie créée !",
        "admin_enter_prod_name": "📝 Entrez le nom du produit :",
        "admin_enter_prod_desc": "📝 Entrez la description (ou /skip) :",
        "admin_enter_prod_price": "💰 Entrez le prix en USD :",
        "admin_enter_prod_warranty": "🔒 Entrez les jours de garantie (ou /skip pour 0) :",
        "admin_enter_prod_emoji": "🎨 Envoyez un émoji (ou /skip) :",
        "admin_prod_created": "✅ Produit créé !",
        "admin_enter_stock": "📋 Envoyez les comptes (un par ligne) :",
        "admin_stock_added": "✅ {count} compte(s) ajouté(s) au stock !",
        "admin_stats_title": "📊 <b>Statistiques (30 jours)</b>",
        "admin_stats_revenue": "💰 Revenus : ${revenue}",
        "admin_stats_orders": "📦 Commandes : {orders}",
        "admin_stats_completed": "✅ Complétées : {completed}",
        "admin_stats_users": "👥 Utilisateurs : {users}",
        "admin_broadcast_prompt": "📢 Envoyez le message à diffuser à tous les utilisateurs :",
        "admin_broadcast_sent": "✅ Envoyé à {sent}/{total} utilisateurs.",
        "admin_no_pending": "✅ Aucune commande en attente.",
        "admin_no_tickets": "✅ Aucun ticket ouvert.",
        "admin_order_confirmed": "✅ Commande #{id} confirmée !",
        "admin_ticket_replied": "✅ Ticket #{id} répondu !",
        "admin_not_found": "❌ Introuvable.",
        "admin_error": "⚠️ Erreur.",
        # ── Referral Program ──
        "referral_title": "👥 <b>Programme de Parrainage</b>\n\nInvitez vos amis avec votre lien de parrainage ! Toutes les <b>20 personnes parrainées</b>, vous avez droit à un <b>lien gratuit</b>.\n\nPour réclamer votre lien gratuit, contactez simplement l'admin via le support.\n\n🔗 <b>Votre lien de parrainage :</b>\n<code>{link}</code>\n\n📊 <b>Statistiques :</b>\n- Amis parrainés : <b>{count}</b>",
        "referral_notif": "🎁 <b>Commission de parrainage reçue !</b>\nVous avez reçu une commission de <b>{amount}</b> grâce à l'achat de votre ami {friend}.",
        # ── BEP20 USDT Payment ──
        "btn_pay_bep20": "🪙 Payer en USDT (BEP20)",
        "bep20_title": "🪙 <b>Paiement en USDT (BEP20)</b>",
        "bep20_address_lbl": "🪙 <b>Adresse de dépôt USDT (BSC/BEP20)</b> (touchez pour copier) :",
        "bep20_instructions": "📝 <b>Instructions :</b>\n1️⃣ Envoyez le montant exact en USDT (BEP20) à l'adresse ci-dessus.\n2️⃣ Une fois le transfert effectué, envoyez le <b>Hash de la transaction (Tx Hash)</b> ici pour vérification.",
        "bep20_waiting_payment": "⏳ <i>En attente du Hash de votre transaction…</i>",
        "bep20_send_tx_hash": "📩 Envoyez le <b>Hash de la transaction (Tx Hash)</b> pour vérifier votre paiement.",
        "bep20_invalid_tx_hash": "❌ Hash de transaction invalide. Veuillez envoyer un hash correct à 66 caractères (ex: 0x...)",
        # ── TRC20 USDT Payment ──
        "btn_pay_trc20": "🪙 Payer en USDT (TRC20)",
        "trc20_title": "🪙 <b>Paiement en USDT (TRC20)</b>",
        "trc20_address_lbl": "🪙 <b>Adresse de dépôt USDT (TRON/TRC20)</b> (touchez pour copier) :",
        "trc20_instructions": "📝 <b>Instructions :</b>\n1️⃣ Envoyez le montant exact en USDT (TRC20) à l'adresse ci-dessus.\n2️⃣ Une fois le transfert effectué, envoyez le <b>Hash de la transaction (Tx Hash)</b> ici pour vérification.",
        "trc20_waiting_payment": "⏳ <i>En attente du Hash de votre transaction…</i>",
        "trc20_send_tx_hash": "📩 Envoyez le <b>Hash de la transaction (Tx Hash)</b> pour vérifier votre paiement.",
        "trc20_invalid_tx_hash": "❌ Hash de transaction invalide. Veuillez envoyer un hash correct à 64 caractères (sans préfixe 0x).",
        "tx_already_used": "❌ Cette transaction a déjà été utilisée pour une autre commande.",
    },

    # ═══════════════════════════════════════════
    #  العربية
    # ═══════════════════════════════════════════
    "ar": {
        "choose_language": "🌐 اختر لغتك:",
        "language_set": "✅ تم تعيين اللغة إلى العربية!",
        "welcome": (
            "🎉 <b>!مرحباً بك</b>\n\n"
            "🎯 <b>:دليل سريع</b>\n"
            "1. اضغط على \"🛒 شراء\"\n"
            "2. اختر المنتج الذي تريده\n"
            "3. أكمل الدفع\n"
            "4. بعد الدفع، أرسل رقم الطلب للتحقق\n\n"
            "🎯 <b>:اختر خياراً</b>"
        ),
        "quick_menu_enabled": "🎯 تم تفعيل القائمة السريعة أسفل شريط الدردشة.",

        "btn_buy": "🛒 شراء",
        "btn_profile": "👤 الملف الشخصي",
        "btn_history": "📋 سجل المشتريات",
        "btn_support": "💬 الدعم",
        "btn_products": "🛍️ المنتجات",
        "btn_back": "◀️ رجوع",
        "btn_cancel": "❌ إلغاء",
        "btn_refresh": "🔄 تحديث",
        "btn_buy_now": "🛒 اشتري الآن",
        "btn_pay_binance": "◇ الدفع عبر Binance",
        "btn_i_paid": "✅ لقد دفعت",
        "btn_new_ticket": "📝 تذكرة جديدة",
        "btn_my_tickets": "📋 تذاكري",
        "btn_language": "🌐 اللغة",
        "btn_start": "🚀 ابدأ",
        "btn_wallet": "💰 المحفظة",
        "btn_referral": "👥 الإحالة",

        # ── Wallet ──
        "wallet_title": "💰 <b>محفظتي</b>",
        "wallet_balance_lbl": "💵 الرصيد:",
        "wallet_topup": "➕ شحن",
        "wallet_history": "📜 السجل",
        "wallet_topup_title": "💰 <b>شحن المحفظة</b>\n\n✏️ أرسل المبلغ بالدولار الذي تريد إضافته:\n(مثال: 5, 10.50, 25)",
        "wallet_topup_preset": "أو اختر مبلغاً:",
        "wallet_invalid_amount": "❌ مبلغ غير صالح. أدخل رقماً (مثال: 5, 10, 20).",
        "wallet_credited": "✅ <b>تم شحن المحفظة!</b>\n\n💵 +${amount} تمت الإضافة\n💰 الرصيد الجديد: ${balance}",
        "wallet_insufficient": "❌ <b>رصيد غير كافٍ!</b>\n\n💰 رصيدك: ${balance}\n💲 المطلوب: ${required}\n\nيرجى شحن محفظتك أولاً.",
        "wallet_paid": "✅ <b>تم الدفع من المحفظة!</b>\n\n💲 خصم: ${amount}\n💰 المتبقي: ${balance}",
        "wallet_no_transactions": "📭 لا توجد معاملات.",
        "wallet_tx_topup": "➕ شحن",
        "wallet_tx_purchase": "🛒 شراء",
        "btn_pay_wallet": "💰 المحفظة (${balance})",

        "categories_title": "📂 <b>الفئات</b>\n\n:اختر فئة",
        "choose_quantity": "🔢 <b>الكمية</b>\n\n✏️ أرسل عدد العناصر التي تريد شراءها:\n📦 المخزون المتاح: {stock}",
        "invalid_quantity": "❌ <b>كمية غير صالحة</b>\n\nيرجى إرسال رقم موجب صالح.",
        "insufficient_stock": "❌ <b>مخزون غير كافٍ</b>\n\nلدينا {stock} أجهزة/حسابات فقط متاحة. يرجى اختيار كمية أقل.",
        "quantity_lbl": "🔢 <b>الكمية:</b> {qty}",
        "no_categories": "📭 لا توجد فئات متاحة حالياً.",
        "product_not_found": "❌ المنتج غير موجود.",
        "access_denied": "❌ دخول مرفوض: هذا الطلب لا يخصك.",
        "cannot_cancel": "❌ لا يمكن إلغاء هذا الطلب (الحالة: {status})",
        "tx_used": "❌ تم استخدام هذه المعاملة بالفعل.",
        "max_topup": "⚠️ الحد الأقصى لمبلغ الشحن هو 10,000 دولار.",
        "contact_support": "لقد دفعت / اتصل بالدعم",
        "banned_msg": "⛔ لقد تم حظرك من هذا البوت.",
        "out_of_stock": "❌ <b>!نفذ المخزون</b>\nهذا المنتج غير متوفر حالياً.",
        "product_detail": (
            "{emoji} <b>{name}</b>\n"
            "💵 <b>السعر:</b> {price}\n"
            "🛡️ <b>الضمان:</b> {warranty} يوم\n"
            "📦 <b>المخزون:</b> {stock} حسابات\n"
            "📊 <b>المباعة:</b> {sold} حسابات\n\n"
            "❞ <b>الوصف:</b>\n{description}"
        ),

        "new_order": "🛒 <b>طلب جديد</b>",
        "product_lbl": "📦 <b>المنتج:</b>",
        "total_lbl": "💰 <b>المجموع:</b>",
        "ref_lbl": "🔖 <b>المرجع:</b>",
        "choose_payment": "💳 <b>:اختر طريقة الدفع</b>",
        "binance_title": "◇ <b>Binance Pay الدفع عبر</b>",
        "binance_id_lbl": "◇ <b>Binance ID</b> :(اضغط للنسخ)",
        "amount_lbl": "💰 <b>المبلغ المطلوب:</b>",
        "pay_instructions": "📝 <b>:التعليمات</b>",
        "pay_step1": "1️⃣ Binance Pay أرسل المبلغ المحدد عبر",
        "pay_step2": "2️⃣ بعد الدفع، أرسل <b>رقم الطلب</b> أو\n   <b>مرجع المعاملة</b> هنا",
        "waiting_payment": "⏳ <i>…في انتظار دفعتك</i>",
        "verifying": "🔍 …جاري التحقق من الدفع",
        "payment_confirmed": "✅ <b>!تم تأكيد الدفع</b>",
        "your_account": "📧 <b>:إليك حسابك</b>",
        "warranty_lbl": "🛡️ <b>الضمان:</b> {days} يوم",
        "save_info": "📌 <b>احتفظ بهذه المعلومات في مكان آمن</b>",
        "thank_you": "🙏 !شكراً لشرائك",
        "delivery_error": "⚠️ <b>نفد المخزون!</b>\nيبدو أنك استغرقت وقتًا طويلاً في الدفع وتم بيع المخزون.\n\n⚠️ <b>إجراء مطلوب:</b> يرجى الاتصال بالدعم الفني مع معرف الطلب <b>#{order_id}</b> للحصول على استرداد أو تسليم يدوي.",
        "payment_not_detected": "⏳ <b>لم يتم اكتشاف الدفع</b>",
        "retry_order_id": "يرجى التحقق من إرسال الدفع،\nثم <b>أعد إرسال رقم الطلب</b>.",
        "support_hint": "💡 <i>إذا استمرت المشكلة، تواصل مع الدعم.</i>",
        "no_pending_order": "⚠️ لا يوجد طلب معلق. استخدم /start للبدء من جديد.",
        "check_title": "📝 <b>التحقق من الدفع</b>",
        "order_lbl": "🔖 <b>الطلب:</b>",
        "send_order_id": "📩 أرسل <b>رقم الطلب</b> أو <b>مرجع المعاملة</b>\nللتحقق من دفعتك.",
        "promo_prompt": "🎫 <b>تطبيق كود الخصم</b>\n\n✏️ أرسل كود الخصم الخاص بك:",
        "promo_success": "✅ <b>تم تطبيق كود الخصم!</b>\n\n🎉 الخصم: <b>{discount}</b>\n💰 الإجمالي الجديد: <b>{total}</b>",
        "promo_invalid": "❌ <b>كود الخصم غير صالح أو منتهي الصلاحية!</b>\n\nيرجى التحقق من الكود وإرساله مرة أخرى، أو الإلغاء.",
        "promo_max_uses_reached": "❌ <b>تم بلوغ الحد الأقصى!</b>\n\nلقد وصلت بالفعل إلى الحد الأقصى لعدد مرات استخدام كود الخصم هذا.",
        "promo_product_invalid": "❌ <b>منتج غير مؤهل!</b>\n\nلا يمكن تطبيق كود الخصم هذا على هذا المنتج.",
        "promo_qty_limit": "❌ <b>حد الكمية!</b>\n\nهذا الكود صالح فقط للطلبات التي لا تتجاوز {max_qty} عنصر/عناصر.",
        "promo_already_applied": "❌ <b>تم تطبيق كود خصم بالفعل على هذه الطلبية.</b>",
        "order_expired_notification": "⏳ <b>انتهى الوقت!</b>\nتم إلغاء طلبك <b>#{order_id}</b> تلقائيًا لأنه لم يتم استلام الدفع خلال المهلة المحددة (5 دقائق).\nإذا كنت ترغب في الشراء أو إذا كنت قد دفعت بالفعل، يرجى إنشاء طلب جديد.",
        "order_cancelled": "❌ <b>تم إلغاء الطلب</b>\n\nتم إلغاء طلبك بنجاح.\nعد إلى القائمة الرئيسية للمتابعة.",
        "order_timeout": "❌ <b>انتهت صلاحية الطلب</b>\n\nانتهت صلاحية طلبك رقم #{id} لعدم تلقي الدفع خلال 5 دقائق.",
        "order_error": "⚠️ خطأ في إنشاء الطلب.",
        "pay_error": "⚠️ خطأ في تهيئة الدفع.",
        "cancel_error": "⚠️ خطأ في الإلغاء.",
        "verify_error": "⚠️ خطأ في التحقق. يرجى المحاولة مرة أخرى.",

        "profile_title": "👤 <b>ملفك الشخصي</b>",
        "id_lbl": "🆔 <b>المعرّف:</b>",
        "name_lbl": "👤 <b>الاسم:</b>",
        "joined_lbl": "📅 <b>تاريخ الانضمام:</b>",
        "purchases_lbl": "🛒 <b>إجمالي المشتريات:</b>",
        "spent_lbl": "💰 <b>إجمالي الإنفاق:</b>",

        "history_title": "📋 <b>سجل المشتريات</b>",
        "no_orders": "📭 لا توجد طلبات بعد.",
        "order_detail": "📦 <b>طلب #{id}</b>",
        "status_lbl": "📊 <b>الحالة:</b>",
        "date_lbl": "📅 <b>التاريخ:</b>",
        "account_lbl": "📧 <b>الحساب:</b>",

        "support_title": "💬 <b>الدعم</b>\n\nللحصول على المساعدة، يرجى الاتصال بالدعم مباشرة على Telegram: @Drbatman2",
        "describe_problem": "📝 :صف مشكلتك",
        "ticket_created": "✅ تم إنشاء التذكرة #{id}! سنرد عليك قريباً.",
        "no_tickets": "📭 لا توجد تذاكر.",
        "ticket_title": "🎫 <b>تذكرة #{id}</b>",
        "message_lbl": "📝 <b>الرسالة:</b>",
        "reply_lbl": "💬 <b>الرد:</b>",
        "ticket_replied": "💬 <b>الرد على تذكرتك رقم #{id}</b>",
        "ticket_closed": "🔒 تم إغلاق تذكرتك رقم #{id}.\nشكراً لتواصلك معنا! 🙏",

        "s_pending": "⏳ قيد الانتظار",
        "s_completed": "✅ مكتمل",
        "s_cancelled": "❌ ملغى",
        "s_awaiting": "⏳ في انتظار الدفع",
        "s_open": "🟢 مفتوح",
        "s_replied": "💬 تم الرد",
        "s_closed": "🔴 مغلق",

        "notif_sale": "🔔 <b>!عملية بيع جديدة</b>",
        "notif_low_stock": "⚠️ <b>!مخزون منخفض</b>",
        "notif_remaining": "📉 :المتبقي",
        "notif_manual": "🔔 <b>مطلوب تحقق يدوي</b>",
        "notif_order_id": "📝 :رقم الطلب المُرسل",

        "error_generic": "⚠️ حدث خطأ.",

        # ── Admin Panel ──
        "admin_panel": "🔧 <b>لوحة الإدارة</b>\n\nاختر خياراً:",
        "admin_access_denied": "🚫 الوصول مرفوض. هذا الأمر للمشرفين فقط.",
        "admin_categories_title": "📂 <b>إدارة الفئات</b>\n\nالإجمالي: {count} فئة(ات)",
        "admin_products_title": "📦 <b>إدارة المنتجات</b>",
        "admin_stock_title": "📦 <b>إدارة المخزون</b>\n\nاختر منتجاً لإضافة مخزون:",
        "admin_enter_cat_name": "📝 أدخل اسم الفئة:",
        "admin_enter_cat_emoji": "🎨 أرسل إيموجي للفئة (أو /skip):",
        "admin_cat_created": "✅ تم إنشاء الفئة!",
        "admin_enter_prod_name": "📝 أدخل اسم المنتج:",
        "admin_enter_prod_desc": "📝 أدخل وصف المنتج (أو /skip):",
        "admin_enter_prod_price": "💰 أدخل السعر بالدولار:",
        "admin_enter_prod_warranty": "🔒 أدخل أيام الضمان (أو /skip لـ 0):",
        "admin_enter_prod_emoji": "🎨 أرسل إيموجي (أو /skip):",
        "admin_prod_created": "✅ تم إنشاء المنتج!",
        "admin_enter_stock": "📋 أرسل الحسابات (واحد في كل سطر):",
        "admin_stock_added": "✅ تمت إضافة {count} حساب(ات) للمخزون!",
        "admin_stats_title": "📊 <b>الإحصائيات (30 يوم)</b>",
        "admin_stats_revenue": "💰 الإيرادات: ${revenue}",
        "admin_stats_orders": "📦 الطلبات: {orders}",
        "admin_stats_completed": "✅ المكتملة: {completed}",
        "admin_stats_users": "👥 المستخدمون: {users}",
        "admin_broadcast_prompt": "📢 أرسل الرسالة للبث لجميع المستخدمين:",
        "admin_broadcast_sent": "✅ تم الإرسال لـ {sent}/{total} مستخدم.",
        "admin_no_pending": "✅ لا توجد طلبات معلقة.",
        "admin_no_tickets": "✅ لا توجد تذاكر مفتوحة.",
        "admin_order_confirmed": "✅ تم تأكيد الطلب #{id}!",
        "admin_ticket_replied": "✅ تم الرد على التذكرة #{id}!",
        "admin_not_found": "❌ غير موجود.",
        "admin_error": "⚠️ خطأ.",
        # ── Referral Program ──
        "referral_title": "👥 <b>برنامج الإحالة</b>\n\nقم بدعوة أصدقائك باستخدام رابط الإحالة الخاص بك! لكل <b>20 صديقًا</b> تقوم بإحالتهم، ستحصل على <b>رابط مجاني</b>.\n\nللمطالبة بمكافأتك، ما عليك سوى فتح تذكرة دعم والاتصال بالمسؤول.\n\n🔗 <b>رابط الإحالة الخاص بك:</b>\n<code>{link}</code>\n\n📊 <b>الإحصائيات:</b>\n- الأصدقاء الذين تمت إحالتهم: <b>{count}</b>",
        "referral_notif": "🎁 <b>تم استلام عمولة الإحالة!</b>\nلقد ربحت عمولة قدرها <b>{amount}</b> من عملية الشراء التي قام بها صديقك {friend}.",
        # ── BEP20 USDT Payment ──
        "btn_pay_bep20": "🪙 الدفع بـ USDT (BEP20)",
        "bep20_title": "🪙 <b>الدفع عبر USDT (BEP20)</b>",
        "bep20_address_lbl": "🪙 <b>عنوان إيداع USDT (BSC/BEP20)</b> (اضغط للنسخ):",
        "bep20_instructions": "📝 <b>التعليمات:</b>\n1️⃣ أرسل المبلغ المحدد من USDT (BEP20) إلى العنوان أعلاه.\n2️⃣ بمجرد الانتهاء، أرسل <b>هاش المعاملة (Tx Hash)</b> هنا للتحقق.",
        "bep20_waiting_payment": "⏳ <i>في انتظار هاش المعاملة الخاص بك...</i>",
        "bep20_send_tx_hash": "📩 أرسل <b>هاش المعاملة (Tx Hash)</b> للتحقق من دفعتك.",
        "bep20_invalid_tx_hash": "❌ هاش المعاملة غير صالح. يرجى إرسال هاش صحيح مكون من 66 حرفاً (يبدأ بـ 0x...)",
        # ── TRC20 USDT Payment ──
        "btn_pay_trc20": "🪙 الدفع بـ USDT (TRC20)",
        "trc20_title": "🪙 <b>الدفع عبر USDT (TRC20)</b>",
        "trc20_address_lbl": "🪙 <b>عنوان إيداع USDT (TRON/TRC20)</b> (اضغط للنسخ):",
        "trc20_instructions": "📝 <b>التعليمات:</b>\n1️⃣ أرسل المبلغ المحدد من USDT (TRC20) إلى العنوان أعلاه.\n2️⃣ بمجرد الانتهاء، أرسل <b>هاش المعاملة (Tx Hash)</b> هنا للتحقق.",
        "trc20_waiting_payment": "⏳ <i>في انتظار هاش المعاملة الخاص بك...</i>",
        "trc20_send_tx_hash": "📩 أرسل <b>هاش المعاملة (Tx Hash)</b> للتحقق من دفعتك.",
        "trc20_invalid_tx_hash": "❌ هاش المعاملة غير صالح. يرجى إرسال هاش صحيح مكون من 64 حرفاً.",
        "tx_already_used": "❌ تم استخدام هذه المعاملة بالفعل لطلب آخر.",
    },
}


def t(key: str, lang: str = "fr") -> str:
    """Get a translated string by key and language code.

    Falls back to French, then to the raw key if not found.
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(
        key, TRANSLATIONS["fr"].get(key, key)
    )
