
function toggleActivationFields(type) {
    if (type === 'add') {
        const val = DOM.prodDeliveryType ? DOM.prodDeliveryType.value : 'stock';
        const container = $('prod-act-msg-container');
        if (container) container.style.display = (val === 'activation') ? 'block' : 'none';
    } else {
        const val = $('edit-prod-delivery-type') ? $('edit-prod-delivery-type').value : 'stock';
        const container = $('edit-prod-act-msg-container');
        if (container) container.style.display = (val === 'activation') ? 'block' : 'none';
    }
}

// dashboard/app.js — VenteBot Admin Dashboard with all features

// —————————————————————————————————————————————————————
//  i18n TRANSLATIONS
// —————————————————————————————————————————————————————
const LANG = {
fr: {
    login_subtitle:"Console de Gestion Administrateur",login_url_label:"URL de l'API",login_url_hint:"Laissez vide si vous êtes déjà sur /dashboard du bot ; sinon collez l'URL Railway",login_key_label:"Clé d'API Administrateur",login_btn:"Se connecter",
    nav_dashboard:"Dashboard",nav_stats:"Statistiques",nav_inventory:"Catalogue & Stock",nav_orders:"Commandes",nav_users:"Utilisateurs",nav_tickets:"Tickets",nav_broadcast:"Broadcast",nav_settings:"Paramètres",
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
    tickets_title:"Tickets Support",no_tickets:"Aucun ticket. 🤝",
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
    nav_finance:"Finance",tab_finance:"Suivi Financier",nav_binance:"Comptes Binance",tab_binance:"Gestion des Comptes Binance",settings_err:"Échec de l'opération : ",
    nav_activations:"Activations",activations_title:"Activations",no_activations:"Aucune activation.",th_telegram_id:"ID Telegram",th_activation_identifier:"Identifiant à activer",th_date:"Date",th_action:"Action",
    activation_waiting_client:"En attente du client",activation_ready:"À activer",activation_waiting_id:"Attend ID client",activation_mark_done:"Marquer activé",activation_confirm_prompt:"Marquer la commande #{id} comme activée ?",delivery_activation:"Activation manuelle",
    nav_resellers:"Revendeurs",nav_api_docs:"Documentation API",resellers_title:"Revendeurs",no_resellers:"Aucun revendeur.",reseller_user_id:"ID Telegram du revendeur",reseller_key_name:"Nom de la clé",btn_create_reseller_key:"Créer la clé",reseller_key_created:"Clé créée, à copier maintenant :",reseller_revoke:"Révoquer"
},
en: {
    login_subtitle:"Admin Management Console",login_url_label:"API URL",login_url_hint:"Leave empty if already on the bot /dashboard; otherwise paste your Railway URL",login_key_label:"Admin API Key",login_btn:"Connect",
    nav_dashboard:"Dashboard",nav_stats:"Statistics",nav_inventory:"Catalog & Stock",nav_orders:"Orders",nav_users:"Users",nav_tickets:"Tickets",nav_broadcast:"Broadcast",nav_settings:"Settings",
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
    tickets_title:"Support Tickets",no_tickets:"No pending tickets. 🤝",
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
    nav_finance:"Finance",tab_finance:"Financial Tracking",nav_binance:"Binance Accounts",tab_binance:"Binance Accounts Management",settings_err:"Operation failed: ",
    nav_activations:"Activations",activations_title:"Activations",no_activations:"No activations.",th_telegram_id:"Telegram ID",th_activation_identifier:"Identifier to activate",th_date:"Date",th_action:"Action",
    activation_waiting_client:"Waiting for customer",activation_ready:"To activate",activation_waiting_id:"Waiting for customer ID",activation_mark_done:"Mark activated",activation_confirm_prompt:"Mark order #{id} as activated?",delivery_activation:"Manual activation",
    nav_resellers:"Resellers",nav_api_docs:"API Documentation",resellers_title:"Resellers",no_resellers:"No resellers.",reseller_user_id:"Reseller Telegram ID",reseller_key_name:"Key name",btn_create_reseller_key:"Create key",reseller_key_created:"Key created, copy it now:",reseller_revoke:"Revoke"
},
ar: {
    login_subtitle:"Ù„Ùˆحة إدارة Ø§Ù„Ù…Ø´Ø±Ù",login_url_label:"رابط API (اختياري)",login_url_hint:"Ø§ØªØ±Ùƒه ÙØ§Ø±ØºØ§Ù‹ Ù„Ø¨Ø±ÙˆÙƒسي Netlify",login_key_label:"Ù…ÙØªØ§Ø­ API Ù„Ù„Ù…Ø´Ø±Ù",login_btn:"اتصال",
    nav_dashboard:"Ù„Ùˆحة Ø§Ù„ØªØ­Ùƒم",nav_inventory:"Ø§Ù„ÙƒØªØ§Ù„Ùˆج ÙˆØ§Ù„Ù…Ø®Ø²Ùˆن",nav_orders:"الطلبات",nav_users:"المستخدمين",nav_tickets:"Ø§Ù„ØªØ°Ø§Ùƒر",nav_broadcast:"البث",nav_settings:"الإعدادات",
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
    tickets_title:"تذاكر الدعم",no_tickets:"لا توجد تذاكر معلقة. 🤝",
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
    nav_finance:"المالية",tab_finance:"المتابعة المالية",nav_binance:"حسابات Binance",tab_binance:"إدارة حسابات Binance",settings_err:"ÙØ´Ù„Øª العملية: ",
    nav_activations:"التفعيلات",activations_title:"التفعيلات",no_activations:"لا توجد طلبات تفعيل.",th_telegram_id:"Telegram ID",th_activation_identifier:"المعرّف المطلوب تفعيله",th_date:"التاريخ",th_action:"الإجراء",
    activation_waiting_client:"بانتظار العميل",activation_ready:"جاهز للتفعيل",activation_waiting_id:"بانتظار معرّف العميل",activation_mark_done:"وضع كمفعّل",activation_confirm_prompt:"هل تريد وضع الطلب #{id} كمفعّل؟",delivery_activation:"تفعيل يدوي",
    nav_resellers:"الموزعون",nav_api_docs:"وثائق API",resellers_title:"الموزعون",no_resellers:"لا يوجد موزعون.",reseller_user_id:"Telegram ID للموزع",reseller_key_name:"اسم المفتاح",btn_create_reseller_key:"إنشاء مفتاح",reseller_key_created:"تم إنشاء المفتاح، انسخه الآن:",reseller_revoke:"إلغاء"
}
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  STATE & DOM
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
LANG.zh = {...LANG.en,
    login_subtitle:'管理员控制台', login_url_label:'API 地址', login_key_label:'管理员 API 密钥', login_btn:'连接',
    nav_dashboard:'控制台', nav_stats:'统计', nav_inventory:'商品与库存', nav_orders:'订单', nav_activations:'激活', nav_resellers:'经销商', nav_users:'用户', nav_tickets:'工单', nav_wallet_history:'钱包记录', nav_finance:'财务', nav_binance:'Binance 账户', nav_broadcast:'群发消息', nav_api_docs:'API 文档', nav_settings:'设置',
    tab_dashboard:'控制台', tab_stats:'分析与统计', tab_inventory:'商品与库存', tab_orders:'订单跟踪', tab_users:'用户管理', tab_tickets:'客服工单', tab_broadcast:'群发消息', tab_settings:'设置',
    metric_revenue:'收入（30天）', metric_sales:'销量（30天）', metric_clients:'客户', metric_initiated:'待处理订单', chart_revenue:'每日收入（$）', chart_orders:'每日订单', stock_status:'库存状态', no_products:'暂无商品。',
    btn_add_product:'添加', filter_all:'全部', filter_pending:'待处理', filter_completed:'已完成', filter_cancelled:'已取消', no_orders:'暂无订单。', no_users:'暂无用户。', no_tickets:'暂无待处理工单。', btn_save:'保存', btn_cancel:'取消'
};
LANG.vi = {...LANG.en,
    login_subtitle:'Bảng điều khiển quản trị', login_url_label:'URL API', login_key_label:'Khóa API quản trị', login_btn:'Kết nối',
    nav_dashboard:'Tổng quan', nav_stats:'Thống kê', nav_inventory:'Sản phẩm & kho', nav_orders:'Đơn hàng', nav_activations:'Kích hoạt', nav_resellers:'Đại lý', nav_users:'Người dùng', nav_tickets:'Hỗ trợ', nav_wallet_history:'Lịch sử ví', nav_finance:'Tài chính', nav_binance:'Tài khoản Binance', nav_broadcast:'Phát tin', nav_api_docs:'Tài liệu API', nav_settings:'Cài đặt',
    tab_dashboard:'Tổng quan', tab_stats:'Phân tích & thống kê', tab_inventory:'Sản phẩm & kho', tab_orders:'Theo dõi đơn hàng', tab_users:'Quản lý người dùng', tab_tickets:'Yêu cầu hỗ trợ', tab_broadcast:'Phát tin', tab_settings:'Cài đặt',
    metric_revenue:'Doanh thu (30 ngày)', metric_sales:'Đã bán (30 ngày)', metric_clients:'Khách hàng', metric_initiated:'Đơn chờ xử lý', chart_revenue:'Doanh thu hàng ngày ($)', chart_orders:'Đơn hàng hàng ngày', stock_status:'Tình trạng kho', no_products:'Chưa có sản phẩm.',
    btn_add_product:'Thêm', filter_all:'Tất cả', filter_pending:'Đang chờ', filter_completed:'Hoàn tất', filter_cancelled:'Đã hủy', no_orders:'Không có đơn hàng.', no_users:'Không có người dùng.', no_tickets:'Không có yêu cầu đang chờ.', btn_save:'Lưu', btn_cancel:'Hủy'
};
LANG.ru = {...LANG.en,
    login_subtitle:'Панель администратора', login_url_label:'URL API', login_key_label:'Ключ API администратора', login_btn:'Подключиться',
    nav_dashboard:'Обзор', nav_stats:'Статистика', nav_inventory:'Каталог и склад', nav_orders:'Заказы', nav_activations:'Активации', nav_resellers:'Реселлеры', nav_users:'Пользователи', nav_tickets:'Обращения', nav_wallet_history:'История кошелька', nav_finance:'Финансы', nav_binance:'Аккаунты Binance', nav_broadcast:'Рассылка', nav_api_docs:'Документация API', nav_settings:'Настройки',
    tab_dashboard:'Обзор', tab_stats:'Аналитика и статистика', tab_inventory:'Каталог и склад', tab_orders:'Отслеживание заказов', tab_users:'Управление пользователями', tab_tickets:'Обращения в поддержку', tab_broadcast:'Рассылка', tab_settings:'Настройки',
    metric_revenue:'Выручка (30 дней)', metric_sales:'Продажи (30 дней)', metric_clients:'Клиенты', metric_initiated:'Заказы в ожидании', chart_revenue:'Выручка по дням ($)', chart_orders:'Заказы по дням', stock_status:'Состояние склада', no_products:'Нет товаров.',
    btn_add_product:'Добавить', filter_all:'Все', filter_pending:'В ожидании', filter_completed:'Завершенные', filter_cancelled:'Отмененные', no_orders:'Нет заказов.', no_users:'Нет пользователей.', no_tickets:'Нет открытых обращений.', btn_save:'Сохранить', btn_cancel:'Отмена'
};
LANG.ar = {...LANG.ar,
    login_subtitle:'لوحة تحكم المسؤول', login_url_label:'رابط API', login_key_label:'مفتاح API للمسؤول', login_btn:'اتصال',
    nav_dashboard:'لوحة التحكم', nav_stats:'الإحصائيات', nav_inventory:'المنتجات والمخزون', nav_orders:'الطلبات', nav_activations:'التفعيلات', nav_resellers:'الموزعون', nav_users:'المستخدمون', nav_tickets:'الدعم', nav_wallet_history:'سجل المحفظة', nav_finance:'المالية', nav_binance:'حسابات Binance', nav_broadcast:'البث', nav_api_docs:'وثائق API', nav_settings:'الإعدادات',
    tab_dashboard:'لوحة التحكم', tab_stats:'التحليلات والإحصائيات', tab_inventory:'المنتجات والمخزون', tab_orders:'متابعة الطلبات', tab_users:'إدارة المستخدمين', tab_tickets:'تذاكر الدعم', tab_broadcast:'البث', tab_settings:'الإعدادات',
    metric_revenue:'الإيرادات (30 يومًا)', metric_sales:'المبيعات (30 يومًا)', metric_clients:'العملاء', metric_initiated:'الطلبات المعلقة', chart_revenue:'الإيرادات اليومية ($)', chart_orders:'الطلبات اليومية', stock_status:'حالة المخزون', no_products:'لا توجد منتجات.',
    btn_add_product:'إضافة', filter_all:'الكل', filter_pending:'قيد الانتظار', filter_completed:'مكتملة', filter_cancelled:'ملغاة', no_orders:'لا توجد طلبات.', no_users:'لا يوجد مستخدمون.', no_tickets:'لا توجد تذاكر مفتوحة.', btn_save:'حفظ', btn_cancel:'إلغاء'
};
Object.assign(LANG.fr, {overview_kicker:'Aujourd’hui', overview_title:'Le magasin en un coup d’œil', today_revenue:'Revenus du jour', today_orders:'Ventes du jour', priorities:'Priorités', actions_title:'À traiter maintenant', activity:'Activité', recent_orders:'Dernières commandes', view_all:'Tout voir', pending_metric:'Commandes en attente'});
Object.assign(LANG.en, {overview_kicker:'Today', overview_title:'Store at a glance', today_revenue:'Today revenue', today_orders:'Today sales', priorities:'Priorities', actions_title:'Needs attention', activity:'Activity', recent_orders:'Recent orders', view_all:'View all', pending_metric:'Pending orders'});
Object.assign(LANG.zh, {overview_kicker:'今天', overview_title:'商店概览', today_revenue:'今日收入', today_orders:'今日销量', priorities:'优先事项', actions_title:'待处理事项', activity:'动态', recent_orders:'最近订单', view_all:'查看全部', pending_metric:'待处理订单'});
Object.assign(LANG.vi, {overview_kicker:'Hôm nay', overview_title:'Tổng quan cửa hàng', today_revenue:'Doanh thu hôm nay', today_orders:'Lượt bán hôm nay', priorities:'Ưu tiên', actions_title:'Cần xử lý', activity:'Hoạt động', recent_orders:'Đơn gần đây', view_all:'Xem tất cả', pending_metric:'Đơn đang chờ'});
Object.assign(LANG.ru, {overview_kicker:'Сегодня', overview_title:'Магазин в цифрах', today_revenue:'Выручка сегодня', today_orders:'Продажи сегодня', priorities:'Приоритеты', actions_title:'Требует внимания', activity:'Активность', recent_orders:'Последние заказы', view_all:'Все заказы', pending_metric:'Заказы в ожидании'});
Object.assign(LANG.ar, {overview_kicker:'اليوم', overview_title:'نظرة عامة على المتجر', today_revenue:'إيرادات اليوم', today_orders:'مبيعات اليوم', priorities:'الأولويات', actions_title:'بحاجة إلى معالجة', activity:'النشاط', recent_orders:'أحدث الطلبات', view_all:'عرض الكل', pending_metric:'الطلبات المعلقة'});

const state = {
    botUrl:'', apiKey:'', currentLang:'fr', currentTab:'dashboard-tab',
    categories:[], products:[], orders:[], activations:[], resellers:[], users:[], promos:[], tickets:[], walletHistory:[], binanceAccounts:[],
    orderFilter:'all', orderPage:0, orderTotal:0,
    whFilter:'all', whPage:0, whTotal:0,
    usersPage:0, usersPerPage:20, usersSearch:'', usersTotal:0, usersSort:'joined', usersOrder:'desc',
    currentStockProductId:null, autoRefresh:false, autoRefreshTimer:null,
    chartDays:30, refreshing:false, lastRefreshAt:null,
    revenueChart:null, ordersChart:null, productSalesChart:null, productMomentumChart:null,
    dynamicPriceChart:null, dynamicSimulationChart:null,
    productStats:[], productMomentum:null, productMomentumSelected:[], deadProductAlerts:[]
};

function $(id) { return document.getElementById(id); }
function $$(sel) { return document.querySelectorAll(sel); }

const DOM = {
    loginScreen:$('login-screen'), loginForm:$('login-form'), botUrlInput:$('bot-url'), apiKeyInput:$('api-key'), loginError:$('login-error'),
    appContainer:$('app-container'), currentTabTitle:$('current-tab-title'),
    btnRefresh:$('btn-refresh'), btnLogout:$('btn-logout'), btnTheme:$('btn-theme'), btnAutoRefresh:$('btn-auto-refresh'),
    loadingOverlay:$('loading-overlay'),
    statRevenue:$('stat-revenue'), statOrders:$('stat-orders'), statUsers:$('stat-users'), statPending:$('stat-pending'),
    statNewUsers:$('stat-new-users'), statReturningUsers:$('stat-returning-users'),
    stockSummaryList:$('stock-summary-list'),
    todayRevenue:$('today-revenue'), todayOrders:$('today-orders'),
    todayRevenueDelta:$('today-revenue-delta'), todayOrdersDelta:$('today-orders-delta'),
    actionCenterList:$('action-center-list'), recentOrdersList:$('recent-orders-list'),
    dashboardRange:$('dashboard-range'), pageContext:$('page-context'), toastRegion:$('toast-region'),
    badgeOrders:$('badge-orders'), badgeActivations:$('badge-activations'), badgeTickets:$('badge-tickets'), apiStatusBadge:$('api-status-badge'),
    productsTableBody:$('products-table-body'),
    statsProductsTableBody:$('stats-products-table-body'),
    statsProductSearch:$('stats-product-search'),
    statsKpiTopProduct:$('stats-kpi-top-product'),
    statsKpiTopProductSub:$('stats-kpi-top-product-sub'),
    statsKpiTotalSales:$('stats-kpi-total-sales'),
    statsKpiTotalRevenue:$('stats-kpi-total-revenue'),
    statsKpiStockAlerts:$('stats-kpi-stock-alerts'),
    chartProductSales:$('chart-product-sales'),
    chartProductMomentum:$('chart-product-momentum'),
    productMomentumControls:$('product-momentum-controls'),
    productMomentumYesterday:$('product-momentum-yesterday'),
    productMomentumRange:$('product-momentum-range'),
    deadProductsAlerts:$('dead-products-alerts'),
    promosTableBody:$('promos-table-body'),
    ordersTableBody:$('orders-table-body'), activationsTableBody:$('activations-table-body'), ordersPagination:$('orders-pagination'),
    ordersPrev:$('orders-prev'), ordersNext:$('orders-next'), ordersPageInfo:$('orders-page-info'),
    usersTableBody:$('users-table-body'), usersSearch:$('users-search'), usersLimitSelector:$('users-limit-selector'),
    usersPagination:$('users-pagination'), usersPrev:$('users-prev'), usersNext:$('users-next'), usersPageInfo:$('users-page-info'),
    openTicketsContainer:$('open-tickets-container'),
    resellersTableBody:$('resellers-table-body'), resellerUserId:$('reseller-user-id'), resellerKeyName:$('reseller-key-name'),
    btnCreateResellerKey:$('btn-create-reseller-key'), resellerKeyOutput:$('reseller-key-output'), resellerNewKey:$('reseller-new-key'),
    broadcastTextarea:$('broadcast-textarea'), broadcastResult:$('broadcast-result'), btnSendBroadcast:$('btn-send-broadcast'),
    broadcastPhotoUrl:$('broadcast-photo-url'), broadcastBtnType:$('broadcast-btn-type'), broadcastBtnProductId:$('broadcast-btn-product-id'),
    broadcastBtnText:$('broadcast-btn-text'), broadcastBtnUrl:$('broadcast-btn-url'),
    stockBroadcastCheckbox:$('stock-broadcast-checkbox'),
    settingsForm:$('settings-form'), settingsBotUrl:$('settings-bot-url'), settingsApiKey:$('settings-api-key'),
    cryptoSettingsForm:$('crypto-settings-form'), settingsBep20Address:$('settings-bep20-address'), settingsTrc20Address:$('settings-trc20-address'),
    prodModal:$('prod-modal'), stockModal:$('stock-modal'), promoModal:$('promo-modal'), tiersModal:$('tiers-modal'),
    orderDetailModal:$('order-detail-modal'), viewStockModal:$('view-stock-modal'), editProdModal:$('edit-prod-modal'),
    addProdForm:$('add-prod-form'), addPromoForm:$('add-promo-form'), prodId:$('prod-id'),
    prodName:$('prod-name'), prodPrice:$('prod-price'), prodWarranty:$('prod-warranty'), prodEmoji:$('prod-emoji'), prodCustomEmojiId:$('prod-custom-emoji-id'), prodDesc:$('prod-desc'), prodImageUrl:$('prod-image-url'), prodDeliveryType:$('prod-delivery-type'),
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
    document.documentElement.lang = state.currentLang;
    $$('.lang-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-lang') === state.currentLang));
    const mobileLanguageSelect = $('mobile-language-select');
    if (mobileLanguageSelect) mobileLanguageSelect.value = state.currentLang;
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
    if (state.autoRefresh) state.autoRefreshTimer = setInterval(() => {
        if (document.hidden || state.refreshing) return;
        refreshData({silent:true});
    }, 60000);
}

function stopAutoRefresh() {
    if (state.autoRefreshTimer) { clearInterval(state.autoRefreshTimer); state.autoRefreshTimer = null; }
}

// ═════════════════════════════════════════════════════════════════════════
//  INIT
// ═════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    state.currentLang = localStorage.getItem('vb_lang') || 'fr';
    const theme = localStorage.getItem('vb_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    DOM.btnTheme.innerHTML = theme === 'dark' ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
    applyTranslations();

    localStorage.removeItem('vb_turbo');
    document.body.classList.remove('turbo-mode');

    const savedUrl = localStorage.getItem('ventebot_url') || '';
    const savedKey = localStorage.getItem('ventebot_key');
    if (savedKey) {
        state.botUrl = resolveBotUrl(savedUrl);
        state.apiKey = savedKey;
        DOM.settingsBotUrl.value = state.botUrl || '';
        if (DOM.botUrlInput) DOM.botUrlInput.value = state.botUrl || '';
        DOM.settingsApiKey.value = savedKey;
        testConnectionAndStart();
    } else {
        const origin = window.location.origin || '';
        if (origin && !origin.startsWith('file:') && DOM.botUrlInput && !DOM.botUrlInput.value) {
            DOM.botUrlInput.placeholder = origin;
        }
        showScreen('login');
    }

    setupEvents();
});

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  EVENT LISTENERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function setupEvents() {
    DOM.loginForm.addEventListener('submit', e => {
        e.preventDefault();
        state.apiKey = DOM.apiKeyInput.value.trim();
        state.botUrl = resolveBotUrl(DOM.botUrlInput.value);
        testConnectionAndStart();
    });
    $$('.menu-item').forEach(i => i.addEventListener('click', e => {
        e.preventDefault();
        if (i.getAttribute('data-external') === 'api-docs') {
            const baseUrl = (state.botUrl || window.location.origin || '').replace(/\/$/, '');
            window.open(`${baseUrl}/api/swagger/`, '_blank', 'noopener');
            return;
        }
        switchTab(i.getAttribute('data-tab'));
    }));
    DOM.btnLogout.addEventListener('click', logout);
    DOM.btnRefresh.addEventListener('click', refreshData);
    DOM.btnTheme.addEventListener('click', toggleTheme);
    DOM.btnAutoRefresh.addEventListener('click', toggleAutoRefresh);
    $('btn-export').addEventListener('click', () => showModal($('exportModal')));
    if (DOM.btnCreateResellerKey) DOM.btnCreateResellerKey.addEventListener('click', createResellerKey);
    
    if (DOM.statsProductSearch) {
        DOM.statsProductSearch.addEventListener('input', () => {
            renderStatsTable();
        });
    }

    $$('.sub-tab').forEach(t => t.addEventListener('click', () => {
        t.closest('.action-bar').querySelectorAll('.sub-tab').forEach(s => s.classList.remove('active'));
        t.closest('section').querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
        t.classList.add('active'); 
        let targetContent = document.querySelector(t.getAttribute('data-sub'));
        if (targetContent) targetContent.classList.add('active');
    }));

    $('btn-open-prod-modal').addEventListener('click', () => { 
        DOM.addProdForm.reset(); 
        DOM.prodId.value=''; 
        setDynamicPricingForm('prod', {});
        if (DOM.prodDeliveryType) DOM.prodDeliveryType.value='stock';
        toggleActivationFields('add'); 
        
        if ($('prod-act-msg')) $('prod-act-msg').value = "Your activation is complete.\n\nProduct: {product}\nOrder: #{order_id}";
        if ($('prod-act-msg-fr')) $('prod-act-msg-fr').value = "Votre activation est terminée.\n\nProduit : {product}\nCommande : #{order_id}";
        if ($('prod-act-msg-ar')) $('prod-act-msg-ar').value = "اكتمل التفعيل.\n\nالمنتج: {product}\nالطلب: #{order_id}";
        if ($('prod-act-msg-zh')) $('prod-act-msg-zh').value = "您的激活已完成。\n\n产品：{product}\n订单：#{order_id}";
        if ($('prod-act-msg-vi')) $('prod-act-msg-vi').value = "Kích hoạt của bạn đã hoàn tất.\n\nSản phẩm: {product}\nĐơn hàng: #{order_id}";
        if ($('prod-act-msg-ru')) $('prod-act-msg-ru').value = "Ваша активация завершена.\n\nТовар: {product}\nЗаказ: #{order_id}";

        if ($('prod-conf-msg')) $('prod-conf-msg').value = "Thank you for your purchase! 🙏";
        if ($('prod-conf-msg-fr')) $('prod-conf-msg-fr').value = "Merci pour votre achat ! 🙏";
        if ($('prod-conf-msg-ar')) $('prod-conf-msg-ar').value = "شكرا لشرائك! 🙏";
        if ($('prod-conf-msg-zh')) $('prod-conf-msg-zh').value = "感谢您的购买！🙏";
        if ($('prod-conf-msg-vi')) $('prod-conf-msg-vi').value = "Cảm ơn bạn đã mua hàng! 🙏";
        if ($('prod-conf-msg-ru')) $('prod-conf-msg-ru').value = "Спасибо за покупку! 🙏";

        showModal(DOM.prodModal); 
    });
    const btnMassTranslate = $('btn-mass-translate');
    if (btnMassTranslate) btnMassTranslate.addEventListener('click', massTranslate);
    $('btn-open-promo-modal').addEventListener('click', async () => {
        if (!state.products || state.products.length === 0) {
            try {
                await loadProducts();
            } catch (e) {
                console.warn('Could not load products for promo modal', e);
            }
        }
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

    
    if (DOM.prodDeliveryType) {
        DOM.prodDeliveryType.addEventListener('change', () => toggleActivationFields('add'));
    }
    if ($('edit-prod-delivery-type')) {
        $('edit-prod-delivery-type').addEventListener('change', () => toggleActivationFields('edit'));
    }
    setupDynamicPricingControls('prod');
    setupDynamicPricingControls('edit-prod');
    const recalculateDynamicButton = $('edit-prod-dynamic-recalculate');
    if (recalculateDynamicButton) recalculateDynamicButton.addEventListener('click', async () => {
        const productId = Number($('edit-prod-id').value);
        try {
            const settings = collectDynamicPricing('edit-prod');
            if (!settings.dynamic_pricing_enabled) throw new Error("Activez d'abord Dynamic Price.");
            settings.price_usd = Number($('edit-prod-price').value);
            showLoading(true);
            const result = await apiCall(
                `/api/products/${productId}/dynamic-pricing/recalculate`,
                'POST',
                settings
            );
            const calculatedProduct = {
                ...settings,
                id: productId,
                price_usd: Number(result.new_price ?? settings.price_usd),
                dynamic_suggested_price: Number(result.suggested_price ?? result.new_price ?? settings.price_usd),
                dynamic_last_calculated_at: new Date().toISOString(),
                dynamic_last_confidence: Number(result.confidence ?? 0),
                dynamic_last_explanation: result.explanation || '',
            };
            $('edit-prod-price').value = calculatedProduct.price_usd.toFixed(2);
            setDynamicPricingForm('edit-prod', calculatedProduct);

            // Display the authoritative calculation response even when a later
            // catalogue refresh is temporarily unavailable.
            try {
                await loadProducts();
                const refreshedProduct = state.products.find(item => Number(item.id) === productId);
                if (refreshedProduct) {
                    $('edit-prod-price').value = Number(refreshedProduct.price_usd).toFixed(2);
                    setDynamicPricingForm('edit-prod', refreshedProduct);
                }
            } catch (refreshError) {
                console.warn('Dynamic price calculated; catalogue refresh deferred.', refreshError);
            }
            await loadDynamicPricingHistory(productId);
            showToast(
                result.status === 'insufficient_data'
                    ? 'Calcul terminé : pas encore assez de données, le prix reste inchangé.'
                    : result.status === 'out_of_stock'
                        ? 'Calcul suspendu : le produit est en rupture de stock.'
                    : result.status === 'unchanged'
                        ? 'Calcul terminé : le prix recommandé reste inchangé.'
                        : 'Recommandation calculée. Utilisez Appliquer pour modifier le prix maintenant.',
                'success'
            );
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            showLoading(false);
        }
    });
    const applyDynamicButton = $('edit-prod-dynamic-apply');
    if (applyDynamicButton) applyDynamicButton.addEventListener('click', async () => {
        const productId = Number($('edit-prod-id').value);
        try {
            showLoading(true);
            const result = await apiCall(`/api/products/${productId}/dynamic-pricing/apply`, 'POST');
            await loadProducts();
            const product = state.products.find(item => Number(item.id) === productId);
            if (product) {
                $('edit-prod-price').value = Number(result.new_price).toFixed(2);
                setDynamicPricingForm('edit-prod', product);
            }
            await loadDynamicPricingHistory(productId);
            showToast(result.status === 'unchanged' ? 'Cette suggestion est déjà appliquée.' : 'Suggestion appliquée au prix du produit.', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            showLoading(false);
        }
    });
    const simulateDynamicButton = $('edit-prod-dynamic-simulate');
    if (simulateDynamicButton) simulateDynamicButton.addEventListener('click', async () => {
        const productId = Number($('edit-prod-id').value);
        try {
            const settings = collectDynamicPricing('edit-prod');
            if (!settings.dynamic_pricing_enabled) throw new Error("Activez d'abord Dynamic Price.");
            settings.price_usd = Number($('edit-prod-price').value);
            showLoading(true);
            await apiCall(`/api/products/${productId}`, 'PUT', settings);
            const simulation = await apiCall(`/api/products/${productId}/dynamic-pricing/simulate?days=30`);
            renderDynamicPricingSimulation(simulation);
            showToast('Simulation 30 jours terminée.', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            showLoading(false);
        }
    });

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
    const mobileLanguageSelect = $('mobile-language-select');
    if (mobileLanguageSelect) mobileLanguageSelect.addEventListener('change', () => setLang(mobileLanguageSelect.value));
    $$('[data-go-tab]').forEach(button => button.addEventListener('click', () => switchTab(button.dataset.goTab)));
    if (DOM.dashboardRange) {
        DOM.dashboardRange.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
            DOM.dashboardRange.querySelectorAll('button').forEach(item => item.classList.remove('active'));
            button.classList.add('active');
            state.chartDays = Number(button.dataset.days || 30);
            loadCharts();
        }));
    }
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && state.autoRefresh && !state.refreshing) refreshData({silent:true});
    });
    $$('.modal-overlay').forEach(modal => {
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.addEventListener('click', event => { if (event.target === modal) hideModal(modal); });
    });
    document.addEventListener('keydown', event => {
        if (event.key !== 'Escape') return;
        const openModal = document.querySelector('.modal-overlay:not(.hidden)');
        if (openModal) hideModal(openModal);
    });

    const btnTranslateAdd = $('btn-translate-add');
    const btnTranslateActAdd = $('btn-translate-act-add');
    const btnTranslateConfAdd = $('btn-translate-conf-add');
    const btnTranslateEdit = $('btn-translate-edit');
    const btnTranslateActEdit = $('btn-translate-act-edit');
    const btnTranslateConfEdit = $('btn-translate-conf-edit');

    if (btnTranslateAdd) btnTranslateAdd.addEventListener('click', () => autoTranslate('add', 'desc'));
    if (btnTranslateActAdd) btnTranslateActAdd.addEventListener('click', () => autoTranslate('add', 'act'));
    if (btnTranslateConfAdd) btnTranslateConfAdd.addEventListener('click', () => autoTranslate('add', 'conf'));
    if (btnTranslateEdit) btnTranslateEdit.addEventListener('click', () => autoTranslate('edit', 'desc'));
    if (btnTranslateActEdit) btnTranslateActEdit.addEventListener('click', () => autoTranslate('edit', 'act'));
    if (btnTranslateConfEdit) btnTranslateConfEdit.addEventListener('click', () => autoTranslate('edit', 'conf'));

}

function dynamicPricingId(prefix, field) {
    return `${prefix}-dynamic-${field}`;
}

function setDynamicPricingEnabled(prefix, enabled, seedBounds=true) {
    const toggle = $(dynamicPricingId(prefix, 'toggle'));
    const input = $(dynamicPricingId(prefix, 'enabled'));
    const settings = $(dynamicPricingId(prefix, 'settings'));
    const status = $(dynamicPricingId(prefix, 'status'));
    if (!toggle || !input || !settings || !status) return;
    input.value = enabled ? '1' : '0';
    toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    status.textContent = enabled ? 'Actif' : 'Désactivé';
    settings.classList.toggle('hidden', !enabled);

    if (enabled && seedBounds) {
        const priceInput = $(prefix === 'prod' ? 'prod-price' : 'edit-prod-price');
        const price = Number(priceInput?.value || 0);
        const minInput = $(dynamicPricingId(prefix, 'min'));
        const maxInput = $(dynamicPricingId(prefix, 'max'));
        if (price > 0 && minInput && !minInput.value) minInput.value = (price * 0.8).toFixed(2);
        if (price > 0 && maxInput && !maxInput.value) maxInput.value = (price * 1.2).toFixed(2);
    }
}

function setDynamicPricingForm(prefix, product={}) {
    const price = Number(product.price_usd || $(prefix === 'prod' ? 'prod-price' : 'edit-prod-price')?.value || 0);
    const setValue = (field, value) => { const element = $(dynamicPricingId(prefix, field)); if (element) element.value = value; };
    setValue('mode', product.dynamic_pricing_mode || 'automatic');
    setValue('sensitivity', product.dynamic_sensitivity || 'normal');
    setValue('min', product.dynamic_min_price ?? (price > 0 ? (price * 0.8).toFixed(2) : ''));
    setValue('max', product.dynamic_max_price ?? (price > 0 ? (price * 1.2).toFixed(2) : ''));
    setValue('target', product.dynamic_target_daily_sales || 1);
    setValue('change', product.dynamic_max_change_pct || 5);
    setValue('cooldown', product.dynamic_cooldown_hours || 6);
    setValue('daily-cap', product.dynamic_daily_cap_pct || 10);
    setValue('weekly-cap', product.dynamic_weekly_cap_pct || 25);
    setValue('confidence', Math.round(Number(product.dynamic_min_confidence ?? 0.30) * 100));
    const psychological = $(dynamicPricingId(prefix, 'psychological'));
    if (psychological) psychological.checked = Boolean(product.dynamic_psychological_rounding);
    setDynamicPricingEnabled(prefix, Boolean(product.dynamic_pricing_enabled), false);

    if (prefix === 'edit-prod') {
        const current = $('edit-prod-dynamic-current');
        const suggested = $('edit-prod-dynamic-suggested');
        const confidence = $('edit-prod-dynamic-confidence-value');
        const explanation = $('edit-prod-dynamic-explanation');
        if (current) current.textContent = price > 0 ? `$${price.toFixed(2)}` : '-';
        const suggestedPrice = product.dynamic_suggested_price;
        if (suggested) suggested.textContent = suggestedPrice === null || suggestedPrice === undefined ? 'À calculer' : `$${Number(suggestedPrice).toFixed(2)}`;
        if (confidence) {
            const confidenceValue = product.dynamic_last_confidence;
            confidence.textContent = confidenceValue === null || confidenceValue === undefined ? '-' : `${Math.round(Number(confidenceValue) * 100)}%`;
        }
        if (explanation && product.dynamic_last_explanation) explanation.textContent = product.dynamic_last_explanation;
        const applyButton = $('edit-prod-dynamic-apply');
        if (applyButton) {
            const canApply = Boolean(product.dynamic_pricing_enabled)
                && suggestedPrice !== null && suggestedPrice !== undefined
                && Math.abs(Number(suggestedPrice) - price) >= 0.01;
            applyButton.classList.toggle('hidden', !canApply);
        }
    }
}

function collectDynamicPricing(prefix) {
    const enabled = $(dynamicPricingId(prefix, 'enabled'))?.value === '1';
    if (!enabled) return {dynamic_pricing_enabled:false};
    const numberValue = field => Number($(dynamicPricingId(prefix, field))?.value);
    const price = Number($(prefix === 'prod' ? 'prod-price' : 'edit-prod-price')?.value);
    const minPrice = numberValue('min');
    const maxPrice = numberValue('max');
    const target = numberValue('target');
    const maxChange = numberValue('change');
    const cooldown = numberValue('cooldown');
    const dailyCap = numberValue('daily-cap');
    const weeklyCap = numberValue('weekly-cap');
    const confidence = numberValue('confidence');
    if (![price, minPrice, maxPrice, target, maxChange, cooldown, dailyCap, weeklyCap, confidence].every(Number.isFinite)) throw new Error('Vérifiez les paramètres du prix dynamique.');
    if (minPrice <= 0 || maxPrice < minPrice) throw new Error('Le prix minimum doit être positif et inférieur au prix maximum.');
    if (price < minPrice || price > maxPrice) throw new Error('Le prix actuel doit être compris entre le minimum et le maximum.');
    if (target < 0.1) throw new Error("L'objectif de ventes doit être supérieur à zéro.");
    if (maxChange < 0.5 || maxChange > 20) throw new Error('La variation maximale doit être comprise entre 0,5 % et 20 %.');
    if (cooldown < 1 || cooldown > 168) throw new Error('Le délai doit être compris entre 1 et 168 heures.');
    if (dailyCap < 0.5 || dailyCap > 100) throw new Error('Le plafond sur 24 h doit être compris entre 0,5 % et 100 %.');
    if (weeklyCap < dailyCap || weeklyCap > 200) throw new Error('Le plafond sur 7 jours doit être supérieur au plafond journalier et inférieur à 200 %.');
    if (confidence < 0 || confidence > 100) throw new Error('La confiance minimum doit être comprise entre 0 % et 100 %.');
    return {
        dynamic_pricing_enabled:true,
        dynamic_pricing_mode:$(dynamicPricingId(prefix, 'mode')).value,
        dynamic_min_price:minPrice,
        dynamic_max_price:maxPrice,
        dynamic_target_daily_sales:target,
        dynamic_max_change_pct:maxChange,
        dynamic_cooldown_hours:cooldown,
        dynamic_sensitivity:$(dynamicPricingId(prefix, 'sensitivity')).value,
        dynamic_daily_cap_pct:dailyCap,
        dynamic_weekly_cap_pct:weeklyCap,
        dynamic_min_confidence:confidence / 100,
        dynamic_psychological_rounding:Boolean($(dynamicPricingId(prefix, 'psychological'))?.checked),
    };
}

function setupDynamicPricingControls(prefix) {
    const toggle = $(dynamicPricingId(prefix, 'toggle'));
    if (!toggle) return;
    toggle.addEventListener('click', () => {
        const enabled = $(dynamicPricingId(prefix, 'enabled')).value === '1';
        setDynamicPricingEnabled(prefix, !enabled, true);
    });
    const priceInput = $(prefix === 'prod' ? 'prod-price' : 'edit-prod-price');
    if (priceInput) priceInput.addEventListener('change', () => {
        if ($(dynamicPricingId(prefix, 'enabled')).value === '1') {
            setDynamicPricingEnabled(prefix, true, true);
        }
    });
}

async function loadDynamicPricingHistory(productId) {
    const container = $('edit-prod-dynamic-history');
    if (!container) return;
    container.innerHTML = '<p class="empty-state">Chargement...</p>';
    try {
        let data;
        try {
            data = await apiCall(`/api/products/${productId}/dynamic-pricing/history?limit=30`);
        } catch (firstError) {
            if (!['UNREACHABLE', 'TIMEOUT'].includes(firstError.message)) throw firstError;
            await new Promise(resolve => setTimeout(resolve, 900));
            data = await apiCall(`/api/products/${productId}/dynamic-pricing/history?limit=30`);
        }
        const history = data.history || [];
        container.innerHTML = history.length ? history.slice(0, 10).map(item => {
            const date = item.created_at ? parseUTCDate(item.created_at).toLocaleString() : '';
            const mode = item.applied ? (item.mode === 'automatic' ? 'Auto appliqué' : 'Appliqué') : 'Prévisualisation';
            const displayedPrice = item.applied ? item.new_price : item.suggested_price;
            return `<div class="dynamic-history-item">
                <strong>$${Number(item.old_price).toFixed(2)} → $${Number(displayedPrice).toFixed(2)}</strong>
                <span>${mode} · ${escapeHtml(date)}</span>
                <small>${escapeHtml(item.explanation || item.reason || '')}</small>
                <div class="dynamic-history-meta">
                    <span class="dynamic-history-pill ${item.applied ? 'applied' : ''}">${item.applied ? 'Prix appliqué' : 'Suggestion'}</span>
                    <span class="dynamic-history-pill">Confiance ${Number(item.confidence_pct || 0)}%</span>
                    <span class="dynamic-history-pill">${(Number(item.sales_3d || 0) / 3).toFixed(1)} vente/j</span>
                    <span class="dynamic-history-pill">Revenu 7j $${Number(item.revenue_7d || 0).toFixed(2)}</span>
                </div>
            </div>`;
        }).join('') : '<p class="empty-state">Aucun historique.</p>';
        const explanation = $('edit-prod-dynamic-explanation');
        if (explanation && history.length) explanation.textContent = history[0].explanation || history[0].reason || 'Décision dynamique enregistrée.';
        renderDynamicPricingHistoryChart(history);
    } catch (error) {
        renderDynamicPricingHistoryChart([]);
        const transient = ['UNREACHABLE', 'TIMEOUT'].includes(error.message);
        const message = transient
            ? "Historique temporairement indisponible. Le prix dynamique reste actif."
            : `Historique indisponible : ${error.message}`;
        container.innerHTML = `<div class="dynamic-history-unavailable"><p>${escapeHtml(message)}</p><button type="button" class="btn-secondary"><i class="fa-solid fa-rotate-right"></i> Réessayer</button></div>`;
        container.querySelector('button').addEventListener('click', () => loadDynamicPricingHistory(productId));
    }
}

function renderDynamicPricingHistoryChart(history) {
    const canvas = $('edit-prod-dynamic-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    if (state.dynamicPriceChart) {
        state.dynamicPriceChart.destroy();
        state.dynamicPriceChart = null;
    }
    if (!history.length) return;
    const rows = [...history].reverse();
    const labels = rows.map(item => item.created_at ? parseUTCDate(item.created_at).toLocaleDateString() : '');
    state.dynamicPriceChart = new Chart(canvas, {
        type:'line',
        data:{labels,datasets:[
            {label:'Prix recommandé ($)',data:rows.map(item=>Number(item.suggested_price||0)),borderColor:'#60a5fa',backgroundColor:'#60a5fa22',tension:.25,pointRadius:3,yAxisID:'y'},
            {label:'Ventes/jour',type:'bar',data:rows.map(item=>Number(item.sales_3d||0)/3),backgroundColor:'#34d39955',borderColor:'#34d399',borderWidth:1,yAxisID:'y1'},
            {label:'Revenu 7j ($)',data:rows.map(item=>Number(item.revenue_7d||0)),borderColor:'#f59e0b',tension:.25,pointRadius:2,yAxisID:'y2',hidden:true},
            {label:'Conversion (%)',data:rows.map(item=>Number(item.conversion_7d||0)*100),borderColor:'#f472b6',tension:.25,pointRadius:2,yAxisID:'y1',hidden:true},
        ]},
        options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{boxWidth:10,usePointStyle:true}}},scales:{
            y:{position:'left',beginAtZero:false,grid:{color:'rgba(148,163,184,.10)'}},
            y1:{position:'right',beginAtZero:true,grid:{display:false}},
            y2:{position:'right',beginAtZero:true,display:false,grid:{display:false}},
            x:{grid:{display:false}}
        }}
    });
}

function renderDynamicPricingSimulation(simulation) {
    const container = $('edit-prod-dynamic-simulation');
    const summary = $('edit-prod-dynamic-simulation-summary');
    const canvas = $('edit-prod-dynamic-simulation-chart');
    if (!container || !summary || !canvas) return;
    container.classList.remove('hidden');
    const values = simulation.summary || {};
    summary.innerHTML = `
        <div class="dynamic-simulation-metric"><span>Prix de départ</span><strong>$${Number(values.start_price||0).toFixed(2)}</strong></div>
        <div class="dynamic-simulation-metric"><span>Prix simulé final</span><strong>$${Number(values.end_price||0).toFixed(2)}</strong></div>
        <div class="dynamic-simulation-metric"><span>Décisions</span><strong>${Number(values.decisions||0)}</strong></div>
        <div class="dynamic-simulation-metric"><span>Ventes observées</span><strong>${Number(values.observed_sales||0)}</strong></div>
        <div class="dynamic-simulation-metric"><span>Revenu observé</span><strong>$${Number(values.observed_revenue||0).toFixed(2)}</strong></div>
        <div class="dynamic-simulation-metric"><span>Fourchette simulée</span><strong>$${Number(values.min_price||0).toFixed(2)} – $${Number(values.max_price||0).toFixed(2)}</strong></div>
        <p class="dynamic-simulation-note"><i class="fa-solid fa-circle-info"></i> ${escapeHtml(simulation.assumption || 'Simulation indicative en lecture seule.')}</p>`;
    if (state.dynamicSimulationChart) state.dynamicSimulationChart.destroy();
    const points = simulation.points || [];
    state.dynamicSimulationChart = new Chart(canvas, {
        type:'line',
        data:{labels:points.map(point=>point.date),datasets:[
            {label:'Prix simulé ($)',data:points.map(point=>point.simulated_price),borderColor:'#60a5fa',backgroundColor:'#60a5fa22',fill:true,tension:.25,pointRadius:1,yAxisID:'y'},
            {label:'Ventes observées',type:'bar',data:points.map(point=>point.sales),backgroundColor:'#34d39955',borderColor:'#34d399',borderWidth:1,yAxisID:'y1'},
            {label:'Revenu observé ($)',data:points.map(point=>point.revenue),borderColor:'#f59e0b',pointRadius:1,tension:.2,yAxisID:'y2',hidden:true},
            {label:'Confiance (%)',data:points.map(point=>Number(point.confidence||0)*100),borderColor:'#f472b6',pointRadius:1,tension:.2,yAxisID:'y1',hidden:true},
        ]},
        options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{boxWidth:10,usePointStyle:true}}},scales:{
            y:{position:'left',beginAtZero:false},y1:{position:'right',beginAtZero:true,grid:{display:false}},
            y2:{position:'right',display:false,grid:{display:false}},x:{grid:{display:false}}
        }}
    });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  API CALL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
const DEFAULT_API_URL = 'https://ventetelegrambotrailway-production.up.railway.app';

function resolveBotUrl(raw) {
    let u = (raw || '').trim().replace(/\/$/, '');
    if (u && !u.startsWith('http://') && !u.startsWith('https://')) u = 'https://' + u;
    if (u) {
        try {
            if (new URL(u).hostname.toLowerCase().endsWith('.netlify.app')) {
                u = DEFAULT_API_URL;
            }
        } catch(e) {}
    }
    if (!u && typeof window !== 'undefined') {
        const localFile = window.location?.protocol === 'file:' || window.location?.origin === 'null';
        const host = (window.location?.hostname || '').toLowerCase();
        const apiHostedHere = host.endsWith('.up.railway.app')
            || host === 'localhost'
            || host === '127.0.0.1';
        // Netlify and local files only host the frontend; the API remains on Railway.
        u = (!localFile && apiHostedHere) ? window.location.origin : DEFAULT_API_URL;
    }
    return u.replace(/\/$/, '');
}

async function apiCall(endpoint, method='GET', body=null) {
    const base = resolveBotUrl(state.botUrl);
    const url = `${base}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    const headers = { 'X-API-Key': state.apiKey };
    if (body) headers['Content-Type'] = 'application/json';
    const ctrl = new AbortController(); const tid = setTimeout(() => ctrl.abort(), 60000);
    const cfg = { method, headers, mode:'cors', signal:ctrl.signal };
    if (body) cfg.body = JSON.stringify(body);
    try {
        const res = await fetch(url, cfg); clearTimeout(tid);
        if (!res.ok) { 
            if (res.status===401) throw new Error('API_KEY_INVALID'); 
            let errDetail = `API ${res.status}`;
            try {
                const errBody = await res.json();
                if (errBody && errBody.detail) errDetail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
            } catch(e) {}
            throw new Error(errDetail); 
        }
        return await res.json();
    } catch(e) {
        clearTimeout(tid);
        if (e.name==='AbortError') throw new Error('TIMEOUT');
        // Browser network/CORS failures surface as TypeError: Failed to fetch
        if (e instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(e.message || '')) {
            throw new Error('UNREACHABLE');
        }
        throw e;
    }
}

async function autoTranslate(type, field) {
    let btn, sourceTextarea, targetFr, targetAr, targetZh, targetVi, targetRu;
    if (field === 'act') {
        btn = type === 'add' ? $('btn-translate-act-add') : $('btn-translate-act-edit');
        sourceTextarea = type === 'add' ? $('prod-act-msg') : $('edit-prod-act-msg');
        targetFr = type === 'add' ? $('prod-act-msg-fr') : $('edit-prod-act-msg-fr');
        targetAr = type === 'add' ? $('prod-act-msg-ar') : $('edit-prod-act-msg-ar');
        targetZh = type === 'add' ? $('prod-act-msg-zh') : $('edit-prod-act-msg-zh');
        targetVi = type === 'add' ? $('prod-act-msg-vi') : $('edit-prod-act-msg-vi');
        targetRu = type === 'add' ? $('prod-act-msg-ru') : $('edit-prod-act-msg-ru');
    } else if (field === 'conf') {
        btn = type === 'add' ? $('btn-translate-conf-add') : $('btn-translate-conf-edit');
        sourceTextarea = type === 'add' ? $('prod-conf-msg') : $('edit-prod-conf-msg');
        targetFr = type === 'add' ? $('prod-conf-msg-fr') : $('edit-prod-conf-msg-fr');
        targetAr = type === 'add' ? $('prod-conf-msg-ar') : $('edit-prod-conf-msg-ar');
        targetZh = type === 'add' ? $('prod-conf-msg-zh') : $('edit-prod-conf-msg-zh');
        targetVi = type === 'add' ? $('prod-conf-msg-vi') : $('edit-prod-conf-msg-vi');
        targetRu = type === 'add' ? $('prod-conf-msg-ru') : $('edit-prod-conf-msg-ru');
    } else {
        btn = type === 'add' ? $('btn-translate-add') : $('btn-translate-edit');
        sourceTextarea = type === 'add' ? DOM.prodDesc : $('edit-prod-desc');
        targetFr = type === 'add' ? $('prod-desc-fr') : $('edit-prod-desc-fr');
        targetAr = type === 'add' ? $('prod-desc-ar') : $('edit-prod-desc-ar');
        targetZh = type === 'add' ? $('prod-desc-zh') : $('edit-prod-desc-zh');
        targetVi = type === 'add' ? $('prod-desc-vi') : $('edit-prod-desc-vi');
        targetRu = type === 'add' ? $('prod-desc-ru') : $('edit-prod-desc-ru');
    }

    const text = sourceTextarea ? sourceTextarea.value.trim() : '';
    if (!text) {
        alert("Veuillez d'abord remplir le texte en anglais !");
        return;
    }

    const originalText = btn ? btn.textContent : "✨ Traduire Message";
    if (btn) { btn.textContent = "⏳..."; btn.disabled = true; }

    try {
        const res = await apiCall('/api/translate', 'POST', { text: text });
        if (res.fr && targetFr) targetFr.value = res.fr;
        if (res.ar && targetAr) targetAr.value = res.ar;
        if (res.zh && targetZh) targetZh.value = res.zh;
        if (res.vi && targetVi) targetVi.value = res.vi;
        if (res.ru && targetRu) targetRu.value = res.ru;
    } catch(e) {
        alert("Erreur de traduction: " + (e.message || "Assurez-vous d'avoir configuré GEMINI_API_KEY sur Railway."));
    } finally {
        if (btn) { btn.textContent = originalText; btn.disabled = false; }
    }
}

let massTranslateCancel = false;

async function massTranslate() {
    if (!state.products || state.products.length === 0) {
        alert("Aucun produit dans le catalogue.");
        return;
    }
    
    // Find products that have an English description but are missing at least one translation
    const toTranslate = state.products.filter(p => {
        const hasEn = p.description && p.description.trim().length > 0;
        const missingTranslation = !p.description_fr || !p.description_ar || !p.description_zh || !p.description_vi || !p.description_ru;
        return hasEn && missingTranslation;
    });
    
    if (toTranslate.length === 0) {
        alert("🎉 Tous les produits sont déjà entièrement traduits !");
        return;
    }
    
    if (!confirm(`Trouvé ${toTranslate.length} produit(s) à traduire. Voulez-vous lancer la traduction automatique ?`)) {
        return;
    }
    
    massTranslateCancel = false;
    const overlay = $('mass-translate-overlay');
    const progressBar = $('mass-translate-progress');
    const statusText = $('mass-translate-status');
    const btnCancel = $('btn-mass-translate-cancel');
    
    overlay.style.display = 'flex';
    progressBar.style.width = '0%';
    
    btnCancel.onclick = () => {
        massTranslateCancel = true;
        btnCancel.textContent = "Annulation en cours...";
        btnCancel.disabled = true;
    };
    btnCancel.textContent = "Annuler";
    btnCancel.disabled = false;
    
    let successCount = 0;
    
    for (let i = 0; i < toTranslate.length; i++) {
        if (massTranslateCancel) break;
        
        const p = toTranslate[i];
        statusText.textContent = `Traduction du produit "${p.name}" (${i+1}/${toTranslate.length})...`;
        progressBar.style.width = `${((i) / toTranslate.length) * 100}%`;
        
        try {
            // Call Gemini
            const res = await apiCall('/api/translate', 'POST', { text: p.description });
            
            // Build updates for the missing fields
            const updates = {};
            if (!p.description_fr && res.fr) updates.description_fr = res.fr;
            if (!p.description_ar && res.ar) updates.description_ar = res.ar;
            if (!p.description_zh && res.zh) updates.description_zh = res.zh;
            if (!p.description_vi && res.vi) updates.description_vi = res.vi;
            if (!p.description_ru && res.ru) updates.description_ru = res.ru;
            
            // Save to database
            if (Object.keys(updates).length > 0) {
                await apiCall(`/api/products/${p.id}`, 'PUT', updates);
                // Update local state so product won't be re-translated if cancelled and restarted
                if (updates.description_fr) p.description_fr = updates.description_fr;
                if (updates.description_ar) p.description_ar = updates.description_ar;
                if (updates.description_zh) p.description_zh = updates.description_zh;
                if (updates.description_vi) p.description_vi = updates.description_vi;
                if (updates.description_ru) p.description_ru = updates.description_ru;
                successCount++;
            }
            
            // Wait 1 second to avoid rate limits
            await new Promise(r => setTimeout(r, 1000));
        } catch (e) {
            console.error(`Erreur pour le produit ${p.id}:`, e);
            // Si c'est l'API_KEY manquante, on arrête tout
            if (e.message && e.message.includes('API_KEY_INVALID')) {
                alert("Clé API invalide ou manquante.");
                break;
            }
            // Sinon on continue avec le produit suivant
        }
    }
    
    progressBar.style.width = '100%';
    statusText.textContent = `Terminé ! ${successCount} produit(s) traduit(s).`;
    
    setTimeout(() => {
        overlay.style.display = 'none';
        fetchProducts(); // Refresh the product list
        if (successCount > 0) {
            alert(`✅ Traduction terminée : ${successCount} produit(s) mis à jour avec succès.`);
        }
    }, 1500);
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  CONNECTION
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
async function testConnectionAndStart() {
    showLoading(true); DOM.loginError.classList.add('hidden');
    try {
        state.botUrl = resolveBotUrl(state.botUrl);
        if (!state.apiKey) throw new Error('MISSING_KEY');

        // /api/stats validates connectivity, database readiness and the admin key
        // in one request. A separate /health request made login less reliable.
        state.initialStats = await apiCall('/api/stats');

        localStorage.setItem('ventebot_url', state.botUrl);
        localStorage.setItem('ventebot_key', state.apiKey);
        DOM.settingsBotUrl.value = state.botUrl;
        DOM.settingsApiKey.value = state.apiKey;
        showScreen('app');
        await refreshData({silent:true});
        startAutoRefresh();
    } catch (e) {
        showScreen('login');
        if (DOM.botUrlInput) DOM.botUrlInput.value = state.botUrl || '';
        DOM.loginError.classList.remove('hidden');
        let msg;
        if (e.message === 'TIMEOUT') {
            msg = '⏱ Timeout — le bot met trop longtemps à répondre (cold start Railway ?). Réessayez dans 30s.';
        } else if (e.message === 'API_KEY_INVALID') {
            msg = '🔑 Clé API invalide — utilisez la variable <code>ADMIN_API_KEY</code> de Railway.';
        } else if (e.message === 'MISSING_KEY') {
            msg = '🔑 Entrez la clé API administrateur (<code>ADMIN_API_KEY</code>).';
        } else if (e.message === 'UNREACHABLE' || e.message === 'BAD_HEALTH' || String(e.message || '').startsWith('HEALTH_')) {
            msg = `❌ Impossible de joindre l'API (<code>${escapeHtml(state.botUrl || '?')}</code>).<br>`
                + `<small style="opacity:.85">Vérifiez : URL Railway correcte (https://….up.railway.app), bot démarré, et CORS. `
                + `Ouvrez le dashboard sur <code>${escapeHtml(state.botUrl || '')}/dashboard/</code> ou entrez cette URL ci-dessus.</small>`;
        } else {
            msg = `❌ ${escapeHtml(e.message || 'Erreur de connexion')}`;
        }
        DOM.loginError.innerHTML = msg;
    } finally {
        showLoading(false);
    }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  REFRESH ALL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
const tabRefreshLoaders = {
    'dashboard-tab': [loadDashboardOverview, loadStats, loadCharts],
    'stats-tab': [loadStats, loadCharts, loadProductStats, loadProductMomentum, loadDeadProductAlerts],
    'inventory-tab': [loadProducts, loadBinanceAccounts],
    'orders-tab': [loadProducts, loadAllOrders],
    'activations-tab': [loadProducts, loadActivations],
    'resellers-tab': [loadResellers],
    'users-tab': [loadUsers],
    'tickets-tab': [loadTickets],
    'settings-tab': [loadProducts, loadPromos, loadPaymentSettings],
    'wallet-history-tab': [loadWalletHistory],
    'finance-tab': [loadFinance],
    'binance-tab': [loadBinanceAccounts],
};

const fullRefreshLoaders = [
    loadDashboardOverview, loadStats, loadFinance, loadProducts, loadAllOrders, loadActivations, loadResellers,
    loadTickets, loadUsers, loadPromos, loadCharts, loadWalletHistory, loadBinanceAccounts,
    loadPaymentSettings, loadProductStats, loadProductMomentum, loadDeadProductAlerts
];

function uniqueLoaders(loaders) {
    return [...new Set(loaders.filter(Boolean))];
}

async function refreshData(options={}) {
    if (state.refreshing) return;
    state.refreshing = true;
    if (!options.silent) showLoading(true);
    DOM.apiStatusBadge.querySelector('.status-indicator').className = 'status-indicator';
    try {
        const loaders = options.full
            ? fullRefreshLoaders
            : uniqueLoaders(tabRefreshLoaders[state.currentTab] || tabRefreshLoaders['dashboard-tab']);
        const results = await Promise.allSettled(loaders.map(loader => loader()));
        const failures = results.filter(result => result.status === 'rejected');
        failures.forEach(result => console.error(result.reason));
        const status = DOM.apiStatusBadge.querySelector('.status-indicator');
        status.classList.add(failures.length === results.length ? 'offline' : 'online');
        if (failures.length && !options.silent) showToast(`${failures.length} section(s) n'ont pas pu être actualisées.`, 'error');
        state.lastRefreshAt = new Date();
    } finally {
        state.refreshing = false;
        if (!options.silent) showLoading(false);
    }
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

function formatComparison(current, previous) {
    const now = Number(current || 0);
    const before = Number(previous || 0);
    if (before === 0) return now === 0 ? {text:'Stable vs hier', className:''} : {text:'Nouveau vs hier', className:'positive'};
    const percent = Math.round(((now - before) / before) * 100);
    return {text:`${percent >= 0 ? '+' : ''}${percent}% vs hier`, className:percent > 0 ? 'positive' : percent < 0 ? 'negative' : ''};
}

async function loadDashboardOverview() {
    const data = await apiCall('/api/dashboard/overview');
    const today = data.today || {};
    const yesterday = data.yesterday || {};
    const actions = data.actions || {};
    const revenueDelta = formatComparison(today.revenue, yesterday.revenue);
    const ordersDelta = formatComparison(today.orders, yesterday.orders);

    DOM.todayRevenue.textContent = `$${Number(today.revenue || 0).toFixed(2)}`;
    DOM.todayOrders.textContent = Number(today.orders || 0).toLocaleString();
    DOM.todayRevenueDelta.textContent = revenueDelta.text;
    DOM.todayRevenueDelta.className = revenueDelta.className;
    DOM.todayOrdersDelta.textContent = ordersDelta.text;
    DOM.todayOrdersDelta.className = ordersDelta.className;

    const actionItems = [
        {count:actions.delivery_issues, icon:'triangle-exclamation', title:'Livraisons à relancer', detail:'Paiement reçu, livraison incomplète', tab:'orders-tab'},
        {count:actions.pending_activations, icon:'bolt', title:'Activations à traiter', detail:'Identifiants clients prêts', tab:'activations-tab'},
        {count:actions.pending_payments, icon:'clock', title:'Paiements en attente', detail:'Commandes à contrôler', tab:'orders-tab'},
        {count:actions.open_tickets, icon:'headset', title:'Tickets ouverts', detail:'Réponses clients attendues', tab:'tickets-tab'}
    ];
    DOM.actionCenterList.innerHTML = actionItems.map(item => `
        <button type="button" class="action-item" data-go-tab="${item.tab}">
            <span class="action-item-icon"><i class="fa-solid fa-${item.icon}"></i></span>
            <span><strong>${item.title}</strong><span>${item.detail}</span></span>
            <span class="action-count">${Number(item.count || 0)}</span>
        </button>`).join('');
    DOM.actionCenterList.querySelectorAll('[data-go-tab]').forEach(button => button.addEventListener('click', () => switchTab(button.dataset.goTab)));

    const recentOrders = Array.isArray(data.recent_orders) ? data.recent_orders : [];
    DOM.recentOrdersList.innerHTML = recentOrders.length ? recentOrders.map(order => {
        const customer = order.username ? `@${order.username}` : (order.user_first_name || order.user_telegram_id || 'Client');
        const product = `${order.product_emoji || ''} ${order.product_name || `Commande #${order.id}`}`.trim();
        const date = order.created_at ? parseUTCDate(order.created_at).toLocaleString([], {dateStyle:'short', timeStyle:'short'}) : '';
        return `<button type="button" class="recent-order-item" data-go-tab="orders-tab">
            <span class="recent-order-meta"><strong>${escapeHtml(product)}</strong><span>${escapeHtml(customer)} · ${escapeHtml(date)}</span></span>
            <span class="status-badge status-${escapeHtml(String(order.status || '').toLowerCase())}">${escapeHtml(order.status || '')}</span>
            <span class="recent-order-amount">$${Number(order.amount_usd || 0).toFixed(2)}</span>
        </button>`;
    }).join('') : '<p class="empty-state">Aucune commande récente.</p>';
    DOM.recentOrdersList.querySelectorAll('[data-go-tab]').forEach(button => button.addEventListener('click', () => switchTab(button.dataset.goTab)));

    const pendingOrders = Number(actions.pending_payments || 0) + Number(actions.delivery_issues || 0);
    DOM.badgeOrders.textContent = pendingOrders;
    DOM.badgeOrders.classList.toggle('hidden', pendingOrders === 0);
    DOM.badgeActivations.textContent = Number(actions.pending_activations || 0);
    DOM.badgeActivations.classList.toggle('hidden', Number(actions.pending_activations || 0) === 0);
    DOM.badgeTickets.textContent = Number(actions.open_tickets || 0);
    DOM.badgeTickets.classList.toggle('hidden', Number(actions.open_tickets || 0) === 0);
}

async function loadStats() {
    const s = state.initialStats || await apiCall('/api/stats');
    state.initialStats = null;
    state.lastStats = s; // Save for modal
    DOM.statRevenue.textContent = `$${parseFloat(s.total_revenue).toFixed(2)}`;
    DOM.statOrders.textContent = s.completed_orders;
    DOM.statUsers.textContent = s.total_users;
    DOM.statPending.textContent = s.pending_orders || 0;
    if (DOM.statNewUsers) DOM.statNewUsers.textContent = s.new_users || 0;
    if (DOM.statReturningUsers) DOM.statReturningUsers.textContent = s.returning_users || 0;
    if (s.stock_summary?.length > 0) {
        DOM.stockSummaryList.innerHTML = s.stock_summary.map(i => {
            const isActivation = i.delivery_type === 'activation';
            const c = isActivation ? 'ok' : (i.stock===0?'empty':(i.stock_risk === 'soon' || i.stock<3)?'low':'ok');
            const daysLeft = isActivation
                ? 'Activation'
                : i.days_left === null || i.days_left === undefined
                ? 'Rupture: -'
                : `Rupture: ~${Number(i.days_left).toFixed(i.days_left < 10 ? 1 : 0)}j`;
            const velocity = Number(i.avg_daily_sales_7d || 0);
            const stockLabel = isActivation ? 'Manuel' : `${i.stock} ${t('stock_in')}`;
            return `<div class="stock-status-item"><div class="prod-badge"><span class="prod-emoji">${escapeHtml(i.emoji || '📦')}</span><span class="prod-name-lbl">${escapeHtml(i.name)}</span></div><div style="display:flex; gap:0.45rem; align-items:center; flex-wrap:wrap; justify-content:flex-end;"><span class="status-badge neutral" title="Ventes moyennes sur 7 jours">${velocity.toFixed(1)}/j</span><span class="stock-count-badge ${c}">${daysLeft}</span><span class="stock-count-badge ${c}">${stockLabel}</span></div></div>`;
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
        const data = await apiCall(`/api/stats/daily?days=${state.chartDays}`);
        const labels = data.map(d => d.day.slice(5));
        const revenues = data.map(d => d.revenue);
        const orders = data.map(d => d.orders);
        const chartColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#6366f1';
        const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.05)';
        const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#9f9baa';
        const opts = { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{ticks:{color:textColor,maxTicksLimit:10},grid:{color:gridColor}},y:{ticks:{color:textColor},grid:{color:gridColor}}} };
        if (state.revenueChart) {
            state.revenueChart.data.labels = labels;
            state.revenueChart.data.datasets[0].data = revenues;
            state.revenueChart.update('none');
        } else {
            state.revenueChart = new Chart(DOM.chartRevenue, { type:'line', data:{ labels, datasets:[{ data:revenues, borderColor:chartColor, backgroundColor:chartColor+'20', fill:true, tension:0.25, pointRadius:2 }] }, options:opts });
        }
        if (state.ordersChart) {
            state.ordersChart.data.labels = labels;
            state.ordersChart.data.datasets[0].data = orders;
            state.ordersChart.update('none');
        } else {
            state.ordersChart = new Chart(DOM.chartOrders, { type:'bar', data:{ labels, datasets:[{ data:orders, backgroundColor:chartColor+'60', borderColor:chartColor, borderWidth:1, borderRadius:4 }] }, options:opts });
        }
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
            if (p.delivery_type !== 'activation' && p.stock < 3) {
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

async function loadProductMomentum() {
    if (!DOM.chartProductMomentum) return;
    try {
        const data = await apiCall('/api/stats/products/momentum?days=30');
        state.productMomentum = data;
        const productsWithSales = (data.products || []).filter(p => (p.total_sold || 0) > 0);
        const validSelected = new Set(productsWithSales.map(p => p.id));
        state.productMomentumSelected = state.productMomentumSelected.filter(id => validSelected.has(id));
        if (state.productMomentumSelected.length === 0) {
            state.productMomentumSelected = productsWithSales.slice(0, 5).map(p => p.id);
        }
        renderProductMomentumControls();
        renderProductMomentumChart();
    } catch (e) {
        console.error("Failed to load product momentum:", e);
        try {
            state.productMomentum = await buildProductMomentumFromOrders(30);
            const productsWithSales = (state.productMomentum.products || []).filter(p => (p.total_sold || 0) > 0);
            state.productMomentumSelected = productsWithSales.slice(0, 5).map(p => p.id);
            renderProductMomentumControls();
            renderProductMomentumChart();
        } catch (fallbackError) {
            console.error("Product momentum fallback failed:", fallbackError);
            if (DOM.productMomentumControls) {
                DOM.productMomentumControls.innerHTML = '<span class="empty-state">Impossible de charger le momentum.</span>';
            }
        }
    }
}

async function buildProductMomentumFromOrders(days = 30) {
    const response = await apiCall(`/api/orders/all?status=COMPLETED&limit=200&offset=0`);
    const orders = response.orders || [];
    const today = new Date();
    const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
    start.setUTCDate(start.getUTCDate() - (days - 1));
    const dayLabels = Array.from({ length: days }, (_, i) => {
        const d = new Date(start);
        d.setUTCDate(start.getUTCDate() + i);
        return d.toISOString().slice(0, 10);
    });
    const yesterdayDate = new Date();
    yesterdayDate.setUTCDate(yesterdayDate.getUTCDate() - 1);
    const yesterday = yesterdayDate.toISOString().slice(0, 10);
    const dayIndex = new Map(dayLabels.map((day, idx) => [day, idx]));
    const products = new Map();

    orders.forEach(order => {
        if (order.status !== 'COMPLETED' || !order.product_id || !order.created_at) return;
        const day = parseUTCDate(order.created_at).toISOString().slice(0, 10);
        const idx = dayIndex.get(day);
        if (idx === undefined) return;

        const productId = Number(order.product_id);
        if (!products.has(productId)) {
            const prod = state.products.find(p => Number(p.id) === productId);
            products.set(productId, {
                id: productId,
                name: order.product_name || (prod ? prod.name : `Product #${productId}`),
                emoji: order.product_emoji || (prod ? prod.emoji : '📦'),
                series: Array(days).fill(0),
                revenue_series: Array(days).fill(0),
                total_sold: 0,
                total_revenue: 0,
                yesterday_sold: 0,
                yesterday_revenue: 0,
            });
        }

        const product = products.get(productId);
        const qty = Math.max(1, Number(order.quantity || 1));
        const revenue = Number(order.amount_usd || 0);
        product.series[idx] += qty;
        product.revenue_series[idx] += revenue;
        product.total_sold += qty;
        product.total_revenue += revenue;
        if (day === yesterday) {
            product.yesterday_sold += qty;
            product.yesterday_revenue += revenue;
        }
    });

    return {
        days: dayLabels,
        yesterday,
        products: [...products.values()].sort((a, b) => (b.total_sold - a.total_sold) || (b.total_revenue - a.total_revenue)),
    };
}

function renderProductMomentumControls() {
    if (!DOM.productMomentumControls || !state.productMomentum) return;
    const products = (state.productMomentum.products || []).filter(p => (p.total_sold || 0) > 0);
    if (products.length === 0) {
        DOM.productMomentumControls.innerHTML = '<span class="empty-state">Aucune vente produit sur la période.</span>';
        if (DOM.productMomentumYesterday) DOM.productMomentumYesterday.textContent = 'Hier: 0 vente';
        return;
    }

    const selected = new Set(state.productMomentumSelected);
    const yesterdayTotal = products.reduce((sum, p) => sum + (p.yesterday_sold || 0), 0);
    if (DOM.productMomentumYesterday) {
        DOM.productMomentumYesterday.textContent = `Hier: ${yesterdayTotal} vente${yesterdayTotal > 1 ? 's' : ''}`;
    }

    DOM.productMomentumControls.innerHTML = products.map(p => {
        const active = selected.has(p.id);
        const activeStyle = active
            ? 'background:rgba(99,102,241,0.18); border-color:var(--primary-color); color:var(--color-text-main);'
            : 'opacity:0.68;';
        return `
            <button type="button" class="btn-secondary btn-sm" style="${activeStyle}" onclick="toggleMomentumProduct(${p.id})" title="Afficher / masquer ${escapeHtml(p.name)}">
                ${escapeHtml(p.emoji || '📦')} ${escapeHtml(p.name)}
                <small style="display:block; color:var(--color-text-muted); margin-top:2px;">Hier: ${p.yesterday_sold || 0} · 30j: ${p.total_sold || 0}</small>
            </button>
        `;
    }).join('');
}

window.toggleMomentumProduct = function(productId) {
    const id = Number(productId);
    const selected = new Set(state.productMomentumSelected);
    if (selected.has(id)) {
        selected.delete(id);
    } else {
        selected.add(id);
    }
    state.productMomentumSelected = [...selected];
    renderProductMomentumControls();
    renderProductMomentumChart();
};

function renderProductMomentumChart() {
    if (!DOM.chartProductMomentum || !state.productMomentum) return;
    const rawDays = state.productMomentum.days || [];
    const selected = new Set(state.productMomentumSelected);
    const products = (state.productMomentum.products || []).filter(p => selected.has(p.id));
    let firstSaleIndex = rawDays.length > 0 ? rawDays.length - 1 : 0;
    let lastSaleIndex = 0;
    let hasVisibleSale = false;

    products.forEach(product => {
        (product.series || []).forEach((qty, idx) => {
            if ((qty || 0) > 0) {
                hasVisibleSale = true;
                firstSaleIndex = Math.min(firstSaleIndex, idx);
                lastSaleIndex = Math.max(lastSaleIndex, idx);
            }
        });
    });

    const startIndex = hasVisibleSale ? Math.max(0, firstSaleIndex - 1) : 0;
    const endIndex = hasVisibleSale ? Math.min(rawDays.length - 1, lastSaleIndex + 1) : rawDays.length - 1;
    const visibleDays = rawDays.slice(startIndex, endIndex + 1);
    const labels = visibleDays.map(d => d.slice(5));

    if (DOM.productMomentumRange) {
        DOM.productMomentumRange.textContent = hasVisibleSale && rawDays[startIndex] && rawDays[endIndex]
            ? `Vue: ${rawDays[startIndex].slice(5)} -> ${rawDays[endIndex].slice(5)}`
            : 'Vue: 30 jours';
    }

    const colors = ['#6366f1', '#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#ef4444', '#84cc16', '#06b6d4'];
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.05)';
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#9f9baa';

    const datasets = products.map((p, idx) => {
        const color = colors[idx % colors.length];
        return {
            label: `${p.emoji || '📦'} ${p.name}`,
            data: (p.series || []).slice(startIndex, endIndex + 1),
            borderColor: color,
            backgroundColor: color + '22',
            pointBackgroundColor: color,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2,
            tension: 0.32,
            fill: false,
        };
    });

    if (state.productMomentumChart) state.productMomentumChart.destroy();
    state.productMomentumChart = new Chart(DOM.chartProductMomentum, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: textColor, boxWidth: 12, padding: 14 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = products[context.datasetIndex];
                            const qty = context.raw || 0;
                            const sourceIndex = startIndex + context.dataIndex;
                            const revenue = p && p.revenue_series ? (p.revenue_series[sourceIndex] || 0) : 0;
                            return ` ${context.dataset.label}: ${qty} vente${qty > 1 ? 's' : ''} · $${revenue.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: textColor, maxTicksLimit: 12 }, grid: { color: gridColor } },
                y: { beginAtZero: true, ticks: { color: textColor, precision: 0 }, grid: { color: gridColor } }
            }
        }
    });
}

async function loadDeadProductAlerts() {
    if (!DOM.deadProductsAlerts) return;
    try {
        const data = await apiCall('/api/stats/products/dead-alerts?days=7&min_views=10&max_conversion=0.05');
        state.deadProductAlerts = data.alerts || [];
        renderDeadProductAlerts();
    } catch (e) {
        console.warn('Dead product alerts failed:', e);
        DOM.deadProductsAlerts.innerHTML = '<p class="empty-state">Impossible de charger les alertes produits.</p>';
    }
}

function renderDeadProductAlerts() {
    if (!DOM.deadProductsAlerts) return;
    const alerts = state.deadProductAlerts || [];
    if (alerts.length === 0) {
        DOM.deadProductsAlerts.innerHTML = '<p class="empty-state">Aucune alerte: pas encore assez de vues faibles en conversion.</p>';
        return;
    }

    DOM.deadProductsAlerts.innerHTML = alerts.map(item => {
        const conversion = Number(item.conversion || 0) * 100;
        return `
            <div class="stock-status-item">
                <div class="prod-badge">
                    <span class="prod-emoji">${escapeHtml(item.emoji || '📦')}</span>
                    <span class="prod-name-lbl">${escapeHtml(item.name || `Produit #${item.id}`)}</span>
                </div>
                <div style="display:flex; gap:0.45rem; align-items:center; flex-wrap:wrap; justify-content:flex-end;">
                    <span class="status-badge info">${item.views || 0} vues</span>
                    <span class="status-badge neutral">${item.sold || 0} ventes</span>
                    <span class="stock-count-badge low">${conversion.toFixed(1)}%</span>
                </div>
            </div>
        `;
    }).join('');
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
                <td><div class="prod-badge"><span class="prod-emoji">${escapeHtml(p.emoji || '📦')}</span><strong>${escapeHtml(p.name)}</strong></div></td>
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
            <td><div class="prod-badge"><span class="prod-emoji">${escapeHtml(p.emoji||'📦')}</span><strong>${escapeHtml(p.name)}</strong></div></td>
            <td><strong>$${parseFloat(p.price_usd).toFixed(2)}</strong>${p.dynamic_pricing_enabled ? `<span class="dynamic-price-badge" title="${p.dynamic_pricing_mode === 'suggestion' ? 'Mode suggestion' : 'Mode automatique'}"><i class="fa-solid fa-wave-square"></i> Dynamic</span>` : ''}</td><td>${p.warranty_days||0} ${t('days')}</td>
            <td>${p.delivery_type === 'activation' ? '<span class="stock-count-badge ok">Activation</span>' : `<span class="stock-count-badge ${p.stock===0?'empty':p.stock<3?'low':'ok'}">${p.stock}</span>`}</td>
            <td><span class="status-dot ${p.is_active?'online':''}"></span> ${p.is_active?t('active'):t('inactive')}</td>
            <td><button class="btn-table-action" onclick="toggleProductVisibility(${Number(p.id)})" title="${p.is_active ? 'Désactiver' : 'Activer'}" style="color:${p.is_active ? '#ef4444' : '#22c55e'};"><i class="fa-solid ${p.is_active ? 'fa-xmark' : 'fa-check'}"></i></button><button class="btn-table-action" onclick="openEditProduct(${Number(p.id)})" title="Modifier" style="color:#3b82f6;"><i class="fa-solid fa-pen"></i></button><button class="btn-table-action" onclick="viewProductStock(${Number(p.id)})" title="Voir stock" style="color:#f59e0b;"><i class="fa-solid fa-box-open"></i></button><button class="btn-table-action stock" onclick="openStockModal(${Number(p.id)})" title="${t('stock_manage')}"><i class="fa-solid fa-warehouse"></i></button><button class="btn-table-action" onclick="openTiersModal(${Number(p.id)})" title="Tarifs" style="color:#a78bfa;"><i class="fa-solid fa-tags"></i></button><button class="btn-table-action delete" onclick="deleteProduct(${Number(p.id)})" title="Supprimer"><i class="fa-solid fa-trash-can"></i></button></td>
        </tr>`).join('');
        if (DOM.broadcastBtnProductId) {
            DOM.broadcastBtnProductId.innerHTML = prods.map(p => `<option value="${Number(p.id)}">${escapeHtml(p.emoji||'📦')} ${escapeHtml(p.name)}</option>`).join('');
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
    const sp = state.orderFilter==='all' ? '' : `status=${state.orderFilter}&`;
    const r = await apiCall(`/api/orders/all?${sp}limit=20&offset=${state.orderPage*20}`);
    state.orders = r.orders; state.orderTotal = r.total;
    if (r.orders.length > 0) {
        DOM.ordersTableBody.innerHTML = r.orders.map(o => {
            const isTopup = o.status === 'TOPUP';
            const prod = !isTopup ? state.products.find(p=>p.id===o.product_id) : null;
            let pn = isTopup ? t('wallet_topup') : (prod ? `${prod.emoji || ''} ${prod.name}` : `#${o.product_id}`);
            if (!isTopup && !prod && o.product_name) {
                pn = `${o.product_emoji || '📦'} ${o.product_name}${o.product_is_deleted ? ' (Supprimé)' : ''}`;
            }
            const d = parseUTCDate(o.created_at).toLocaleDateString();
            pn = escapeHtml(pn);
            const uname = escapeHtml(o.username ? `@${o.username}` : (o.user_first_name || o.user_telegram_id));
            const orderNo = escapeHtml(o.merchant_trade_no || '—');
            // Payment method badge
            let payMethod = '—';
            if (isTopup) {
                payMethod = `<span class="pay-method-badge wallet">${t('pay_method_wallet')}</span>`;
            } else if (o.payment_method === 'wallet') {
                payMethod = `<span class="pay-method-badge wallet">${t('pay_method_wallet')}</span>`;
            } else if (o.payment_method === 'binance' || o.payment_method == null) {
                payMethod = `<span class="pay-method-badge binance">${t('pay_method_binance')}</span>`;
            } else {
                payMethod = `<span class="pay-method-badge">${escapeHtml(o.payment_method)}</span>`;
            }
            let actions = '';
            if (isTopup) {
                actions = `<span style="font-size:0.78rem;color:var(--color-text-muted);">Balance: $${parseFloat(o.balance_after||0).toFixed(2)}</span>`;
            } else if (o.status === 'PENDING' || o.status === 'AWAITING_PAYMENT') {
                actions = `<button class="btn-table-action" onclick="confirmOrderPayment(${o.id})" title="Confirmer" style="color:#22c55e;"><i class="fa-solid fa-check"></i></button> <button class="btn-table-action" onclick="cancelOrder(${o.id})" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`;
            } else if (o.status === 'PAID_PENDING_DELIVERY') {
                actions = `<button class="btn-table-action" onclick="confirmOrderPayment(${o.id})" title="Relancer la livraison" style="color:#22c55e;"><i class="fa-solid fa-rotate-right"></i></button>`;
            } else if (o.status === 'AWAITING_ACTIVATION') {
                actions = `<button class="btn-table-action" onclick="completeActivation(${o.id})" title="${t('activation_mark_done')}" style="color:#22c55e;"><i class="fa-solid fa-bolt"></i></button>`;
            } else if (o.status === 'AWAITING_ACTIVATION_INFO') {
                actions = '—';
            } else if (o.status === 'COMPLETED') {
                actions = `<button class="btn-table-action" onclick="openOrderDetail(${o.id})" title="Voir les articles livrés" style="color:#22c55e;"><i class="fa-solid fa-eye"></i></button>`;
            } else {
                actions = '—';
            }
            let statusHtml = escapeHtml(o.status);
            if (o.status === 'PAID_PENDING_DELIVERY') statusHtml = 'PAYÉ — LIVRAISON EN ATTENTE';
            if (!isTopup && o.activation_identifier) {
                statusHtml += `<br><span style="font-size:0.72rem; color:var(--color-text-muted); display:block; margin-top:4px;">ID: ${escapeHtml(o.activation_identifier)}</span>`;
            }
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
                    statusHtml += `<span style="font-size:0.7rem; color:var(--color-error); font-weight:bold; display:block; margin-top:2px;">⚠️ ID Invalide</span>`;
                }
            }

            const rawBId = String(o.binance_order_id || '—');
            let displayBId = escapeHtml(rawBId);
            if (displayBId.length > 15 && displayBId !== '—') {
                displayBId = `<span title="${escapeHtml(rawBId)}" style="cursor:help; border-bottom: 1px dotted rgba(255,255,255,0.5);">${escapeHtml(rawBId.substring(0, 3))}...${escapeHtml(rawBId.substring(rawBId.length - 4))}</span>`;
            }

            return `<tr><td><strong>#${Number(o.id)}</strong></td><td><code>${orderNo}</code></td><td><code>${displayBId}</code></td><td>${uname}</td><td>${pn}</td><td>$${parseFloat(o.amount_usd).toFixed(2)}</td><td>${isTopup ? '—' : Number(o.quantity||1)}</td><td>${payMethod}</td><td><div class="status-badge ${escapeHtml(String(o.status || '').toLowerCase())}">${statusHtml}</div></td><td>${escapeHtml(d)}</td><td>${actions}</td></tr>`;
        }).join('');
    } else DOM.ordersTableBody.innerHTML = `<tr><td colspan="11" class="empty-state" data-i18n="no_orders">Aucune commande.</td></tr>`;
    const tp = Math.max(1, Math.ceil(r.total/20));
    DOM.ordersPageInfo.textContent = `${state.orderPage+1} / ${tp}`;
    DOM.ordersPagination.classList.toggle('hidden', tp <= 1);
}

async function loadActivations() {
    const r = await apiCall('/api/orders/activations?limit=100&offset=0');
    state.activations = r.orders || [];

    if (DOM.badgeActivations) {
        if (state.activations.length > 0) {
            DOM.badgeActivations.textContent = state.activations.length;
            DOM.badgeActivations.classList.remove('hidden');
        } else {
            DOM.badgeActivations.classList.add('hidden');
        }
    }

    if (!DOM.activationsTableBody) return;
    if (state.activations.length === 0) {
        DOM.activationsTableBody.innerHTML = `<tr><td colspan="9" class="empty-state">${t('no_activations')}</td></tr>`;
        return;
    }

    DOM.activationsTableBody.innerHTML = state.activations.map(o => {
        const prod = state.products.find(p => p.id === o.product_id);
        let pn = prod ? `${prod.emoji || '📦'} ${escapeHtml(prod.name)}` : `#${o.product_id}`;
        if (!prod && o.product_name) pn = `${o.product_emoji || '📦'} ${escapeHtml(o.product_name)}`;
        const uname = o.username ? `@${escapeHtml(o.username)}` : escapeHtml(o.user_first_name || o.user_telegram_id);
        const identifier = o.activation_identifier ? `<code>${escapeHtml(o.activation_identifier)}</code>` : `<span style="color:var(--color-text-muted);">${t('activation_waiting_client')}</span>`;
        const d = parseUTCDate(o.created_at).toLocaleDateString();
        const statusLabel = o.status === 'AWAITING_ACTIVATION' ? t('activation_ready') : t('activation_waiting_id');
        const actions = o.status === 'AWAITING_ACTIVATION'
            ? `<button class="btn-table-action" onclick="completeActivation(${o.id})" title="${t('activation_mark_done')}" style="color:#22c55e;"><i class="fa-solid fa-bolt"></i></button> <button class="btn-table-action" onclick="cancelOrder(${o.id})" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`
            : `<button class="btn-table-action" onclick="cancelOrder(${o.id})" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`;

        return `<tr>
            <td><strong>#${o.id}</strong></td>
            <td>${uname}</td>
            <td><code>${escapeHtml(o.user_telegram_id)}</code></td>
            <td>${pn}</td>
            <td>${identifier}</td>
            <td>$${parseFloat(o.amount_usd || 0).toFixed(2)}</td>
            <td><div class="status-badge ${o.status.toLowerCase()}">${statusLabel}</div></td>
            <td>${d}</td>
            <td>${actions}</td>
        </tr>`;
    }).join('');
}

async function loadResellers() {
    if (!DOM.resellersTableBody) return;
    const r = await apiCall('/api/resellers');
    state.resellers = r.resellers || [];
    if (state.resellers.length === 0) {
        DOM.resellersTableBody.innerHTML = `<tr><td colspan="10" class="empty-state">${t('no_resellers')}</td></tr>`;
        return;
    }
    DOM.resellersTableBody.innerHTML = state.resellers.map(k => {
        const client = k.username ? `@${escapeHtml(k.username)}` : escapeHtml(k.first_name || k.user_telegram_id);
        const active = Number(k.is_active) === 1;
        const status = active ? `<span class="status-badge completed">${t('active')}</span>` : `<span class="status-badge cancelled">${t('inactive')}</span>`;
        const created = k.created_at ? parseUTCDate(k.created_at).toLocaleDateString() : '';
        const action = active
            ? `<button class="btn-table-action delete" onclick="revokeResellerKey(${k.id})" title="${t('reseller_revoke')}"><i class="fa-solid fa-ban"></i></button>`
            : '—';
        return `<tr>
            <td><strong>#${k.id}</strong></td>
            <td>${client}<br><code>${k.user_telegram_id}</code></td>
            <td>${escapeHtml(k.name || '')}</td>
            <td><code>${escapeHtml(k.key_prefix || '')}</code></td>
            <td>$${parseFloat(k.wallet_balance || 0).toFixed(2)}</td>
            <td>${k.order_count || 0}</td>
            <td>$${parseFloat(k.total_spent || 0).toFixed(2)}</td>
            <td>${status}</td>
            <td>${created}</td>
            <td>${action}</td>
        </tr>`;
    }).join('');
}

async function createResellerKey() {
    const userId = DOM.resellerUserId ? DOM.resellerUserId.value.trim() : '';
    const name = DOM.resellerKeyName ? DOM.resellerKeyName.value.trim() : '';
    if (!userId) { alert(t('reseller_user_id')); return; }
    showLoading(true);
    try {
        const r = await apiCall('/api/resellers/keys', 'POST', { user_telegram_id: userId, name });
        if (DOM.resellerNewKey && DOM.resellerKeyOutput) {
            DOM.resellerNewKey.textContent = r.key.api_key;
            DOM.resellerKeyOutput.classList.remove('hidden');
        }
        if (DOM.resellerKeyName) DOM.resellerKeyName.value = '';
        await loadResellers();
    } catch(e) {
        alert(e.message);
    } finally {
        showLoading(false);
    }
}

window.revokeResellerKey = async function(id) {
    if (!confirm(t('reseller_revoke') + ` #${id} ?`)) return;
    showLoading(true);
    try {
        await apiCall(`/api/resellers/keys/${id}`, 'DELETE');
        await loadResellers();
    } catch(e) {
        alert(e.message);
    } finally {
        showLoading(false);
    }
};

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
            const uname = escapeHtml(tx.username ? `@${tx.username}` : (tx.user_first_name || tx.user_telegram_id));
            const d = tx.created_at ? parseUTCDate(tx.created_at).toLocaleString() : '—';
            const isTopup = tx.type === 'topup';
            const typeLabel = isTopup
                ? `<span class="status-badge completed" style="background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.3);">➕ Recharge</span>`
                : `<span class="status-badge" style="background:rgba(99,102,241,0.15);color:#818cf8;border:1px solid rgba(99,102,241,0.3);">🛒 Achat</span>`;
            const amountColor = isTopup ? '#22c55e' : '#ef4444';
            const amountSign = isTopup ? '+' : '-';
            const desc = escapeHtml(tx.description || '—');
            const balAfter = parseFloat(tx.balance_after||0).toFixed(2);
            return `<tr>
                <td><strong>#${Number(tx.id)}</strong></td>
                <td>${uname}</td>
                <td>${typeLabel}</td>
                <td style="color:${amountColor};font-weight:600;">${amountSign}$${parseFloat(tx.amount||0).toFixed(2)}</td>
                <td>💰 $${balAfter}</td>
                <td style="font-size:0.82rem;color:var(--color-text-muted);">${desc}</td>
                <td style="font-size:0.82rem;">${escapeHtml(d)}</td>
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
        DOM.openTicketsContainer.innerHTML = tks.map(tk => `<div class="ticket-card glass-panel"><div class="ticket-header"><h3>Ticket #${Number(tk.id)}</h3><p><i class="fa-solid fa-user"></i> <code>${escapeHtml(tk.user_telegram_id)}</code></p></div><div class="ticket-message"><p>${escapeHtml(tk.message)}</p></div><form class="ticket-reply-form" onsubmit="submitTicketReply(event,${Number(tk.id)})"><div class="form-group"><input type="text" placeholder="${escapeHtml(t('reply_placeholder'))}" required></div><button type="submit" class="btn-primary btn-send-reply" title="Répondre"><i class="fa-solid fa-paper-plane"></i></button></form></div>`).join('');
    } else { DOM.badgeTickets.classList.add('hidden'); DOM.openTicketsContainer.innerHTML = `<p class="empty-state">${t('no_tickets')}</p>`; }
}

async function loadUsers() {
    try {
        const limit = state.usersPerPage || 20;
        const offset = (state.usersPage || 0) * limit;
        const search = encodeURIComponent(state.usersSearch || '');
        const sort = state.usersSort || 'joined';
        const order = state.usersOrder || 'desc';
        const r = await apiCall(`/api/users?limit=${limit}&offset=${offset}&search=${search}&sort=${sort}&order=${order}`);
        state.users = r.users;
        state.usersTotal = r.total;
        
        if (r.users.length > 0) {
            DOM.usersTableBody.innerHTML = r.users.map(u => {
                const banned = u.is_banned;
                const d = u.created_at ? parseUTCDate(u.created_at).toLocaleDateString() : '—';
                const wb = parseFloat(u.wallet_balance||0).toFixed(2);
                const refBy = u.referred_by ? `<code>${escapeHtml(u.referred_by)}</code>` : '—';
                const refCount = u.referrals_count > 0 ? `${Number(u.referrals_count)} <button class="btn-table-action" onclick="viewUserReferrals(${Number(u.telegram_id)})" title="Voir les filleuls" style="margin-left:5px;color:#3b82f6;"><i class="fa-solid fa-users"></i></button>` : 0;
                const refEarnings = parseFloat(u.referral_earnings||0).toFixed(2);
                return `<tr><td><code>${escapeHtml(u.telegram_id)}</code></td><td>${escapeHtml(u.username||'—')}</td><td>${escapeHtml(u.first_name||'—')}</td><td>${escapeHtml(u.language||'fr')}</td><td>${Number(u.total_orders||0)}</td><td>$${parseFloat(u.total_spent||0).toFixed(2)}</td><td>$${wb}</td><td>${refBy}</td><td>${refCount}</td><td>$${refEarnings}</td><td>${escapeHtml(d)}</td><td><button class="btn-table-action" onclick="creditWallet(${Number(u.telegram_id)})" title="Créditer" style="color:#22c55e;"><i class="fa-solid fa-circle-plus"></i></button> <button class="btn-table-action" onclick="debitWallet(${Number(u.telegram_id)})" title="Retirer" style="color:#ef4444;"><i class="fa-solid fa-circle-minus"></i></button> ${banned?`<span class="status-badge banned">${t('banned')}</span> <button class="btn-table-action unban" onclick="unbanUser(${Number(u.telegram_id)})"><i class="fa-solid fa-lock-open"></i></button>`:`<button class="btn-table-action ban" onclick="banUser(${Number(u.telegram_id)})"><i class="fa-solid fa-ban"></i></button>`}</td></tr>`;
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
        updateUsersSortIcons();
    } catch(e) { console.warn('loadUsers:', e); }
}

function sortUsers(field) {
    if (state.usersSort === field) {
        state.usersOrder = state.usersOrder === 'asc' ? 'desc' : 'asc';
    } else {
        state.usersSort = field;
        state.usersOrder = 'desc';
    }
    state.usersPage = 0;
    loadUsers();
}

function updateUsersSortIcons() {
    const fields = ['telegram_id', 'username', 'orders', 'spent', 'wallet', 'referrals', 'referral_earnings', 'joined'];
    fields.forEach(f => {
        const icon = document.getElementById(`sort-${f}`);
        if (icon) {
            if (state.usersSort === f) {
                icon.innerHTML = state.usersOrder === 'asc' ? '<i class="fa-solid fa-sort-up"></i>' : '<i class="fa-solid fa-sort-down"></i>';
            } else {
                icon.innerHTML = '<i class="fa-solid fa-sort" style="opacity: 0.3;"></i>';
            }
        }
    });
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

async function runDashboardAction(action, successMessage) {
    showLoading(true);
    try {
        await action();
        await refreshData({silent:true});
        if (successMessage) showToast(successMessage, 'success');
        return true;
    } catch (error) {
        showToast(error.message || 'Opération impossible.', 'error');
        return false;
    } finally {
        showLoading(false);
    }
}

window.toggleProductVisibility = id => runDashboardAction(
    () => apiCall(`/api/products/${id}/toggle-active`, 'POST'),
    'Visibilité du produit mise à jour.'
);
window.deleteProduct = async function(id) {
    if (confirm(t('confirm_delete'))) await runDashboardAction(() => apiCall(`/api/products/${id}`, 'DELETE'), 'Produit supprimé.');
};
window.deletePromo = id => runDashboardAction(() => apiCall(`/api/promos/${id}`, 'DELETE'), 'Code promo supprimé.');
window.confirmOrderPayment = async function(id) {
    if (confirm(`${t('confirm_order')}${id}?`)) await runDashboardAction(() => apiCall(`/api/orders/${id}/confirm`, 'POST'), `Commande #${id} confirmée.`);
};
window.completeActivation = async function(id) {
    if (confirm(t('activation_confirm_prompt').replace('{id}', id))) await runDashboardAction(() => apiCall(`/api/orders/${id}/activate`, 'POST'), `Activation #${id} terminée.`);
};
window.cancelOrder = async function(id) {
    if (confirm(`Annuler la commande #${id} ?`)) await runDashboardAction(() => apiCall(`/api/orders/${id}/cancel`, 'POST'), `Commande #${id} annulée.`);
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  PRICE TIERS MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
let _tiersProductId = null;

window.openTiersModal = async function(productId) {
    const product = state.products.find(item => Number(item.id) === Number(productId));
    if (!product) return showToast('Produit introuvable.', 'error');
    const productName = product.name;
    const basePrice = Number(product.price_usd || 0);
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
        $('order-detail-info').innerHTML = `<p style="color:var(--color-error);">Erreur: ${escapeHtml(e.message)}</p>`;
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  VIEW REMAINING STOCK MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.viewProductStock = async function(productId) {
    const product = state.products.find(item => Number(item.id) === Number(productId));
    if (!product) return showToast('Produit introuvable.', 'error');
    const emoji = product.emoji || '📦';
    const name = product.name;
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
                const safeData = escapeHtml(it.account_data || '');
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
        $('view-stock-list').innerHTML = `<p style="color:var(--color-error);">Erreur: ${escapeHtml(e.message)}</p>`;
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  EDIT PRODUCT MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
window.openEditProduct = function(productId) {
    const p = state.products.find(pr => pr.id === productId);
    if (!p) return;
    const dynamicExplanation = $('edit-prod-dynamic-explanation');
    if (dynamicExplanation) dynamicExplanation.textContent = 'Calculez une recommandation pour afficher les facteurs de décision.';
    const simulationPanel = $('edit-prod-dynamic-simulation');
    if (simulationPanel) simulationPanel.classList.add('hidden');
    if (state.dynamicSimulationChart) {
        state.dynamicSimulationChart.destroy();
        state.dynamicSimulationChart = null;
    }
    $('edit-prod-id').value = p.id;
    $('edit-prod-emoji').value = p.emoji || '📦';
    $('edit-prod-name').value = p.name;
    $('edit-prod-price').value = parseFloat(p.price_usd).toFixed(2);
    setDynamicPricingForm('edit-prod', p);
    loadDynamicPricingHistory(p.id);
    $('edit-prod-warranty').value = p.warranty_days || 0;
    $('edit-prod-desc').value = p.description || '';
    if ($('edit-prod-desc-fr')) $('edit-prod-desc-fr').value = p.description_fr || '';
    if ($('edit-prod-desc-ar')) $('edit-prod-desc-ar').value = p.description_ar || '';
    if ($('edit-prod-desc-zh')) $('edit-prod-desc-zh').value = p.description_zh || '';
    if ($('edit-prod-desc-vi')) $('edit-prod-desc-vi').value = p.description_vi || '';
    if ($('edit-prod-desc-ru')) $('edit-prod-desc-ru').value = p.description_ru || '';
    if ($('edit-prod-image-url')) $('edit-prod-image-url').value = p.image_url || '';
    if ($('edit-prod-custom-emoji-id')) $('edit-prod-custom-emoji-id').value = p.custom_emoji_id || '';
    if ($('edit-prod-delivery-type')) $('edit-prod-delivery-type').value = p.delivery_type || 'stock';
    toggleActivationFields('edit');

    if ($('edit-prod-act-msg')) $('edit-prod-act-msg').value = p.activation_message || '';
    if ($('edit-prod-act-msg-fr')) $('edit-prod-act-msg-fr').value = p.activation_message_fr || '';
    if ($('edit-prod-act-msg-ar')) $('edit-prod-act-msg-ar').value = p.activation_message_ar || '';
    if ($('edit-prod-act-msg-zh')) $('edit-prod-act-msg-zh').value = p.activation_message_zh || '';
    if ($('edit-prod-act-msg-vi')) $('edit-prod-act-msg-vi').value = p.activation_message_vi || '';
    if ($('edit-prod-act-msg-ru')) $('edit-prod-act-msg-ru').value = p.activation_message_ru || '';

    if ($('edit-prod-conf-msg')) $('edit-prod-conf-msg').value = p.confirmation_message || '';
    if ($('edit-prod-conf-msg-fr')) $('edit-prod-conf-msg-fr').value = p.confirmation_message_fr || '';
    if ($('edit-prod-conf-msg-ar')) $('edit-prod-conf-msg-ar').value = p.confirmation_message_ar || '';
    if ($('edit-prod-conf-msg-zh')) $('edit-prod-conf-msg-zh').value = p.confirmation_message_zh || '';
    if ($('edit-prod-conf-msg-vi')) $('edit-prod-conf-msg-vi').value = p.confirmation_message_vi || '';
    if ($('edit-prod-conf-msg-ru')) $('edit-prod-conf-msg-ru').value = p.confirmation_message_ru || '';

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
        description_fr: $('edit-prod-desc-fr') ? $('edit-prod-desc-fr').value.trim() : '',
        description_ar: $('edit-prod-desc-ar') ? $('edit-prod-desc-ar').value.trim() : '',
        description_zh: $('edit-prod-desc-zh') ? $('edit-prod-desc-zh').value.trim() : '',
        description_vi: $('edit-prod-desc-vi') ? $('edit-prod-desc-vi').value.trim() : '',
        description_ru: $('edit-prod-desc-ru') ? $('edit-prod-desc-ru').value.trim() : '',
        image_url: $('edit-prod-image-url') && $('edit-prod-image-url').value.trim() ? $('edit-prod-image-url').value.trim() : null,
        delivery_type: $('edit-prod-delivery-type') ? $('edit-prod-delivery-type').value : 'stock',
        activation_message: $('edit-prod-act-msg') ? $('edit-prod-act-msg').value.trim() : '',
        activation_message_fr: $('edit-prod-act-msg-fr') ? $('edit-prod-act-msg-fr').value.trim() : '',
        activation_message_ar: $('edit-prod-act-msg-ar') ? $('edit-prod-act-msg-ar').value.trim() : '',
        activation_message_zh: $('edit-prod-act-msg-zh') ? $('edit-prod-act-msg-zh').value.trim() : '',
        activation_message_vi: $('edit-prod-act-msg-vi') ? $('edit-prod-act-msg-vi').value.trim() : '',
        activation_message_ru: $('edit-prod-act-msg-ru') ? $('edit-prod-act-msg-ru').value.trim() : '',
        confirmation_message: $('edit-prod-conf-msg') ? $('edit-prod-conf-msg').value.trim() : '',
        confirmation_message_fr: $('edit-prod-conf-msg-fr') ? $('edit-prod-conf-msg-fr').value.trim() : '',
        confirmation_message_ar: $('edit-prod-conf-msg-ar') ? $('edit-prod-conf-msg-ar').value.trim() : '',
        confirmation_message_zh: $('edit-prod-conf-msg-zh') ? $('edit-prod-conf-msg-zh').value.trim() : '',
        confirmation_message_vi: $('edit-prod-conf-msg-vi') ? $('edit-prod-conf-msg-vi').value.trim() : '',
        confirmation_message_ru: $('edit-prod-conf-msg-ru') ? $('edit-prod-conf-msg-ru').value.trim() : ''
    };
    try {
        Object.assign(data, collectDynamicPricing('edit-prod'));
    } catch (error) {
        showToast(error.message, 'error');
        return;
    }
    if (!data.name || isNaN(data.price_usd) || data.price_usd < 0) {
        alert('Vérifiez le nom et le prix.'); return;
    }
    showLoading(true);
    try {
        await apiCall(`/api/products/${id}`, 'PUT', data);
        hideModal(DOM.editProdModal);
        showToast('Produit enregistré.', 'success');
        try {
            await refreshData();
        } catch (refreshError) {
            console.warn('Product saved; dashboard refresh deferred.', refreshError);
            showToast('Produit enregistré. Actualisation temporairement indisponible.', 'info');
        }
    } catch(err) { alert(err.message); }
    finally { showLoading(false); }
});

window.submitTicketReply = async function(event, id) {
    event.preventDefault();
    const input = event.target.querySelector('input');
    const sent = await runDashboardAction(
        () => apiCall(`/api/tickets/${id}/reply`, 'POST', {reply_text:input.value.trim()}),
        `Réponse envoyée pour le ticket #${id}.`
    );
    if (sent) input.value = '';
};
window.viewUserReferrals = function(tid) {
    if(DOM.usersSearch) {
        DOM.usersSearch.value = tid;
        state.usersSearch = tid.toString();
        state.usersPage = 0;
        loadUsers();
    }
};

window.recalculateStats = async function() {
    if (!confirm('Voulez-vous recalculer les statistiques de tous les utilisateurs (Commandes et Dépenses) ? Cela peut prendre quelques secondes.')) return;
    showLoading(true);
    try {
        const res = await apiCall('/api/recalculate-stats');
        alert(res.message || 'Statistiques recalculées avec succès.');
        if (state.currentTab === 'tab_users') {
            await loadUsers();
        }
    } catch (err) {
        alert(err.message);
    } finally {
        showLoading(false);
    }
};

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
window.openStockModal = async function(pid) {
    const product = state.products.find(item => Number(item.id) === Number(pid));
    if (!product) return showToast('Produit introuvable.', 'error');
    const emoji = product.emoji || '📦';
    const name = product.name;
    state.currentStockProductId = pid;
    DOM.stockModalTitle.textContent = `${emoji} ${name} — ${t('stock_manage')}`;
    DOM.stockTextarea.value = ''; DOM.stockLineCount.textContent = `0 ${t('accounts_detected')}`;
    showModal(DOM.stockModal);
    try {
        const items = await apiCall(`/api/products/${pid}/stock`);
        DOM.stockExistingCount.textContent = items.filter(i=>!i.is_sold).length;
        if (items.length > 0) DOM.stockItemsList.innerHTML = items.map(i => {
            const safeData = escapeHtml(i.account_data || '');
            return `<div class="stock-item-row">
            <span class="stock-item-data">${safeData}</span>
            <span class="stock-item-status ${i.is_sold?'sold':'available'}">${i.is_sold?t('sold'):t('available')}</span>
            ${!i.is_sold ? `<button class="btn-table-action delete" onclick="deleteStockItem(${i.id})" title="Supprimer"><i class="fa-solid fa-trash-can"></i></button>` : ''}
        </div>`;
        }).join('');
        else DOM.stockItemsList.innerHTML = `<p class="empty-state">${t('no_stock')}</p>`;
    } catch(e) { DOM.stockItemsList.innerHTML = `<p class="empty-state">Error: ${escapeHtml(e.message)}</p>`; }
};

window.deleteStockItem = async function(stockId) {
    if (!confirm('Supprimer cet article du stock ?')) return;
    showLoading(true);
    try {
        await apiCall(`/api/stock/${stockId}`, 'DELETE');
        await openStockModal(state.currentStockProductId);
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
        await openStockModal(state.currentStockProductId);
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
    } catch(e) { DOM.broadcastResult.textContent = `❌ ${e.message}`; }
    finally { showLoading(false); }
}

// Settings
function handleSaveSettings(e) {
    e.preventDefault();
    state.apiKey = DOM.settingsApiKey.value.trim();
    state.botUrl = resolveBotUrl(DOM.settingsBotUrl.value);
    testConnectionAndStart();
}

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

const tabKeys = { 'dashboard-tab':'tab_dashboard','stats-tab':'tab_stats','inventory-tab':'tab_inventory','orders-tab':'tab_orders','activations-tab':'nav_activations','resellers-tab':'nav_resellers','users-tab':'tab_users','tickets-tab':'tab_tickets','broadcast-tab':'tab_broadcast','settings-tab':'tab_settings','wallet-history-tab':'nav_wallet_history','finance-tab':'tab_finance','binance-tab':'tab_binance' };
const tabContexts = {
    'dashboard-tab':'Vue opérationnelle', 'stats-tab':'Tendances de ventes et produits',
    'inventory-tab':'Produits, prix et disponibilité', 'orders-tab':'Paiements et livraisons',
    'activations-tab':'Demandes manuelles à traiter', 'resellers-tab':'Accès et activité API',
    'users-tab':'Clients, wallets et parrainages', 'tickets-tab':'Demandes de support ouvertes',
    'broadcast-tab':'Communication aux clients', 'settings-tab':'Connexion et paiements',
    'wallet-history-tab':'Mouvements des soldes clients', 'finance-tab':'Revenus et ajustements',
    'binance-tab':'Comptes de réception'
};

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
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
    if (DOM.pageContext) DOM.pageContext.textContent = tabContexts[tabId] || '';
    state.currentTab = tabId;
    if (!DOM.appContainer.classList.contains('hidden')) refreshData();
}

function showModal(m) {
    if (!m) return;
    state.modalReturnFocus = document.activeElement;
    m.classList.remove('hidden');
    const focusTarget = m.querySelector('input:not([type="hidden"]), textarea, select, button');
    if (focusTarget) requestAnimationFrame(() => focusTarget.focus());
}
function hideModal(m) {
    if (!m) return;
    m.classList.add('hidden');
    if (state.modalReturnFocus?.focus) state.modalReturnFocus.focus();
    state.modalReturnFocus = null;
}
function showLoading(v) { if(v)DOM.loadingOverlay.classList.remove('hidden');else DOM.loadingOverlay.classList.add('hidden'); }
function showToast(message, type='info') {
    if (!DOM.toastRegion) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    const icon = type === 'success' ? 'circle-check' : type === 'error' ? 'triangle-exclamation' : 'circle-info';
    toast.innerHTML = `<i class="fa-solid fa-${icon}"></i><p>${escapeHtml(message)}</p><button type="button" title="Fermer" aria-label="Fermer"><i class="fa-solid fa-xmark"></i></button>`;
    toast.querySelector('button').addEventListener('click', () => toast.remove());
    DOM.toastRegion.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}
function logout() {
    state.botUrl=''; state.apiKey='';
    localStorage.removeItem('ventebot_url'); localStorage.removeItem('ventebot_key');
    DOM.loginForm.reset(); showScreen('login'); stopAutoRefresh();
}

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
    DOM.binanceApiKey.placeholder = '';
    DOM.binanceApiSecret.placeholder = '';
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
            if (!payload.api_key) delete payload.api_key;
            if (!payload.api_secret) delete payload.api_secret;
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
    DOM.binanceApiKey.value = '';
    DOM.binanceApiSecret.value = '';
    DOM.binanceApiKey.placeholder = acc.has_api_key ? 'Configurée — laisser vide pour conserver' : '';
    DOM.binanceApiSecret.placeholder = acc.has_api_secret ? 'Configuré — laisser vide pour conserver' : '';
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
    setDynamicPricingForm('prod', p);
    DOM.prodWarranty.value = p.warranty_days || 0;
    DOM.prodEmoji.value = p.emoji;
    if (DOM.prodDesc) DOM.prodDesc.value = p.description || '';
    if ($('prod-desc-fr')) $('prod-desc-fr').value = p.description_fr || '';
    if ($('prod-desc-ar')) $('prod-desc-ar').value = p.description_ar || '';
    if ($('prod-desc-zh')) $('prod-desc-zh').value = p.description_zh || '';
    if ($('prod-desc-vi')) $('prod-desc-vi').value = p.description_vi || '';
    if ($('prod-desc-ru')) $('prod-desc-ru').value = p.description_ru || '';
    if (DOM.prodImageUrl) DOM.prodImageUrl.value = p.image_url || '';
    if (DOM.prodBinanceAccount) DOM.prodBinanceAccount.value = p.binance_account_id || '';
    if (DOM.prodDeliveryType) DOM.prodDeliveryType.value = p.delivery_type || 'stock';
    if ($('prod-act-msg')) $('prod-act-msg').value = p.activation_message || '';
    if ($('prod-act-msg-fr')) $('prod-act-msg-fr').value = p.activation_message_fr || '';
    if ($('prod-act-msg-ar')) $('prod-act-msg-ar').value = p.activation_message_ar || '';
    if ($('prod-act-msg-zh')) $('prod-act-msg-zh').value = p.activation_message_zh || '';
    if ($('prod-act-msg-vi')) $('prod-act-msg-vi').value = p.activation_message_vi || '';
    if ($('prod-act-msg-ru')) $('prod-act-msg-ru').value = p.activation_message_ru || '';
    if ($('prod-conf-msg')) $('prod-conf-msg').value = p.confirmation_message || '';
    if ($('prod-conf-msg-fr')) $('prod-conf-msg-fr').value = p.confirmation_message_fr || '';
    if ($('prod-conf-msg-ar')) $('prod-conf-msg-ar').value = p.confirmation_message_ar || '';
    if ($('prod-conf-msg-zh')) $('prod-conf-msg-zh').value = p.confirmation_message_zh || '';
    if ($('prod-conf-msg-vi')) $('prod-conf-msg-vi').value = p.confirmation_message_vi || '';
    if ($('prod-conf-msg-ru')) $('prod-conf-msg-ru').value = p.confirmation_message_ru || '';
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
        description_fr: $('prod-desc-fr') ? $('prod-desc-fr').value.trim() : '',
        description_ar: $('prod-desc-ar') ? $('prod-desc-ar').value.trim() : '',
        description_zh: $('prod-desc-zh') ? $('prod-desc-zh').value.trim() : '',
        description_vi: $('prod-desc-vi') ? $('prod-desc-vi').value.trim() : '',
        description_ru: $('prod-desc-ru') ? $('prod-desc-ru').value.trim() : '',
        image_url: DOM.prodImageUrl && DOM.prodImageUrl.value.trim() ? DOM.prodImageUrl.value.trim() : null,
        binance_account_id: DOM.prodBinanceAccount && DOM.prodBinanceAccount.value ? parseInt(DOM.prodBinanceAccount.value) : null,
        delivery_type: DOM.prodDeliveryType ? DOM.prodDeliveryType.value : 'stock',
        activation_message: $('prod-act-msg') ? $('prod-act-msg').value.trim() : '',
        activation_message_fr: $('prod-act-msg-fr') ? $('prod-act-msg-fr').value.trim() : '',
        activation_message_ar: $('prod-act-msg-ar') ? $('prod-act-msg-ar').value.trim() : '',
        activation_message_zh: $('prod-act-msg-zh') ? $('prod-act-msg-zh').value.trim() : '',
        activation_message_vi: $('prod-act-msg-vi') ? $('prod-act-msg-vi').value.trim() : '',
        activation_message_ru: $('prod-act-msg-ru') ? $('prod-act-msg-ru').value.trim() : '',
        confirmation_message: $('prod-conf-msg') ? $('prod-conf-msg').value.trim() : '',
        confirmation_message_fr: $('prod-conf-msg-fr') ? $('prod-conf-msg-fr').value.trim() : '',
        confirmation_message_ar: $('prod-conf-msg-ar') ? $('prod-conf-msg-ar').value.trim() : '',
        confirmation_message_zh: $('prod-conf-msg-zh') ? $('prod-conf-msg-zh').value.trim() : '',
        confirmation_message_vi: $('prod-conf-msg-vi') ? $('prod-conf-msg-vi').value.trim() : '',
        confirmation_message_ru: $('prod-conf-msg-ru') ? $('prod-conf-msg-ru').value.trim() : ''
    };
    try {
        Object.assign(payload, collectDynamicPricing('prod'));
    } catch (error) {
        showLoading(false);
        showToast(error.message, 'error');
        return;
    }
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
