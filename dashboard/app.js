// dashboard/app.js — VenteBot Admin Dashboard with all features

// —————————————————————————————————————————————————————
//  i18n TRANSLATIONS
// —————————————————————————————————————————————————————
const LANG = {
fr: {
    login_subtitle:"Console de Gestion Administrateur",login_url_label:"URL de l'API (optionnel)",login_url_hint:"Laissez vide pour le proxy Netlify",login_key_label:"Clé d'API Administrateur",login_btn:"Se connecter",
    nav_dashboard:"Dashboard",nav_stats:"Statistiques",nav_inventory:"Catalogue & Stock",nav_orders:"Commandes",nav_users:"Utilisateurs",nav_tickets:"Tickets",nav_broadcast:"Broadcast",nav_settings:"Paramètres",nav_ventedz:"Vente DZ",tab_ventedz:"Gestion Vente DZ",
    admin_title:"Administrateur",status_connected:"Connecté",btn_logout:"Déconnexion",
    tab_dashboard:"Tableau de Bord",tab_stats:"Analyses & Statistiques",tab_inventory:"Catalogue & Stock",tab_orders:"Suivi des Commandes",tab_users:"Gestion des Utilisateurs",tab_tickets:"Tickets Support",tab_broadcast:"Broadcast",tab_settings:"Paramètres",
    metric_revenue:"Revenus (30J)",metric_sales:"Ventes (30J)",metric_clients:"Clients",metric_initiated:"Commandes (30J)",
    chart_revenue:"Revenus quotidiens ($)",chart_orders:"Commandes quotidiennes",
    stock_status:"État des Stocks",no_products:"Aucun produit configuré.",
    sub_products:"Produits",sub_categories:"Catégories",sub_promos:"Codes Promo",
    all_products:"Tous les Produits",btn_add_product:"Ajouter",th_product:"Produit",th_price:"Prix",th_warranty:"Garantie",th_status:"Statut",
    all_categories:"Catégories",btn_add_category:"Ajouter",no_categories:"Aucune catégorie.",
    all_promos:"Codes Promo",btn_add_promo:"Créer un Code",no_promos:"Aucun code promo.",th_type:"Type",th_value:"Valeur",th_uses:"Utilisations",
    orders_title:"Suivi des Commandes",filter_all:"Toutes",filter_pending:"En attente",filter_completed:"Complétées",filter_cancelled:"Annulées",filter_topup:"Top-up",no_orders:"Aucune commande.",th_binance_id:"ID Binance / Tx Hash",th_payment_method:"Méthode",th_client:"Client",th_amount:"Montant",th_qty:"Qté",wallet_topup:"💰 Wallet Top-up",
    users_title:"Gestion des Utilisateurs",no_users:"Aucun utilisateur.",th_firstname:"Prénom",th_lang:"Langue",th_orders_count:"Commandes",th_spent:"Dépenses",th_joined:"Inscrit",th_referrer:"Parrain",th_referrals:"Filleuls",th_referral_earnings:"Gains Parrainage",users_show_count:"Afficher :",users_search_placeholder:"Rechercher par ID ou nom...",
    tickets_title:"Tickets Support",no_tickets:"Aucun ticket. ðŸ¤",
    broadcast_title:"Envoyer un Message Broadcast",broadcast_desc:"Ce message sera envoyé à tous les utilisateurs du bot.",broadcast_label:"Message (HTML supporté) :",btn_send_broadcast:"Envoyer à tous",
    settings_title:"Configuration de l'API",settings_desc:"Synchronisation avec votre bot.",btn_save:"Enregistrer",
    modal_add_cat:"Ajouter une Catégorie",modal_add_prod:"Ajouter un Produit",modal_add_promo:"Créer un Code Promo",
    lbl_name:"Nom",lbl_category:"Catégorie",lbl_prod_name:"Nom du Produit",lbl_price:"Prix USD ($)",lbl_warranty:"Garantie (J)",lbl_discount_type:"Type",lbl_discount_value:"Valeur",lbl_max_uses:"Max utilisations",lbl_expires:"Expiration",
    btn_cancel:"Annuler",btn_create_cat:"Créer",btn_create_prod:"Créer",btn_create_promo:"Créer",
    stock_manage:"Gérer le Stock",stock_add_label:"Ajouter des comptes (un par ligne) :",btn_add_stock:"Ajouter",btn_import_file:"Importer .txt",stock_existing:"Stock existant",stock_items_lbl:"articles",no_stock:"Aucun article.",
    stock_in:"en stock",days:"jours",active:"Actif",inactive:"Inactif",
    confirm_delete:"Supprimer ce produit ?",confirm_order:"Confirmer le paiement #",accounts_detected:"comptes détectés",
    available:"✓ Disponible",sold:"✗ Vendu",no_desc:"Pas de description",btn_confirm:"Confirmer",reply_placeholder:"Votre réponse...",btn_reply:"Répondre",
    ban:"Bannir",unban:"Débannir",banned:"Banni",confirm_ban:"Bannir cet utilisateur ?",confirm_unban:"Débannir cet utilisateur ?",ban_modal_title:"Bannir l'utilisateur",ban_modal_desc:"Voulez-vous vraiment bannir cet utilisateur ?",ban_modal_notify:"Informer l'utilisateur qu'il a été banni",
    broadcast_sent:"Envoyé : {sent}/{total}",broadcast_failed:"Échecs : {failed}",unlimited:"Illimité",percent:"Pourcentage",fixed:"Montant fixe",
    nav_wallet_history:"Wallet History",wh_title:"Historique Wallet",wh_total_topups:"Total Recharges",wh_total_purchases:"Total Achats Wallet",wh_total_count:"Transactions",
    wh_filter_topup:"Recharges",wh_filter_purchase:"Achats Wallet",wh_th_type:"Type",wh_th_balance_after:"Solde après",wh_th_description:"Description",wh_no_tx:"Aucune transaction.",
    th_payment_method:"Méthode",pay_method_wallet:"💰 Wallet",pay_method_binance:"⚡ Binance",pay_method_unknown:"—",
    nav_finance:"Finance",tab_finance:"Suivi Financier",nav_binance:"Comptes Binance",tab_binance:"Gestion des Comptes Binance",settings_err:"Échec de l'opération : "
},
en: {
    login_subtitle:"Admin Management Console",login_url_label:"API URL (optional)",login_url_hint:"Leave empty for Netlify proxy",login_key_label:"Admin API Key",login_btn:"Connect",
    nav_dashboard:"Dashboard",nav_stats:"Statistics",nav_inventory:"Catalog & Stock",nav_orders:"Orders",nav_users:"Users",nav_tickets:"Tickets",nav_broadcast:"Broadcast",nav_settings:"Settings",nav_ventedz:"Vente DZ",tab_ventedz:"Vente DZ Management",
    admin_title:"Administrator",status_connected:"Connected",btn_logout:"Logout",
    tab_dashboard:"Dashboard",tab_stats:"Analytics & Statistics",tab_inventory:"Catalog & Stock",tab_orders:"Order Tracking",tab_users:"User Management",tab_tickets:"Support Tickets",tab_broadcast:"Broadcast",tab_settings:"Settings",
    metric_revenue:"Revenue (30D)",metric_sales:"Sales (30D)",metric_clients:"Clients",metric_initiated:"Orders (30D)",
    chart_revenue:"Daily Revenue ($)",chart_orders:"Daily Orders",
    stock_status:"Stock Status",no_products:"No products configured.",
    sub_products:"Products",sub_categories:"Categories",sub_promos:"Promo Codes",
    all_products:"All Products",btn_add_product:"Add",th_product:"Product",th_price:"Price",th_warranty:"Warranty",th_status:"Status",
    all_categories:"Categories",btn_add_category:"Add",no_categories:"No categories.",
    all_promos:"Promo Codes",btn_add_promo:"Create Code",no_promos:"No promo codes.",th_type:"Type",th_value:"Value",th_uses:"Uses",
    orders_title:"Order Tracking",filter_all:"All",filter_pending:"Pending",filter_completed:"Completed",filter_cancelled:"Cancelled",filter_topup:"Top-up",no_orders:"No orders.",th_client:"Client",th_amount:"Amount",th_qty:"Qty",wallet_topup:"💰 Wallet Top-up",
    users_title:"User Management",no_users:"No users.",th_firstname:"First Name",th_lang:"Language",th_orders_count:"Orders",th_spent:"Spent",th_joined:"Joined",th_referrer:"Referrer",th_referrals:"Referrals",th_referral_earnings:"Referral Earnings",users_show_count:"Show:",users_search_placeholder:"Search by ID or name...",
    tickets_title:"Support Tickets",no_tickets:"No pending tickets. ðŸ¤",
    broadcast_title:"Send Broadcast Message",broadcast_desc:"This message will be sent to all bot users.",broadcast_label:"Message (HTML supported):",btn_send_broadcast:"Send to all",
    settings_title:"API Configuration",settings_desc:"Sync with your bot.",btn_save:"Save",
    modal_add_cat:"Add Category",modal_add_prod:"Add Product",modal_add_promo:"Create Promo Code",
    lbl_name:"Name",lbl_category:"Category",lbl_prod_name:"Product Name",lbl_price:"Price USD ($)",lbl_warranty:"Warranty (D)",lbl_discount_type:"Type",lbl_discount_value:"Value",lbl_max_uses:"Max uses",lbl_expires:"Expires",
    btn_cancel:"Cancel",btn_create_cat:"Create",btn_create_prod:"Create",btn_create_promo:"Create",
    stock_manage:"Manage Stock",stock_add_label:"Add accounts (one per line):",btn_add_stock:"Add",btn_import_file:"Import .txt",stock_existing:"Existing Stock",stock_items_lbl:"items",no_stock:"No stock items.",
    stock_in:"in stock",days:"days",active:"Active",inactive:"Inactive",
    confirm_delete:"Delete this product?",confirm_order:"Confirm payment #",accounts_detected:"accounts detected",
    available:"✓ Available",sold:"✗ Sold",no_desc:"No description",btn_confirm:"Confirm",reply_placeholder:"Your reply...",btn_reply:"Reply",
    ban:"Ban",unban:"Unban",banned:"Banned",confirm_ban:"Ban this user?",confirm_unban:"Unban this user?",ban_modal_title:"Ban User",ban_modal_desc:"Are you sure you want to ban this user?",ban_modal_notify:"Inform the user they have been banned",
    broadcast_sent:"Sent: {sent}/{total}",broadcast_failed:"Failed: {failed}",unlimited:"Unlimited",percent:"Percentage",fixed:"Fixed amount",
    nav_wallet_history:"Wallet History",wh_title:"Wallet History",wh_total_topups:"Total Top-ups",wh_total_purchases:"Total Wallet Purchases",wh_total_count:"Transactions",
    wh_filter_topup:"Top-ups",wh_filter_purchase:"Wallet Purchases",wh_th_type:"Type",wh_th_balance_after:"Balance after",wh_th_description:"Description",wh_no_tx:"No transactions.",
    th_payment_method:"Method",pay_method_wallet:"💰 Wallet",pay_method_binance:"⚡ Binance",pay_method_unknown:"—",
    nav_finance:"Finance",tab_finance:"Financial Tracking",nav_binance:"Binance Accounts",tab_binance:"Binance Accounts Management",settings_err:"Operation failed: "
},
ar: {
    login_subtitle:"Ù„Ùˆحة إدارة Ø§Ù„Ù…Ø´Ø±Ù",login_url_label:"رابط API (اختياري)",login_url_hint:"Ø§ØªØ±Ùƒه ÙØ§Ø±ØºØ§Ù‹ Ù„Ø¨Ø±ÙˆÙƒسي Netlify",login_key_label:"Ù…ÙØªØ§Ø­ API Ù„Ù„Ù…Ø´Ø±Ù",login_btn:"اتصال",
    nav_dashboard:"Ù„Ùˆحة Ø§Ù„ØªØ­Ùƒم",nav_inventory:"Ø§Ù„ÙƒØªØ§Ù„Ùˆج ÙˆØ§Ù„Ù…Ø®Ø²Ùˆن",nav_orders:"الطلبات",nav_users:"المستخدمين",nav_tickets:"Ø§Ù„ØªØ°Ø§Ùƒر",nav_broadcast:"البث",nav_settings:"الإعدادات",nav_ventedz:"Vente DZ",tab_ventedz:"إدارة Vente DZ",
    admin_title:"Ø§Ù„Ù…Ø´Ø±Ù",status_connected:"متصل",btn_logout:"Ø®Ø±Ùˆج",
    tab_dashboard:"Ù„Ùˆحة Ø§Ù„ØªØ­Ùƒم",tab_inventory:"Ø§Ù„ÙƒØªØ§Ù„Ùˆج ÙˆØ§Ù„Ù…Ø®Ø²Ùˆن",tab_orders:"تتبع الطلبات",tab_users:"إدارة المستخدمين",tab_tickets:"ØªØ°Ø§Ùƒر الدعم",tab_broadcast:"البث",tab_settings:"الإعدادات",
    metric_revenue:"الإيرادات (30 ÙŠÙˆم)",metric_sales:"المبيعات (30 ÙŠÙˆم)",metric_clients:"العملاء",metric_initiated:"الطلبات (30 ÙŠÙˆم)",
    chart_revenue:"الإيرادات Ø§Ù„ÙŠÙˆمية ($)",chart_orders:"الطلبات Ø§Ù„ÙŠÙˆمية",
    stock_status:"حالة Ø§Ù„Ù…Ø®Ø²Ùˆن",no_products:"لم يتم ØªÙƒÙˆين منتجات.",
    sub_products:"المنتجات",sub_categories:"Ø§Ù„ÙØ¦Ø§Øª",sub_promos:"Ø£ÙƒÙˆاد الخصم",
    all_products:"جميع المنتجات",btn_add_product:"Ø¥Ø¶Ø§ÙØ©",th_product:"المنتج",th_price:"السعر",th_warranty:"الضمان",th_status:"الحالة",
    all_categories:"Ø§Ù„ÙØ¦Ø§Øª",btn_add_category:"Ø¥Ø¶Ø§ÙØ©",no_categories:"لا ØªÙˆجد ÙØ¦Ø§Øª.",
    all_promos:"Ø£ÙƒÙˆاد الخصم",btn_add_promo:"إنشاء ÙƒÙˆد",no_promos:"لا ØªÙˆجد Ø£ÙƒÙˆاد خصم.",th_type:"Ø§Ù„Ù†Ùˆع",th_value:"القيمة",th_uses:"الاستخدامات",
    orders_title:"تتبع الطلبات",filter_all:"Ø§Ù„Ùƒل",filter_pending:"قيد الانتظار",filter_completed:"Ù…Ùƒتملة",filter_cancelled:"ملغاة",filter_topup:"شحن",no_orders:"لا ØªÙˆجد طلبات.",th_client:"العميل",th_amount:"المبلغ",th_qty:"Ø§Ù„Ùƒمية",wallet_topup:"💰 شحن Ø§Ù„Ù…Ø­ÙØ¸Ø©",
    users_title:"إدارة المستخدمين",no_users:"لا ÙŠÙˆجد Ù…Ø³ØªØ®Ø¯Ù…Ùˆن.",th_firstname:"الاسم",th_lang:"اللغة",th_orders_count:"الطلبات",th_spent:"Ø§Ù„Ù…ØµØ±ÙˆÙØ§Øª",th_joined:"التسجيل",th_referrer:"المرجع",th_referrals:"الإحالات",th_referral_earnings:"أرباح الإحالة",users_show_count:"عرض:",users_search_placeholder:"بحث Ø¨Ø§Ù„Ù…Ø¹Ø±Ù أو الاسم...",
    tickets_title:"ØªØ°Ø§Ùƒر الدعم",no_tickets:"لا ØªÙˆجد ØªØ°Ø§Ùƒر معلقة. ðŸ¤",
    broadcast_title:"إرسال رسالة بث",broadcast_desc:"Ø³ØªÙØ±Ø³Ù„ هذه الرسالة لجميع مستخدمي Ø§Ù„Ø¨Ùˆت.",broadcast_label:"الرسالة (يدعم HTML):",btn_send_broadcast:"إرسال للجميع",
    settings_title:"إعدادات API",settings_desc:"المزامنة مع Ø§Ù„Ø¨Ùˆت.",btn_save:"Ø­ÙØ¸",
    modal_add_cat:"Ø¥Ø¶Ø§ÙØ© ÙØ¦Ø©",modal_add_prod:"Ø¥Ø¶Ø§ÙØ© منتج",modal_add_promo:"إنشاء ÙƒÙˆد خصم",
    lbl_name:"الاسم",lbl_category:"Ø§Ù„ÙØ¦Ø©",lbl_prod_name:"اسم المنتج",lbl_price:"السعر ($)",lbl_warranty:"الضمان (أيام)",lbl_discount_type:"Ø§Ù„Ù†Ùˆع",lbl_discount_value:"القيمة",lbl_max_uses:"الحد الأقصى",lbl_expires:"انتهاء الصلاحية",
    btn_cancel:"إلغاء",btn_create_cat:"إنشاء",btn_create_prod:"إنشاء",btn_create_promo:"إنشاء",
    stock_manage:"إدارة Ø§Ù„Ù…Ø®Ø²Ùˆن",stock_add_label:"Ø£Ø¶Ù حسابات (Ùˆاحد ÙÙŠ Ùƒل سطر):",btn_add_stock:"Ø¥Ø¶Ø§ÙØ©",btn_import_file:"استيراد .txt",stock_existing:"Ø§Ù„Ù…Ø®Ø²Ùˆن الحالي",stock_items_lbl:"عناصر",no_stock:"لا ØªÙˆجد عناصر.",
    stock_in:"ÙÙŠ Ø§Ù„Ù…Ø®Ø²Ùˆن",days:"أيام",active:"نشط",inactive:"غير نشط",
    confirm_delete:"Ø­Ø°Ù هذا المنتج؟",confirm_order:"ØªØ£Ùƒيد Ø§Ù„Ø¯ÙØ¹ #",accounts_detected:"حسابات Ù…ÙƒØªØ´ÙØ©",
    available:"✓ متاح",sold:"✗ مباع",no_desc:"Ø¨Ø¯Ùˆن ÙˆØµÙ",btn_confirm:"ØªØ£Ùƒيد",reply_placeholder:"ردك...",btn_reply:"رد",
    ban:"حظر",unban:"إلغاء الحظر",banned:"Ù…Ø­Ø¸Ùˆر",confirm_ban:"حظر هذا المستخدم؟",confirm_unban:"إلغاء حظر هذا المستخدم؟",ban_modal_title:"حظر المستخدم",ban_modal_desc:"هل أنت Ù…ØªØ£Ùƒد أنك تريد حظر هذا المستخدم؟",ban_modal_notify:"إبلاغ المستخدم بأنه تم حظره",
    broadcast_sent:"Ø£ÙØ±Ø³Ù„: {sent}/{total}",broadcast_failed:"ÙØ´Ù„: {failed}",unlimited:"غير Ù…Ø­Ø¯Ùˆد",percent:"نسبة Ù…Ø¦Ùˆية",fixed:"مبلغ ثابت",
    nav_wallet_history:"سجل Ø§Ù„Ù…Ø­ÙØ¸Ø©",wh_title:"سجل Ø§Ù„Ù…Ø­ÙØ¸Ø©",wh_total_topups:"إجمالي الشحنات",wh_total_purchases:"إجمالي مشتريات الرصيد",wh_total_count:"المعاملات",
    wh_filter_topup:"الشحنات",wh_filter_purchase:"مشتريات الرصيد",wh_th_type:"Ø§Ù„Ù†Ùˆع",wh_th_balance_after:"الرصيد بعد",wh_th_description:"Ø§Ù„ÙˆØµÙ",wh_no_tx:"لا ØªÙˆجد معاملات.",
    th_payment_method:"الطريقة",pay_method_wallet:"💰 Ø§Ù„Ù…Ø­ÙØ¸Ø©",pay_method_binance:"⚡ Binance",pay_method_unknown:"—",
    nav_finance:"المالية",tab_finance:"المتابعة المالية",nav_binance:"حسابات Binance",tab_binance:"إدارة حسابات Binance",settings_err:"ÙØ´Ù„Øª العملية: "
}
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  STATE & DOM
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
const state = {
    dzProducts: [], dz_usd_to_dzd: 250, dz_profit_per_usd: 100, dz_oneclick_api_key: '',
    botUrl:'', apiKey:'', currentLang:'fr', currentTab:'dashboard-tab',
    categories:[], products:[], orders:[], users:[], promos:[], tickets:[], walletHistory:[], binanceAccounts:[],
    orderFilter:'all', orderPage:0, orderTotal:0,
    whFilter:'all', whPage:0, whTotal:0,
    usersPage:0, usersPerPage:20, usersSearch:'', usersTotal:0,
    currentStockProductId:null, autoRefresh:false, autoRefreshTimer:null,
    revenueChart:null, ordersChart:null, productSalesChart:null,
    productStats:[]
};

function $(id) { return document.getElementById(id); }
function $$(sel) { return document.querySelectorAll(sel); }

const DOM = {
    loginScreen:$('login-screen'), loginForm:$('login-form'), botUrlInput:$('bot-url'), apiKeyInput:$('api-key'), loginError:$('login-error'),
    appContainer:$('app-container'), currentTabTitle:$('current-tab-title'),
    btnRefresh:$('btn-refresh'), btnLogout:$('btn-logout'), btnTheme:$('btn-theme'), btnAutoRefresh:$('btn-auto-refresh'),
    loadingOverlay:$('loading-overlay'),
    statRevenue:$('stat-revenue'), statOrders:$('stat-orders'), statUsers:$('stat-users'), statPending:$('stat-pending'),
    stockSummaryList:$('stock-summary-list'),
    badgeOrders:$('badge-orders'), badgeTickets:$('badge-tickets'), apiStatusBadge:$('api-status-badge'),
    productsTableBody:$('products-table-body'),
    statsProductsTableBody:$('stats-products-table-body'),
    statsProductSearch:$('stats-product-search'),
    statsKpiTopProduct:$('stats-kpi-top-product'),
    statsKpiTopProductSub:$('stats-kpi-top-product-sub'),
    statsKpiTotalSales:$('stats-kpi-total-sales'),
    statsKpiTotalRevenue:$('stats-kpi-total-revenue'),
    statsKpiStockAlerts:$('stats-kpi-stock-alerts'),
    promosTableBody:$('promos-table-body'),
    ordersTableBody:$('orders-table-body'), ordersPagination:$('orders-pagination'),
    ordersPrev:$('orders-prev'), ordersNext:$('orders-next'), ordersPageInfo:$('orders-page-info'),
    usersTableBody:$('users-table-body'), usersSearch:$('users-search'), usersLimitSelector:$('users-limit-selector'),
    usersPagination:$('users-pagination'), usersPrev:$('users-prev'), usersNext:$('users-next'), usersPageInfo:$('users-page-info'),
    openTicketsContainer:$('open-tickets-container'),
    broadcastTextarea:$('broadcast-textarea'), broadcastResult:$('broadcast-result'), btnSendBroadcast:$('btn-send-broadcast'),
    broadcastPhotoUrl:$('broadcast-photo-url'), broadcastBtnType:$('broadcast-btn-type'), broadcastBtnProductId:$('broadcast-btn-product-id'),
    broadcastBtnText:$('broadcast-btn-text'), broadcastBtnUrl:$('broadcast-btn-url'),
    stockBroadcastCheckbox:$('stock-broadcast-checkbox'),
    settingsForm:$('settings-form'), settingsBotUrl:$('settings-bot-url'), settingsApiKey:$('settings-api-key'),
    cryptoSettingsForm:$('crypto-settings-form'), settingsBep20Address:$('settings-bep20-address'), settingsTrc20Address:$('settings-trc20-address'),
    prodModal:$('prod-modal'), stockModal:$('stock-modal'), promoModal:$('promo-modal'), tiersModal:$('tiers-modal'),
    orderDetailModal:$('order-detail-modal'), viewStockModal:$('view-stock-modal'), editProdModal:$('edit-prod-modal'),
    addProdForm:$('add-prod-form'), addPromoForm:$('add-promo-form'), prodId:$('prod-id'),
    prodName:$('prod-name'), prodPrice:$('prod-price'), prodWarranty:$('prod-warranty'), prodEmoji:$('prod-emoji'), prodCustomEmojiId:$('prod-custom-emoji-id'), prodDesc:$('prod-desc'), prodImageUrl:$('prod-image-url'),
    stockTextarea:$('stock-textarea'), stockLineCount:$('stock-line-count'), btnAddStock:$('btn-add-stock'),
    stockItemsList:$('stock-items-list'), stockExistingCount:$('stock-existing-count'), stockModalTitle:$('stock-modal-title'),
    stockFileInput:$('stock-file-input'),
    chartRevenue:$('chart-revenue'), chartOrders:$('chart-orders'),
    whTableBody:$('wh-table-body'), whPagination:$('wh-pagination'),
    whPrev:$('wh-prev'), whNext:$('wh-next'), whPageInfo:$('wh-page-info'),
    whStatTopups:$('wh-stat-topups'), whStatPurchases:$('wh-stat-purchases'), whStatCount:$('wh-stat-count'),
    revenueModal:$('revenue-modal'), revDetOrders:$('rev-det-orders'), revDetTopups:$('rev-det-topups'),
    revDetAdmin:$('rev-det-admin'), revDetTotal:$('rev-det-total'),
    binanceModal:$('binanceModal'), binanceForm:$('binanceForm'), binanceList:$('binance-table-body'),
    binanceId:$('binanceId'), binanceLabel:$('binanceLabel'), binanceUid:$('binanceUid'),
    binanceApiKey:$('binanceApiKey'), binanceApiSecret:$('binanceApiSecret'), binanceIsDefault:$('binanceIsDefault'),
    prodBinanceAccount:$('prod-binance-account'),
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  i18n HELPERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function t(key) { return LANG[state.currentLang]?.[key] || LANG.fr[key] || key; }

function parseUTCDate(str) {
    if (!str) return new Date();
    let isoStr = str;
    if (!str.includes('T') && !str.includes('Z')) {
        isoStr = str.replace(' ', 'T') + 'Z';
    }
    return new Date(isoStr);
}

function applyTranslations() {
    $$('[data-i18n]').forEach(el => { const k = el.getAttribute('data-i18n'); const v = t(k); if (v) el.textContent = v; });
    $$('[data-i18n-placeholder]').forEach(el => { const k = el.getAttribute('data-i18n-placeholder'); const v = t(k); if (v) el.placeholder = v; });
    document.documentElement.dir = state.currentLang === 'ar' ? 'rtl' : 'ltr';
    $$('.lang-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-lang') === state.currentLang));
}

function setLang(lang) {
    state.currentLang = lang;
    localStorage.setItem('vb_lang', lang);
    applyTranslations();
    if (!DOM.appContainer.classList.contains('hidden')) refreshData();
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  THEME
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('vb_theme', next);
    DOM.btnTheme.innerHTML = next === 'dark' ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  AUTO-REFRESH
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function toggleAutoRefresh() {
    state.autoRefresh = !state.autoRefresh;
    DOM.btnAutoRefresh.classList.toggle('active', state.autoRefresh);
    if (state.autoRefresh) startAutoRefresh(); else stopAutoRefresh();
}

function startAutoRefresh() {
    stopAutoRefresh();
    if (state.autoRefresh) state.autoRefreshTimer = setInterval(() => { if (!DOM.loadingOverlay.classList.contains('hidden')) return; refreshData(); }, 60000);
}

function stopAutoRefresh() {
    if (state.autoRefreshTimer) { clearInterval(state.autoRefreshTimer); state.autoRefreshTimer = null; }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  INIT
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
document.addEventListener('DOMContentLoaded', () => {
    state.currentLang = localStorage.getItem('vb_lang') || 'fr';
    const theme = localStorage.getItem('vb_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    DOM.btnTheme.innerHTML = theme === 'dark' ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
    applyTranslations();

    // Initialize Turbo Mode
    state.turboMode = localStorage.getItem('vb_turbo') === 'true';
    const turboCheckbox = $('settings-turbo-mode');
    if (turboCheckbox) {
        turboCheckbox.checked = state.turboMode;
    }
    if (state.turboMode) {
        document.body.classList.add('turbo-mode');
    }

    const savedUrl = localStorage.getItem('ventebot_url') || '';
    const savedKey = localStorage.getItem('ventebot_key');
    if (savedKey) {
        state.botUrl = savedUrl; state.apiKey = savedKey;
        DOM.settingsBotUrl.value = savedUrl || '';
        DOM.settingsApiKey.value = savedKey;
        testConnectionAndStart();
    } else showScreen('login');

    setupEvents();
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  EVENT LISTENERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function setupEvents() {
    DOM.loginForm.addEventListener('submit', e => {
        e.preventDefault();
        let u = DOM.botUrlInput.value.trim().replace(/\/$/,'');
        if (u && !u.startsWith('http://') && !u.startsWith('https://')) u = 'https://' + u;
        state.apiKey = DOM.apiKeyInput.value.trim();
        state.botUrl = u || '';
        testConnectionAndStart();
    });
    $$('.menu-item').forEach(i => i.addEventListener('click', e => { e.preventDefault(); switchTab(i.getAttribute('data-tab')); }));
    DOM.btnLogout.addEventListener('click', logout);
    DOM.btnRefresh.addEventListener('click', refreshData);
    DOM.btnTheme.addEventListener('click', toggleTheme);
    DOM.btnAutoRefresh.addEventListener('click', toggleAutoRefresh);
    $('btn-export').addEventListener('click', () => showModal($('exportModal')));
    
    if (DOM.statsProductSearch) {
        DOM.statsProductSearch.addEventListener('input', () => {
            renderStatsTable();
        });
    }

    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {
        t.closest('.action-bar').querySelectorAll('.sub-tab').forEach(s => s.classList.remove('active'));
        t.closest('section').querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
        t.classList.add('active'); $(t.getAttribute('data-sub')).classList.add('active');
    }));

    $('btn-open-prod-modal').addEventListener('click', () => { DOM.addProdForm.reset(); DOM.prodId.value=''; showModal(DOM.prodModal); });
    $('btn-open-promo-modal').addEventListener('click', () => {
        const sel = $('promo-products');
        sel.innerHTML = '';
        state.products.forEach(p => {
            const lbl = document.createElement('label');
            lbl.style.display = 'flex';
            lbl.style.alignItems = 'center';
            lbl.style.gap = '8px';
            lbl.style.cursor = 'pointer';
            lbl.style.margin = '0';
            
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = p.id;
            cb.className = 'promo-product-cb';
            
            lbl.appendChild(cb);
            lbl.appendChild(document.createTextNode(' ' + p.name));
            sel.appendChild(lbl);
        });
        showModal(DOM.promoModal);
    });
    $('btn-open-binance-modal').addEventListener('click', openBinanceModal);
    $$('.btn-close-modal').forEach(b => b.addEventListener('click', () => { [DOM.prodModal,DOM.stockModal,DOM.promoModal,DOM.tiersModal,DOM.orderDetailModal,DOM.viewStockModal,DOM.editProdModal,DOM.revenueModal,DOM.binanceModal,$('banModal'),$('finance-withdraw-modal'),$('finance-adjust-modal'), $('exportModal')].forEach(m => { if (m) hideModal(m); }); }));

    DOM.addProdForm.addEventListener('submit', handleAddProduct);
    DOM.addPromoForm.addEventListener('submit', handleAddPromo);
    DOM.settingsForm.addEventListener('submit', handleSaveSettings);
    DOM.cryptoSettingsForm.addEventListener('submit', handleSaveCryptoSettings);

    $$('.order-filter-btn').forEach(b => b.addEventListener('click', () => {
        $$('.order-filter-btn').forEach(x => x.classList.remove('active')); b.classList.add('active');
    state.orderFilter = b.getAttribute('data-status'); state.orderPage = 0; loadAllOrders();
    }));
    DOM.ordersPrev.addEventListener('click', () => { if (state.orderPage > 0) { state.orderPage--; loadAllOrders(); }});
    DOM.ordersNext.addEventListener('click', () => { if (state.orderPage < Math.ceil(state.orderTotal/20)-1) { state.orderPage++; loadAllOrders(); }});

    if (DOM.usersPrev) DOM.usersPrev.addEventListener('click', () => { if (state.usersPage > 0) { state.usersPage--; loadUsers(); }});
    if (DOM.usersNext) DOM.usersNext.addEventListener('click', () => { if (state.usersPage < Math.ceil(state.usersTotal/state.usersPerPage)-1) { state.usersPage++; loadUsers(); }});
    if (DOM.usersLimitSelector) {
        DOM.usersLimitSelector.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.usersLimitSelector.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.usersPerPage = parseInt(btn.getAttribute('data-limit')) || 20;
                state.usersPage = 0;
                loadUsers();
            });
        });
    }
    if (DOM.usersSearch) {
        let searchTimeout;
        DOM.usersSearch.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.usersSearch = DOM.usersSearch.value.trim();
                state.usersPage = 0;
                loadUsers();
            }, 300);
        });
    }

    if (DOM.whPrev) DOM.whPrev.addEventListener('click', () => { if (state.whPage > 0) { state.whPage--; loadWalletHistory(); }});
    if (DOM.whNext) DOM.whNext.addEventListener('click', () => { if (state.whPage < Math.ceil(state.whTotal/20)-1) { state.whPage++; loadWalletHistory(); }});
    $$('.wh-filter-btn').forEach(b => b.addEventListener('click', () => {
        $$('.wh-filter-btn').forEach(x => x.classList.remove('active')); b.classList.add('active');
        state.whFilter = b.getAttribute('data-type'); state.whPage = 0; loadWalletHistory();
    }));

    DOM.stockTextarea.addEventListener('input', () => { const n = DOM.stockTextarea.value.split('\n').filter(l=>l.trim()).length; DOM.stockLineCount.textContent = `${n} ${t('accounts_detected')}`; });
    DOM.btnAddStock.addEventListener('click', handleAddStock);
    DOM.stockFileInput.addEventListener('change', handleFileImport);
    DOM.btnSendBroadcast.addEventListener('click', handleBroadcast);
    DOM.broadcastBtnType.addEventListener('change', (e) => {
        const type = e.target.value;
        $('broadcast-buy-group').classList.toggle('hidden', type !== 'buy');
        $('broadcast-url-group').classList.toggle('hidden', type !== 'url');
    });
    $$('.lang-btn').forEach(b => b.addEventListener('click', () => setLang(b.getAttribute('data-lang'))));

    // Turbo Mode toggle listener
    const turboModeToggle = $('settings-turbo-mode');
    if (turboModeToggle) {
        turboModeToggle.addEventListener('change', (e) => {
            state.turboMode = e.target.checked;
            localStorage.setItem('vb_turbo', state.turboMode);
            document.body.classList.toggle('turbo-mode', state.turboMode);
        });
    }

    // Spotlight cursor follow effect
    document.addEventListener('mousemove', (e) => {
        if (!state.turboMode) return;
        const panels = document.querySelectorAll('.glass-panel');
        panels.forEach(el => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            el.style.setProperty('--mx', `${x}px`);
            el.style.setProperty('--my', `${y}px`);
        });
    });

    // Particle click burst
    document.addEventListener('click', (e) => {
        if (!state.turboMode) return;
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT' || e.target.closest('button') || e.target.closest('a')) return;
        createParticleBurst(e.clientX, e.clientY);
    });
}

// ── Particle Generator Utility ──
function createParticleBurst(x, y) {
    const count = 15;
    const colors = ['#6366f1', '#ec4899', '#a78bfa', '#f59e0b', '#10b981'];
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'click-particle';
        p.style.left = `${x}px`;
        p.style.top = `${y}px`;
        p.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        
        const angle = Math.random() * Math.PI * 2;
        const velocity = 40 + Math.random() * 80;
        const tx = Math.cos(angle) * velocity;
        const ty = Math.sin(angle) * velocity;
        
        document.body.appendChild(p);
        
        requestAnimationFrame(() => {
            p.style.transform = `translate(${tx}px, ${ty}px) scale(0)`;
            p.style.opacity = '0';
        });
        
        setTimeout(() => p.remove(), 800);
    }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  API CALL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
async function apiCall(endpoint, method='GET', body=null) {
    const url = `${state.botUrl}${endpoint}`;
    const headers = { 'X-API-Key': state.apiKey };
    if (body) headers['Content-Type'] = 'application/json';
    const ctrl = new AbortController(); const tid = setTimeout(() => ctrl.abort(), 60000);
    const cfg = { method, headers, mode:'cors', signal:ctrl.signal };
    if (body) cfg.body = JSON.stringify(body);
    try {
        const res = await fetch(url, cfg); clearTimeout(tid);
        if (!res.ok) { if (res.status===401) throw new Error('API_KEY_INVALID'); throw new Error(`API ${res.status}`); }
        return await res.json();
    } catch(e) { clearTimeout(tid); if (e.name==='AbortError') throw new Error('TIMEOUT'); throw e; }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  CONNECTION
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
async function testConnectionAndStart() {
    showLoading(true); DOM.loginError.classList.add('hidden');
    try {
        const ctrl = new AbortController(); const tid = setTimeout(() => ctrl.abort(), 60000);
        try { const r = await fetch(`${state.botUrl}/health`, {mode:'cors',signal:ctrl.signal}); clearTimeout(tid); const h = await r.json(); if (!h||h.status!=='ok') throw new Error('BAD'); }
        catch(e) { clearTimeout(tid); if (e.name==='AbortError') throw new Error('TIMEOUT'); throw new Error('UNREACHABLE'); }
        try { await apiCall('/api/stats'); } catch(e) { if (e.message==='API_KEY_INVALID') throw e; throw e; }
        localStorage.setItem('ventebot_url', state.botUrl); localStorage.setItem('ventebot_key', state.apiKey);
        DOM.settingsBotUrl.value = state.botUrl; DOM.settingsApiKey.value = state.apiKey;
        showScreen('app'); refreshData(); startAutoRefresh();
    } catch(e) {
        showScreen('login'); DOM.botUrlInput.value = state.botUrl; DOM.loginError.classList.remove('hidden');
        let msg = e.message==='TIMEOUT' ? 'â± Timeout — réessayez dans 30s' : e.message==='API_KEY_INVALID' ? '🔑 Clé API invalide' : `âŒ ${e.message}`;
        DOM.loginError.innerHTML = msg;
    } finally { showLoading(false); }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  REFRESH ALL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
async function refreshData() {
    showLoading(true);
    DOM.apiStatusBadge.querySelector('.status-indicator').className = 'status-indicator';
    try {
        await Promise.all([loadStats(), loadFinance(), loadProducts(), loadAllOrders(), loadTickets(), loadUsers(), loadPromos(), loadCharts(), loadWalletHistory(), loadBinanceAccounts(), loadPaymentSettings(), loadProductStats()]);
        DOM.apiStatusBadge.querySelector('.status-indicator').classList.add('online');
    } catch(e) { console.error(e); DOM.apiStatusBadge.querySelector('.status-indicator').classList.add('offline'); }
    finally { showLoading(false); }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  DATA LOADERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
async function loadBinanceAccounts() {
    try {
        const accounts = await apiCall('/api/binance-accounts');
        state.binanceAccounts = accounts;
        
        // Populate table
        if (accounts.length === 0) {
            DOM.binanceList.innerHTML = '<tr><td colspan="4" class="empty-state">Aucun compte Binance.</td></tr>';
        } else {
            DOM.binanceList.innerHTML = accounts.map(a => `
                <tr>
                    <td><strong>${escapeHtml(a.label)}</strong></td>
                    <td><code>${escapeHtml(a.uid)}</code></td>
                    <td>${a.is_default ? '<span class="status-badge status-completed">Oui</span>' : '-'}</td>
                    <td>
                        <button class="btn-secondary btn-sm" onclick="editBinanceAccount(${a.id})" title="Modifier"><i class="fa-solid fa-pen"></i></button>
                        <button class="btn-secondary btn-sm" onclick="deleteBinanceAccount(${a.id})" title="Supprimer" style="color:#ef4444"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        // Populate dropdown in product modal
        if (DOM.prodBinanceAccount) {
            const currentVal = DOM.prodBinanceAccount.value;
            DOM.prodBinanceAccount.innerHTML = '<option value="">-- Par défaut --</option>' +
                accounts.map(a => `<option value="${a.id}">${escapeHtml(a.label)} (${escapeHtml(a.uid)})</option>`).join('');
            DOM.prodBinanceAccount.value = currentVal; // Restore selection if any
        }
    } catch(e) {
        console.error('Failed to load Binance accounts', e);
    }
}

async function loadStats() {
    const s = await apiCall('/api/stats');
    state.lastStats = s; // Save for modal
    DOM.statRevenue.textContent = `$${parseFloat(s.total_revenue).toFixed(2)}`;
    DOM.statOrders.textContent = s.completed_orders;
    DOM.statUsers.textContent = s.total_users;
    DOM.statPending.textContent = s.total_orders;
    if (s.stock_summary?.length > 0) {
        DOM.stockSummaryList.innerHTML = s.stock_summary.map(i => {
            const c = i.stock===0?'empty':i.stock<3?'low':'ok';
            return `<div class="stock-status-item"><div class="prod-badge"><span class="prod-emoji">${i.emoji}</span><span class="prod-name-lbl">${i.name}</span></div><span class="stock-count-badge ${c}">${i.stock} ${t('stock_in')}</span></div>`;
        }).join('');
    } else DOM.stockSummaryList.innerHTML = `<p class="empty-state">${t('no_products')}</p>`;
}

window.showRevenueDetails = function() {
    if (!state.lastStats) return;
    DOM.revDetOrders.textContent = `$${parseFloat(state.lastStats.order_revenue || 0).toFixed(2)}`;
    DOM.revDetTopups.textContent = `+$${parseFloat(state.lastStats.topup_revenue || 0).toFixed(2)}`;
    DOM.revDetAdmin.textContent = `-$${parseFloat(state.lastStats.admin_deductions || 0).toFixed(2)}`;
    DOM.revDetTotal.textContent = `$${parseFloat(state.lastStats.total_revenue || 0).toFixed(2)}`;
    showModal(DOM.revenueModal);
};

async function loadCharts() {
    try {
        const data = await apiCall('/api/stats/daily?days=30');
        const labels = data.map(d => d.day.slice(5));
        const revenues = data.map(d => d.revenue);
        const orders = data.map(d => d.orders);
        const chartColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#6366f1';
        const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.05)';
        const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#9f9baa';
        const opts = { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{ticks:{color:textColor,maxTicksLimit:10},grid:{color:gridColor}},y:{ticks:{color:textColor},grid:{color:gridColor}}} };
        if (state.revenueChart) state.revenueChart.destroy();
        state.revenueChart = new Chart(DOM.chartRevenue, { type:'line', data:{ labels, datasets:[{ data:revenues, borderColor:chartColor, backgroundColor:chartColor+'20', fill:true, tension:0.4, pointRadius:2 }] }, options:opts });
        if (state.ordersChart) state.ordersChart.destroy();
        state.ordersChart = new Chart(DOM.chartOrders, { type:'bar', data:{ labels, datasets:[{ data:orders, backgroundColor:chartColor+'60', borderColor:chartColor, borderWidth:1, borderRadius:4 }] }, options:opts });
    } catch(e) { console.warn('Charts failed:', e); }
}

async function loadProductStats() {
    try {
        const stats = await apiCall('/api/stats/products');
        state.productStats = stats;
        
        let topProduct = null;
        let maxSold = -1;
        let totalSalesVolume = 0;
        let totalRevenue = 0;
        let stockAlerts = 0;
        
        stats.forEach(p => {
            totalSalesVolume += p.total_sold;
            totalRevenue += p.total_revenue;
            if (p.total_sold > maxSold) {
                maxSold = p.total_sold;
                topProduct = p;
            }
            if (p.stock < 3) {
                stockAlerts++;
            }
        });
        
        if (topProduct && maxSold > 0) {
            DOM.statsKpiTopProduct.textContent = `${topProduct.emoji} ${topProduct.name}`;
            DOM.statsKpiTopProductSub.textContent = `${maxSold} vente(s) ($${topProduct.total_revenue.toFixed(2)})`;
        } else {
            DOM.statsKpiTopProduct.textContent = "-";
            DOM.statsKpiTopProductSub.textContent = "Aucune vente";
        }
        
        DOM.statsKpiTotalSales.textContent = totalSalesVolume;
        DOM.statsKpiTotalRevenue.textContent = `$${totalRevenue.toFixed(2)}`;
        DOM.statsKpiStockAlerts.textContent = stockAlerts;
        
        renderProductSalesChart(stats);
        renderStatsTable();
        
    } catch(e) {
        console.error("Failed to load product stats:", e);
    }
}

function renderProductSalesChart(stats) {
    if (!DOM.chartProductSales) return;
    
    const sortedStats = [...stats].sort((a, b) => b.total_revenue - a.total_revenue);
    const topN = sortedStats.slice(0, 5);
    const others = sortedStats.slice(5);
    
    const labels = [];
    const revenues = [];
    
    topN.forEach(p => {
        if (p.total_revenue > 0) {
            labels.push(`${p.emoji} ${p.name}`);
            revenues.push(p.total_revenue);
        }
    });
    
    if (others.length > 0) {
        const othersRevenue = others.reduce((sum, p) => sum + p.total_revenue, 0);
        if (othersRevenue > 0) {
            labels.push("Autres produits");
            revenues.push(othersRevenue);
        }
    }
    
    if (revenues.length === 0) {
        labels.push("Aucune vente");
        revenues.push(1);
    }
    
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.05)';
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#9f9baa';
    const colors = ['#6366f1', '#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'];
    
    if (state.productSalesChart) state.productSalesChart.destroy();
    
    const hasSales = revenues.length > 1 || (revenues.length === 1 && labels[0] !== "Aucune vente");
    const bgColors = hasSales ? colors.slice(0, revenues.length) : ['rgba(255, 255, 255, 0.05)'];
    const borderColors = hasSales ? colors.slice(0, revenues.length).map(c => c + 'aa') : ['rgba(255, 255, 255, 0.1)'];
    
    state.productSalesChart = new Chart(DOM.chartProductSales, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: revenues,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textColor,
                        boxWidth: 12,
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            if (!hasSales) return "Aucune vente enregistrée";
                            const val = context.raw;
                            return ` ${context.label}: $${val.toFixed(2)}`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

function renderStatsTable() {
    if (!DOM.statsProductsTableBody) return;
    
    const query = DOM.statsProductSearch ? DOM.statsProductSearch.value.trim().toLowerCase() : '';
    const filtered = state.productStats.filter(p => {
        return p.name.toLowerCase().includes(query) || (p.emoji && p.emoji.includes(query));
    });
    
    if (filtered.length === 0) {
        DOM.statsProductsTableBody.innerHTML = `<tr><td colspan="6" class="empty-state">Aucun produit trouvé.</td></tr>`;
        return;
    }
    
    DOM.statsProductsTableBody.innerHTML = filtered.map(p => {
        let statusBadge = '';
        if (p.total_sold >= 10) {
            statusBadge = '<span class="status-badge success"><i class="fa-solid fa-fire"></i> Top Vente</span>';
        } else if (p.total_sold === 0) {
            statusBadge = '<span class="status-badge neutral">Pas de vente</span>';
        } else {
            statusBadge = '<span class="status-badge info">Normal</span>';
        }
        
        let stockBadge = '';
        if (p.stock === 0) {
            stockBadge = '<span class="stock-count-badge empty">Rupture</span>';
        } else if (p.stock < 3) {
            stockBadge = `<span class="stock-count-badge low">${p.stock} (Bas)</span>`;
        } else {
            stockBadge = `<span class="stock-count-badge ok">${p.stock}</span>`;
        }
        
        return `
            <tr>
                <td><div class="prod-badge"><span class="prod-emoji">${p.emoji}</span><strong>${p.name}</strong></div></td>
                <td>$${p.price_usd.toFixed(2)}</td>
                <td>${p.total_sold}</td>
                <td><strong>$${p.total_revenue.toFixed(2)}</strong></td>
                <td>${stockBadge}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    }).join('');
}

// Categories removed — products shown directly

async function loadProducts() {
    const prods = await apiCall('/api/products'); state.products = prods;
    if (prods.length > 0) {
        DOM.productsTableBody.innerHTML = prods.map(p => `<tr data-id="${p.id}">
            <td class="drag-handle" style="cursor: grab; text-align: center;"><i class="fas fa-bars" style="color:var(--color-primary);"></i></td>
            <td><div class="prod-badge"><span class="prod-emoji">${p.emoji||'📦'}</span><strong>${p.name}</strong></div></td>
            <td>$${parseFloat(p.price_usd).toFixed(2)}</td><td>${p.warranty_days||0} ${t('days')}</td>
            <td><span class="stock-count-badge ${p.stock===0?'empty':p.stock<3?'low':'ok'}">${p.stock}</span></td>
            <td><span class="status-dot ${p.is_active?'online':''}"></span> ${p.is_active?t('active'):t('inactive')}</td>
            <td><button class="btn-table-action" onclick="openEditProduct(${p.id})" title="Modifier" style="color:#3b82f6;"><i class="fa-solid fa-pen"></i></button><button class="btn-table-action" onclick="viewProductStock(${p.id},'${(p.emoji||'📦').replace(/'/g,'\\\'')}','${p.name.replace(/'/g,'\\\'')}')" title="Voir stock" style="color:#f59e0b;"><i class="fa-solid fa-eye"></i></button><button class="btn-table-action stock" onclick="openStockModal(${p.id},'${(p.emoji||'📦').replace(/'/g,'\\\'')}','${p.name.replace(/'/g,'\\\'')}')" title="${t('stock_manage')}"><i class="fa-solid fa-warehouse"></i></button><button class="btn-table-action" onclick="openTiersModal(${p.id},'${p.name.replace(/'/g,'\\\'')}',${parseFloat(p.price_usd).toFixed(2)})" title="Tarifs" style="color:#a78bfa;"><i class="fa-solid fa-tags"></i></button><button class="btn-table-action delete" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash-can"></i></button></td>
        </tr>`).join('');
        if (DOM.broadcastBtnProductId) {
            DOM.broadcastBtnProductId.innerHTML = prods.map(p => `<option value="${p.id}">${p.emoji||'📦'} ${p.name}</option>`).join('');
        }
        
        if (!window.productsSortable) {
            window.productsSortable = new Sortable(DOM.productsTableBody, {
                handle: '.drag-handle',
                animation: 150,
                onEnd: async function () {
                    const rows = DOM.productsTableBody.querySelectorAll('tr[data-id]');
                    const newOrder = Array.from(rows).map((row, index) => ({
                        id: parseInt(row.getAttribute('data-id')),
                        sort_order: index
                    }));
                    try {
                        await apiCall('/api/products/update-sort', 'POST', { orders: newOrder });
                    } catch (e) {
                        alert('Erreur de sauvegarde: ' + e.message + '\nCible: ' + (state.botUrl || 'relative') + '/api/products/update-sort');
                        loadProducts();
                    }
                }
            });
        }
    } else {
        DOM.productsTableBody.innerHTML = `<tr><td colspan="7" class="empty-state">${t('no_products')}</td></tr>`;
        if (DOM.broadcastBtnProductId) {
            DOM.broadcastBtnProductId.innerHTML = '<option value="">Aucun produit</option>';
        }
    }
}

async function loadAllOrders() {
    // Auto-cancel expired PENDING orders server-side before loading
    try { await apiCall('/api/orders/cleanup', 'POST'); } catch(e) {}

    const sp = state.orderFilter==='all' ? '' : `status=${state.orderFilter}&`;
    const r = await apiCall(`/api/orders/all?${sp}limit=20&offset=${state.orderPage*20}`);
    state.orders = r.orders; state.orderTotal = r.total;
    // badge
    try { const pending = await apiCall('/api/orders'); if (pending.length>0) { DOM.badgeOrders.textContent=pending.length; DOM.badgeOrders.classList.remove('hidden'); } else DOM.badgeOrders.classList.add('hidden'); } catch(e) {}

    if (r.orders.length > 0) {
        DOM.ordersTableBody.innerHTML = r.orders.map(o => {
            const isTopup = o.status === 'TOPUP';
            const prod = !isTopup ? state.products.find(p=>p.id===o.product_id) : null;
            let pn = isTopup ? t('wallet_topup') : (prod ? `${prod.emoji} ${prod.name}` : `#${o.product_id}`);
            if (!isTopup && !prod && o.product_name) {
                pn = `${o.product_emoji || '📦'} ${o.product_name}${o.product_is_deleted ? ' (Supprimé)' : ''}`;
            }
            const d = parseUTCDate(o.created_at).toLocaleDateString();
            const uname = o.username ? `@${o.username}` : (o.user_first_name || o.user_telegram_id);
            const orderNo = o.merchant_trade_no || '—';
            // Payment method badge
            let payMethod = '—';
            if (isTopup) {
                payMethod = `<span class="pay-method-badge wallet">${t('pay_method_wallet')}</span>`;
            } else if (o.payment_method === 'wallet') {
                payMethod = `<span class="pay-method-badge wallet">${t('pay_method_wallet')}</span>`;
            } else if (o.payment_method === 'binance' || o.payment_method == null) {
                payMethod = `<span class="pay-method-badge binance">${t('pay_method_binance')}</span>`;
            } else {
                payMethod = `<span class="pay-method-badge">${o.payment_method}</span>`;
            }
            let actions = '';
            if (isTopup) {
                actions = `<span style="font-size:0.78rem;color:var(--color-text-muted);">Balance: $${parseFloat(o.balance_after||0).toFixed(2)}</span>`;
            } else if (o.status === 'PENDING' || o.status === 'AWAITING_PAYMENT') {
                actions = `<button class="btn-table-action" onclick="confirmOrderPayment(${o.id})" title="Confirmer" style="color:#22c55e;"><i class="fa-solid fa-check"></i></button> <button class="btn-table-action" onclick="cancelOrder(${o.id})" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`;
            } else if (o.status === 'COMPLETED') {
                actions = `<button class="btn-table-action" onclick="openOrderDetail(${o.id})" title="Voir les articles livrés" style="color:#22c55e;"><i class="fa-solid fa-eye"></i></button>`;
            } else {
                actions = '—';
            }
            let statusHtml = o.status;
            if (!isTopup && (o.status === 'PENDING' || o.status === 'AWAITING_PAYMENT')) {
                const elapsed = Math.floor((Date.now() - parseUTCDate(o.created_at).getTime()) / 1000);
                const left = 300 - elapsed;
                const eM = Math.floor(elapsed / 60);
                const eS = elapsed % 60;
                
                if (left > 0) {
                    const lM = Math.floor(left / 60);
                    const lS = left % 60;
                    statusHtml += `<br><span style="font-size:0.7rem; color:var(--color-text-muted); display:block; margin-top:4px;">Depuis ${eM}m ${eS}s<br>Reste ${lM}m ${lS}s</span>`;
                } else {
                    statusHtml += `<br><span style="font-size:0.7rem; color:var(--color-error); display:block; margin-top:4px;">Expiré (Depuis ${eM}m ${eS}s)</span>`;
                }

                if (o.status === 'AWAITING_PAYMENT' && o.binance_order_id) {
                    statusHtml += `<span style="font-size:0.7rem; color:var(--color-error); font-weight:bold; display:block; margin-top:2px;">âš ï¸ ID Invalide</span>`;
                }
            }

            let displayBId = o.binance_order_id || '—';
            if (displayBId.length > 15 && displayBId !== '—') {
                displayBId = `<span title="${o.binance_order_id}" style="cursor:help; border-bottom: 1px dotted rgba(255,255,255,0.5);">${o.binance_order_id.substring(0, 3)}...${o.binance_order_id.substring(o.binance_order_id.length - 4)}</span>`;
            }

            return `<tr><td><strong>#${o.id}</strong></td><td><code>${orderNo}</code></td><td><code>${displayBId}</code></td><td>${uname}</td><td>${pn}</td><td>$${parseFloat(o.amount_usd).toFixed(2)}</td><td>${isTopup ? '—' : (o.quantity||1)}</td><td>${payMethod}</td><td><div class="status-badge ${o.status.toLowerCase()}">${statusHtml}</div></td><td>${d}</td><td>${actions}</td></tr>`;
        }).join('');
    } else DOM.ordersTableBody.innerHTML = `<tr><td colspan="11" class="empty-state" data-i18n="no_orders">Aucune commande.</td></tr>`;
    const tp = Math.max(1, Math.ceil(r.total/20));
    DOM.ordersPageInfo.textContent = `${state.orderPage+1} / ${tp}`;
    DOM.ordersPagination.classList.toggle('hidden', tp <= 1);
}

async function loadWalletHistory() {
    const type = state.whFilter === 'all' ? '' : `&tx_type=${state.whFilter}`;
    let data;
    try {
        data = await apiCall(`/api/wallet/history?limit=20&offset=${state.whPage*20}${type}`);
    } catch(e) { console.warn('Wallet history load failed:', e); return; }
    const txs = data.transactions || [];
    const total = data.total || 0;
    state.whTotal = total;

    // Compute stats (sum topups, purchases)
    let sumTopups = 0, sumPurchases = 0;
    txs.forEach(tx => {
        if (tx.type === 'topup') sumTopups += parseFloat(tx.amount||0);
        else sumPurchases += parseFloat(tx.amount||0);
    });
    if (DOM.whStatTopups) DOM.whStatTopups.textContent = `$${sumTopups.toFixed(2)}`;
    if (DOM.whStatPurchases) DOM.whStatPurchases.textContent = `$${sumPurchases.toFixed(2)}`;
    if (DOM.whStatCount) DOM.whStatCount.textContent = total;

    if (txs.length > 0) {
        DOM.whTableBody.innerHTML = txs.map(tx => {
            const uname = tx.username ? `@${tx.username}` : (tx.user_first_name || tx.user_telegram_id);
            const d = tx.created_at ? parseUTCDate(tx.created_at).toLocaleString() : '—';
            const isTopup = tx.type === 'topup';
            const typeLabel = isTopup
                ? `<span class="status-badge completed" style="background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.3);">➕ Recharge</span>`
                : `<span class="status-badge" style="background:rgba(99,102,241,0.15);color:#818cf8;border:1px solid rgba(99,102,241,0.3);">🛒 Achat</span>`;
            const amountColor = isTopup ? '#22c55e' : '#ef4444';
            const amountSign = isTopup ? '+' : '-';
            const desc = tx.description || '—';
            const balAfter = parseFloat(tx.balance_after||0).toFixed(2);
            return `<tr>
                <td><strong>#${tx.id}</strong></td>
                <td>${uname}</td>
                <td>${typeLabel}</td>
                <td style="color:${amountColor};font-weight:600;">${amountSign}$${parseFloat(tx.amount||0).toFixed(2)}</td>
                <td>💰 $${balAfter}</td>
                <td style="font-size:0.82rem;color:var(--color-text-muted);">${desc}</td>
                <td style="font-size:0.82rem;">${d}</td>
            </tr>`;
        }).join('');
    } else {
        DOM.whTableBody.innerHTML = `<tr><td colspan="7" class="empty-state">${t('wh_no_tx')}</td></tr>`;
    }
    const tp = Math.max(1, Math.ceil(total/20));
    DOM.whPageInfo.textContent = `${state.whPage+1} / ${tp}`;
    DOM.whPagination.classList.toggle('hidden', tp <= 1);
}

async function loadTickets() {
    const tks = await apiCall('/api/tickets'); state.tickets = tks;
    if (tks.length > 0) {
        DOM.badgeTickets.textContent = tks.length; DOM.badgeTickets.classList.remove('hidden');
        DOM.openTicketsContainer.innerHTML = tks.map(tk => `<div class="ticket-card glass-panel animate-slide"><div class="ticket-header"><h3>🎫 #${tk.id}</h3><p>👤 <code>${tk.user_telegram_id}</code></p></div><div class="ticket-message"><p>${tk.message}</p></div><form class="ticket-reply-form" onsubmit="submitTicketReply(event,${tk.id})"><div class="form-group"><input type="text" placeholder="${t('reply_placeholder')}" required></div><button type="submit" class="btn-primary btn-send-reply"><i class="fa-solid fa-paper-plane"></i></button></form></div>`).join('');
    } else { DOM.badgeTickets.classList.add('hidden'); DOM.openTicketsContainer.innerHTML = `<p class="empty-state">${t('no_tickets')}</p>`; }
}

async function loadUsers() {
    try {
        const limit = state.usersPerPage || 20;
        const offset = (state.usersPage || 0) * limit;
        const search = encodeURIComponent(state.usersSearch || '');
        const r = await apiCall(`/api/users?limit=${limit}&offset=${offset}&search=${search}`);
        state.users = r.users;
        state.usersTotal = r.total;
        
        if (r.users.length > 0) {
            DOM.usersTableBody.innerHTML = r.users.map(u => {
                const banned = u.is_banned;
                const d = u.created_at ? parseUTCDate(u.created_at).toLocaleDateString() : '—';
                const wb = parseFloat(u.wallet_balance||0).toFixed(2);
                const refBy = u.referred_by ? `<code>${u.referred_by}</code>` : '—';
                const refCount = u.referrals_count || 0;
                const refEarnings = parseFloat(u.referral_earnings||0).toFixed(2);
                return `<tr><td><code>${u.telegram_id}</code></td><td>${u.username||'—'}</td><td>${u.first_name||'—'}</td><td>${u.language||'fr'}</td><td>${u.total_orders||0}</td><td>$${parseFloat(u.total_spent||0).toFixed(2)}</td><td>💰 $${wb}</td><td>${refBy}</td><td>${refCount}</td><td>💰 $${refEarnings}</td><td>${d}</td><td><button class="btn-table-action" onclick="creditWallet(${u.telegram_id})" title="Créditer" style="color:#22c55e;"><i class="fa-solid fa-circle-plus"></i></button> <button class="btn-table-action" onclick="debitWallet(${u.telegram_id})" title="Retirer" style="color:#ef4444;"><i class="fa-solid fa-circle-minus"></i></button> ${banned?`<span class="status-badge banned">${t('banned')}</span> <button class="btn-table-action unban" onclick="unbanUser(${u.telegram_id})"><i class="fa-solid fa-lock-open"></i></button>`:`<button class="btn-table-action ban" onclick="banUser(${u.telegram_id})"><i class="fa-solid fa-ban"></i></button>`}</td></tr>`;
            }).join('');
        } else {
            DOM.usersTableBody.innerHTML = `<tr><td colspan="12" class="empty-state">${t('no_users')}</td></tr>`;
        }

        const totalPages = Math.ceil(state.usersTotal / limit) || 1;
        DOM.usersPageInfo.textContent = `${(state.usersPage || 0) + 1} / ${totalPages}`;
        if (state.usersTotal > limit) {
            DOM.usersPagination.classList.remove('hidden');
        } else {
            DOM.usersPagination.classList.add('hidden');
        }
    } catch(e) { console.warn('loadUsers:', e); }
}

async function loadPromos() {
    try {
        const promos = await apiCall('/api/promos');
        if (promos.length > 0) {
            DOM.promosTableBody.innerHTML = promos.map(p => {
                const typeLabel = p.discount_type==='percent' ? '%' : '$';
                let usesLabel = p.max_uses > 0 ? `${p.used_count}/${p.max_uses}` : `${p.used_count} (${t('unlimited')})`;
                if (p.max_uses_per_user > 0) usesLabel += ` <br><small>(${p.max_uses_per_user}/user)</small>`;
                if (p.max_qty_per_order > 0) usesLabel += ` <br><small>(Max ${p.max_qty_per_order}/cmd)</small>`;
                if (p.applicable_product_ids) usesLabel += ` <br><small>(Produits limités)</small>`;
                const active = p.is_active ? 'active-promo' : 'expired';
                return `<tr><td><strong>${p.code}</strong></td><td>${p.discount_type==='percent'?t('percent'):t('fixed')}</td><td>${p.discount_value}${typeLabel}</td><td>${usesLabel}</td><td><span class="status-badge ${active}">${p.is_active?t('active'):t('inactive')}</span></td><td><button class="btn-table-action delete" onclick="deletePromo(${p.id})"><i class="fa-solid fa-trash-can"></i></button></td></tr>`;
            }).join('');
        } else DOM.promosTableBody.innerHTML = `<tr><td colspan="6" class="empty-state">${t('no_promos')}</td></tr>`;
    } catch(e) { console.warn('loadPromos:', e); }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  ACTIONS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async function handleAddPromo(e) { e.preventDefault(); showLoading(true); try { const applicable_product_ids = Array.from(document.querySelectorAll('.promo-product-cb:checked')).map(o => o.value).join(','); await apiCall('/api/promos','POST',{code:$('promo-code').value.trim(),discount_type:$('promo-type').value,discount_value:$('promo-value').value,max_uses:$('promo-max').value||0,max_uses_per_user:$('promo-max-user').value||0,max_qty_per_order:$('promo-max-qty').value||0,applicable_product_ids:applicable_product_ids,expires_at:$('promo-expires').value||null}); hideModal(DOM.promoModal); DOM.addPromoForm.reset(); await refreshData(); } catch(e){alert(e.message);} finally{showLoading(false);} }

window.deleteProduct = async function(id) { if(!confirm(t('confirm_delete'))) return; showLoading(true); try{await apiCall(`/api/products/${id}`,'DELETE'); await refreshData();}catch(e){alert(e.message);}finally{showLoading(false);} };
window.deletePromo = async function(id) { showLoading(true); try{await apiCall(`/api/promos/${id}`,'DELETE'); await refreshData();}catch(e){alert(e.message);}finally{showLoading(false);} };
window.confirmOrderPayment = async function(id) { if(!confirm(`${t('confirm_order')}${id}?`)) return; showLoading(true); try{await apiCall(`/api/orders/${id}/confirm`,'POST'); await refreshData();}catch(e){alert(e.message);}finally{showLoading(false);} };
window.cancelOrder = async function(id) { if(!confirm(`Annuler la commande #${id} ?`)) return; showLoading(true); try{await apiCall(`/api/orders/${id}/cancel`,'POST'); await refreshData();}catch(e){alert(e.message);}finally{showLoading(false);} };

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  PRICE TIERS MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
let _tiersProductId = null;

window.openTiersModal = async function(productId, productName, basePrice) {
    _tiersProductId = productId;
    $('tiers-modal-title').textContent = `Tarifs — ${productName} (base: $${basePrice})`;
    const container = $('tiers-rows-container');
    container.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Chargement...</p>';
    showModal(DOM.tiersModal);

    try {
        const tiers = await apiCall(`/api/products/${productId}/tiers`);
        container.innerHTML = '';
        if (tiers.length === 0) {
            _addTierRow(container, 1, 10, basePrice);
        } else {
            tiers.forEach(tier => _addTierRow(container, tier.min_qty, tier.max_qty, tier.price_usd));
        }
    } catch(e) {
        container.innerHTML = '<p style="color:var(--color-error);">Erreur de chargement.</p>';
    }
};

function _addTierRow(container, min, max, price) {
    const row = document.createElement('div');
    row.className = 'tier-row';
    row.innerHTML = `
        <div class="form-row" style="align-items:flex-end;gap:0.5rem;margin-bottom:0.5rem;">
            <div class="form-group" style="flex:1;margin-bottom:0;"><label style="font-size:0.75rem;">Min Qté</label><input type="number" class="tier-min" value="${min}" min="1"></div>
            <div class="form-group" style="flex:1;margin-bottom:0;"><label style="font-size:0.75rem;">Max Qté</label><input type="number" class="tier-max" value="${max}" min="1"></div>
            <div class="form-group" style="flex:1;margin-bottom:0;"><label style="font-size:0.75rem;">Prix/u ($)</label><input type="number" step="0.01" class="tier-price" value="${parseFloat(price).toFixed(2)}"></div>
            <button type="button" class="btn-table-action delete" onclick="this.closest('.tier-row').remove()" style="margin-bottom:0.3rem;"><i class="fa-solid fa-trash-can"></i></button>
        </div>`;
    container.appendChild(row);
}

$('btn-add-tier-row').addEventListener('click', () => {
    const container = $('tiers-rows-container');
    const rows = container.querySelectorAll('.tier-row');
    const lastMax = rows.length > 0 ? parseInt(rows[rows.length-1].querySelector('.tier-max').value)||0 : 0;
    _addTierRow(container, lastMax+1, lastMax+10, 0);
});

$('btn-save-tiers').addEventListener('click', async () => {
    if (!_tiersProductId) return;
    const rows = $('tiers-rows-container').querySelectorAll('.tier-row');
    const tiers = [];
    for (const row of rows) {
        const min = parseInt(row.querySelector('.tier-min').value);
        const max = parseInt(row.querySelector('.tier-max').value);
        const price = parseFloat(row.querySelector('.tier-price').value);
        if (isNaN(min)||isNaN(max)||isNaN(price)||min<=0||max<min||price<0) {
            alert('Vérifiez les valeurs des paliers (min ≤ max, prix ≥ 0).');
            return;
        }
        tiers.push({min_qty:min, max_qty:max, price_usd:price});
    }
    showLoading(true);
    try {
        await apiCall(`/api/products/${_tiersProductId}/tiers`, 'PUT', {tiers});
        hideModal(DOM.tiersModal);
    } catch(e) { alert(e.message); }
    finally { showLoading(false); }
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  ORDER DETAIL MODAL (delivered items)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.openOrderDetail = async function(orderId) {
    $('order-detail-title').textContent = `Commande #${orderId}`;
    $('order-detail-info').innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Chargement...</p>';
    $('order-items-list').innerHTML = '';
    $('order-items-count').textContent = '...';
    $('btn-download-order-txt').style.display = 'none';
    showModal(DOM.orderDetailModal);

    try {
        const data = await apiCall(`/api/orders/${orderId}/items`);
        const order = state.orders.find(o => o.id === orderId);
        const prod = order ? state.products.find(p => p.id === order.product_id) : null;
        let pn = prod ? `${prod.emoji} ${prod.name}` : (order ? `#${order.product_id}` : '?');
        if (order && !prod && order.product_name) {
            pn = `${order.product_emoji || '📦'} ${order.product_name}${order.product_is_deleted ? ' (Supprimé)' : ''}`;
        }
        const uname = order ? (order.username ? `@${order.username}` : (order.user_first_name || order.user_telegram_id)) : '?';
        
        $('order-detail-info').innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.88rem;">
                <div>👤 <strong>Client :</strong> ${uname}</div>
                <div>📦 <strong>Produit :</strong> ${pn}</div>
                <div>💵 <strong>Montant :</strong> $${order ? parseFloat(order.amount_usd).toFixed(2) : '?'}</div>
                <div>📊 <strong>Quantité :</strong> ${order ? (order.quantity || 1) : '?'}</div>
                <div>📅 <strong>Date :</strong> ${order ? parseUTCDate(order.created_at).toLocaleString() : '?'}</div>
                <div>✅ <strong>Statut :</strong> <span class="status-badge completed">${data.status}</span></div>
            </div>`;

        const items = data.items || [];
        $('order-items-count').textContent = items.length;

        if (items.length > 0) {
            const btnDownload = $('btn-download-order-txt');
            btnDownload.style.display = 'inline-block';
            btnDownload.onclick = () => {
                const textContent = items.map((it, idx) => `Produit ${idx + 1} :\n${it.account_data}`).join('\n\n');
                const blob = new Blob([textContent], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Commande_${orderId}_Articles.txt`;
                a.click();
                URL.revokeObjectURL(url);
            };

            $('order-items-list').innerHTML = items.map((it, i) => {
                const safeData = it.account_data ? it.account_data.replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
                return `
                <div class="stock-item-row">
                    <span class="stock-item-data">🔑 ${safeData}</span>
                    <span class="stock-item-status sold" style="font-size:0.72rem;">Livré ${it.sold_at ? parseUTCDate(it.sold_at).toLocaleDateString() : ''}</span>
                </div>`;
            }).join('');
        } else {
            $('btn-download-order-txt').style.display = 'none';
            $('order-items-list').innerHTML = '<p class="empty-state">Aucun article livré trouvé.</p>';
        }
    } catch(e) {
        $('order-detail-info').innerHTML = `<p style="color:var(--color-error);">Erreur: ${e.message}</p>`;
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  VIEW REMAINING STOCK MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.viewProductStock = async function(productId, emoji, name) {
    $('view-stock-title').textContent = `${emoji} ${name} — Stock`;
    $('view-stock-list').innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Chargement...</p>';
    $('view-stock-count').textContent = '...';
    showModal(DOM.viewStockModal);

    try {
        const items = await apiCall(`/api/products/${productId}/stock`);
        const available = items.filter(i => !i.is_sold);
        const sold = items.filter(i => i.is_sold);
        $('view-stock-count').textContent = `${available.length} dispo / ${sold.length} vendus`;

        if (items.length > 0) {
            $('view-stock-list').innerHTML = items.map(it => {
                const safeData = it.account_data ? it.account_data.replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
                return `
                <div class="stock-item-row">
                    <span class="stock-item-data">${it.is_sold ? '🔴' : '🟢'} ${safeData}</span>
                    <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
                        <button class="btn-table-action" onclick="this.parentElement.previousElementSibling.classList.toggle('expanded')" title="Voir tout" style="color:#a78bfa;"><i class="fa-solid fa-eye"></i></button>
                        <span class="stock-item-status ${it.is_sold ? 'sold' : 'available'}">${it.is_sold ? '✗ Vendu' : '✓ Dispo'}</span>
                    </div>
                </div>`;
            }).join('');
        } else {
            $('view-stock-list').innerHTML = '<p class="empty-state">Aucun article en stock.</p>';
        }
    } catch(e) {
        $('view-stock-list').innerHTML = `<p style="color:var(--color-error);">Erreur: ${e.message}</p>`;
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  EDIT PRODUCT MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.openEditProduct = function(productId) {
    const p = state.products.find(pr => pr.id === productId);
    if (!p) return;
    $('edit-prod-id').value = p.id;
    $('edit-prod-emoji').value = p.emoji || '📦';
    $('edit-prod-name').value = p.name;
    $('edit-prod-price').value = parseFloat(p.price_usd).toFixed(2);
    $('edit-prod-warranty').value = p.warranty_days || 0;
    $('edit-prod-desc').value = p.description || '';
    if ($('edit-prod-image-url')) $('edit-prod-image-url').value = p.image_url || '';
    if ($('edit-prod-custom-emoji-id')) $('edit-prod-custom-emoji-id').value = p.custom_emoji_id || '';
    $('edit-prod-title').textContent = `Modifier — ${p.emoji || '📦'} ${p.name}`;
    showModal(DOM.editProdModal);
};

$('edit-prod-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('edit-prod-id').value;
    const data = {
        emoji: $('edit-prod-emoji').value.trim() || '📦',
        custom_emoji_id: $('edit-prod-custom-emoji-id') ? $('edit-prod-custom-emoji-id').value.trim() : '',
        name: $('edit-prod-name').value.trim(),
        price_usd: parseFloat($('edit-prod-price').value),
        warranty_days: parseInt($('edit-prod-warranty').value) || 0,
        description: $('edit-prod-desc').value.trim(),
        image_url: $('edit-prod-image-url') && $('edit-prod-image-url').value.trim() ? $('edit-prod-image-url').value.trim() : null,
    };
    if (!data.name || isNaN(data.price_usd) || data.price_usd < 0) {
        alert('Vérifiez le nom et le prix.'); return;
    }
    showLoading(true);
    try {
        await apiCall(`/api/products/${id}`, 'PUT', data);
        hideModal(DOM.editProdModal);
        await refreshData();
    } catch(err) { alert(err.message); }
    finally { showLoading(false); }
});

window.submitTicketReply = async function(e,id) { e.preventDefault(); showLoading(true); const inp=e.target.querySelector('input'); try{await apiCall(`/api/tickets/${id}/reply`,'POST',{reply_text:inp.value.trim()}); inp.value=''; await refreshData();}catch(e){alert(e.message);}finally{showLoading(false);} };
window.banUser = function(tid) {
    $('banUserId').value = tid;
    $('banNotifyUser').checked = false;
    showModal($('banModal'));
};

window.closeBanModal = function() {
    hideModal($('banModal'));
};

window.confirmBanUser = async function() {
    const tid = $('banUserId').value;
    const notify = $('banNotifyUser').checked;
    closeBanModal();
    showLoading(true);
    try {
        await apiCall(`/api/users/${tid}/ban?notify=${notify}`, 'POST');
        await loadUsers();
    } catch(e) {
        alert(e.message);
    } finally {
        showLoading(false);
    }
};
window.unbanUser = async function(tid) { if(!confirm(t('confirm_unban'))) return; showLoading(true); try{await apiCall(`/api/users/${tid}/unban`,'POST'); await loadUsers();}catch(e){alert(e.message);}finally{showLoading(false);} };
window.creditWallet = async function(tid) {
    const amount = prompt('Montant à créditer (USD) :');
    if (!amount) return;
    const val = parseFloat(amount);
    if (isNaN(val) || val <= 0) { alert('Montant invalide'); return; }
    showLoading(true);
    try { await apiCall(`/api/users/${tid}/wallet/topup`, 'POST', { amount: val }); await loadUsers(); }
    catch(e) { alert(e.message); }
    finally { showLoading(false); }
};
window.debitWallet = async function(tid) {
    const amount = prompt('Montant à retirer (USD) :');
    if (!amount) return;
    const val = parseFloat(amount);
    if (isNaN(val) || val <= 0) { alert('Montant invalide'); return; }
    showLoading(true);
    try { await apiCall(`/api/users/${tid}/wallet/deduct`, 'POST', { amount: val }); await loadUsers(); }
    catch(e) { alert(e.message); }
    finally { showLoading(false); }
};

// Stock
window.openStockModal = async function(pid, emoji, name) {
    state.currentStockProductId = pid;
    DOM.stockModalTitle.textContent = `${emoji} ${name} — ${t('stock_manage')}`;
    DOM.stockTextarea.value = ''; DOM.stockLineCount.textContent = `0 ${t('accounts_detected')}`;
    showModal(DOM.stockModal);
    try {
        const items = await apiCall(`/api/products/${pid}/stock`);
        DOM.stockExistingCount.textContent = items.filter(i=>!i.is_sold).length;
        if (items.length > 0) DOM.stockItemsList.innerHTML = items.map(i => {
            const safeData = i.account_data ? i.account_data.replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
            return `<div class="stock-item-row">
            <span class="stock-item-data">${safeData}</span>
            <span class="stock-item-status ${i.is_sold?'sold':'available'}">${i.is_sold?t('sold'):t('available')}</span>
            ${!i.is_sold ? `<button class="btn-table-action delete" onclick="deleteStockItem(${i.id})" title="Supprimer"><i class="fa-solid fa-trash-can"></i></button>` : ''}
        </div>`;
        }).join('');
        else DOM.stockItemsList.innerHTML = `<p class="empty-state">${t('no_stock')}</p>`;
    } catch(e) { DOM.stockItemsList.innerHTML = `<p class="empty-state">Error: ${e.message}</p>`; }
};

window.deleteStockItem = async function(stockId) {
    if (!confirm('Supprimer cet article du stock ?')) return;
    showLoading(true);
    try {
        await apiCall(`/api/stock/${stockId}`, 'DELETE');
        await openStockModal(state.currentStockProductId, '', DOM.stockModalTitle.textContent.split('—')[0].trim());
        loadProducts(); loadStats();
    } catch(e) { alert(e.message); }
    finally { showLoading(false); }
};

async function handleAddStock() {
    const lines = DOM.stockTextarea.value.split('\n').filter(l=>l.trim());
    if (!lines.length) return;
    showLoading(true);
    const broadcastRestock = DOM.stockBroadcastCheckbox ? DOM.stockBroadcastCheckbox.checked : false;
    try { 
        await apiCall(`/api/products/${state.currentStockProductId}/stock`,'POST',{items:lines, broadcast_restock: broadcastRestock}); 
        DOM.stockTextarea.value=''; 
        if (DOM.stockBroadcastCheckbox) DOM.stockBroadcastCheckbox.checked = false;
        await openStockModal(state.currentStockProductId,'',DOM.stockModalTitle.textContent.split('—')[0].trim()); 
        loadProducts(); 
        loadStats(); 
    }
    catch(e){alert(e.message);} finally{showLoading(false);}
}

function handleFileImport(e) {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = function(ev) { DOM.stockTextarea.value = ev.target.result; const n=ev.target.result.split('\n').filter(l=>l.trim()).length; DOM.stockLineCount.textContent=`${n} ${t('accounts_detected')}`; };
    reader.readAsText(file);
    e.target.value = '';
}

// Broadcast
async function handleBroadcast() {
    const msg = DOM.broadcastTextarea.value.trim();
    const photoUrl = DOM.broadcastPhotoUrl ? DOM.broadcastPhotoUrl.value.trim() : '';
    const btnType = DOM.broadcastBtnType ? DOM.broadcastBtnType.value : 'none';
    const btnProdId = DOM.broadcastBtnProductId ? parseInt(DOM.broadcastBtnProductId.value) : null;
    const btnText = DOM.broadcastBtnText ? DOM.broadcastBtnText.value.trim() : '';
    const btnUrl = DOM.broadcastBtnUrl ? DOM.broadcastBtnUrl.value.trim() : '';

    if (!msg && !photoUrl) {
        alert('Veuillez entrer un message ou une URL de photo.');
        return;
    }
    if (!confirm(`Envoyer ce message à tous les utilisateurs ?`)) return;
    showLoading(true); DOM.broadcastResult.textContent = '';
    try {
        const r = await apiCall('/api/broadcast','POST',{
            message: msg,
            photo_url: photoUrl,
            btn_type: btnType,
            btn_prod_id: btnType === 'buy' ? btnProdId : null,
            btn_text: btnType === 'url' ? btnText : '',
            btn_url: btnType === 'url' ? btnUrl : ''
        });
        DOM.broadcastResult.textContent = `✅ ${t('broadcast_sent').replace('{sent}',r.sent).replace('{total}',r.total)} | ${t('broadcast_failed').replace('{failed}',r.failed)}`;
        
        // Reset inputs
        DOM.broadcastTextarea.value = '';
        if (DOM.broadcastPhotoUrl) DOM.broadcastPhotoUrl.value = '';
        if (DOM.broadcastBtnType) DOM.broadcastBtnType.value = 'none';
        $('broadcast-buy-group').classList.add('hidden');
        $('broadcast-url-group').classList.add('hidden');
    } catch(e) { DOM.broadcastResult.textContent = `âŒ ${e.message}`; }
    finally { showLoading(false); }
}

// Settings
function handleSaveSettings(e) { e.preventDefault(); let u=DOM.settingsBotUrl.value.trim().replace(/\/$/,''); if(u&&!u.startsWith('http://')&&!u.startsWith('https://'))u='https://'+u; state.apiKey=DOM.settingsApiKey.value.trim(); state.botUrl=u||''; testConnectionAndStart(); }

async function loadPaymentSettings() {
    try {
        const s = await apiCall('/api/settings/payment');
        DOM.settingsBep20Address.value = s.bep20_address || '';
        DOM.settingsTrc20Address.value = s.trc20_address || '';
    } catch(e) { console.error('Failed loading payment settings:', e); }
}

async function handleSaveCryptoSettings(e) {
    e.preventDefault();
    showLoading(true);
    const bep20 = DOM.settingsBep20Address.value.trim();
    const trc20 = DOM.settingsTrc20Address.value.trim();
    try {
        await apiCall('/api/settings/payment', 'POST', {
            bep20_address: bep20,
            trc20_address: trc20
        });
        alert('Adresses crypto enregistrées avec succès !');
        await loadPaymentSettings();
    } catch(err) { alert(`Erreur: ${err.message}`); }
    finally { showLoading(false); }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  UI HELPERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// Category select removed — not needed

const tabKeys = { 'ventedz-tab':'tab_ventedz', 'dashboard-tab':'tab_dashboard','stats-tab':'tab_stats','inventory-tab':'tab_inventory','orders-tab':'tab_orders','users-tab':'tab_users','tickets-tab':'tab_tickets','broadcast-tab':'tab_broadcast','settings-tab':'tab_settings','wallet-history-tab':'nav_wallet_history','finance-tab':'tab_finance','binance-tab':'tab_binance' };

function escapeHtml(str) {
    if (!str) return '';
    return str.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function showScreen(s) { if(s==='login'){DOM.loginScreen.classList.remove('hidden');DOM.appContainer.classList.add('hidden');stopAutoRefresh();}else{DOM.loginScreen.classList.add('hidden');DOM.appContainer.classList.remove('hidden');} }

function switchTab(tabId) {
    $$('.menu-item').forEach(i=>i.classList.remove('active'));
    $$('.tab-content').forEach(c=>c.classList.remove('active'));
    const ai = document.querySelector(`.menu-item[data-tab="${tabId}"]`); if(ai) ai.classList.add('active');
    const ac = $(tabId); if(ac) ac.classList.add('active');
    DOM.currentTabTitle.textContent = t(tabKeys[tabId]||'tab_dashboard');
    state.currentTab = tabId;
}

function showModal(m) { m.classList.remove('hidden'); }
function hideModal(m) { m.classList.add('hidden'); }
function showLoading(v) { if(v)DOM.loadingOverlay.classList.remove('hidden');else DOM.loadingOverlay.classList.add('hidden'); }
function logout() { state.botUrl='';state.apiKey='';localStorage.removeItem('ventebot_url');localStorage.removeItem('ventebot_key');DOM.loginForm.reset();showScreen('login');stopAutoRefresh(); }

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  EXCEL EXPORT (SheetJS)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
$('exportForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const startLocal = $('exportStartDate').value;
    const endLocal = $('exportEndDate').value;
    // Convert local datetime to UTC ISO string to align with the database timezone
    const start = startLocal ? new Date(startLocal).toISOString() : '';
    const end = endLocal ? new Date(endLocal).toISOString() : '';
    const format = $('exportFormat').value;
    hideModal($('exportModal'));
    showLoading(true);
    try {
        const transactions = await apiCall(`/api/export/transactions?start_date=${start}&end_date=${end}`);
        
        // Compute running total chronologically (from oldest to newest)
        let runningTotal = 0;
        const reversed = [...transactions].reverse();
        const rows = [];
        reversed.forEach(t => {
            runningTotal += parseFloat(t['Montant (USD)']);
            // Format the UTC date from database to user's local timezone
            const localDateStr = t['Date'] ? parseUTCDate(t['Date']).toLocaleString() : '—';
            rows.push({
                'Date': localDateStr,
                'Type': t['Type'],
                'Client': t['Client'],
                'Montant (USD)': parseFloat(t['Montant (USD)']),
                'Cumul (USD)': runningTotal,
                'Méthode': t['Méthode'],
                'Identifiant': t['Identifiant']
            });
        });
        rows.reverse(); // put back in newest-first order
        
        // Add a final total row
        const totalRow = {
            'Date': 'TOTAL',
            'Type': '',
            'Client': '',
            'Montant (USD)': runningTotal,
            'Cumul (USD)': '',
            'Méthode': '',
            'Identifiant': ''
        };
        rows.push(totalRow);

        if (format === 'excel') {
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.json_to_sheet(rows);
            ws['!cols'] = [{wch:20},{wch:10},{wch:15},{wch:15},{wch:15},{wch:15},{wch:40}];
            XLSX.utils.book_append_sheet(wb, ws, 'Transactions');
            XLSX.writeFile(wb, `Transactions_${start}_to_${end}.xlsx`);
        } else if (format === 'pdf') {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            doc.text(`Export des Transactions (${start} au ${end})`, 14, 15);
            
            const headers = [['Date', 'Type', 'Client', 'Montant (USD)', 'Cumul (USD)', 'Méthode', 'Identifiant']];
            const body = rows.map(t => [
                t['Date'] || '',
                t['Type'] || '',
                t['Client'] || '',
                `$${parseFloat(t['Montant (USD)']).toFixed(2)}`,
                t['Date'] === 'TOTAL' ? '' : `$${parseFloat(t['Cumul (USD)']).toFixed(2)}`,
                t['Méthode'] || '',
                t['Identifiant'] || ''
            ]);
            
            doc.autoTable({
                head: headers,
                body: body,
                startY: 20,
                theme: 'striped',
                styles: { fontSize: 8 },
                columnStyles: { 6: { cellWidth: 40 } }
            });
            doc.save(`Transactions_${start}_to_${end}.pdf`);
        }
    } catch(err) {
        console.error('Export failed:', err);
        alert('Erreur: ' + err.message);
    } finally {
        showLoading(false);
    }
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  BINANCE ACCOUNTS MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.openBinanceModal = function() {
    DOM.binanceForm.reset();
    DOM.binanceId.value = '';
    $('binanceModalTitle').textContent = 'Ajouter un compte Binance';
    showModal(DOM.binanceModal);
};

window.closeBinanceModal = function() {
    hideModal(DOM.binanceModal);
};

window.saveBinanceAccount = async function() {
    const payload = {
        label: DOM.binanceLabel.value.trim(),
        uid: DOM.binanceUid.value.trim(),
        api_key: DOM.binanceApiKey.value.trim(),
        api_secret: DOM.binanceApiSecret.value.trim(),
        is_default: DOM.binanceIsDefault.checked ? 1 : 0
    };
    if (!payload.label || !payload.uid) return alert('Label et UID sont requis.');
    
    try {
        const id = DOM.binanceId.value;
        if (id) {
            await apiCall(`/api/binance-accounts/${id}`, 'PUT', payload);
        } else {
            await apiCall('/api/binance-accounts', 'POST', payload);
        }
        closeBinanceModal();
        refreshData();
    } catch(err) {
        alert('Erreur: ' + err.message);
    }
};

window.editBinanceAccount = function(id) {
    const acc = state.binanceAccounts.find(a => a.id === id);
    if (!acc) return;
    DOM.binanceId.value = acc.id;
    DOM.binanceLabel.value = acc.label;
    DOM.binanceUid.value = acc.uid;
    DOM.binanceApiKey.value = acc.api_key || '';
    DOM.binanceApiSecret.value = acc.api_secret || '';
    DOM.binanceIsDefault.checked = !!acc.is_default;
    $('binanceModalTitle').textContent = 'Modifier le compte Binance';
    showModal(DOM.binanceModal);
};

window.deleteBinanceAccount = async function(id) {
    if (!confirm('Voulez-vous vraiment supprimer ce compte Binance ? Les produits liés utiliseront le compte par défaut.')) return;
    try {
        await apiCall(`/api/binance-accounts/${id}`, 'DELETE');
        refreshData();
    } catch(err) {
        alert('Erreur: ' + err.message);
    }
};

window.openEditProdModal = function(id) {
    const p = state.products.find(x => x.id === id);
    if (!p) return;
    DOM.prodId.value = p.id;
    DOM.prodName.value = p.name;
    DOM.prodPrice.value = p.price_usd;
    DOM.prodWarranty.value = p.warranty_days || 0;
    DOM.prodEmoji.value = p.emoji;
    if (DOM.prodDesc) DOM.prodDesc.value = p.description || '';
    if (DOM.prodImageUrl) DOM.prodImageUrl.value = p.image_url || '';
    if (DOM.prodBinanceAccount) DOM.prodBinanceAccount.value = p.binance_account_id || '';
    showModal(DOM.prodModal);
}

async function handleAddProduct(e) {
    e.preventDefault();
    showLoading(true);
    const payload = {
        category_id: 1,
        name: DOM.prodName.value.trim(),
        price_usd: parseFloat(DOM.prodPrice.value),
        warranty_days: parseInt(DOM.prodWarranty.value) || 0,
        emoji: DOM.prodEmoji.value.trim() || '📦',
        custom_emoji_id: DOM.prodCustomEmojiId && DOM.prodCustomEmojiId.value.trim() ? DOM.prodCustomEmojiId.value.trim() : null,
        description: DOM.prodDesc ? DOM.prodDesc.value.trim() : '',
        image_url: DOM.prodImageUrl && DOM.prodImageUrl.value.trim() ? DOM.prodImageUrl.value.trim() : null,
        binance_account_id: DOM.prodBinanceAccount && DOM.prodBinanceAccount.value ? parseInt(DOM.prodBinanceAccount.value) : null
    };
    try {
        const id = DOM.prodId.value;
        if (id) {
            await apiCall(`/api/products/${id}`, 'PUT', payload);
        } else {
            await apiCall('/api/products', 'POST', payload);
        }
        hideModal(DOM.prodModal);
        DOM.addProdForm.reset();
        await refreshData();
    } catch(err) {
        alert('Erreur: ' + err.message);
    } finally {
        showLoading(false);
    }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  FINANCE TAB LOGIC
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

let currentFinanceBalance = 0;

async function loadFinance() {
    try {
        let url = '/api/finance';
        const filterSelect = $('finance-method-filter');
        if (filterSelect && filterSelect.value !== 'all') {
            url += `?method=${filterSelect.value}`;
        }
        const data = await apiCall(url);
        $('finance-daily').textContent = `$${parseFloat(data.daily_revenue || 0).toFixed(2)}`;
        $('finance-weekly').textContent = `$${parseFloat(data.weekly_revenue || 0).toFixed(2)}`;
        $('finance-monthly').textContent = `$${parseFloat(data.monthly_revenue || 0).toFixed(2)}`;
        
        currentFinanceBalance = parseFloat(data.bot_balance || 0);
        $('finance-balance').textContent = `$${currentFinanceBalance.toFixed(2)}`;
        $('withdraw-current-balance').textContent = `$${currentFinanceBalance.toFixed(2)}`;
        
        if ($('finance-sales-binance')) {
            $('finance-sales-binance').textContent = `$${parseFloat(data.sales_binance_30d || 0).toFixed(2)}`;
            $('finance-sales-bep20').textContent = `$${parseFloat(data.sales_bep20_30d || 0).toFixed(2)}`;
            $('finance-sales-trc20').textContent = `$${parseFloat(data.sales_trc20_30d || 0).toFixed(2)}`;
            $('finance-sales-wallet').textContent = `$${parseFloat(data.sales_wallet_30d || 0).toFixed(2)}`;
            $('finance-topup-count').textContent = data.topup_count_30d || 0;
            $('finance-topup-revenue').textContent = `$${parseFloat(data.topup_revenue_30d || 0).toFixed(2)}`;
        }
    } catch(err) {
        console.error('Error loading finance stats', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btnWithdraw = $('btn-finance-withdraw');
    const btnAdjust = $('btn-finance-adjust');
    const modalWithdraw = $('finance-withdraw-modal');
    const modalAdjust = $('finance-adjust-modal');
    const formWithdraw = $('finance-withdraw-form');
    const formAdjust = $('finance-adjust-form');
    const btnWithdrawAll = $('btn-withdraw-all');
    
    if (modalWithdraw) {
        modalWithdraw.querySelectorAll('.btn-close-modal').forEach(b => b.addEventListener('click', () => hideModal(modalWithdraw)));
    }
    if (modalAdjust) {
        modalAdjust.querySelectorAll('.btn-close-modal').forEach(b => b.addEventListener('click', () => hideModal(modalAdjust)));
    }
    
    if (btnWithdraw) btnWithdraw.addEventListener('click', () => {
        $('withdraw-amount').value = '';
        showModal(modalWithdraw);
    });
    
    if (btnAdjust) btnAdjust.addEventListener('click', () => {
        $('adjust-amount').value = '';
        showModal(modalAdjust);
    });
    
    if (btnWithdrawAll) btnWithdrawAll.addEventListener('click', () => {
        $('withdraw-amount').value = currentFinanceBalance.toFixed(2);
    });
    
    if (formWithdraw) formWithdraw.addEventListener('submit', async (e) => {
        e.preventDefault();
        const filterSelect = $('finance-method-filter');
        const method = filterSelect ? filterSelect.value : 'all';
        if (method === 'all') {
            alert('Veuillez sélectionner une méthode spécifique (Binance, BEP20, etc.) pour retirer du solde.');
            return;
        }
        
        const amt = parseFloat($('withdraw-amount').value);
        if (isNaN(amt) || amt <= 0) return;
        if (amt > currentFinanceBalance) {
            alert("Montant supérieur au solde actuel.");
            return;
        }
        
        try {
            showLoading(true);
            await apiCall('/api/finance/adjust', 'POST', { amount: -amt, method: method });
            hideModal(modalWithdraw);
            refreshData();
        } catch(err) {
            alert('Erreur: ' + err.message);
        } finally {
            showLoading(false);
        }
    });
    
    if (formAdjust) formAdjust.addEventListener('submit', async (e) => {
        e.preventDefault();
        const filterSelect = $('finance-method-filter');
        const method = filterSelect ? filterSelect.value : 'all';
        if (method === 'all') {
            alert('Veuillez sélectionner une méthode spécifique (Binance, BEP20, etc.) pour ajuster le solde.');
            return;
        }
        
        const amt = parseFloat($('adjust-amount').value);
        if (isNaN(amt)) return;
        
        try {
            showLoading(true);
            await apiCall('/api/finance/adjust', 'POST', { amount: amt, method: method });
            hideModal(modalAdjust);
            refreshData();
        } catch(err) {
            alert('Erreur: ' + err.message);
        } finally {
            showLoading(false);
        }
    });
});


// Listener pour le filtre finance
const methodFilterEl = $('finance-method-filter');
if(methodFilterEl) {
    methodFilterEl.addEventListener('change', () => {
        loadFinance();
    });
}
