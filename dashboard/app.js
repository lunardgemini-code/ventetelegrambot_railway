
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

// dashboard/app.js — BatmanBot V2 Admin Dashboard with all features

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
Object.assign(LANG.ar, {
    login_url_hint:'اتركه فارغًا إذا كنت على لوحة تحكم البوت، وإلا ألصق رابط Railway', admin_title:'المسؤول', btn_logout:'تسجيل الخروج',
    sub_products:'المنتجات', sub_categories:'الفئات', sub_promos:'رموز الخصم', all_products:'كل المنتجات', th_product:'المنتج', th_price:'السعر', th_warranty:'الضمان', th_status:'الحالة', all_categories:'الفئات', btn_add_category:'إضافة', no_categories:'لا توجد فئات.', all_promos:'رموز الخصم', btn_add_promo:'إنشاء رمز', no_promos:'لا توجد رموز خصم.', th_type:'النوع', th_value:'القيمة', th_uses:'الاستخدامات',
    orders_title:'متابعة الطلبات', filter_topup:'شحن', th_client:'العميل', th_amount:'المبلغ', th_qty:'الكمية', wallet_topup:'شحن المحفظة', users_title:'إدارة المستخدمين', th_firstname:'الاسم الأول', th_lang:'اللغة', th_orders_count:'الطلبات', th_spent:'الإنفاق', th_joined:'تاريخ الانضمام', th_referrer:'المُحيل', th_referrals:'الإحالات', th_referral_earnings:'أرباح الإحالة', users_show_count:'عرض:', users_search_placeholder:'البحث بالمعرّف أو الاسم...',
    tickets_title:'تذاكر الدعم', broadcast_title:'إرسال رسالة بث', broadcast_desc:'ستُرسل هذه الرسالة إلى جميع مستخدمي البوت.', broadcast_label:'الرسالة (يدعم HTML):', btn_send_broadcast:'إرسال للجميع', settings_title:'إعدادات API', settings_desc:'المزامنة مع البوت.', modal_add_cat:'إضافة فئة', modal_add_prod:'إضافة منتج', modal_add_promo:'إنشاء رمز خصم', lbl_name:'الاسم', lbl_category:'الفئة', lbl_prod_name:'اسم المنتج', lbl_price:'السعر بالدولار', lbl_warranty:'الضمان (أيام)', lbl_discount_type:'النوع', lbl_discount_value:'القيمة', lbl_max_uses:'الحد الأقصى للاستخدام', lbl_expires:'تاريخ الانتهاء', btn_create_cat:'إنشاء', btn_create_prod:'إنشاء', btn_create_promo:'إنشاء',
    stock_manage:'إدارة المخزون', stock_add_label:'أضف الحسابات، حساب واحد في كل سطر:', btn_add_stock:'إضافة', btn_import_file:'استيراد .txt', stock_existing:'المخزون الحالي', stock_items_lbl:'عناصر', no_stock:'لا توجد عناصر.', stock_in:'في المخزون', confirm_delete:'حذف هذا المنتج؟', confirm_order:'تأكيد الدفع #', accounts_detected:'حسابات مكتشفة', available:'✓ متاح', sold:'✗ مباع', no_desc:'لا يوجد وصف', btn_confirm:'تأكيد', reply_placeholder:'اكتب ردك...', btn_reply:'رد', banned:'محظور', confirm_ban:'حظر هذا المستخدم؟', confirm_unban:'إلغاء حظر هذا المستخدم؟', ban_modal_title:'حظر المستخدم', ban_modal_desc:'هل تريد فعلًا حظر هذا المستخدم؟', ban_modal_notify:'إبلاغ المستخدم بأنه حُظر', broadcast_sent:'تم الإرسال: {sent}/{total}', broadcast_failed:'فشل: {failed}', unlimited:'غير محدود', percent:'نسبة مئوية', fixed:'مبلغ ثابت',
    nav_wallet_history:'سجل المحفظة', wh_title:'سجل المحفظة', wh_total_topups:'إجمالي الشحن', wh_total_purchases:'إجمالي مشتريات المحفظة', wh_total_count:'المعاملات', wh_filter_topup:'الشحن', wh_filter_purchase:'مشتريات المحفظة', wh_th_type:'النوع', wh_th_balance_after:'الرصيد بعد العملية', wh_th_description:'الوصف', wh_no_tx:'لا توجد معاملات.', th_payment_method:'الطريقة', pay_method_wallet:'المحفظة', settings_err:'فشلت العملية: '
});
Object.assign(LANG.fr, {overview_kicker:'Aujourd’hui', overview_title:'Le magasin en un coup d’œil', today_revenue:'Revenus du jour', today_orders:'Ventes du jour', priorities:'Priorités', actions_title:'À traiter maintenant', activity:'Activité', recent_orders:'Dernières commandes', view_all:'Tout voir', pending_metric:'Commandes en attente'});
Object.assign(LANG.en, {overview_kicker:'Today', overview_title:'Store at a glance', today_revenue:'Today revenue', today_orders:'Today sales', priorities:'Priorities', actions_title:'Needs attention', activity:'Activity', recent_orders:'Recent orders', view_all:'View all', pending_metric:'Pending orders'});
Object.assign(LANG.zh, {overview_kicker:'今天', overview_title:'商店概览', today_revenue:'今日收入', today_orders:'今日销量', priorities:'优先事项', actions_title:'待处理事项', activity:'动态', recent_orders:'最近订单', view_all:'查看全部', pending_metric:'待处理订单'});
Object.assign(LANG.vi, {overview_kicker:'Hôm nay', overview_title:'Tổng quan cửa hàng', today_revenue:'Doanh thu hôm nay', today_orders:'Lượt bán hôm nay', priorities:'Ưu tiên', actions_title:'Cần xử lý', activity:'Hoạt động', recent_orders:'Đơn gần đây', view_all:'Xem tất cả', pending_metric:'Đơn đang chờ'});
Object.assign(LANG.ru, {overview_kicker:'Сегодня', overview_title:'Магазин в цифрах', today_revenue:'Выручка сегодня', today_orders:'Продажи сегодня', priorities:'Приоритеты', actions_title:'Требует внимания', activity:'Активность', recent_orders:'Последние заказы', view_all:'Все заказы', pending_metric:'Заказы в ожидании'});
Object.assign(LANG.ar, {overview_kicker:'اليوم', overview_title:'نظرة عامة على المتجر', today_revenue:'إيرادات اليوم', today_orders:'مبيعات اليوم', priorities:'الأولويات', actions_title:'بحاجة إلى معالجة', activity:'النشاط', recent_orders:'أحدث الطلبات', view_all:'عرض الكل', pending_metric:'الطلبات المعلقة'});
Object.assign(LANG.fr, {nav_supplier_bots:'API Bot Gestion', supplier_title:'API Bot Gestion', supplier_sync:'Synchroniser'});
Object.assign(LANG.en, {nav_supplier_bots:'Bot API Management', supplier_title:'Bot API Management', supplier_sync:'Sync catalog'});
Object.assign(LANG.fr, {nav_ai_bot:'IA Bot'});
Object.assign(LANG.en, {nav_ai_bot:'AI Bot'});
['ar','zh','vi','ru'].forEach(lang => Object.assign(LANG[lang], {nav_ai_bot:'AI Bot'}));
Object.assign(LANG.fr, {reseller_security:'Securite API', reseller_ip_allowlist:'Adresses IP autorisees', reseller_ip_hint:'Une IP ou un reseau CIDR par ligne. Vide = toutes les IP.', reseller_webhook_enable:'Activer les webhooks de depot', reseller_webhook_rotate:'Generer un nouveau secret', reseller_secret_once:'Copiez ce secret maintenant :'});
Object.assign(LANG.en, {reseller_security:'API security', reseller_ip_allowlist:'Allowed IP addresses', reseller_ip_hint:'One IP or CIDR network per line. Empty = all IPs.', reseller_webhook_enable:'Enable deposit webhooks', reseller_webhook_rotate:'Generate a new signing secret', reseller_secret_once:'Copy this secret now:'});
['ar','zh','vi','ru'].forEach(lang => Object.assign(LANG[lang], {reseller_security:LANG.en.reseller_security, reseller_ip_allowlist:LANG.en.reseller_ip_allowlist, reseller_ip_hint:LANG.en.reseller_ip_hint, reseller_webhook_enable:LANG.en.reseller_webhook_enable, reseller_webhook_rotate:LANG.en.reseller_webhook_rotate, reseller_secret_once:LANG.en.reseller_secret_once}));
Object.assign(LANG.fr, {reseller_special_prices:'Prix spéciaux', reseller_special_prices_for:'Tarifs de', reseller_special_product:'Produit', reseller_special_price:'Prix revendeur ($)', reseller_standard_price:'Prix standard', reseller_special_active:'Tarif actif', reseller_special_telegram:'Appliquer aussi sur Telegram', reseller_special_telegram_hint:'Le même tarif sera utilisé sur son compte Telegram et via son API.', reseller_scope_both:'API + Telegram', reseller_scope_api:'API uniquement', reseller_cost_protection:'Protection du coût fournisseur', reseller_cost_protection_hint:'Bloque la vente si le coût fournisseur atteint ou dépasse ce tarif.', reseller_special_expiry:'Expiration facultative', reseller_no_special_prices:'Aucun prix spécial pour ce revendeur.', reseller_special_saved:'Prix spécial enregistré.', reseller_special_delete_confirm:'Supprimer ce prix spécial ?', reseller_special_effective:'Appliqué', reseller_special_expired:'Expiré', reseller_special_blocked:'Bloqué par le coût', reseller_special_inactive:'Inactif', reseller_special_edit:'Modifier', reseller_special_count:'prix spéciaux'});
Object.assign(LANG.en, {reseller_special_prices:'Special prices', reseller_special_prices_for:'Pricing for', reseller_special_product:'Product', reseller_special_price:'Reseller price ($)', reseller_standard_price:'Standard price', reseller_special_active:'Active price', reseller_special_telegram:'Also apply on Telegram', reseller_special_telegram_hint:'The same price will be used on their Telegram account and through the API.', reseller_scope_both:'API + Telegram', reseller_scope_api:'API only', reseller_cost_protection:'Supplier cost protection', reseller_cost_protection_hint:'Blocks sales when the supplier cost reaches or exceeds this price.', reseller_special_expiry:'Optional expiry', reseller_no_special_prices:'No special prices for this reseller.', reseller_special_saved:'Special price saved.', reseller_special_delete_confirm:'Delete this special price?', reseller_special_effective:'Applied', reseller_special_expired:'Expired', reseller_special_blocked:'Blocked by cost', reseller_special_inactive:'Inactive', reseller_special_edit:'Edit', reseller_special_count:'special prices'});
Object.assign(LANG.zh, {reseller_special_prices:'专属价格', reseller_special_prices_for:'价格账户', reseller_special_product:'产品', reseller_special_price:'经销商价格 ($)', reseller_standard_price:'标准价格', reseller_special_active:'启用价格', reseller_special_telegram:'同时应用于 Telegram', reseller_special_telegram_hint:'同一价格将用于其 Telegram 账户和 API。', reseller_scope_both:'API + Telegram', reseller_scope_api:'仅 API', reseller_cost_protection:'供应商成本保护', reseller_cost_protection_hint:'当供应商成本达到或超过此价格时阻止销售。', reseller_special_expiry:'可选到期时间', reseller_no_special_prices:'此经销商没有专属价格。', reseller_special_saved:'专属价格已保存。', reseller_special_delete_confirm:'删除此专属价格？', reseller_special_effective:'已应用', reseller_special_expired:'已过期', reseller_special_blocked:'因成本被阻止', reseller_special_inactive:'未启用', reseller_special_edit:'编辑', reseller_special_count:'个专属价格'});
Object.assign(LANG.vi, {reseller_special_prices:'Giá đặc biệt', reseller_special_prices_for:'Bảng giá của', reseller_special_product:'Sản phẩm', reseller_special_price:'Giá đại lý ($)', reseller_standard_price:'Giá tiêu chuẩn', reseller_special_active:'Kích hoạt giá', reseller_special_telegram:'Áp dụng cả trên Telegram', reseller_special_telegram_hint:'Cùng một mức giá sẽ dùng cho tài khoản Telegram và API của họ.', reseller_scope_both:'API + Telegram', reseller_scope_api:'Chỉ API', reseller_cost_protection:'Bảo vệ chi phí nhà cung cấp', reseller_cost_protection_hint:'Chặn bán khi chi phí nhà cung cấp bằng hoặc cao hơn mức giá này.', reseller_special_expiry:'Hết hạn tùy chọn', reseller_no_special_prices:'Đại lý này chưa có giá đặc biệt.', reseller_special_saved:'Đã lưu giá đặc biệt.', reseller_special_delete_confirm:'Xóa giá đặc biệt này?', reseller_special_effective:'Đang áp dụng', reseller_special_expired:'Đã hết hạn', reseller_special_blocked:'Bị chặn bởi chi phí', reseller_special_inactive:'Không hoạt động', reseller_special_edit:'Chỉnh sửa', reseller_special_count:'giá đặc biệt'});
Object.assign(LANG.ru, {reseller_special_prices:'Специальные цены', reseller_special_prices_for:'Цены для', reseller_special_product:'Товар', reseller_special_price:'Цена реселлера ($)', reseller_standard_price:'Обычная цена', reseller_special_active:'Цена активна', reseller_special_telegram:'Применять также в Telegram', reseller_special_telegram_hint:'Одна цена будет действовать в аккаунте Telegram и через API.', reseller_scope_both:'API + Telegram', reseller_scope_api:'Только API', reseller_cost_protection:'Защита стоимости поставщика', reseller_cost_protection_hint:'Блокирует продажу, если стоимость поставщика достигает этой цены.', reseller_special_expiry:'Необязательный срок', reseller_no_special_prices:'Для этого реселлера нет специальных цен.', reseller_special_saved:'Специальная цена сохранена.', reseller_special_delete_confirm:'Удалить специальную цену?', reseller_special_effective:'Применяется', reseller_special_expired:'Истекла', reseller_special_blocked:'Заблокирована ценой', reseller_special_inactive:'Неактивна', reseller_special_edit:'Изменить', reseller_special_count:'специальных цен'});
Object.assign(LANG.ar, {reseller_special_prices:'أسعار خاصة', reseller_special_prices_for:'أسعار', reseller_special_product:'المنتج', reseller_special_price:'سعر الموزع ($)', reseller_standard_price:'السعر القياسي', reseller_special_active:'السعر فعال', reseller_special_telegram:'تطبيقه أيضاً على تيليجرام', reseller_special_telegram_hint:'سيُستخدم السعر نفسه في حساب تيليجرام وعبر API.', reseller_scope_both:'API + تيليجرام', reseller_scope_api:'API فقط', reseller_cost_protection:'حماية تكلفة المورد', reseller_cost_protection_hint:'يوقف البيع عندما تصل تكلفة المورد إلى هذا السعر أو تتجاوزه.', reseller_special_expiry:'انتهاء اختياري', reseller_no_special_prices:'لا توجد أسعار خاصة لهذا الموزع.', reseller_special_saved:'تم حفظ السعر الخاص.', reseller_special_delete_confirm:'حذف هذا السعر الخاص؟', reseller_special_effective:'مطبق', reseller_special_expired:'منتهي', reseller_special_blocked:'محظور بسبب التكلفة', reseller_special_inactive:'غير فعال', reseller_special_edit:'تعديل', reseller_special_count:'أسعار خاصة'});
Object.assign(LANG.ar, {nav_supplier_bots:'إدارة API للبوت', supplier_title:'إدارة API للبوت', supplier_sync:'مزامنة الكتالوج'});
Object.assign(LANG.zh, {nav_supplier_bots:'机器人 API 管理', supplier_title:'机器人 API 管理', supplier_sync:'同步目录'});
Object.assign(LANG.vi, {nav_supplier_bots:'Quản lý API Bot', supplier_title:'Quản lý API Bot', supplier_sync:'Đồng bộ danh mục'});
Object.assign(LANG.ru, {nav_supplier_bots:'Управление API бота', supplier_title:'Управление API бота', supplier_sync:'Синхронизировать'});

Object.assign(LANG.fr, {nav_payment_review:'Centre paiements', payment_review_title:'Centre de contrôle des paiements', conversion_title:'Tunnel de conversion'});
Object.assign(LANG.en, {nav_payment_review:'Payment control', payment_review_title:'Payment control center', conversion_title:'Conversion funnel'});
Object.assign(LANG.ar, {nav_payment_review:'Payment center', payment_review_title:'Payment control center', conversion_title:'Conversion funnel'});
Object.assign(LANG.zh, {nav_payment_review:'Payment center', payment_review_title:'Payment control center', conversion_title:'Conversion funnel'});
Object.assign(LANG.vi, {nav_payment_review:'Payment center', payment_review_title:'Payment control center', conversion_title:'Conversion funnel'});
Object.assign(LANG.ru, {nav_payment_review:'Payment center', payment_review_title:'Payment control center', conversion_title:'Conversion funnel'});
Object.assign(LANG.fr, {nav_game:'Jeu & Matchs', tab_game:'Jeu & Matchs'});
Object.assign(LANG.en, {nav_game:'Game & Matches', tab_game:'Game & Matches'});
Object.assign(LANG.ar, {nav_game:'اللعبة والمباريات', tab_game:'اللعبة والمباريات'});
Object.assign(LANG.zh, {nav_game:'游戏与比赛', tab_game:'游戏与比赛'});
Object.assign(LANG.vi, {nav_game:'Trò chơi & Trận đấu', tab_game:'Trò chơi & Trận đấu'});
Object.assign(LANG.ru, {nav_game:'Игра и матчи', tab_game:'Игра и матчи'});

const AI_TRANSLATIONS = {
fr: {
    nav_ai_bot:"IA Bot", ai_context:"Recherche stricte parmi tous les catalogues fournisseurs",
    ai_eyebrow:"Comparateur multi-fournisseur", ai_intro:"Classez tout le catalogue avec l'IA, puis comparez les offres par produit et durée.",
    ai_sync_all:"Synchroniser tous les bots", ai_analyze:"Analyse IA", ai_bots_configured:"Bots configurés", ai_products_indexed:"Produits indexés", ai_last_analysis:"Dernière analyse", ai_state:"État", ai_never:"Jamais",
    ai_status_ready:"Prêt", ai_status_completed:"Terminé", ai_status_failed:"Échec", ai_status_analysis_running:"Analyse IA en cours", ai_status_sync_running:"Synchronisation en cours", ai_status_waiting:"En attente", ai_status_unavailable:"Indisponible", ai_sync_waiting:"Synchronisation en attente",
    ai_background_hint:"La tâche continue sur Railway même si vous fermez le dashboard.", ai_search_product:"Produit recherché", ai_search_example:"Ex. Grok 1 mois", ai_duration:"Durée", ai_auto:"Auto", ai_unit:"Unité", ai_month_one:"mois", ai_months:"Mois", ai_day_one:"jour", ai_days:"Jours", ai_years:"Années",
    ai_min_warranty:"Garantie minimale", ai_any_f:"Indifférente", ai_any_m:"Indifférent", ai_warranty_known:"Garantie connue", ai_7_days:"7 jours", ai_30_days:"30 jours", ai_90_days:"90 jours", ai_delivery:"Livraison", ai_account_provided:"Compte fourni", ai_customer_activation:"Activation client", ai_access:"Accès", ai_private:"Privé", ai_shared:"Partagé",
    ai_max_price:"Prix maximum ($)", ai_no_limit:"Aucune limite", ai_show_unfunded:"Afficher aussi les offres sans solde suffisant", ai_unfunded_hint:"Ces offres servent à comparer les prix, mais ne sont pas achetables pour le moment.", ai_search_best:"Rechercher la meilleure offre",
    ai_compliant_results:"Résultats conformes", ai_search_prompt:"Synchronisez les bots, puis lancez une recherche.", ai_no_search:"Aucune recherche lancée.", ai_similar_products:"Produits similaires", ai_analysis_prompt:"Synchronisez les bots, puis lancez l'analyse IA.", ai_refresh_groups:"Actualiser les groupes", ai_no_analysis:"Aucune analyse lancée.",
    ai_col_product:"Produit", ai_col_supplier:"Fournisseur", ai_col_price:"Prix", ai_col_warranty:"Garantie", ai_col_stock:"Stock", ai_col_reliability:"Fiabilité", ai_col_analysis:"Analyse", ai_col_action:"Action", ai_col_group:"Groupe", ai_col_characteristics:"Caractéristiques", ai_col_best_offer:"Meilleure offre", ai_col_alternatives:"Alternatives", ai_col_max_difference:"Écart maximal",
    ai_operation_analysis:"Analyse IA", ai_operation_sync:"Synchronisation", ai_progress:"{operation} : {processed}/{total}{failures}", ai_failures:" · Échecs : {count}",
    ai_analysis_done:"Analyse IA terminée. Les produits similaires sont regroupés.", ai_sync_done:"Catalogues synchronisés. Vous pouvez lancer l'analyse IA.", ai_analysis_failed:"L'analyse IA s'est terminée avec une erreur.", ai_sync_failed:"La synchronisation s'est terminée avec une erreur.", ai_sync_launched:"Synchronisation globale lancée.", ai_sync_already:"Une synchronisation est déjà en cours.", ai_sync_launch_error:"Impossible de lancer la synchronisation.", ai_analysis_launched:"Indexation IA complète lancée sur tout le catalogue.", ai_analysis_already:"Une analyse IA est déjà en cours.", ai_analysis_launch_error:"Impossible de lancer l'analyse IA.",
    ai_no_groups:"Aucun groupe disponible. Synchronisez les bots, puis lancez l'analyse IA.", ai_no_products_analyzed:"Aucun produit analysé.", ai_group_summary:"Produits disponibles : {available} · Groupes : {groups} · Groupes multi-offres : {comparison}", ai_days_warranty:"Garantie : {days} jours", ai_no_warranty:"Sans garantie", ai_full_warranty:"Garantie complète", ai_mixed_warranties:"Garanties variées", ai_limited_warranty:"Garantie : {days} jours",
    ai_delivery_unknown:"Livraison non précisée", ai_delivery_mixed:"Modes de livraison variés", ai_access_unknown:"Accès non précisé", ai_access_mixed:"Accès variés", ai_regions_mixed:"Régions variées", ai_supplier_balance:"Solde fournisseur : ${balance}", ai_stock_ratio:"achetable / disponible", ai_cheapest:"Moins cher", ai_open_supplier:"Ouvrir ce fournisseur", ai_comparable_offers:"Offres comparables : {count}", ai_classification_incomplete:"Classification incomplète", ai_show_all_offers:"Afficher toutes les offres", ai_hide_offers:"Masquer les offres", ai_groups_loading:"Chargement des groupes...", ai_groups_unavailable:"Groupes indisponibles.", ai_duration_unknown:"Durée non précisée",
    ai_results_summary:"Offres conformes : {count} · Classement par coût et fiabilité.", ai_hidden_summary:"Offres conformes masquées faute de solde fournisseur : {count}.", ai_no_criteria:"Aucune offre ne respecte tous les critères. Vérifiez la durée, la garantie et les autres filtres.", ai_unfunded_exists:"Des offres existent. Activez « Afficher aussi les offres sans solde suffisant » pour les comparer.", ai_no_result:"Aucun résultat conforme.", ai_sync_unknown:"Synchronisation inconnue", ai_sync_recent:"Synchronisé récemment", ai_sync_hours:"Synchronisé il y a {hours} h", ai_connection_disabled:"connexion désactivée", ai_balance:"Solde : ${balance}", ai_warranty_days:"{days} jours", ai_searching:"Recherche en cours...", ai_search_unavailable:"Recherche indisponible.",
    ai_reason_compliant:"Conforme aux filtres", ai_reason_reliability:"Fiabilité {percent} %", ai_reason_affordable:"Unités achetables : {count}", ai_reason_unfunded:"Solde fournisseur insuffisant",
    ai_error_default:"Une erreur est survenue dans IA Bot.", ai_error_query_required:"Saisissez un produit à rechercher.", ai_error_duration:"La durée indiquée n'est pas valide.", ai_error_filter:"L'un des filtres de recherche n'est pas valide.", ai_error_no_suppliers:"Aucun bot fournisseur actif et configuré.", ai_error_analysis_running:"Une analyse IA est déjà en cours.", ai_error_sync_running:"Une synchronisation est déjà en cours.", ai_error_job_missing:"Cette tâche IA n'existe plus.", ai_error_sync_missing:"Cette tâche de synchronisation n'existe plus.", ai_error_server:"Le serveur IA Bot a rencontré une erreur temporaire."
},
en: {
    nav_ai_bot:"AI Bot", ai_context:"Strict search across all supplier catalogs",
    ai_eyebrow:"Multi-supplier comparison", ai_intro:"Classify the entire catalog with AI, then compare offers by product and duration.",
    ai_sync_all:"Sync all bots", ai_analyze:"AI analysis", ai_bots_configured:"Configured bots", ai_products_indexed:"Indexed products", ai_last_analysis:"Last analysis", ai_state:"Status", ai_never:"Never",
    ai_status_ready:"Ready", ai_status_completed:"Completed", ai_status_failed:"Failed", ai_status_analysis_running:"AI analysis in progress", ai_status_sync_running:"Synchronization in progress", ai_status_waiting:"Waiting", ai_status_unavailable:"Unavailable", ai_sync_waiting:"Waiting to synchronize",
    ai_background_hint:"The task continues on Railway even if you close the dashboard.", ai_search_product:"Product search", ai_search_example:"E.g. Grok 1 month", ai_duration:"Duration", ai_auto:"Auto", ai_unit:"Unit", ai_month_one:"month", ai_months:"Months", ai_day_one:"day", ai_days:"Days", ai_years:"Years",
    ai_min_warranty:"Minimum warranty", ai_any_f:"Any", ai_any_m:"Any", ai_warranty_known:"Known warranty", ai_7_days:"7 days", ai_30_days:"30 days", ai_90_days:"90 days", ai_delivery:"Delivery", ai_account_provided:"Account provided", ai_customer_activation:"Customer activation", ai_access:"Access", ai_private:"Private", ai_shared:"Shared",
    ai_max_price:"Maximum price ($)", ai_no_limit:"No limit", ai_show_unfunded:"Also show offers with insufficient balance", ai_unfunded_hint:"These offers can be used for price comparison, but cannot be purchased right now.", ai_search_best:"Find the best offer",
    ai_compliant_results:"Matching results", ai_search_prompt:"Sync the bots, then run a search.", ai_no_search:"No search has been run.", ai_similar_products:"Similar products", ai_analysis_prompt:"Sync the bots, then run the AI analysis.", ai_refresh_groups:"Refresh groups", ai_no_analysis:"No analysis has been run.",
    ai_col_product:"Product", ai_col_supplier:"Supplier", ai_col_price:"Price", ai_col_warranty:"Warranty", ai_col_stock:"Stock", ai_col_reliability:"Reliability", ai_col_analysis:"Analysis", ai_col_action:"Action", ai_col_group:"Group", ai_col_characteristics:"Characteristics", ai_col_best_offer:"Best offer", ai_col_alternatives:"Alternatives", ai_col_max_difference:"Maximum difference",
    ai_operation_analysis:"AI analysis", ai_operation_sync:"Synchronization", ai_progress:"{operation}: {processed}/{total}{failures}", ai_failures:" · Failures: {count}",
    ai_analysis_done:"AI analysis completed. Similar products have been grouped.", ai_sync_done:"Catalogs synchronized. You can now run the AI analysis.", ai_analysis_failed:"The AI analysis ended with an error.", ai_sync_failed:"Synchronization ended with an error.", ai_sync_launched:"Full synchronization started.", ai_sync_already:"A synchronization is already in progress.", ai_sync_launch_error:"Unable to start synchronization.", ai_analysis_launched:"Full AI indexing started for the entire catalog.", ai_analysis_already:"An AI analysis is already in progress.", ai_analysis_launch_error:"Unable to start the AI analysis.",
    ai_no_groups:"No groups available. Sync the bots, then run the AI analysis.", ai_no_products_analyzed:"No products analyzed.", ai_group_summary:"Available products: {available} · Groups: {groups} · Multi-offer groups: {comparison}", ai_days_warranty:"{days}-day warranty", ai_no_warranty:"No warranty", ai_full_warranty:"Full warranty", ai_mixed_warranties:"Various warranties", ai_limited_warranty:"{days}-day warranty",
    ai_delivery_unknown:"Delivery not specified", ai_delivery_mixed:"Various delivery methods", ai_access_unknown:"Access not specified", ai_access_mixed:"Various access types", ai_regions_mixed:"Various regions", ai_supplier_balance:"Supplier balance: ${balance}", ai_stock_ratio:"purchasable / available", ai_cheapest:"Cheapest", ai_open_supplier:"Open this supplier", ai_comparable_offers:"Comparable offers: {count}", ai_classification_incomplete:"Incomplete classification", ai_show_all_offers:"Show all offers", ai_hide_offers:"Hide offers", ai_groups_loading:"Loading groups...", ai_groups_unavailable:"Groups unavailable.", ai_duration_unknown:"Duration not specified",
    ai_results_summary:"Matching offers: {count} · Ranked by cost and reliability.", ai_hidden_summary:"Matching offers hidden due to insufficient supplier balance: {count}.", ai_no_criteria:"No offer matches every criterion. Check the duration, warranty, and other filters.", ai_unfunded_exists:"Offers are available. Enable “Also show offers with insufficient balance” to compare them.", ai_no_result:"No matching results.", ai_sync_unknown:"Synchronization unknown", ai_sync_recent:"Synchronized recently", ai_sync_hours:"Synchronized {hours}h ago", ai_connection_disabled:"connection disabled", ai_balance:"Balance: ${balance}", ai_warranty_days:"{days} days", ai_searching:"Searching...", ai_search_unavailable:"Search unavailable.",
    ai_reason_compliant:"Matches filters", ai_reason_reliability:"Reliability {percent}%", ai_reason_affordable:"Purchasable units: {count}", ai_reason_unfunded:"Insufficient supplier balance",
    ai_error_default:"An error occurred in AI Bot.", ai_error_query_required:"Enter a product to search for.", ai_error_duration:"The selected duration is invalid.", ai_error_filter:"One of the search filters is invalid.", ai_error_no_suppliers:"No active and configured supplier bot.", ai_error_analysis_running:"An AI analysis is already in progress.", ai_error_sync_running:"A synchronization is already in progress.", ai_error_job_missing:"This AI task no longer exists.", ai_error_sync_missing:"This synchronization task no longer exists.", ai_error_server:"The AI Bot server encountered a temporary error."
},
ar: {
    nav_ai_bot:"بوت الذكاء الاصطناعي", ai_context:"بحث دقيق في جميع كتالوجات الموردين",
    ai_eyebrow:"مقارنة بين عدة موردين", ai_intro:"صنّف الكتالوج بالكامل بالذكاء الاصطناعي، ثم قارن العروض حسب المنتج والمدة.",
    ai_sync_all:"مزامنة جميع البوتات", ai_analyze:"تحليل بالذكاء الاصطناعي", ai_bots_configured:"البوتات المهيأة", ai_products_indexed:"المنتجات المفهرسة", ai_last_analysis:"آخر تحليل", ai_state:"الحالة", ai_never:"أبدًا",
    ai_status_ready:"جاهز", ai_status_completed:"مكتمل", ai_status_failed:"فشل", ai_status_analysis_running:"التحليل جارٍ", ai_status_sync_running:"المزامنة جارية", ai_status_waiting:"قيد الانتظار", ai_status_unavailable:"غير متاح", ai_sync_waiting:"بانتظار المزامنة",
    ai_background_hint:"تستمر المهمة على Railway حتى إذا أغلقت لوحة التحكم.", ai_search_product:"البحث عن منتج", ai_search_example:"مثال: Grok لمدة شهر", ai_duration:"المدة", ai_auto:"تلقائي", ai_unit:"الوحدة", ai_month_one:"شهر", ai_months:"أشهر", ai_day_one:"يوم", ai_days:"أيام", ai_years:"سنوات",
    ai_min_warranty:"الحد الأدنى للضمان", ai_any_f:"الكل", ai_any_m:"الكل", ai_warranty_known:"ضمان معروف", ai_7_days:"7 أيام", ai_30_days:"30 يومًا", ai_90_days:"90 يومًا", ai_delivery:"التسليم", ai_account_provided:"حساب جاهز", ai_customer_activation:"تفعيل حساب العميل", ai_access:"نوع الوصول", ai_private:"خاص", ai_shared:"مشترك",
    ai_max_price:"السعر الأقصى ($)", ai_no_limit:"بدون حد", ai_show_unfunded:"إظهار العروض ذات الرصيد غير الكافي أيضًا", ai_unfunded_hint:"يمكن استخدام هذه العروض لمقارنة الأسعار، لكنها غير قابلة للشراء الآن.", ai_search_best:"البحث عن أفضل عرض",
    ai_compliant_results:"النتائج المطابقة", ai_search_prompt:"زامن البوتات ثم ابدأ البحث.", ai_no_search:"لم يتم إجراء بحث.", ai_similar_products:"المنتجات المتشابهة", ai_analysis_prompt:"زامن البوتات ثم شغّل التحليل.", ai_refresh_groups:"تحديث المجموعات", ai_no_analysis:"لم يتم إجراء تحليل.",
    ai_col_product:"المنتج", ai_col_supplier:"المورد", ai_col_price:"السعر", ai_col_warranty:"الضمان", ai_col_stock:"المخزون", ai_col_reliability:"الموثوقية", ai_col_analysis:"التحليل", ai_col_action:"الإجراء", ai_col_group:"المجموعة", ai_col_characteristics:"الخصائص", ai_col_best_offer:"أفضل عرض", ai_col_alternatives:"البدائل", ai_col_max_difference:"أقصى فرق",
    ai_operation_analysis:"تحليل الذكاء الاصطناعي", ai_operation_sync:"المزامنة", ai_progress:"{operation}: {processed}/{total}{failures}", ai_failures:" · حالات الفشل: {count}",
    ai_analysis_done:"اكتمل التحليل وتم تجميع المنتجات المتشابهة.", ai_sync_done:"تمت مزامنة الكتالوجات. يمكنك الآن تشغيل التحليل.", ai_analysis_failed:"انتهى التحليل بخطأ.", ai_sync_failed:"انتهت المزامنة بخطأ.", ai_sync_launched:"بدأت المزامنة الكاملة.", ai_sync_already:"توجد مزامنة جارية بالفعل.", ai_sync_launch_error:"تعذر بدء المزامنة.", ai_analysis_launched:"بدأت الفهرسة الكاملة للكتالوج بالذكاء الاصطناعي.", ai_analysis_already:"يوجد تحليل جارٍ بالفعل.", ai_analysis_launch_error:"تعذر بدء التحليل.",
    ai_no_groups:"لا توجد مجموعات. زامن البوتات ثم شغّل التحليل.", ai_no_products_analyzed:"لم يتم تحليل أي منتج.", ai_group_summary:"المنتجات المتاحة: {available} · المجموعات: {groups} · مجموعات متعددة العروض: {comparison}", ai_days_warranty:"ضمان {days} يومًا", ai_no_warranty:"بدون ضمان", ai_full_warranty:"ضمان كامل", ai_mixed_warranties:"ضمانات متنوعة", ai_limited_warranty:"ضمان {days} يومًا",
    ai_delivery_unknown:"طريقة التسليم غير محددة", ai_delivery_mixed:"طرق تسليم متنوعة", ai_access_unknown:"نوع الوصول غير محدد", ai_access_mixed:"أنواع وصول متنوعة", ai_regions_mixed:"مناطق متنوعة", ai_supplier_balance:"رصيد المورد: ${balance}", ai_stock_ratio:"قابل للشراء / متاح", ai_cheapest:"الأرخص", ai_open_supplier:"فتح هذا المورد", ai_comparable_offers:"العروض القابلة للمقارنة: {count}", ai_classification_incomplete:"تصنيف غير مكتمل", ai_show_all_offers:"إظهار جميع العروض", ai_hide_offers:"إخفاء العروض", ai_groups_loading:"جارٍ تحميل المجموعات...", ai_groups_unavailable:"المجموعات غير متاحة.", ai_duration_unknown:"المدة غير محددة",
    ai_results_summary:"العروض المطابقة: {count} · مرتبة حسب التكلفة والموثوقية.", ai_hidden_summary:"عروض مطابقة مخفية بسبب عدم كفاية رصيد المورد: {count}.", ai_no_criteria:"لا يوجد عرض يطابق جميع المعايير. تحقق من المدة والضمان وبقية الفلاتر.", ai_unfunded_exists:"توجد عروض. فعّل خيار إظهار العروض ذات الرصيد غير الكافي لمقارنتها.", ai_no_result:"لا توجد نتائج مطابقة.", ai_sync_unknown:"حالة المزامنة غير معروفة", ai_sync_recent:"تمت المزامنة مؤخرًا", ai_sync_hours:"تمت المزامنة قبل {hours} ساعة", ai_connection_disabled:"الاتصال معطل", ai_balance:"الرصيد: ${balance}", ai_warranty_days:"{days} يومًا", ai_searching:"جارٍ البحث...", ai_search_unavailable:"البحث غير متاح.",
    ai_reason_compliant:"مطابق للفلاتر", ai_reason_reliability:"الموثوقية {percent}%", ai_reason_affordable:"الوحدات القابلة للشراء: {count}", ai_reason_unfunded:"رصيد المورد غير كافٍ",
    ai_error_default:"حدث خطأ في بوت الذكاء الاصطناعي.", ai_error_query_required:"أدخل منتجًا للبحث عنه.", ai_error_duration:"المدة المحددة غير صالحة.", ai_error_filter:"أحد فلاتر البحث غير صالح.", ai_error_no_suppliers:"لا يوجد بوت مورد نشط ومهيأ.", ai_error_analysis_running:"يوجد تحليل جارٍ بالفعل.", ai_error_sync_running:"توجد مزامنة جارية بالفعل.", ai_error_job_missing:"مهمة التحليل هذه لم تعد موجودة.", ai_error_sync_missing:"مهمة المزامنة هذه لم تعد موجودة.", ai_error_server:"واجه خادم بوت الذكاء الاصطناعي خطأً مؤقتًا."
},
zh: {
    nav_ai_bot:"AI 智能选品", ai_context:"严格搜索所有供应商目录",
    ai_eyebrow:"多供应商比较", ai_intro:"使用 AI 对整个目录分类，然后按产品和时长比较报价。",
    ai_sync_all:"同步所有机器人", ai_analyze:"AI 分析", ai_bots_configured:"已配置机器人", ai_products_indexed:"已索引产品", ai_last_analysis:"上次分析", ai_state:"状态", ai_never:"从未",
    ai_status_ready:"就绪", ai_status_completed:"已完成", ai_status_failed:"失败", ai_status_analysis_running:"AI 分析中", ai_status_sync_running:"同步中", ai_status_waiting:"等待中", ai_status_unavailable:"不可用", ai_sync_waiting:"等待同步",
    ai_background_hint:"即使关闭控制台，任务也会继续在 Railway 上运行。", ai_search_product:"搜索产品", ai_search_example:"例如：Grok 1 个月", ai_duration:"时长", ai_auto:"自动", ai_unit:"单位", ai_month_one:"个月", ai_months:"月", ai_day_one:"天", ai_days:"天", ai_years:"年",
    ai_min_warranty:"最低保修", ai_any_f:"不限", ai_any_m:"不限", ai_warranty_known:"已知保修", ai_7_days:"7 天", ai_30_days:"30 天", ai_90_days:"90 天", ai_delivery:"交付方式", ai_account_provided:"提供账号", ai_customer_activation:"客户账号激活", ai_access:"访问类型", ai_private:"独享", ai_shared:"共享",
    ai_max_price:"最高价格 ($)", ai_no_limit:"不限", ai_show_unfunded:"同时显示余额不足的报价", ai_unfunded_hint:"这些报价可用于价格比较，但目前无法购买。", ai_search_best:"查找最佳报价",
    ai_compliant_results:"匹配结果", ai_search_prompt:"先同步机器人，然后开始搜索。", ai_no_search:"尚未进行搜索。", ai_similar_products:"相似产品", ai_analysis_prompt:"先同步机器人，然后运行 AI 分析。", ai_refresh_groups:"刷新分组", ai_no_analysis:"尚未进行分析。",
    ai_col_product:"产品", ai_col_supplier:"供应商", ai_col_price:"价格", ai_col_warranty:"保修", ai_col_stock:"库存", ai_col_reliability:"可靠性", ai_col_analysis:"分析", ai_col_action:"操作", ai_col_group:"分组", ai_col_characteristics:"特征", ai_col_best_offer:"最佳报价", ai_col_alternatives:"其他报价", ai_col_max_difference:"最大价差",
    ai_operation_analysis:"AI 分析", ai_operation_sync:"同步", ai_progress:"{operation}：{processed}/{total}{failures}", ai_failures:" · 失败：{count}",
    ai_analysis_done:"AI 分析已完成，相似产品已分组。", ai_sync_done:"目录已同步，现在可以运行 AI 分析。", ai_analysis_failed:"AI 分析因错误而结束。", ai_sync_failed:"同步因错误而结束。", ai_sync_launched:"已开始完整同步。", ai_sync_already:"已有同步任务正在运行。", ai_sync_launch_error:"无法开始同步。", ai_analysis_launched:"已开始对整个目录进行完整 AI 索引。", ai_analysis_already:"已有 AI 分析正在运行。", ai_analysis_launch_error:"无法开始 AI 分析。",
    ai_no_groups:"暂无分组。请先同步机器人，然后运行 AI 分析。", ai_no_products_analyzed:"尚未分析产品。", ai_group_summary:"可用产品：{available} · 分组：{groups} · 多报价分组：{comparison}", ai_days_warranty:"保修 {days} 天", ai_no_warranty:"无保修", ai_full_warranty:"全程保修", ai_mixed_warranties:"多种保修", ai_limited_warranty:"保修 {days} 天",
    ai_delivery_unknown:"未注明交付方式", ai_delivery_mixed:"多种交付方式", ai_access_unknown:"未注明访问类型", ai_access_mixed:"多种访问类型", ai_regions_mixed:"多个地区", ai_supplier_balance:"供应商余额：${balance}", ai_stock_ratio:"可购买 / 可用", ai_cheapest:"最低价", ai_open_supplier:"打开此供应商", ai_comparable_offers:"可比较报价：{count}", ai_classification_incomplete:"分类不完整", ai_show_all_offers:"显示所有报价", ai_hide_offers:"隐藏报价", ai_groups_loading:"正在加载分组...", ai_groups_unavailable:"分组不可用。", ai_duration_unknown:"未注明时长",
    ai_results_summary:"匹配报价：{count} · 按成本和可靠性排序。", ai_hidden_summary:"因供应商余额不足而隐藏的匹配报价：{count}。", ai_no_criteria:"没有报价符合全部条件。请检查时长、保修和其他筛选条件。", ai_unfunded_exists:"存在可比较的报价。启用“同时显示余额不足的报价”即可查看。", ai_no_result:"没有匹配结果。", ai_sync_unknown:"同步状态未知", ai_sync_recent:"最近已同步", ai_sync_hours:"{hours} 小时前同步", ai_connection_disabled:"连接已禁用", ai_balance:"余额：${balance}", ai_warranty_days:"{days} 天", ai_searching:"搜索中...", ai_search_unavailable:"搜索不可用。",
    ai_reason_compliant:"符合筛选条件", ai_reason_reliability:"可靠性 {percent}%", ai_reason_affordable:"可购买数量：{count}", ai_reason_unfunded:"供应商余额不足",
    ai_error_default:"AI 智能选品发生错误。", ai_error_query_required:"请输入要搜索的产品。", ai_error_duration:"所选时长无效。", ai_error_filter:"某个搜索筛选条件无效。", ai_error_no_suppliers:"没有已启用并配置的供应商机器人。", ai_error_analysis_running:"已有 AI 分析正在运行。", ai_error_sync_running:"已有同步任务正在运行。", ai_error_job_missing:"此 AI 任务已不存在。", ai_error_sync_missing:"此同步任务已不存在。", ai_error_server:"AI 智能选品服务器遇到临时错误。"
},
vi: {
    nav_ai_bot:"AI Bot", ai_context:"Tìm kiếm chính xác trong toàn bộ danh mục nhà cung cấp",
    ai_eyebrow:"So sánh nhiều nhà cung cấp", ai_intro:"Phân loại toàn bộ danh mục bằng AI, sau đó so sánh ưu đãi theo sản phẩm và thời hạn.",
    ai_sync_all:"Đồng bộ tất cả bot", ai_analyze:"Phân tích AI", ai_bots_configured:"Bot đã cấu hình", ai_products_indexed:"Sản phẩm đã lập chỉ mục", ai_last_analysis:"Lần phân tích gần nhất", ai_state:"Trạng thái", ai_never:"Chưa bao giờ",
    ai_status_ready:"Sẵn sàng", ai_status_completed:"Hoàn tất", ai_status_failed:"Thất bại", ai_status_analysis_running:"Đang phân tích AI", ai_status_sync_running:"Đang đồng bộ", ai_status_waiting:"Đang chờ", ai_status_unavailable:"Không khả dụng", ai_sync_waiting:"Đang chờ đồng bộ",
    ai_background_hint:"Tác vụ vẫn tiếp tục trên Railway ngay cả khi bạn đóng dashboard.", ai_search_product:"Tìm sản phẩm", ai_search_example:"Ví dụ: Grok 1 tháng", ai_duration:"Thời hạn", ai_auto:"Tự động", ai_unit:"Đơn vị", ai_month_one:"tháng", ai_months:"Tháng", ai_day_one:"ngày", ai_days:"Ngày", ai_years:"Năm",
    ai_min_warranty:"Bảo hành tối thiểu", ai_any_f:"Bất kỳ", ai_any_m:"Bất kỳ", ai_warranty_known:"Có thông tin bảo hành", ai_7_days:"7 ngày", ai_30_days:"30 ngày", ai_90_days:"90 ngày", ai_delivery:"Hình thức giao", ai_account_provided:"Cung cấp tài khoản", ai_customer_activation:"Kích hoạt tài khoản khách", ai_access:"Quyền truy cập", ai_private:"Riêng tư", ai_shared:"Dùng chung",
    ai_max_price:"Giá tối đa ($)", ai_no_limit:"Không giới hạn", ai_show_unfunded:"Hiển thị cả ưu đãi không đủ số dư", ai_unfunded_hint:"Các ưu đãi này dùng để so sánh giá nhưng hiện chưa thể mua.", ai_search_best:"Tìm ưu đãi tốt nhất",
    ai_compliant_results:"Kết quả phù hợp", ai_search_prompt:"Đồng bộ các bot rồi bắt đầu tìm kiếm.", ai_no_search:"Chưa thực hiện tìm kiếm.", ai_similar_products:"Sản phẩm tương tự", ai_analysis_prompt:"Đồng bộ các bot rồi chạy phân tích AI.", ai_refresh_groups:"Làm mới nhóm", ai_no_analysis:"Chưa thực hiện phân tích.",
    ai_col_product:"Sản phẩm", ai_col_supplier:"Nhà cung cấp", ai_col_price:"Giá", ai_col_warranty:"Bảo hành", ai_col_stock:"Kho", ai_col_reliability:"Độ tin cậy", ai_col_analysis:"Phân tích", ai_col_action:"Thao tác", ai_col_group:"Nhóm", ai_col_characteristics:"Đặc điểm", ai_col_best_offer:"Ưu đãi tốt nhất", ai_col_alternatives:"Lựa chọn khác", ai_col_max_difference:"Chênh lệch tối đa",
    ai_operation_analysis:"Phân tích AI", ai_operation_sync:"Đồng bộ", ai_progress:"{operation}: {processed}/{total}{failures}", ai_failures:" · Thất bại: {count}",
    ai_analysis_done:"Phân tích AI hoàn tất. Các sản phẩm tương tự đã được gom nhóm.", ai_sync_done:"Danh mục đã đồng bộ. Bạn có thể chạy phân tích AI.", ai_analysis_failed:"Phân tích AI kết thúc với lỗi.", ai_sync_failed:"Đồng bộ kết thúc với lỗi.", ai_sync_launched:"Đã bắt đầu đồng bộ toàn bộ.", ai_sync_already:"Một phiên đồng bộ đang chạy.", ai_sync_launch_error:"Không thể bắt đầu đồng bộ.", ai_analysis_launched:"Đã bắt đầu lập chỉ mục AI cho toàn bộ danh mục.", ai_analysis_already:"Một phiên phân tích AI đang chạy.", ai_analysis_launch_error:"Không thể bắt đầu phân tích AI.",
    ai_no_groups:"Chưa có nhóm. Hãy đồng bộ các bot rồi chạy phân tích AI.", ai_no_products_analyzed:"Chưa có sản phẩm được phân tích.", ai_group_summary:"Sản phẩm khả dụng: {available} · Nhóm: {groups} · Nhóm nhiều ưu đãi: {comparison}", ai_days_warranty:"Bảo hành {days} ngày", ai_no_warranty:"Không bảo hành", ai_full_warranty:"Bảo hành toàn thời hạn", ai_mixed_warranties:"Nhiều loại bảo hành", ai_limited_warranty:"Bảo hành {days} ngày",
    ai_delivery_unknown:"Chưa nêu hình thức giao", ai_delivery_mixed:"Nhiều hình thức giao", ai_access_unknown:"Chưa nêu quyền truy cập", ai_access_mixed:"Nhiều loại quyền truy cập", ai_regions_mixed:"Nhiều khu vực", ai_supplier_balance:"Số dư nhà cung cấp: ${balance}", ai_stock_ratio:"có thể mua / khả dụng", ai_cheapest:"Rẻ nhất", ai_open_supplier:"Mở nhà cung cấp này", ai_comparable_offers:"Ưu đãi có thể so sánh: {count}", ai_classification_incomplete:"Phân loại chưa đầy đủ", ai_show_all_offers:"Hiển thị tất cả ưu đãi", ai_hide_offers:"Ẩn ưu đãi", ai_groups_loading:"Đang tải nhóm...", ai_groups_unavailable:"Nhóm không khả dụng.", ai_duration_unknown:"Chưa nêu thời hạn",
    ai_results_summary:"Ưu đãi phù hợp: {count} · Xếp hạng theo chi phí và độ tin cậy.", ai_hidden_summary:"Ưu đãi phù hợp bị ẩn do nhà cung cấp không đủ số dư: {count}.", ai_no_criteria:"Không có ưu đãi nào đáp ứng mọi tiêu chí. Hãy kiểm tra thời hạn, bảo hành và các bộ lọc khác.", ai_unfunded_exists:"Có ưu đãi để so sánh. Bật “Hiển thị cả ưu đãi không đủ số dư” để xem.", ai_no_result:"Không có kết quả phù hợp.", ai_sync_unknown:"Không rõ trạng thái đồng bộ", ai_sync_recent:"Đã đồng bộ gần đây", ai_sync_hours:"Đã đồng bộ {hours} giờ trước", ai_connection_disabled:"kết nối đã tắt", ai_balance:"Số dư: ${balance}", ai_warranty_days:"{days} ngày", ai_searching:"Đang tìm kiếm...", ai_search_unavailable:"Tìm kiếm không khả dụng.",
    ai_reason_compliant:"Phù hợp bộ lọc", ai_reason_reliability:"Độ tin cậy {percent}%", ai_reason_affordable:"Số lượng có thể mua: {count}", ai_reason_unfunded:"Số dư nhà cung cấp không đủ",
    ai_error_default:"Đã xảy ra lỗi trong AI Bot.", ai_error_query_required:"Nhập sản phẩm cần tìm.", ai_error_duration:"Thời hạn đã chọn không hợp lệ.", ai_error_filter:"Một bộ lọc tìm kiếm không hợp lệ.", ai_error_no_suppliers:"Không có bot nhà cung cấp nào đang hoạt động và được cấu hình.", ai_error_analysis_running:"Một phiên phân tích AI đang chạy.", ai_error_sync_running:"Một phiên đồng bộ đang chạy.", ai_error_job_missing:"Tác vụ AI này không còn tồn tại.", ai_error_sync_missing:"Tác vụ đồng bộ này không còn tồn tại.", ai_error_server:"Máy chủ AI Bot gặp lỗi tạm thời."
},
ru: {
    nav_ai_bot:"ИИ-бот", ai_context:"Точный поиск по всем каталогам поставщиков",
    ai_eyebrow:"Сравнение поставщиков", ai_intro:"Классифицируйте весь каталог с помощью ИИ и сравнивайте предложения по продукту и сроку.",
    ai_sync_all:"Синхронизировать всех ботов", ai_analyze:"Анализ ИИ", ai_bots_configured:"Настроенные боты", ai_products_indexed:"Проиндексированные товары", ai_last_analysis:"Последний анализ", ai_state:"Состояние", ai_never:"Никогда",
    ai_status_ready:"Готово", ai_status_completed:"Завершено", ai_status_failed:"Ошибка", ai_status_analysis_running:"Выполняется анализ ИИ", ai_status_sync_running:"Выполняется синхронизация", ai_status_waiting:"Ожидание", ai_status_unavailable:"Недоступно", ai_sync_waiting:"Ожидание синхронизации",
    ai_background_hint:"Задача продолжит выполняться на Railway, даже если закрыть панель.", ai_search_product:"Поиск товара", ai_search_example:"Например: Grok на 1 месяц", ai_duration:"Срок", ai_auto:"Авто", ai_unit:"Единица", ai_month_one:"месяц", ai_months:"Месяцы", ai_day_one:"день", ai_days:"Дни", ai_years:"Годы",
    ai_min_warranty:"Минимальная гарантия", ai_any_f:"Любая", ai_any_m:"Любой", ai_warranty_known:"Известная гарантия", ai_7_days:"7 дней", ai_30_days:"30 дней", ai_90_days:"90 дней", ai_delivery:"Доставка", ai_account_provided:"Готовый аккаунт", ai_customer_activation:"Активация аккаунта клиента", ai_access:"Доступ", ai_private:"Личный", ai_shared:"Общий",
    ai_max_price:"Максимальная цена ($)", ai_no_limit:"Без ограничений", ai_show_unfunded:"Показывать предложения с недостаточным балансом", ai_unfunded_hint:"Эти предложения можно сравнивать по цене, но сейчас их нельзя купить.", ai_search_best:"Найти лучшее предложение",
    ai_compliant_results:"Подходящие результаты", ai_search_prompt:"Синхронизируйте ботов и выполните поиск.", ai_no_search:"Поиск ещё не выполнялся.", ai_similar_products:"Похожие товары", ai_analysis_prompt:"Синхронизируйте ботов и запустите анализ ИИ.", ai_refresh_groups:"Обновить группы", ai_no_analysis:"Анализ ещё не выполнялся.",
    ai_col_product:"Товар", ai_col_supplier:"Поставщик", ai_col_price:"Цена", ai_col_warranty:"Гарантия", ai_col_stock:"Наличие", ai_col_reliability:"Надёжность", ai_col_analysis:"Анализ", ai_col_action:"Действие", ai_col_group:"Группа", ai_col_characteristics:"Характеристики", ai_col_best_offer:"Лучшее предложение", ai_col_alternatives:"Альтернативы", ai_col_max_difference:"Максимальная разница",
    ai_operation_analysis:"Анализ ИИ", ai_operation_sync:"Синхронизация", ai_progress:"{operation}: {processed}/{total}{failures}", ai_failures:" · Ошибки: {count}",
    ai_analysis_done:"Анализ ИИ завершён. Похожие товары сгруппированы.", ai_sync_done:"Каталоги синхронизированы. Теперь можно запустить анализ ИИ.", ai_analysis_failed:"Анализ ИИ завершился с ошибкой.", ai_sync_failed:"Синхронизация завершилась с ошибкой.", ai_sync_launched:"Полная синхронизация запущена.", ai_sync_already:"Синхронизация уже выполняется.", ai_sync_launch_error:"Не удалось запустить синхронизацию.", ai_analysis_launched:"Запущена полная ИИ-индексация всего каталога.", ai_analysis_already:"Анализ ИИ уже выполняется.", ai_analysis_launch_error:"Не удалось запустить анализ ИИ.",
    ai_no_groups:"Групп пока нет. Синхронизируйте ботов и запустите анализ ИИ.", ai_no_products_analyzed:"Нет проанализированных товаров.", ai_group_summary:"Доступные товары: {available} · Группы: {groups} · Группы с несколькими предложениями: {comparison}", ai_days_warranty:"Гарантия: {days} дн.", ai_no_warranty:"Без гарантии", ai_full_warranty:"Полная гарантия", ai_mixed_warranties:"Разные гарантии", ai_limited_warranty:"Гарантия: {days} дн.",
    ai_delivery_unknown:"Способ доставки не указан", ai_delivery_mixed:"Разные способы доставки", ai_access_unknown:"Тип доступа не указан", ai_access_mixed:"Разные типы доступа", ai_regions_mixed:"Разные регионы", ai_supplier_balance:"Баланс поставщика: ${balance}", ai_stock_ratio:"можно купить / доступно", ai_cheapest:"Самое дешёвое", ai_open_supplier:"Открыть поставщика", ai_comparable_offers:"Сравнимые предложения: {count}", ai_classification_incomplete:"Неполная классификация", ai_show_all_offers:"Показать все предложения", ai_hide_offers:"Скрыть предложения", ai_groups_loading:"Загрузка групп...", ai_groups_unavailable:"Группы недоступны.", ai_duration_unknown:"Срок не указан",
    ai_results_summary:"Подходящие предложения: {count} · Сортировка по цене и надёжности.", ai_hidden_summary:"Подходящие предложения скрыты из-за недостаточного баланса поставщика: {count}.", ai_no_criteria:"Нет предложения, соответствующего всем условиям. Проверьте срок, гарантию и другие фильтры.", ai_unfunded_exists:"Предложения существуют. Включите показ предложений с недостаточным балансом для сравнения.", ai_no_result:"Нет подходящих результатов.", ai_sync_unknown:"Статус синхронизации неизвестен", ai_sync_recent:"Недавно синхронизировано", ai_sync_hours:"Синхронизировано {hours} ч. назад", ai_connection_disabled:"подключение отключено", ai_balance:"Баланс: ${balance}", ai_warranty_days:"{days} дн.", ai_searching:"Поиск...", ai_search_unavailable:"Поиск недоступен.",
    ai_reason_compliant:"Соответствует фильтрам", ai_reason_reliability:"Надёжность {percent}%", ai_reason_affordable:"Можно купить: {count}", ai_reason_unfunded:"Недостаточный баланс поставщика",
    ai_error_default:"Произошла ошибка в ИИ-боте.", ai_error_query_required:"Введите товар для поиска.", ai_error_duration:"Выбран неверный срок.", ai_error_filter:"Один из фильтров поиска недействителен.", ai_error_no_suppliers:"Нет активных и настроенных ботов-поставщиков.", ai_error_analysis_running:"Анализ ИИ уже выполняется.", ai_error_sync_running:"Синхронизация уже выполняется.", ai_error_job_missing:"Эта задача ИИ больше не существует.", ai_error_sync_missing:"Эта задача синхронизации больше не существует.", ai_error_server:"Сервер ИИ-бота столкнулся с временной ошибкой."
}
};
Object.entries(AI_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));

const OPERATIONS_TRANSLATIONS = {
fr: {
    ops_reconcile_title:"Contrôle financier", ops_reconcile_desc:"Vérification quotidienne, en lecture seule, des soldes, paiements et livraisons.", ops_reconcile_run:"Vérifier maintenant", ops_reconcile_running:"Vérification...", ops_reconcile_empty:"Aucun contrôle disponible.", ops_reconcile_updated:"Dernière vérification : {date}", ops_reconcile_summary:"{critical} critique(s) · {warnings} avertissement(s)", ops_reconcile_read_only:"Ce contrôle ne modifie aucune commande, aucun solde et aucun stock.", ops_reconcile_done:"Contrôle financier terminé.", ops_reconcile_failed:"Le contrôle financier est momentanément indisponible.",
    ops_status_healthy:"Sain", ops_status_warning:"À surveiller", ops_status_critical:"Critique",
    ops_check_negative_wallets:"Soldes wallet négatifs", ops_check_stuck_paid_orders:"Commandes payées bloquées depuis plus de 15 minutes", ops_check_unknown_supplier_outcomes:"Achats fournisseur au résultat inconnu", ops_check_unprofitable_supplier_orders:"Achats fournisseur terminés sans marge", ops_check_completed_without_delivery:"Commandes terminées sans livraison enregistrée", ops_check_finished_provider_payments_unresolved:"Paiements fournisseur terminés non reflétés dans la commande",
    order_timeline_title:"Chronologie", order_timeline_loading:"Chargement de la chronologie...", order_timeline_empty:"Aucun événement enregistré.", order_timeline_unavailable:"Chronologie momentanément indisponible.",
    order_event_created:"Commande créée", order_event_payment_confirmed:"Paiement confirmé", order_event_activation_requested:"Identifiant d'activation reçu", order_event_activation_completed:"Activation terminée", order_event_provider_created:"Paiement fournisseur créé", order_event_provider_status:"Statut du paiement fournisseur mis à jour", order_event_provider_processed:"Paiement fournisseur traité", order_event_supplier_started:"Livraison fournisseur démarrée", order_event_supplier_status:"Statut fournisseur mis à jour", order_event_supplier_completed:"Livraison fournisseur terminée", order_event_stock_reserved:"Stock réservé pour la livraison", order_event_review_action:"Action de contrôle manuel"
},
en: {
    ops_reconcile_title:"Financial control", ops_reconcile_desc:"Daily read-only verification of balances, payments, and deliveries.", ops_reconcile_run:"Check now", ops_reconcile_running:"Checking...", ops_reconcile_empty:"No control report is available.", ops_reconcile_updated:"Last check: {date}", ops_reconcile_summary:"{critical} critical · {warnings} warning(s)", ops_reconcile_read_only:"This check never changes orders, balances, or stock.", ops_reconcile_done:"Financial control completed.", ops_reconcile_failed:"Financial control is temporarily unavailable.",
    ops_status_healthy:"Healthy", ops_status_warning:"Needs attention", ops_status_critical:"Critical",
    ops_check_negative_wallets:"Negative wallet balances", ops_check_stuck_paid_orders:"Paid orders stuck for over 15 minutes", ops_check_unknown_supplier_outcomes:"Supplier purchases with an unknown outcome", ops_check_unprofitable_supplier_orders:"Completed supplier purchases without profit", ops_check_completed_without_delivery:"Completed orders without a persisted delivery", ops_check_finished_provider_payments_unresolved:"Finished provider payments not reflected in the order",
    order_timeline_title:"Timeline", order_timeline_loading:"Loading timeline...", order_timeline_empty:"No event has been recorded.", order_timeline_unavailable:"Timeline is temporarily unavailable.",
    order_event_created:"Order created", order_event_payment_confirmed:"Payment confirmed", order_event_activation_requested:"Activation identifier received", order_event_activation_completed:"Activation completed", order_event_provider_created:"Provider payment created", order_event_provider_status:"Provider payment status updated", order_event_provider_processed:"Provider payment processed", order_event_supplier_started:"Supplier fulfillment started", order_event_supplier_status:"Supplier status updated", order_event_supplier_completed:"Supplier fulfillment completed", order_event_stock_reserved:"Stock reserved for delivery", order_event_review_action:"Manual review action"
},
ar: {
    ops_reconcile_title:"التحقق المالي", ops_reconcile_desc:"فحص يومي للقراءة فقط للأرصدة والمدفوعات وعمليات التسليم.", ops_reconcile_run:"تحقق الآن", ops_reconcile_running:"جارٍ التحقق...", ops_reconcile_empty:"لا يوجد تقرير تحقق متاح.", ops_reconcile_updated:"آخر تحقق: {date}", ops_reconcile_summary:"{critical} حرجة · {warnings} تحذير", ops_reconcile_read_only:"هذا الفحص لا يغير الطلبات أو الأرصدة أو المخزون.", ops_reconcile_done:"اكتمل التحقق المالي.", ops_reconcile_failed:"التحقق المالي غير متاح مؤقتًا.",
    ops_status_healthy:"سليم", ops_status_warning:"يحتاج متابعة", ops_status_critical:"حرج",
    ops_check_negative_wallets:"أرصدة محفظة سالبة", ops_check_stuck_paid_orders:"طلبات مدفوعة عالقة لأكثر من 15 دقيقة", ops_check_unknown_supplier_outcomes:"مشتريات مورد بنتيجة غير معروفة", ops_check_unprofitable_supplier_orders:"مشتريات مورد مكتملة دون ربح", ops_check_completed_without_delivery:"طلبات مكتملة دون تسليم محفوظ", ops_check_finished_provider_payments_unresolved:"مدفوعات مورد مكتملة غير منعكسة في الطلب",
    order_timeline_title:"التسلسل الزمني", order_timeline_loading:"جارٍ تحميل التسلسل الزمني...", order_timeline_empty:"لم يتم تسجيل أي حدث.", order_timeline_unavailable:"التسلسل الزمني غير متاح مؤقتًا.",
    order_event_created:"تم إنشاء الطلب", order_event_payment_confirmed:"تم تأكيد الدفع", order_event_activation_requested:"تم استلام معرّف التفعيل", order_event_activation_completed:"اكتمل التفعيل", order_event_provider_created:"تم إنشاء دفعة المورد", order_event_provider_status:"تم تحديث حالة دفعة المورد", order_event_provider_processed:"تمت معالجة دفعة المورد", order_event_supplier_started:"بدأ تنفيذ المورد", order_event_supplier_status:"تم تحديث حالة المورد", order_event_supplier_completed:"اكتمل تنفيذ المورد", order_event_stock_reserved:"تم حجز المخزون للتسليم", order_event_review_action:"إجراء مراجعة يدوي"
},
zh: {
    ops_reconcile_title:"财务核对", ops_reconcile_desc:"每日只读检查余额、付款和交付记录。", ops_reconcile_run:"立即检查", ops_reconcile_running:"检查中...", ops_reconcile_empty:"暂无核对报告。", ops_reconcile_updated:"上次检查：{date}", ops_reconcile_summary:"严重 {critical} 项 · 警告 {warnings} 项", ops_reconcile_read_only:"此检查不会修改订单、余额或库存。", ops_reconcile_done:"财务核对已完成。", ops_reconcile_failed:"财务核对暂时不可用。",
    ops_status_healthy:"正常", ops_status_warning:"需要关注", ops_status_critical:"严重",
    ops_check_negative_wallets:"钱包余额为负", ops_check_stuck_paid_orders:"已付款订单卡住超过 15 分钟", ops_check_unknown_supplier_outcomes:"供应商采购结果未知", ops_check_unprofitable_supplier_orders:"已完成但无利润的供应商采购", ops_check_completed_without_delivery:"已完成但未保存交付记录的订单", ops_check_finished_provider_payments_unresolved:"供应商付款完成但订单未更新",
    order_timeline_title:"时间线", order_timeline_loading:"正在加载时间线...", order_timeline_empty:"暂无事件记录。", order_timeline_unavailable:"时间线暂时不可用。",
    order_event_created:"订单已创建", order_event_payment_confirmed:"付款已确认", order_event_activation_requested:"已收到激活标识", order_event_activation_completed:"激活已完成", order_event_provider_created:"供应商付款已创建", order_event_provider_status:"供应商付款状态已更新", order_event_provider_processed:"供应商付款已处理", order_event_supplier_started:"供应商交付已开始", order_event_supplier_status:"供应商状态已更新", order_event_supplier_completed:"供应商交付已完成", order_event_stock_reserved:"库存已为交付保留", order_event_review_action:"人工审核操作"
},
vi: {
    ops_reconcile_title:"Đối soát tài chính", ops_reconcile_desc:"Kiểm tra chỉ đọc hằng ngày đối với số dư, thanh toán và giao hàng.", ops_reconcile_run:"Kiểm tra ngay", ops_reconcile_running:"Đang kiểm tra...", ops_reconcile_empty:"Chưa có báo cáo đối soát.", ops_reconcile_updated:"Lần kiểm tra gần nhất: {date}", ops_reconcile_summary:"{critical} nghiêm trọng · {warnings} cảnh báo", ops_reconcile_read_only:"Kiểm tra này không thay đổi đơn hàng, số dư hoặc kho.", ops_reconcile_done:"Đã hoàn tất đối soát tài chính.", ops_reconcile_failed:"Đối soát tài chính tạm thời không khả dụng.",
    ops_status_healthy:"Ổn định", ops_status_warning:"Cần chú ý", ops_status_critical:"Nghiêm trọng",
    ops_check_negative_wallets:"Số dư ví âm", ops_check_stuck_paid_orders:"Đơn đã thanh toán bị treo hơn 15 phút", ops_check_unknown_supplier_outcomes:"Giao dịch nhà cung cấp chưa rõ kết quả", ops_check_unprofitable_supplier_orders:"Giao dịch nhà cung cấp hoàn tất nhưng không có lợi nhuận", ops_check_completed_without_delivery:"Đơn hoàn tất nhưng chưa lưu giao hàng", ops_check_finished_provider_payments_unresolved:"Thanh toán nhà cung cấp hoàn tất nhưng đơn chưa cập nhật",
    order_timeline_title:"Dòng thời gian", order_timeline_loading:"Đang tải dòng thời gian...", order_timeline_empty:"Chưa ghi nhận sự kiện nào.", order_timeline_unavailable:"Dòng thời gian tạm thời không khả dụng.",
    order_event_created:"Đã tạo đơn hàng", order_event_payment_confirmed:"Đã xác nhận thanh toán", order_event_activation_requested:"Đã nhận mã kích hoạt", order_event_activation_completed:"Đã kích hoạt", order_event_provider_created:"Đã tạo thanh toán nhà cung cấp", order_event_provider_status:"Đã cập nhật trạng thái thanh toán nhà cung cấp", order_event_provider_processed:"Đã xử lý thanh toán nhà cung cấp", order_event_supplier_started:"Nhà cung cấp bắt đầu giao hàng", order_event_supplier_status:"Đã cập nhật trạng thái nhà cung cấp", order_event_supplier_completed:"Nhà cung cấp đã hoàn tất giao hàng", order_event_stock_reserved:"Đã giữ kho để giao hàng", order_event_review_action:"Thao tác kiểm tra thủ công"
},
ru: {
    ops_reconcile_title:"Финансовая сверка", ops_reconcile_desc:"Ежедневная проверка балансов, платежей и доставок в режиме только чтения.", ops_reconcile_run:"Проверить сейчас", ops_reconcile_running:"Проверка...", ops_reconcile_empty:"Отчёт о сверке пока недоступен.", ops_reconcile_updated:"Последняя проверка: {date}", ops_reconcile_summary:"Критических: {critical} · предупреждений: {warnings}", ops_reconcile_read_only:"Проверка не изменяет заказы, балансы или склад.", ops_reconcile_done:"Финансовая сверка завершена.", ops_reconcile_failed:"Финансовая сверка временно недоступна.",
    ops_status_healthy:"Норма", ops_status_warning:"Требует внимания", ops_status_critical:"Критично",
    ops_check_negative_wallets:"Отрицательные балансы кошельков", ops_check_stuck_paid_orders:"Оплаченные заказы зависли более чем на 15 минут", ops_check_unknown_supplier_outcomes:"Неизвестный результат покупки у поставщика", ops_check_unprofitable_supplier_orders:"Завершённые покупки у поставщика без прибыли", ops_check_completed_without_delivery:"Завершённые заказы без сохранённой доставки", ops_check_finished_provider_payments_unresolved:"Завершённые платежи поставщика не отражены в заказе",
    order_timeline_title:"Хронология", order_timeline_loading:"Загрузка хронологии...", order_timeline_empty:"События не зарегистрированы.", order_timeline_unavailable:"Хронология временно недоступна.",
    order_event_created:"Заказ создан", order_event_payment_confirmed:"Платёж подтверждён", order_event_activation_requested:"Получен идентификатор активации", order_event_activation_completed:"Активация завершена", order_event_provider_created:"Платёж поставщика создан", order_event_provider_status:"Статус платежа поставщика обновлён", order_event_provider_processed:"Платёж поставщика обработан", order_event_supplier_started:"Выполнение поставщиком начато", order_event_supplier_status:"Статус поставщика обновлён", order_event_supplier_completed:"Выполнение поставщиком завершено", order_event_stock_reserved:"Товар зарезервирован для доставки", order_event_review_action:"Ручная проверка"
}
};
Object.entries(OPERATIONS_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));

const SHELL_TRANSLATIONS = {
fr: {
    install_app:"Installer l'application", app_installed:"Application installée", pwa_install_success:"BatmanBot V2 a été installé sur cet appareil.", pwa_install_unavailable:"Utilisez le menu du navigateur puis Ajouter à l'écran d'accueil.", pwa_ios_instructions:"Sur iPhone, ouvrez ce dashboard dans Safari puis choisissez Partager → Sur l'écran d'accueil.", pwa_update_ready:"Une nouvelle version est prête. Elle sera appliquée au prochain lancement.",
    skip_to_content:"Aller au contenu", primary_navigation:"Navigation principale", sidebar_operations:"Opérations", mobile_menu:"Menu", language_label:"Langue",
    nav_group_overview:"Vue générale", nav_group_sales:"Ventes et paiements", nav_group_catalog:"Catalogue et stock", nav_group_clients:"Clients et support", nav_group_resellers:"Revendeurs et fournisseurs API", nav_group_analytics:"Analyses", nav_group_tools:"Outils et configuration",
    context_dashboard:"Vue opérationnelle", context_stats:"Tendances de ventes et produits", context_inventory:"Produits, prix et disponibilité", context_orders:"Paiements et livraisons", context_payment_review:"Anomalies de paiement et actions manuelles", context_activations:"Demandes manuelles à traiter", context_finance:"Revenus et ajustements", context_wallet:"Mouvements des soldes clients", context_users:"Clients, wallets et parrainages", context_tickets:"Demandes de support ouvertes", context_resellers:"Accès et activité API", context_suppliers:"Catalogues distants, marges et produits affichés", context_ai:"Recherche parmi tous les catalogues fournisseurs", context_game:"Matchs publiés et règlements", context_binance:"Comptes de réception", context_broadcast:"Communication aux clients", context_settings:"Connexion et paiements",
    change_theme:"Changer le thème", auto_refresh:"Actualisation automatique", export_action:"Exporter", refresh_action:"Actualiser", loading:"Chargement", chart_period:"Période des graphiques", versus_yesterday:"vs hier", metric_new_users:"Nouveaux (30J)", metric_returning_users:"Clients récurrents",
    performance_realtime:"Temps réel - 5 minutes", performance_title:"Performance du bot", collecting:"Collecte...", export_diagnostic:"Exporter le diagnostic en JSON", export_json:"Exporter JSON", workers:"Workers", recommended_placeholder:"Recommandé : -", queue:"File d'attente", processing:"Traitement", error_placeholder:"- erreur", webhook_capacity:"Capacité webhook", observation:"Observation", manual:"Manuel", off:"Arrêt", observe_only:"Observation uniquement", reset_workers:"Retour à 8", stop_autoscaling:"Arrêt autoscaling", next_analysis_placeholder:"Prochaine analyse : -", no_autoscale_decisions:"Aucune décision enregistrée.",
    retry:"Réessayer", close:"Fermer", refresh_partial_error:"Certaines données n'ont pas pu être actualisées.", refresh_total_error:"Les données de cet écran sont temporairement indisponibles.", refresh_success:"Données actualisées.", action_in_progress:"Action en cours",
    action_delivery_title:"Livraisons à relancer", action_delivery_detail:"Paiement reçu, livraison incomplète", action_activation_title:"Activations à traiter", action_activation_detail:"Identifiants clients prêts", action_payment_title:"Paiements en attente", action_payment_detail:"Commandes à contrôler", action_ticket_title:"Tickets ouverts", action_ticket_detail:"Réponses clients attendues",
    recent_orders_empty:"Aucune commande récente.", generic_customer:"Client", generic_order:"Commande #{id}", stock_activation:"Activation", stock_out_unknown:"Rupture : -", stock_out_days:"Rupture : ~{days} j", stock_manual:"Manuel", stock_sales_average:"Ventes moyennes sur 7 jours", sales_per_day:"{value}/j"
},
en: {
    install_app:"Install app", app_installed:"App installed", pwa_install_success:"BatmanBot V2 was installed on this device.", pwa_install_unavailable:"Use your browser menu and choose Add to Home screen.", pwa_ios_instructions:"On iPhone, open this dashboard in Safari, then choose Share → Add to Home Screen.", pwa_update_ready:"A new version is ready. It will be applied the next time the app starts.",
    skip_to_content:"Skip to content", primary_navigation:"Primary navigation", sidebar_operations:"Operations", mobile_menu:"Menu", language_label:"Language",
    nav_group_overview:"Overview", nav_group_sales:"Sales and payments", nav_group_catalog:"Catalog and stock", nav_group_clients:"Customers and support", nav_group_resellers:"Resellers and API suppliers", nav_group_analytics:"Analytics", nav_group_tools:"Tools and configuration",
    context_dashboard:"Operational overview", context_stats:"Sales and product trends", context_inventory:"Products, pricing and availability", context_orders:"Payments and fulfillment", context_payment_review:"Payment anomalies and manual actions", context_activations:"Manual requests to process", context_finance:"Revenue and adjustments", context_wallet:"Customer balance movements", context_users:"Customers, wallets and referrals", context_tickets:"Open support requests", context_resellers:"API access and activity", context_suppliers:"Remote catalogs, margins and displayed products", context_ai:"Search across all supplier catalogs", context_game:"Published matches and settlements", context_binance:"Receiving accounts", context_broadcast:"Customer communications", context_settings:"Connection and payments",
    change_theme:"Change theme", auto_refresh:"Automatic refresh", export_action:"Export", refresh_action:"Refresh", loading:"Loading", chart_period:"Chart period", versus_yesterday:"vs yesterday", metric_new_users:"New (30D)", metric_returning_users:"Returning customers",
    performance_realtime:"Live - 5 minutes", performance_title:"Bot performance", collecting:"Collecting...", export_diagnostic:"Export diagnostic as JSON", export_json:"Export JSON", workers:"Workers", recommended_placeholder:"Recommended: -", queue:"Queue", processing:"Processing", error_placeholder:"- error", webhook_capacity:"Webhook capacity", observation:"Observation", manual:"Manual", off:"Off", observe_only:"Observation only", reset_workers:"Reset to 8", stop_autoscaling:"Stop autoscaling", next_analysis_placeholder:"Next analysis: -", no_autoscale_decisions:"No decisions recorded.",
    retry:"Retry", close:"Close", refresh_partial_error:"Some data could not be refreshed.", refresh_total_error:"Data for this screen is temporarily unavailable.", refresh_success:"Data refreshed.", action_in_progress:"Action in progress",
    action_delivery_title:"Deliveries to retry", action_delivery_detail:"Payment received, fulfillment incomplete", action_activation_title:"Activations to process", action_activation_detail:"Customer identifiers are ready", action_payment_title:"Pending payments", action_payment_detail:"Orders requiring review", action_ticket_title:"Open tickets", action_ticket_detail:"Customer replies are waiting",
    recent_orders_empty:"No recent orders.", generic_customer:"Customer", generic_order:"Order #{id}", stock_activation:"Activation", stock_out_unknown:"Out of stock: -", stock_out_days:"Out of stock in ~{days}d", stock_manual:"Manual", stock_sales_average:"Average sales over 7 days", sales_per_day:"{value}/day"
},
ar: {
    install_app:"تثبيت التطبيق", app_installed:"التطبيق مثبت", pwa_install_success:"تم تثبيت BatmanBot V2 على هذا الجهاز.", pwa_install_unavailable:"استخدم قائمة المتصفح ثم اختر إضافة إلى الشاشة الرئيسية.", pwa_ios_instructions:"على iPhone، افتح لوحة التحكم في Safari ثم اختر مشاركة ← إضافة إلى الشاشة الرئيسية.", pwa_update_ready:"إصدار جديد جاهز وسيتم تطبيقه عند تشغيل التطبيق في المرة القادمة.",
    skip_to_content:"الانتقال إلى المحتوى", primary_navigation:"التنقل الرئيسي", sidebar_operations:"العمليات", mobile_menu:"القائمة", language_label:"اللغة",
    nav_group_overview:"نظرة عامة", nav_group_sales:"المبيعات والمدفوعات", nav_group_catalog:"الكتالوج والمخزون", nav_group_clients:"العملاء والدعم", nav_group_resellers:"الموزعون وموردو API", nav_group_analytics:"التحليلات", nav_group_tools:"الأدوات والإعدادات",
    context_dashboard:"نظرة تشغيلية", context_stats:"اتجاهات المبيعات والمنتجات", context_inventory:"المنتجات والأسعار والتوفر", context_orders:"المدفوعات والتسليم", context_payment_review:"مشكلات الدفع والإجراءات اليدوية", context_activations:"طلبات يدوية للمعالجة", context_finance:"الإيرادات والتعديلات", context_wallet:"حركات أرصدة العملاء", context_users:"العملاء والمحافظ والإحالات", context_tickets:"طلبات الدعم المفتوحة", context_resellers:"الوصول إلى API والنشاط", context_suppliers:"الكتالوجات الخارجية والهوامش والمنتجات المعروضة", context_ai:"البحث في جميع كتالوجات الموردين", context_game:"المباريات المنشورة والتسويات", context_binance:"حسابات الاستلام", context_broadcast:"التواصل مع العملاء", context_settings:"الاتصال والمدفوعات",
    change_theme:"تغيير المظهر", auto_refresh:"تحديث تلقائي", export_action:"تصدير", refresh_action:"تحديث", loading:"جارٍ التحميل", chart_period:"فترة الرسم البياني", versus_yesterday:"مقارنة بالأمس", metric_new_users:"جدد (30 يومًا)", metric_returning_users:"عملاء عائدون",
    performance_realtime:"مباشر - 5 دقائق", performance_title:"أداء البوت", collecting:"جارٍ جمع البيانات...", export_diagnostic:"تصدير التشخيص بصيغة JSON", export_json:"تصدير JSON", workers:"العمال", recommended_placeholder:"الموصى به: -", queue:"قائمة الانتظار", processing:"المعالجة", error_placeholder:"- خطأ", webhook_capacity:"سعة Webhook", observation:"مراقبة", manual:"يدوي", off:"إيقاف", observe_only:"مراقبة فقط", reset_workers:"العودة إلى 8", stop_autoscaling:"إيقاف التوسع التلقائي", next_analysis_placeholder:"التحليل التالي: -", no_autoscale_decisions:"لا توجد قرارات مسجلة.",
    retry:"إعادة المحاولة", close:"إغلاق", refresh_partial_error:"تعذر تحديث بعض البيانات.", refresh_total_error:"بيانات هذه الشاشة غير متاحة مؤقتًا.", refresh_success:"تم تحديث البيانات.", action_in_progress:"الإجراء قيد التنفيذ",
    action_delivery_title:"عمليات تسليم تحتاج إعادة المحاولة", action_delivery_detail:"تم استلام الدفع ولم يكتمل التسليم", action_activation_title:"تفعيلات تحتاج معالجة", action_activation_detail:"معرّفات العملاء جاهزة", action_payment_title:"مدفوعات معلّقة", action_payment_detail:"طلبات تحتاج إلى مراجعة", action_ticket_title:"تذاكر مفتوحة", action_ticket_detail:"ردود العملاء بانتظارك",
    recent_orders_empty:"لا توجد طلبات حديثة.", generic_customer:"العميل", generic_order:"الطلب رقم {id}", stock_activation:"تفعيل", stock_out_unknown:"نفاد المخزون: -", stock_out_days:"ينفد المخزون خلال ~{days} يوم", stock_manual:"يدوي", stock_sales_average:"متوسط المبيعات خلال 7 أيام", sales_per_day:"{value}/يوم"
},
zh: {
    install_app:"安装应用", app_installed:"应用已安装", pwa_install_success:"BatmanBot V2 已安装到此设备。", pwa_install_unavailable:"打开浏览器菜单，然后选择添加到主屏幕。", pwa_ios_instructions:"在 iPhone 上，请用 Safari 打开此控制台，然后选择分享 → 添加到主屏幕。", pwa_update_ready:"新版本已准备好，将在下次启动应用时生效。",
    skip_to_content:"跳到内容", primary_navigation:"主导航", sidebar_operations:"运营", mobile_menu:"菜单", language_label:"语言",
    nav_group_overview:"概览", nav_group_sales:"销售与支付", nav_group_catalog:"目录与库存", nav_group_clients:"客户与支持", nav_group_resellers:"经销商与 API 供应商", nav_group_analytics:"分析", nav_group_tools:"工具与配置",
    context_dashboard:"运营概览", context_stats:"销售和产品趋势", context_inventory:"产品、价格和库存", context_orders:"支付和交付", context_payment_review:"支付异常和手动操作", context_activations:"待处理的手动请求", context_finance:"收入和调整", context_wallet:"客户余额变动", context_users:"客户、钱包和推荐", context_tickets:"未处理的支持请求", context_resellers:"API 访问和活动", context_suppliers:"远程目录、利润和展示产品", context_ai:"搜索所有供应商目录", context_game:"已发布比赛和结算", context_binance:"收款账户", context_broadcast:"客户沟通", context_settings:"连接和支付",
    change_theme:"切换主题", auto_refresh:"自动刷新", export_action:"导出", refresh_action:"刷新", loading:"加载中", chart_period:"图表周期", versus_yesterday:"较昨天", metric_new_users:"新增（30天）", metric_returning_users:"回访客户",
    performance_realtime:"实时 - 5 分钟", performance_title:"机器人性能", collecting:"采集中...", export_diagnostic:"导出 JSON 诊断", export_json:"导出 JSON", workers:"工作线程", recommended_placeholder:"建议：-", queue:"队列", processing:"处理中", error_placeholder:"- 个错误", webhook_capacity:"Webhook 容量", observation:"观察", manual:"手动", off:"关闭", observe_only:"仅观察", reset_workers:"重置为 8", stop_autoscaling:"停止自动扩缩", next_analysis_placeholder:"下次分析：-", no_autoscale_decisions:"暂无决策记录。",
    retry:"重试", close:"关闭", refresh_partial_error:"部分数据无法刷新。", refresh_total_error:"此页面的数据暂时不可用。", refresh_success:"数据已刷新。", action_in_progress:"操作进行中",
    action_delivery_title:"需要重试的交付", action_delivery_detail:"已收到付款，但交付未完成", action_activation_title:"待处理的激活", action_activation_detail:"客户标识已就绪", action_payment_title:"待处理付款", action_payment_detail:"需要检查的订单", action_ticket_title:"未处理工单", action_ticket_detail:"客户回复正在等待处理",
    recent_orders_empty:"暂无最近订单。", generic_customer:"客户", generic_order:"订单 #{id}", stock_activation:"激活", stock_out_unknown:"预计售罄：-", stock_out_days:"预计约 {days} 天售罄", stock_manual:"手动", stock_sales_average:"过去 7 天平均销量", sales_per_day:"{value}/天"
},
vi: {
    install_app:"Cài đặt ứng dụng", app_installed:"Ứng dụng đã cài", pwa_install_success:"BatmanBot V2 đã được cài đặt trên thiết bị này.", pwa_install_unavailable:"Mở menu trình duyệt rồi chọn Thêm vào màn hình chính.", pwa_ios_instructions:"Trên iPhone, hãy mở dashboard này bằng Safari rồi chọn Chia sẻ → Thêm vào Màn hình chính.", pwa_update_ready:"Phiên bản mới đã sẵn sàng và sẽ được áp dụng vào lần mở ứng dụng tiếp theo.",
    skip_to_content:"Chuyển đến nội dung", primary_navigation:"Điều hướng chính", sidebar_operations:"Vận hành", mobile_menu:"Menu", language_label:"Ngôn ngữ",
    nav_group_overview:"Tổng quan", nav_group_sales:"Bán hàng và thanh toán", nav_group_catalog:"Danh mục và tồn kho", nav_group_clients:"Khách hàng và hỗ trợ", nav_group_resellers:"Đại lý và nhà cung cấp API", nav_group_analytics:"Phân tích", nav_group_tools:"Công cụ và cấu hình",
    context_dashboard:"Tổng quan vận hành", context_stats:"Xu hướng bán hàng và sản phẩm", context_inventory:"Sản phẩm, giá và tình trạng", context_orders:"Thanh toán và giao hàng", context_payment_review:"Bất thường thanh toán và thao tác thủ công", context_activations:"Yêu cầu thủ công cần xử lý", context_finance:"Doanh thu và điều chỉnh", context_wallet:"Biến động số dư khách hàng", context_users:"Khách hàng, ví và giới thiệu", context_tickets:"Yêu cầu hỗ trợ đang mở", context_resellers:"Quyền truy cập và hoạt động API", context_suppliers:"Danh mục từ xa, biên lợi nhuận và sản phẩm hiển thị", context_ai:"Tìm kiếm trong mọi danh mục nhà cung cấp", context_game:"Trận đấu đã đăng và quyết toán", context_binance:"Tài khoản nhận tiền", context_broadcast:"Truyền thông khách hàng", context_settings:"Kết nối và thanh toán",
    change_theme:"Đổi giao diện", auto_refresh:"Tự động làm mới", export_action:"Xuất", refresh_action:"Làm mới", loading:"Đang tải", chart_period:"Khoảng thời gian biểu đồ", versus_yesterday:"so với hôm qua", metric_new_users:"Mới (30 ngày)", metric_returning_users:"Khách quay lại",
    performance_realtime:"Trực tiếp - 5 phút", performance_title:"Hiệu suất bot", collecting:"Đang thu thập...", export_diagnostic:"Xuất chẩn đoán JSON", export_json:"Xuất JSON", workers:"Worker", recommended_placeholder:"Đề xuất: -", queue:"Hàng đợi", processing:"Xử lý", error_placeholder:"- lỗi", webhook_capacity:"Công suất webhook", observation:"Quan sát", manual:"Thủ công", off:"Tắt", observe_only:"Chỉ quan sát", reset_workers:"Đặt lại về 8", stop_autoscaling:"Dừng tự động điều chỉnh", next_analysis_placeholder:"Lần phân tích tiếp theo: -", no_autoscale_decisions:"Chưa có quyết định nào.",
    retry:"Thử lại", close:"Đóng", refresh_partial_error:"Không thể làm mới một số dữ liệu.", refresh_total_error:"Dữ liệu của màn hình này tạm thời không khả dụng.", refresh_success:"Đã làm mới dữ liệu.", action_in_progress:"Đang thực hiện",
    action_delivery_title:"Đơn giao cần thử lại", action_delivery_detail:"Đã nhận thanh toán nhưng giao hàng chưa hoàn tất", action_activation_title:"Kích hoạt cần xử lý", action_activation_detail:"Mã khách hàng đã sẵn sàng", action_payment_title:"Thanh toán đang chờ", action_payment_detail:"Đơn hàng cần kiểm tra", action_ticket_title:"Yêu cầu đang mở", action_ticket_detail:"Phản hồi khách hàng đang chờ xử lý",
    recent_orders_empty:"Không có đơn hàng gần đây.", generic_customer:"Khách hàng", generic_order:"Đơn hàng #{id}", stock_activation:"Kích hoạt", stock_out_unknown:"Hết hàng: -", stock_out_days:"Dự kiến hết hàng sau ~{days} ngày", stock_manual:"Thủ công", stock_sales_average:"Doanh số trung bình trong 7 ngày", sales_per_day:"{value}/ngày"
},
ru: {
    install_app:"Установить приложение", app_installed:"Приложение установлено", pwa_install_success:"BatmanBot V2 установлен на этом устройстве.", pwa_install_unavailable:"Откройте меню браузера и выберите Добавить на главный экран.", pwa_ios_instructions:"На iPhone откройте панель в Safari и выберите Поделиться → На экран «Домой».", pwa_update_ready:"Новая версия готова и будет применена при следующем запуске приложения.",
    skip_to_content:"Перейти к содержимому", primary_navigation:"Основная навигация", sidebar_operations:"Операции", mobile_menu:"Меню", language_label:"Язык",
    nav_group_overview:"Обзор", nav_group_sales:"Продажи и платежи", nav_group_catalog:"Каталог и склад", nav_group_clients:"Клиенты и поддержка", nav_group_resellers:"Реселлеры и API-поставщики", nav_group_analytics:"Аналитика", nav_group_tools:"Инструменты и настройки",
    context_dashboard:"Оперативный обзор", context_stats:"Тенденции продаж и товаров", context_inventory:"Товары, цены и наличие", context_orders:"Платежи и доставка", context_payment_review:"Проблемы платежей и ручные действия", context_activations:"Ручные запросы в обработке", context_finance:"Доходы и корректировки", context_wallet:"Движения балансов клиентов", context_users:"Клиенты, кошельки и рефералы", context_tickets:"Открытые запросы поддержки", context_resellers:"Доступ и активность API", context_suppliers:"Внешние каталоги, наценки и опубликованные товары", context_ai:"Поиск по всем каталогам поставщиков", context_game:"Опубликованные матчи и расчёты", context_binance:"Счета получения", context_broadcast:"Связь с клиентами", context_settings:"Подключение и платежи",
    change_theme:"Сменить тему", auto_refresh:"Автообновление", export_action:"Экспорт", refresh_action:"Обновить", loading:"Загрузка", chart_period:"Период графика", versus_yesterday:"к вчера", metric_new_users:"Новые (30 дн.)", metric_returning_users:"Повторные клиенты",
    performance_realtime:"Онлайн - 5 минут", performance_title:"Производительность бота", collecting:"Сбор данных...", export_diagnostic:"Экспорт диагностики в JSON", export_json:"Экспорт JSON", workers:"Воркеры", recommended_placeholder:"Рекомендуется: -", queue:"Очередь", processing:"Обработка", error_placeholder:"- ошибок", webhook_capacity:"Ёмкость webhook", observation:"Наблюдение", manual:"Вручную", off:"Выключено", observe_only:"Только наблюдение", reset_workers:"Вернуть 8", stop_autoscaling:"Остановить автомасштабирование", next_analysis_placeholder:"Следующий анализ: -", no_autoscale_decisions:"Решений пока нет.",
    retry:"Повторить", close:"Закрыть", refresh_partial_error:"Не удалось обновить часть данных.", refresh_total_error:"Данные этого экрана временно недоступны.", refresh_success:"Данные обновлены.", action_in_progress:"Действие выполняется",
    action_delivery_title:"Доставки для повтора", action_delivery_detail:"Платёж получен, доставка не завершена", action_activation_title:"Активации в обработке", action_activation_detail:"Идентификаторы клиентов готовы", action_payment_title:"Ожидающие платежи", action_payment_detail:"Заказы требуют проверки", action_ticket_title:"Открытые обращения", action_ticket_detail:"Ожидаются ответы клиентам",
    recent_orders_empty:"Недавних заказов нет.", generic_customer:"Клиент", generic_order:"Заказ #{id}", stock_activation:"Активация", stock_out_unknown:"До исчерпания: -", stock_out_days:"До исчерпания ~{days} дн.", stock_manual:"Вручную", stock_sales_average:"Средние продажи за 7 дней", sales_per_day:"{value}/день"
}
};
Object.entries(SHELL_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
const DASHBOARD_DETAIL_TRANSLATIONS = {
fr: {revenue_details:"Détails des revenus (30J)", revenue_store:"Ventes (boutique)", revenue_topups:"Recharges (wallet)", revenue_deductions:"Déductions (remboursements)", revenue_net:"Total net", worker_manual_controls:"Réglage manuel des workers", worker_remove:"Retirer un worker inactif", worker_add:"Ajouter un worker"},
en: {revenue_details:"Revenue details (30D)", revenue_store:"Store sales", revenue_topups:"Wallet top-ups", revenue_deductions:"Deductions (refunds)", revenue_net:"Net total", worker_manual_controls:"Manual worker controls", worker_remove:"Remove an idle worker", worker_add:"Add a worker"},
ar: {revenue_details:"تفاصيل الإيرادات (30 يومًا)", revenue_store:"مبيعات المتجر", revenue_topups:"شحن المحفظة", revenue_deductions:"الخصومات (المبالغ المستردة)", revenue_net:"الصافي", worker_manual_controls:"التحكم اليدوي بالعمال", worker_remove:"إزالة عامل خامل", worker_add:"إضافة عامل"},
zh: {revenue_details:"收入明细（30天）", revenue_store:"商店销售", revenue_topups:"钱包充值", revenue_deductions:"扣款（退款）", revenue_net:"净额", worker_manual_controls:"手动工作线程控制", worker_remove:"移除空闲工作线程", worker_add:"添加工作线程"},
vi: {revenue_details:"Chi tiết doanh thu (30 ngày)", revenue_store:"Doanh số cửa hàng", revenue_topups:"Nạp ví", revenue_deductions:"Khấu trừ (hoàn tiền)", revenue_net:"Tổng ròng", worker_manual_controls:"Điều khiển worker thủ công", worker_remove:"Bớt một worker đang rảnh", worker_add:"Thêm một worker"},
ru: {revenue_details:"Детали выручки (30 дней)", revenue_store:"Продажи магазина", revenue_topups:"Пополнения кошелька", revenue_deductions:"Списания (возвраты)", revenue_net:"Итого нетто", worker_manual_controls:"Ручное управление воркерами", worker_remove:"Убрать свободный воркер", worker_add:"Добавить воркер"}
};
Object.entries(DASHBOARD_DETAIL_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
Object.assign(LANG.ar, {nav_payment_review:'مراقبة المدفوعات', payment_review_title:'مركز مراقبة المدفوعات', conversion_title:'مسار التحويل'});
Object.assign(LANG.zh, {nav_payment_review:'支付监控', payment_review_title:'支付监控中心', conversion_title:'转化漏斗'});
Object.assign(LANG.vi, {nav_payment_review:'Kiểm soát thanh toán', payment_review_title:'Trung tâm kiểm soát thanh toán', conversion_title:'Phễu chuyển đổi'});
Object.assign(LANG.ru, {nav_payment_review:'Контроль платежей', payment_review_title:'Центр контроля платежей', conversion_title:'Воронка конверсии'});
const LEGACY_SCREEN_TRANSLATIONS = {
fr: {
    translate_all:"✨ Traduire tout", table_stock:"Stock", table_actions:"Actions", table_code:"Code", table_order_number:"N° Commande", table_supplier:"Fournisseur", table_received_expected:"Reçu / attendu", table_issue:"Problème", table_updated:"Mis à jour",
    stats_best_product:"Meilleur produit", stats_sales_volume:"Volume de ventes", stats_stock_alerts:"Alertes de stock", stats_restock_help:"Produits à restocker (< 3)", stats_momentum_description:"Ventes quotidiennes sur 30 jours. Cliquez sur un produit pour l'afficher ou le masquer.", stats_view_30:"Vue : 30 jours", stats_yesterday_none:"Hier : -", conversion_tracking_note:"Mesure comparable depuis le premier clic Acheter suivi.", conversion_rate_none:"Conversion : -", conversion_loading:"Chargement du tunnel...", conversion_popular_low:"Produits populaires qui convertissent mal", stats_watch_products:"Produits à surveiller", stats_alert_loading:"Chargement des alertes...", stats_product_performance:"Performances des produits", stats_search_product:"Rechercher un produit...", stats_loading:"Chargement des statistiques...",
    finance_today:"Revenus (aujourd'hui)", finance_7d:"Revenus (7 jours)", finance_30d:"Revenus (30 jours)", finance_operational_balance:"Solde opérationnel suivi", finance_sales_breakdown:"Répartition des ventes (30 jours)", finance_binance_sales:"Achats Binance Pay", finance_bep20_sales:"Achats BEP20", finance_trc20_sales:"Achats TRC20", finance_wallet_sales:"Achats par wallet", finance_total_topup:"Montant total rechargé", finance_topup_count:"Nombre de recharges",
    review_description:"Sous-paiements, confirmations, expirations et paiements reçus après annulation.", review_to_process:"À traiter", review_underpaid:"Sous-payés", review_confirming:"En confirmation", review_after_cancel:"Après annulation", review_expired:"Expirés", review_all:"Tous", review_confirmations:"Confirmations", review_validation:"Validation", review_empty:"Aucun paiement dans cette catégorie.",
    common_product:"Produit", common_views:"Vues", common_buy_clicks:"Clics Acheter", common_payments_created:"Paiements créés", common_completed:"Terminés", common_conversion:"Conversion", common_price:"Prix", common_quantity_sold:"Quantité vendue", common_revenue:"Chiffre d'affaires", common_stock_remaining:"Stock restant", common_performance_status:"Performance / Statut", common_client:"Client", common_status:"État", common_date:"Date", common_action:"Action"
},
en: {
    translate_all:"✨ Translate all", table_stock:"Stock", table_actions:"Actions", table_code:"Code", table_order_number:"Order no.", table_supplier:"Supplier", table_received_expected:"Received / expected", table_issue:"Issue", table_updated:"Updated",
    stats_best_product:"Top product", stats_sales_volume:"Sales volume", stats_stock_alerts:"Stock alerts", stats_restock_help:"Products to restock (< 3)", stats_momentum_description:"Daily sales over 30 days. Select a product to show or hide it.", stats_view_30:"View: 30 days", stats_yesterday_none:"Yesterday: -", conversion_tracking_note:"Comparable tracking starts with the first recorded Buy click.", conversion_rate_none:"Conversion: -", conversion_loading:"Loading funnel...", conversion_popular_low:"Popular products with low conversion", stats_watch_products:"Products to watch", stats_alert_loading:"Loading alerts...", stats_product_performance:"Product performance", stats_search_product:"Search for a product...", stats_loading:"Loading statistics...",
    finance_today:"Revenue (today)", finance_7d:"Revenue (7 days)", finance_30d:"Revenue (30 days)", finance_operational_balance:"Tracked operating balance", finance_sales_breakdown:"Sales breakdown (30 days)", finance_binance_sales:"Binance Pay purchases", finance_bep20_sales:"BEP20 purchases", finance_trc20_sales:"TRC20 purchases", finance_wallet_sales:"Wallet purchases", finance_total_topup:"Total amount topped up", finance_topup_count:"Number of top-ups",
    review_description:"Underpayments, confirmations, expirations and payments received after cancellation.", review_to_process:"Needs action", review_underpaid:"Underpaid", review_confirming:"Confirming", review_after_cancel:"After cancellation", review_expired:"Expired", review_all:"All", review_confirmations:"Confirmations", review_validation:"Validation", review_empty:"No payments in this category.",
    common_product:"Product", common_views:"Views", common_buy_clicks:"Buy clicks", common_payments_created:"Payments created", common_completed:"Completed", common_conversion:"Conversion", common_price:"Price", common_quantity_sold:"Quantity sold", common_revenue:"Revenue", common_stock_remaining:"Stock remaining", common_performance_status:"Performance / status", common_client:"Customer", common_status:"Status", common_date:"Date", common_action:"Action"
},
ar: {
    translate_all:"✨ ترجمة الكل", table_stock:"المخزون", table_actions:"الإجراءات", table_code:"الرمز", table_order_number:"رقم الطلب", table_supplier:"المورد", table_received_expected:"المستلم / المتوقع", table_issue:"المشكلة", table_updated:"آخر تحديث",
    stats_best_product:"أفضل منتج", stats_sales_volume:"حجم المبيعات", stats_stock_alerts:"تنبيهات المخزون", stats_restock_help:"منتجات تحتاج إعادة تخزين (< 3)", stats_momentum_description:"المبيعات اليومية خلال 30 يومًا. اختر منتجًا لإظهاره أو إخفائه.", stats_view_30:"العرض: 30 يومًا", stats_yesterday_none:"الأمس: -", conversion_tracking_note:"تبدأ المقارنة من أول نقرة شراء مسجلة.", conversion_rate_none:"التحويل: -", conversion_loading:"جارٍ تحميل مسار التحويل...", conversion_popular_low:"منتجات شائعة ذات تحويل منخفض", stats_watch_products:"منتجات تحتاج متابعة", stats_alert_loading:"جارٍ تحميل التنبيهات...", stats_product_performance:"أداء المنتجات", stats_search_product:"ابحث عن منتج...", stats_loading:"جارٍ تحميل الإحصائيات...",
    finance_today:"إيرادات اليوم", finance_7d:"إيرادات 7 أيام", finance_30d:"إيرادات 30 يومًا", finance_operational_balance:"الرصيد التشغيلي المتابع", finance_sales_breakdown:"توزيع المبيعات (30 يومًا)", finance_binance_sales:"مشتريات Binance Pay", finance_bep20_sales:"مشتريات BEP20", finance_trc20_sales:"مشتريات TRC20", finance_wallet_sales:"مشتريات المحفظة", finance_total_topup:"إجمالي مبالغ الشحن", finance_topup_count:"عدد عمليات الشحن",
    review_description:"المدفوعات الناقصة والتأكيدات وحالات الانتهاء والمدفوعات المستلمة بعد الإلغاء.", review_to_process:"تحتاج إجراء", review_underpaid:"مدفوعة جزئيًا", review_confirming:"قيد التأكيد", review_after_cancel:"بعد الإلغاء", review_expired:"منتهية", review_all:"الكل", review_confirmations:"التأكيدات", review_validation:"التحقق", review_empty:"لا توجد مدفوعات في هذه الفئة.",
    common_product:"المنتج", common_views:"المشاهدات", common_buy_clicks:"نقرات الشراء", common_payments_created:"مدفوعات منشأة", common_completed:"مكتملة", common_conversion:"التحويل", common_price:"السعر", common_quantity_sold:"الكمية المباعة", common_revenue:"الإيرادات", common_stock_remaining:"المخزون المتبقي", common_performance_status:"الأداء / الحالة", common_client:"العميل", common_status:"الحالة", common_date:"التاريخ", common_action:"الإجراء"
},
zh: {
    translate_all:"✨ 全部翻译", table_stock:"库存", table_actions:"操作", table_code:"代码", table_order_number:"订单号", table_supplier:"供应商", table_received_expected:"已收 / 应收", table_issue:"问题", table_updated:"更新时间",
    stats_best_product:"最佳产品", stats_sales_volume:"销量", stats_stock_alerts:"库存提醒", stats_restock_help:"需要补货的产品（< 3）", stats_momentum_description:"过去 30 天的每日销量。选择产品可显示或隐藏。", stats_view_30:"视图：30 天", stats_yesterday_none:"昨天：-", conversion_tracking_note:"可比数据从首次记录的购买点击开始。", conversion_rate_none:"转化率：-", conversion_loading:"正在加载漏斗...", conversion_popular_low:"热门但转化率较低的产品", stats_watch_products:"需要关注的产品", stats_alert_loading:"正在加载提醒...", stats_product_performance:"产品表现", stats_search_product:"搜索产品...", stats_loading:"正在加载统计数据...",
    finance_today:"今日收入", finance_7d:"7 天收入", finance_30d:"30 天收入", finance_operational_balance:"跟踪的运营余额", finance_sales_breakdown:"销售构成（30 天）", finance_binance_sales:"Binance Pay 购买", finance_bep20_sales:"BEP20 购买", finance_trc20_sales:"TRC20 购买", finance_wallet_sales:"钱包购买", finance_total_topup:"充值总额", finance_topup_count:"充值次数",
    review_description:"付款不足、确认中、已过期以及取消后收到的付款。", review_to_process:"需要处理", review_underpaid:"付款不足", review_confirming:"确认中", review_after_cancel:"取消后收到", review_expired:"已过期", review_all:"全部", review_confirmations:"确认", review_validation:"验证", review_empty:"此类别中没有付款。",
    common_product:"产品", common_views:"浏览", common_buy_clicks:"购买点击", common_payments_created:"已创建付款", common_completed:"已完成", common_conversion:"转化率", common_price:"价格", common_quantity_sold:"售出数量", common_revenue:"收入", common_stock_remaining:"剩余库存", common_performance_status:"表现 / 状态", common_client:"客户", common_status:"状态", common_date:"日期", common_action:"操作"
},
vi: {
    translate_all:"✨ Dịch tất cả", table_stock:"Tồn kho", table_actions:"Thao tác", table_code:"Mã", table_order_number:"Mã đơn", table_supplier:"Nhà cung cấp", table_received_expected:"Đã nhận / dự kiến", table_issue:"Vấn đề", table_updated:"Cập nhật",
    stats_best_product:"Sản phẩm tốt nhất", stats_sales_volume:"Sản lượng bán", stats_stock_alerts:"Cảnh báo tồn kho", stats_restock_help:"Sản phẩm cần nhập thêm (< 3)", stats_momentum_description:"Doanh số hằng ngày trong 30 ngày. Chọn sản phẩm để hiện hoặc ẩn.", stats_view_30:"Khung nhìn: 30 ngày", stats_yesterday_none:"Hôm qua: -", conversion_tracking_note:"Dữ liệu so sánh bắt đầu từ lần nhấn Mua đầu tiên được ghi nhận.", conversion_rate_none:"Chuyển đổi: -", conversion_loading:"Đang tải phễu...", conversion_popular_low:"Sản phẩm phổ biến có chuyển đổi thấp", stats_watch_products:"Sản phẩm cần theo dõi", stats_alert_loading:"Đang tải cảnh báo...", stats_product_performance:"Hiệu suất sản phẩm", stats_search_product:"Tìm sản phẩm...", stats_loading:"Đang tải thống kê...",
    finance_today:"Doanh thu hôm nay", finance_7d:"Doanh thu 7 ngày", finance_30d:"Doanh thu 30 ngày", finance_operational_balance:"Số dư vận hành theo dõi", finance_sales_breakdown:"Cơ cấu doanh số (30 ngày)", finance_binance_sales:"Mua qua Binance Pay", finance_bep20_sales:"Mua qua BEP20", finance_trc20_sales:"Mua qua TRC20", finance_wallet_sales:"Mua bằng ví", finance_total_topup:"Tổng tiền đã nạp", finance_topup_count:"Số lần nạp",
    review_description:"Thanh toán thiếu, đang xác nhận, hết hạn và khoản nhận sau khi hủy.", review_to_process:"Cần xử lý", review_underpaid:"Thanh toán thiếu", review_confirming:"Đang xác nhận", review_after_cancel:"Sau khi hủy", review_expired:"Đã hết hạn", review_all:"Tất cả", review_confirmations:"Xác nhận", review_validation:"Xác minh", review_empty:"Không có khoản thanh toán trong mục này.",
    common_product:"Sản phẩm", common_views:"Lượt xem", common_buy_clicks:"Lượt nhấn Mua", common_payments_created:"Thanh toán đã tạo", common_completed:"Hoàn tất", common_conversion:"Chuyển đổi", common_price:"Giá", common_quantity_sold:"Số lượng đã bán", common_revenue:"Doanh thu", common_stock_remaining:"Tồn kho còn lại", common_performance_status:"Hiệu suất / trạng thái", common_client:"Khách hàng", common_status:"Trạng thái", common_date:"Ngày", common_action:"Thao tác"
},
ru: {
    translate_all:"✨ Перевести всё", table_stock:"Склад", table_actions:"Действия", table_code:"Код", table_order_number:"Номер заказа", table_supplier:"Поставщик", table_received_expected:"Получено / ожидается", table_issue:"Проблема", table_updated:"Обновлено",
    stats_best_product:"Лучший товар", stats_sales_volume:"Объём продаж", stats_stock_alerts:"Предупреждения по складу", stats_restock_help:"Товары для пополнения (< 3)", stats_momentum_description:"Ежедневные продажи за 30 дней. Выберите товар, чтобы показать или скрыть его.", stats_view_30:"Период: 30 дней", stats_yesterday_none:"Вчера: -", conversion_tracking_note:"Сопоставимые данные начинаются с первого зарегистрированного нажатия «Купить».", conversion_rate_none:"Конверсия: -", conversion_loading:"Загрузка воронки...", conversion_popular_low:"Популярные товары с низкой конверсией", stats_watch_products:"Товары под наблюдением", stats_alert_loading:"Загрузка предупреждений...", stats_product_performance:"Эффективность товаров", stats_search_product:"Найти товар...", stats_loading:"Загрузка статистики...",
    finance_today:"Выручка сегодня", finance_7d:"Выручка за 7 дней", finance_30d:"Выручка за 30 дней", finance_operational_balance:"Отслеживаемый операционный баланс", finance_sales_breakdown:"Распределение продаж (30 дней)", finance_binance_sales:"Покупки через Binance Pay", finance_bep20_sales:"Покупки через BEP20", finance_trc20_sales:"Покупки через TRC20", finance_wallet_sales:"Покупки из кошелька", finance_total_topup:"Общая сумма пополнений", finance_topup_count:"Количество пополнений",
    review_description:"Недоплаты, подтверждения, истёкшие платежи и поступления после отмены.", review_to_process:"Требуют действий", review_underpaid:"Недоплата", review_confirming:"Подтверждаются", review_after_cancel:"После отмены", review_expired:"Истекли", review_all:"Все", review_confirmations:"Подтверждения", review_validation:"Проверка", review_empty:"В этой категории нет платежей.",
    common_product:"Товар", common_views:"Просмотры", common_buy_clicks:"Нажатия «Купить»", common_payments_created:"Создано платежей", common_completed:"Завершено", common_conversion:"Конверсия", common_price:"Цена", common_quantity_sold:"Продано", common_revenue:"Выручка", common_stock_remaining:"Остаток", common_performance_status:"Эффективность / статус", common_client:"Клиент", common_status:"Статус", common_date:"Дата", common_action:"Действие"
}
};
Object.entries(LEGACY_SCREEN_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
Object.assign(LANG.fr, {stats_zero_sales:"0 vente", stats_zero_revenue:"0,00 $ de revenus", stats_revenue_by_product:"Chiffre d'affaires par produit", stats_momentum_title:"Momentum des ventes par produit"});
Object.assign(LANG.en, {stats_zero_sales:"0 sales", stats_zero_revenue:"$0.00 revenue", stats_revenue_by_product:"Revenue by product", stats_momentum_title:"Sales momentum by product"});
Object.assign(LANG.ar, {stats_zero_sales:"0 مبيعات", stats_zero_revenue:"إيرادات 0.00 $", stats_revenue_by_product:"الإيرادات حسب المنتج", stats_momentum_title:"زخم المبيعات حسب المنتج"});
Object.assign(LANG.zh, {stats_zero_sales:"0 笔销售", stats_zero_revenue:"收入 $0.00", stats_revenue_by_product:"各产品收入", stats_momentum_title:"各产品销售趋势"});
Object.assign(LANG.vi, {stats_zero_sales:"0 lượt bán", stats_zero_revenue:"Doanh thu $0.00", stats_revenue_by_product:"Doanh thu theo sản phẩm", stats_momentum_title:"Đà bán hàng theo sản phẩm"});
Object.assign(LANG.ru, {stats_zero_sales:"0 продаж", stats_zero_revenue:"Выручка $0.00", stats_revenue_by_product:"Выручка по товарам", stats_momentum_title:"Динамика продаж по товарам"});
const STATS_DYNAMIC_TRANSLATIONS = {
fr: {stats_sales_revenue:"{count} vente(s) ({revenue})", stats_no_sales:"Aucune vente", stats_other_products:"Autres produits", stats_no_sales_recorded:"Aucune vente enregistrée", stats_no_product_sales:"Aucune vente produit sur la période.", stats_yesterday_sales:"Hier : {count} vente(s)", stats_product_period:"Hier : {yesterday} · 30 j : {total}", stats_view_range:"Vue : {start} → {end}", stats_toggle_product:"Afficher ou masquer {product}", stats_units_revenue:"{count} vente(s) · {revenue}", stats_momentum_unavailable:"Impossible de charger le momentum.", stats_alerts_unavailable:"Impossible de charger les alertes produits.", stats_no_low_conversion_alert:"Aucune alerte : pas encore assez de vues avec une faible conversion.", stats_views_count:"{count} vues", stats_sales_count:"{count} ventes", conversion_unavailable:"Impossible de charger le tunnel de conversion.", data_unavailable:"Données indisponibles.", conversion_stage_view:"Produit affiché", conversion_stage_buy:"Clic Acheter", conversion_stage_created:"Paiement créé", conversion_stage_completed:"Paiement terminé", conversion_entry_point:"Point d'entrée", conversion_direct_entries:"Entrées directes incluses", conversion_previous_rate:"{rate}% de l'étape précédente", conversion_global:"Conversion globale : {rate}%", conversion_tracking_since:"Fenêtre comparable depuis {date}. Les achats directs sont inclus.", conversion_tracking_future:"Le suivi des clics Acheter commencera après le déploiement de cette version.", conversion_not_enough:"Pas encore assez de données comparables."},
en: {stats_sales_revenue:"{count} sale(s) ({revenue})", stats_no_sales:"No sales", stats_other_products:"Other products", stats_no_sales_recorded:"No recorded sales", stats_no_product_sales:"No product sales during this period.", stats_yesterday_sales:"Yesterday: {count} sale(s)", stats_product_period:"Yesterday: {yesterday} · 30D: {total}", stats_view_range:"View: {start} → {end}", stats_toggle_product:"Show or hide {product}", stats_units_revenue:"{count} sale(s) · {revenue}", stats_momentum_unavailable:"Unable to load sales momentum.", stats_alerts_unavailable:"Unable to load product alerts.", stats_no_low_conversion_alert:"No alerts: there is not enough low-conversion traffic yet.", stats_views_count:"{count} views", stats_sales_count:"{count} sales", conversion_unavailable:"Unable to load the conversion funnel.", data_unavailable:"Data unavailable.", conversion_stage_view:"Product viewed", conversion_stage_buy:"Buy click", conversion_stage_created:"Payment created", conversion_stage_completed:"Payment completed", conversion_entry_point:"Entry point", conversion_direct_entries:"Direct entries included", conversion_previous_rate:"{rate}% of the previous stage", conversion_global:"Overall conversion: {rate}%", conversion_tracking_since:"Comparable window since {date}. Direct purchases are included.", conversion_tracking_future:"Buy-click tracking will begin after this version is deployed.", conversion_not_enough:"Not enough comparable data yet."},
ar: {stats_sales_revenue:"{count} مبيعات ({revenue})", stats_no_sales:"لا توجد مبيعات", stats_other_products:"منتجات أخرى", stats_no_sales_recorded:"لا توجد مبيعات مسجلة", stats_no_product_sales:"لا توجد مبيعات منتجات في هذه الفترة.", stats_yesterday_sales:"الأمس: {count} مبيعات", stats_product_period:"الأمس: {yesterday} · 30 يومًا: {total}", stats_view_range:"العرض: {start} ← {end}", stats_toggle_product:"إظهار أو إخفاء {product}", stats_units_revenue:"{count} مبيعات · {revenue}", stats_momentum_unavailable:"تعذر تحميل زخم المبيعات.", stats_alerts_unavailable:"تعذر تحميل تنبيهات المنتجات.", stats_no_low_conversion_alert:"لا توجد تنبيهات: لا توجد بيانات كافية عن التحويل المنخفض بعد.", stats_views_count:"{count} مشاهدة", stats_sales_count:"{count} مبيعات", conversion_unavailable:"تعذر تحميل مسار التحويل.", data_unavailable:"البيانات غير متاحة.", conversion_stage_view:"تمت مشاهدة المنتج", conversion_stage_buy:"نقرة شراء", conversion_stage_created:"تم إنشاء الدفع", conversion_stage_completed:"اكتمل الدفع", conversion_entry_point:"نقطة الدخول", conversion_direct_entries:"تشمل الإدخالات المباشرة", conversion_previous_rate:"{rate}% من المرحلة السابقة", conversion_global:"التحويل الإجمالي: {rate}%", conversion_tracking_since:"نافذة قابلة للمقارنة منذ {date}. تشمل المشتريات المباشرة.", conversion_tracking_future:"سيبدأ تتبع نقرات الشراء بعد نشر هذا الإصدار.", conversion_not_enough:"لا توجد بيانات قابلة للمقارنة بعد."},
zh: {stats_sales_revenue:"{count} 笔销售（{revenue}）", stats_no_sales:"暂无销售", stats_other_products:"其他产品", stats_no_sales_recorded:"暂无销售记录", stats_no_product_sales:"此期间没有产品销售。", stats_yesterday_sales:"昨天：{count} 笔", stats_product_period:"昨天：{yesterday} · 30 天：{total}", stats_view_range:"视图：{start} → {end}", stats_toggle_product:"显示或隐藏 {product}", stats_units_revenue:"{count} 笔销售 · {revenue}", stats_momentum_unavailable:"无法加载销售趋势。", stats_alerts_unavailable:"无法加载产品提醒。", stats_no_low_conversion_alert:"暂无提醒：低转化流量数据仍不足。", stats_views_count:"{count} 次浏览", stats_sales_count:"{count} 笔销售", conversion_unavailable:"无法加载转化漏斗。", data_unavailable:"数据不可用。", conversion_stage_view:"产品浏览", conversion_stage_buy:"购买点击", conversion_stage_created:"创建付款", conversion_stage_completed:"完成付款", conversion_entry_point:"入口", conversion_direct_entries:"包含直接进入", conversion_previous_rate:"上一阶段的 {rate}%", conversion_global:"总转化率：{rate}%", conversion_tracking_since:"可比窗口从 {date} 开始，包含直接购买。", conversion_tracking_future:"此版本部署后将开始跟踪购买点击。", conversion_not_enough:"暂无足够的可比数据。"},
vi: {stats_sales_revenue:"{count} lượt bán ({revenue})", stats_no_sales:"Chưa có lượt bán", stats_other_products:"Sản phẩm khác", stats_no_sales_recorded:"Chưa ghi nhận lượt bán", stats_no_product_sales:"Không có sản phẩm bán ra trong giai đoạn này.", stats_yesterday_sales:"Hôm qua: {count} lượt", stats_product_period:"Hôm qua: {yesterday} · 30 ngày: {total}", stats_view_range:"Khung nhìn: {start} → {end}", stats_toggle_product:"Hiện hoặc ẩn {product}", stats_units_revenue:"{count} lượt bán · {revenue}", stats_momentum_unavailable:"Không thể tải đà bán hàng.", stats_alerts_unavailable:"Không thể tải cảnh báo sản phẩm.", stats_no_low_conversion_alert:"Không có cảnh báo: chưa đủ lưu lượng chuyển đổi thấp.", stats_views_count:"{count} lượt xem", stats_sales_count:"{count} lượt bán", conversion_unavailable:"Không thể tải phễu chuyển đổi.", data_unavailable:"Dữ liệu không khả dụng.", conversion_stage_view:"Đã xem sản phẩm", conversion_stage_buy:"Nhấn Mua", conversion_stage_created:"Đã tạo thanh toán", conversion_stage_completed:"Đã hoàn tất thanh toán", conversion_entry_point:"Điểm vào", conversion_direct_entries:"Bao gồm lượt vào trực tiếp", conversion_previous_rate:"{rate}% so với bước trước", conversion_global:"Chuyển đổi tổng: {rate}%", conversion_tracking_since:"Khoảng so sánh từ {date}. Bao gồm mua trực tiếp.", conversion_tracking_future:"Theo dõi lượt nhấn Mua sẽ bắt đầu sau khi triển khai phiên bản này.", conversion_not_enough:"Chưa đủ dữ liệu để so sánh."},
ru: {stats_sales_revenue:"{count} продаж ({revenue})", stats_no_sales:"Продаж нет", stats_other_products:"Другие товары", stats_no_sales_recorded:"Продажи не зарегистрированы", stats_no_product_sales:"За этот период товары не продавались.", stats_yesterday_sales:"Вчера: {count} продаж", stats_product_period:"Вчера: {yesterday} · 30 дн.: {total}", stats_view_range:"Период: {start} → {end}", stats_toggle_product:"Показать или скрыть {product}", stats_units_revenue:"{count} продаж · {revenue}", stats_momentum_unavailable:"Не удалось загрузить динамику продаж.", stats_alerts_unavailable:"Не удалось загрузить предупреждения по товарам.", stats_no_low_conversion_alert:"Предупреждений нет: данных о низкой конверсии пока недостаточно.", stats_views_count:"{count} просмотров", stats_sales_count:"{count} продаж", conversion_unavailable:"Не удалось загрузить воронку конверсии.", data_unavailable:"Данные недоступны.", conversion_stage_view:"Просмотр товара", conversion_stage_buy:"Нажатие «Купить»", conversion_stage_created:"Платёж создан", conversion_stage_completed:"Платёж завершён", conversion_entry_point:"Точка входа", conversion_direct_entries:"Включены прямые входы", conversion_previous_rate:"{rate}% от предыдущего этапа", conversion_global:"Общая конверсия: {rate}%", conversion_tracking_since:"Сопоставимый период с {date}. Прямые покупки включены.", conversion_tracking_future:"Отслеживание нажатий «Купить» начнётся после развёртывания этой версии.", conversion_not_enough:"Сопоставимых данных пока недостаточно."}
};
Object.entries(STATS_DYNAMIC_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
const DASHBOARD_RUNTIME_TRANSLATIONS = {
fr: {
    stats_no_product_found:"Aucun produit trouvé.", stats_top_sale:"Top vente", stats_no_sale:"Pas de vente", stats_normal:"Normal", stock_out:"Rupture", stock_low:"Bas",
    review_category_underpaid:"Sous-payé", review_category_expired:"Expiré", review_category_confirming:"Confirmation", review_category_late:"Reçu après annulation", review_category_validation:"Validation requise", review_category_accepted:"Traité manuellement", review_finalized:"Finalisé", review_reopen:"Réouvrir", review_audit_required:"Audit à contrôler", review_reset:"Réinitialiser", review_recheck:"Relire NOWPayments", review_accept:"Accepter", review_archive:"Classer", review_expected:"attendu {amount}", review_wallet:"Wallet", review_dismiss_prompt:"Indiquez pourquoi ce paiement est classé. Cette note sera conservée dans l'audit.", review_accept_confirm:"Confirmer l'acceptation du paiement {paymentId} ?\n\nCette action peut livrer une commande ou créditer un wallet. NOWPayments sera vérifié une dernière fois.", review_accept_note:"Accepté depuis la boîte de confirmation du dashboard.", review_reopen_prompt:"Motif de réouverture (facultatif) :", review_accept_success:"Paiement accepté et traité.", review_updated:"Dossier mis à jour.", review_action_failed:"Action impossible.",
    product_manage_supplier:"Gérer dans API Bot Gestion", product_view_stock:"Voir le stock", product_dynamic_suggestion:"Mode suggestion", product_dynamic_auto:"Mode automatique", product_dynamic:"Dynamique", product_activation:"Activation", product_disable:"Désactiver", product_enable:"Activer", product_edit:"Modifier", product_tiers:"Tarifs", product_delete:"Supprimer", product_none:"Aucun produit", product_sort_error:"Erreur de sauvegarde : {message}",
    order_deleted:"Supprimé", order_balance:"Solde : {amount}", order_confirm:"Confirmer", order_cancel:"Annuler", order_retry_delivery:"Relancer la livraison", order_view_items:"Voir les articles livrés", order_paid_pending:"PAYÉ — LIVRAISON EN ATTENTE", order_since:"Depuis {minutes}m {seconds}s", order_remaining:"Reste {minutes}m {seconds}s", order_expired_since:"Expiré (depuis {minutes}m {seconds}s)", order_invalid_id:"ID invalide"
},
en: {
    stats_no_product_found:"No products found.", stats_top_sale:"Top seller", stats_no_sale:"No sales", stats_normal:"Normal", stock_out:"Out of stock", stock_low:"Low",
    review_category_underpaid:"Underpaid", review_category_expired:"Expired", review_category_confirming:"Confirming", review_category_late:"Received after cancellation", review_category_validation:"Validation required", review_category_accepted:"Handled manually", review_finalized:"Finalized", review_reopen:"Reopen", review_audit_required:"Audit required", review_reset:"Reset", review_recheck:"Check NOWPayments again", review_accept:"Accept", review_archive:"Archive", review_expected:"expected {amount}", review_wallet:"Wallet", review_dismiss_prompt:"Explain why this payment is being archived. The note will be kept in the audit trail.", review_accept_confirm:"Accept payment {paymentId}?\n\nThis action may deliver an order or credit a wallet. NOWPayments will be checked one last time.", review_accept_note:"Accepted from the dashboard confirmation dialog.", review_reopen_prompt:"Reason for reopening (optional):", review_accept_success:"Payment accepted and processed.", review_updated:"Record updated.", review_action_failed:"Unable to complete the action.",
    product_manage_supplier:"Manage in API Bot Management", product_view_stock:"View stock", product_dynamic_suggestion:"Suggestion mode", product_dynamic_auto:"Automatic mode", product_dynamic:"Dynamic", product_activation:"Activation", product_disable:"Disable", product_enable:"Enable", product_edit:"Edit", product_tiers:"Pricing tiers", product_delete:"Delete", product_none:"No products", product_sort_error:"Unable to save: {message}",
    order_deleted:"Deleted", order_balance:"Balance: {amount}", order_confirm:"Confirm", order_cancel:"Cancel", order_retry_delivery:"Retry delivery", order_view_items:"View delivered items", order_paid_pending:"PAID — DELIVERY PENDING", order_since:"For {minutes}m {seconds}s", order_remaining:"{minutes}m {seconds}s remaining", order_expired_since:"Expired ({minutes}m {seconds}s ago)", order_invalid_id:"Invalid ID"
},
ar: {
    stats_no_product_found:"لم يتم العثور على منتجات.", stats_top_sale:"الأكثر مبيعًا", stats_no_sale:"لا مبيعات", stats_normal:"عادي", stock_out:"نفد المخزون", stock_low:"منخفض",
    review_category_underpaid:"مدفوع جزئيًا", review_category_expired:"منتهي", review_category_confirming:"قيد التأكيد", review_category_late:"مستلم بعد الإلغاء", review_category_validation:"يتطلب التحقق", review_category_accepted:"عولج يدويًا", review_finalized:"مكتمل", review_reopen:"إعادة فتح", review_audit_required:"يلزم تدقيق", review_reset:"إعادة ضبط", review_recheck:"إعادة فحص NOWPayments", review_accept:"قبول", review_archive:"أرشفة", review_expected:"المتوقع {amount}", review_wallet:"المحفظة", review_dismiss_prompt:"اذكر سبب أرشفة هذا الدفع. ستُحفظ الملاحظة في سجل التدقيق.", review_accept_confirm:"هل تريد قبول الدفع {paymentId}؟\n\nقد يؤدي هذا الإجراء إلى تسليم طلب أو إضافة رصيد إلى محفظة. سيتم فحص NOWPayments مرة أخيرة.", review_accept_note:"تم القبول من نافذة تأكيد لوحة التحكم.", review_reopen_prompt:"سبب إعادة الفتح (اختياري):", review_accept_success:"تم قبول الدفع ومعالجته.", review_updated:"تم تحديث السجل.", review_action_failed:"تعذر تنفيذ الإجراء.",
    product_manage_supplier:"الإدارة في API Bot", product_view_stock:"عرض المخزون", product_dynamic_suggestion:"وضع الاقتراح", product_dynamic_auto:"الوضع التلقائي", product_dynamic:"ديناميكي", product_activation:"تفعيل", product_disable:"تعطيل", product_enable:"تفعيل", product_edit:"تعديل", product_tiers:"شرائح الأسعار", product_delete:"حذف", product_none:"لا توجد منتجات", product_sort_error:"تعذر الحفظ: {message}",
    order_deleted:"محذوف", order_balance:"الرصيد: {amount}", order_confirm:"تأكيد", order_cancel:"إلغاء", order_retry_delivery:"إعادة محاولة التسليم", order_view_items:"عرض العناصر المسلّمة", order_paid_pending:"مدفوع — التسليم معلق", order_since:"منذ {minutes} د {seconds} ث", order_remaining:"متبقي {minutes} د {seconds} ث", order_expired_since:"منتهي (منذ {minutes} د {seconds} ث)", order_invalid_id:"معرّف غير صالح"
},
zh: {
    stats_no_product_found:"未找到产品。", stats_top_sale:"热销", stats_no_sale:"暂无销售", stats_normal:"正常", stock_out:"缺货", stock_low:"库存低",
    review_category_underpaid:"付款不足", review_category_expired:"已过期", review_category_confirming:"确认中", review_category_late:"取消后收到", review_category_validation:"需要验证", review_category_accepted:"已手动处理", review_finalized:"已完成", review_reopen:"重新打开", review_audit_required:"需要审计", review_reset:"重置", review_recheck:"重新检查 NOWPayments", review_accept:"接受", review_archive:"归档", review_expected:"应收 {amount}", review_wallet:"钱包", review_dismiss_prompt:"请说明归档此付款的原因。该备注将保留在审计记录中。", review_accept_confirm:"接受付款 {paymentId}？\n\n此操作可能会交付订单或为钱包充值。NOWPayments 将进行最后一次检查。", review_accept_note:"已通过仪表板确认对话框接受。", review_reopen_prompt:"重新打开的原因（可选）：", review_accept_success:"付款已接受并处理。", review_updated:"记录已更新。", review_action_failed:"无法完成操作。",
    product_manage_supplier:"在 API 机器人管理中处理", product_view_stock:"查看库存", product_dynamic_suggestion:"建议模式", product_dynamic_auto:"自动模式", product_dynamic:"动态", product_activation:"激活", product_disable:"停用", product_enable:"启用", product_edit:"编辑", product_tiers:"价格阶梯", product_delete:"删除", product_none:"没有产品", product_sort_error:"无法保存：{message}",
    order_deleted:"已删除", order_balance:"余额：{amount}", order_confirm:"确认", order_cancel:"取消", order_retry_delivery:"重试交付", order_view_items:"查看已交付项目", order_paid_pending:"已付款 — 等待交付", order_since:"已等待 {minutes}分 {seconds}秒", order_remaining:"剩余 {minutes}分 {seconds}秒", order_expired_since:"已过期（{minutes}分 {seconds}秒）", order_invalid_id:"ID 无效"
},
vi: {
    stats_no_product_found:"Không tìm thấy sản phẩm.", stats_top_sale:"Bán chạy", stats_no_sale:"Chưa có lượt bán", stats_normal:"Bình thường", stock_out:"Hết hàng", stock_low:"Thấp",
    review_category_underpaid:"Thanh toán thiếu", review_category_expired:"Đã hết hạn", review_category_confirming:"Đang xác nhận", review_category_late:"Nhận sau khi hủy", review_category_validation:"Cần xác minh", review_category_accepted:"Đã xử lý thủ công", review_finalized:"Đã hoàn tất", review_reopen:"Mở lại", review_audit_required:"Cần kiểm tra", review_reset:"Đặt lại", review_recheck:"Kiểm tra lại NOWPayments", review_accept:"Chấp nhận", review_archive:"Lưu trữ", review_expected:"dự kiến {amount}", review_wallet:"Ví", review_dismiss_prompt:"Hãy nêu lý do lưu trữ khoản thanh toán này. Ghi chú sẽ được giữ trong nhật ký kiểm tra.", review_accept_confirm:"Chấp nhận khoản thanh toán {paymentId}?\n\nThao tác này có thể giao đơn hàng hoặc cộng tiền vào ví. NOWPayments sẽ được kiểm tra lần cuối.", review_accept_note:"Đã chấp nhận từ hộp thoại xác nhận của dashboard.", review_reopen_prompt:"Lý do mở lại (không bắt buộc):", review_accept_success:"Khoản thanh toán đã được chấp nhận và xử lý.", review_updated:"Đã cập nhật hồ sơ.", review_action_failed:"Không thể hoàn tất thao tác.",
    product_manage_supplier:"Quản lý trong API Bot", product_view_stock:"Xem tồn kho", product_dynamic_suggestion:"Chế độ đề xuất", product_dynamic_auto:"Chế độ tự động", product_dynamic:"Động", product_activation:"Kích hoạt", product_disable:"Tắt", product_enable:"Bật", product_edit:"Sửa", product_tiers:"Bậc giá", product_delete:"Xóa", product_none:"Không có sản phẩm", product_sort_error:"Không thể lưu: {message}",
    order_deleted:"Đã xóa", order_balance:"Số dư: {amount}", order_confirm:"Xác nhận", order_cancel:"Hủy", order_retry_delivery:"Thử giao lại", order_view_items:"Xem mặt hàng đã giao", order_paid_pending:"ĐÃ THANH TOÁN — CHỜ GIAO", order_since:"Trong {minutes} phút {seconds} giây", order_remaining:"Còn {minutes} phút {seconds} giây", order_expired_since:"Đã hết hạn ({minutes} phút {seconds} giây)", order_invalid_id:"ID không hợp lệ"
},
ru: {
    stats_no_product_found:"Товары не найдены.", stats_top_sale:"Хит продаж", stats_no_sale:"Продаж нет", stats_normal:"Норма", stock_out:"Нет в наличии", stock_low:"Мало",
    review_category_underpaid:"Недоплата", review_category_expired:"Истёк", review_category_confirming:"Подтверждается", review_category_late:"Получен после отмены", review_category_validation:"Требуется проверка", review_category_accepted:"Обработан вручную", review_finalized:"Завершено", review_reopen:"Открыть снова", review_audit_required:"Требуется аудит", review_reset:"Сбросить", review_recheck:"Повторно проверить NOWPayments", review_accept:"Принять", review_archive:"Архивировать", review_expected:"ожидалось {amount}", review_wallet:"Кошелёк", review_dismiss_prompt:"Укажите причину архивации этого платежа. Примечание сохранится в журнале аудита.", review_accept_confirm:"Принять платёж {paymentId}?\n\nЭто действие может доставить заказ или пополнить кошелёк. NOWPayments будет проверен ещё раз.", review_accept_note:"Принято в окне подтверждения панели управления.", review_reopen_prompt:"Причина повторного открытия (необязательно):", review_accept_success:"Платёж принят и обработан.", review_updated:"Запись обновлена.", review_action_failed:"Не удалось выполнить действие.",
    product_manage_supplier:"Управлять в API Bot", product_view_stock:"Посмотреть склад", product_dynamic_suggestion:"Режим рекомендаций", product_dynamic_auto:"Автоматический режим", product_dynamic:"Динамический", product_activation:"Активация", product_disable:"Отключить", product_enable:"Включить", product_edit:"Изменить", product_tiers:"Ценовые уровни", product_delete:"Удалить", product_none:"Товаров нет", product_sort_error:"Не удалось сохранить: {message}",
    order_deleted:"Удалён", order_balance:"Баланс: {amount}", order_confirm:"Подтвердить", order_cancel:"Отменить", order_retry_delivery:"Повторить доставку", order_view_items:"Посмотреть доставленные позиции", order_paid_pending:"ОПЛАЧЕН — ОЖИДАЕТ ДОСТАВКИ", order_since:"В ожидании {minutes} мин {seconds} с", order_remaining:"Осталось {minutes} мин {seconds} с", order_expired_since:"Истёк ({minutes} мин {seconds} с)", order_invalid_id:"Неверный ID"
}
};
Object.entries(DASHBOARD_RUNTIME_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
const OPERATIONAL_SCREEN_TRANSLATIONS = {
fr: {
    finance_title:"Gestion financière", finance_all_methods:"Toutes les méthodes", finance_internal_wallet:"Portefeuille interne", finance_withdraw:"Retirer", finance_adjust:"Ajuster", finance_topups_30:"Rechargements wallet (30 jours)", review_show_archived:"Afficher les dossiers classés", review_payment:"Paiement", review_loading_payments:"Chargement des paiements...", binance_add_account:"Ajouter un compte", binance_no_accounts:"Aucun compte Binance.",
    supplier_external_catalog:"Catalogue externe", supplier_bot:"Bot fournisseur", supplier_not_configured:"Non configuré", supplier_balance_label:"Solde fournisseur", supplier_last_sync:"Dernière synchronisation", supplier_never:"Jamais", supplier_visible_products:"Produits affichés", supplier_pending_deliveries:"Livraisons à vérifier", supplier_catalog_settings:"Configuration du catalogue", supplier_display_name:"Nom affiché", supplier_active_connection:"Connexion active", supplier_active_hint:"Masque tous les produits distants lorsqu'elle est désactivée.", supplier_global_margin:"Marge globale", supplier_value:"Valeur", supplier_units_per_usd:"Unités pour 1 USD", supplier_key_hint:"La clé est lue depuis SUPPLIER_API_KEY sur Railway et n'est jamais envoyée au navigateur.", supplier_catalog:"Catalogue fournisseur", supplier_catalog_hint:"Le stock achetable est automatiquement limité par votre solde fournisseur. Un produit à 0 n'apparaît pas sur le bot.", supplier_show:"Afficher", supplier_source_product:"Produit fournisseur", supplier_source_price:"Prix source", supplier_api_stock:"Stock API", supplier_purchasable:"Achetable", supplier_applied_margin:"Marge appliquée", supplier_client_price:"Prix client", supplier_sync_start:"Synchronisez le catalogue pour commencer.", supplier_period_7:"7 jours", supplier_period_30:"30 jours", supplier_period_90:"90 jours", supplier_spent:"Dépensé", supplier_purchase_cost:"Coût des achats fournisseur", supplier_sales_by_product:"Ventes par produit", supplier_sales_help:"Identifiez les produits qui génèrent le plus de volume et de marge.",
    game_arena:"Arène des matchs", game_description:"Choisissez les matchs du fournisseur qui seront visibles dans le bot.", game_refresh_catalog:"Actualiser le catalogue", game_open_matches:"Matchs ouverts", game_api_missing:"API sportive non configurée", game_api_missing_help:"Ajoutez FOOTBALL_DATA_API_KEY dans les variables Railway. Aucun appel externe n'est effectué sans cette clé.", game_catalog:"Catalogue", game_published:"Matchs publiés", game_results_confirm:"Résultats à confirmer", game_history:"Historique", game_search:"Recherche", game_available:"Matchs disponibles", game_load_start:"Chargez le catalogue pour commencer.", game_competition:"Compétition", game_match:"Match", game_stage:"Phase", game_no_loaded:"Aucun match chargé.", game_published_help:"Seuls ces matchs sont synchronisés en arrière-plan et visibles par les clients.", game_market:"Marché", game_closing:"Fermeture", game_pot:"Pot", game_no_published:"Aucun match publié.", game_results_help:"Le résultat du fournisseur est proposé, mais aucun gain ne part sans confirmation.", game_api_score:"Score API", game_proposed_result:"Résultat proposé", game_no_pending:"Aucun résultat en attente.", game_history_help:"Matchs réglés ou annulés et résultat appliqué.", game_predictions:"Pronostics", game_no_history:"Aucun historique.",
    broadcast_photo_url:"URL de la photo / image (optionnel) :", broadcast_no_button:"Aucun bouton", broadcast_product_button:"Bouton d'achat (produit)", broadcast_select_product:"Sélectionner le produit :", settings_bep20_address:"Adresse BEP20 USDT (BNB Chain)", settings_trc20_address:"Adresse TRC20 USDT (TRON Chain)", settings_save_addresses:"Enregistrer les adresses"
},
en: {
    finance_title:"Financial management", finance_all_methods:"All methods", finance_internal_wallet:"Internal wallet", finance_withdraw:"Withdraw", finance_adjust:"Adjust", finance_topups_30:"Wallet top-ups (30 days)", review_show_archived:"Show archived records", review_payment:"Payment", review_loading_payments:"Loading payments...", binance_add_account:"Add account", binance_no_accounts:"No Binance accounts.",
    supplier_external_catalog:"External catalog", supplier_bot:"Supplier bot", supplier_not_configured:"Not configured", supplier_balance_label:"Supplier balance", supplier_last_sync:"Last sync", supplier_never:"Never", supplier_visible_products:"Visible products", supplier_pending_deliveries:"Deliveries to review", supplier_catalog_settings:"Catalog settings", supplier_display_name:"Display name", supplier_active_connection:"Active connection", supplier_active_hint:"Hides every remote product when disabled.", supplier_global_margin:"Global margin", supplier_value:"Value", supplier_units_per_usd:"Units per USD", supplier_key_hint:"The key is read from SUPPLIER_API_KEY on Railway and is never sent to the browser.", supplier_catalog:"Supplier catalog", supplier_catalog_hint:"Purchasable stock is automatically limited by your supplier balance. A product with 0 purchasable stock is hidden from the bot.", supplier_show:"Show", supplier_source_product:"Supplier product", supplier_source_price:"Source price", supplier_api_stock:"API stock", supplier_purchasable:"Purchasable", supplier_applied_margin:"Applied margin", supplier_client_price:"Customer price", supplier_sync_start:"Sync the catalog to get started.", supplier_period_7:"7 days", supplier_period_30:"30 days", supplier_period_90:"90 days", supplier_spent:"Spent", supplier_purchase_cost:"Supplier purchase cost", supplier_sales_by_product:"Sales by product", supplier_sales_help:"Identify the products that generate the most volume and margin.",
    game_arena:"Match arena", game_description:"Choose which provider matches will be visible in the bot.", game_refresh_catalog:"Refresh catalog", game_open_matches:"Open matches", game_api_missing:"Sports API not configured", game_api_missing_help:"Add FOOTBALL_DATA_API_KEY to the Railway variables. No external call is made without this key.", game_catalog:"Catalog", game_published:"Published matches", game_results_confirm:"Results to confirm", game_history:"History", game_search:"Search", game_available:"Available matches", game_load_start:"Load the catalog to get started.", game_competition:"Competition", game_match:"Match", game_stage:"Stage", game_no_loaded:"No matches loaded.", game_published_help:"Only these matches are synchronized in the background and visible to customers.", game_market:"Market", game_closing:"Closes", game_pot:"Pool", game_no_published:"No published matches.", game_results_help:"The provider result is suggested, but no reward is issued without confirmation.", game_api_score:"API score", game_proposed_result:"Suggested result", game_no_pending:"No results are awaiting confirmation.", game_history_help:"Settled or cancelled matches and their applied result.", game_predictions:"Predictions", game_no_history:"No history.",
    broadcast_photo_url:"Photo / image URL (optional):", broadcast_no_button:"No button", broadcast_product_button:"Purchase button (product)", broadcast_select_product:"Select product:", settings_bep20_address:"BEP20 USDT address (BNB Chain)", settings_trc20_address:"TRC20 USDT address (TRON Chain)", settings_save_addresses:"Save addresses"
},
ar: {
    finance_title:"الإدارة المالية", finance_all_methods:"كل طرق الدفع", finance_internal_wallet:"المحفظة الداخلية", finance_withdraw:"سحب", finance_adjust:"تعديل", finance_topups_30:"شحن المحفظة (30 يومًا)", review_show_archived:"إظهار السجلات المؤرشفة", review_payment:"الدفع", review_loading_payments:"جارٍ تحميل المدفوعات...", binance_add_account:"إضافة حساب", binance_no_accounts:"لا توجد حسابات Binance.",
    supplier_external_catalog:"الكتالوج الخارجي", supplier_bot:"بوت المورد", supplier_not_configured:"غير مهيأ", supplier_balance_label:"رصيد المورد", supplier_last_sync:"آخر مزامنة", supplier_never:"لم تتم", supplier_visible_products:"المنتجات المعروضة", supplier_pending_deliveries:"تسليمات تحتاج مراجعة", supplier_catalog_settings:"إعدادات الكتالوج", supplier_display_name:"الاسم المعروض", supplier_active_connection:"الاتصال فعال", supplier_active_hint:"يخفي جميع المنتجات البعيدة عند تعطيله.", supplier_global_margin:"الهامش العام", supplier_value:"القيمة", supplier_units_per_usd:"وحدات لكل دولار", supplier_key_hint:"تُقرأ الخانة من SUPPLIER_API_KEY على Railway ولا تُرسل إلى المتصفح.", supplier_catalog:"كتالوج المورد", supplier_catalog_hint:"يُحدَّد المخزون القابل للشراء تلقائيًا حسب رصيد المورد. المنتج ذو المخزون 0 لا يظهر في البوت.", supplier_show:"إظهار", supplier_source_product:"منتج المورد", supplier_source_price:"سعر المصدر", supplier_api_stock:"مخزون API", supplier_purchasable:"قابل للشراء", supplier_applied_margin:"الهامش المطبق", supplier_client_price:"سعر العميل", supplier_sync_start:"زامن الكتالوج للبدء.", supplier_period_7:"7 أيام", supplier_period_30:"30 يومًا", supplier_period_90:"90 يومًا", supplier_spent:"المنفق", supplier_purchase_cost:"تكلفة مشتريات المورد", supplier_sales_by_product:"المبيعات حسب المنتج", supplier_sales_help:"اعرف المنتجات التي تحقق أكبر حجم ومقدار هامش.",
    game_arena:"ساحة المباريات", game_description:"اختر مباريات المورد التي ستظهر في البوت.", game_refresh_catalog:"تحديث الكتالوج", game_open_matches:"المباريات المفتوحة", game_api_missing:"API الرياضة غير مهيأ", game_api_missing_help:"أضف FOOTBALL_DATA_API_KEY إلى متغيرات Railway. لن تُجرى اتصالات خارجية من دون هذا المفتاح.", game_catalog:"الكتالوج", game_published:"المباريات المنشورة", game_results_confirm:"نتائج للتأكيد", game_history:"السجل", game_search:"بحث", game_available:"المباريات المتاحة", game_load_start:"حمّل الكتالوج للبدء.", game_competition:"المسابقة", game_match:"المباراة", game_stage:"المرحلة", game_no_loaded:"لم تُحمّل مباريات.", game_published_help:"تتم مزامنة هذه المباريات فقط في الخلفية وتظهر للعملاء.", game_market:"السوق", game_closing:"الإغلاق", game_pot:"المجموع", game_no_published:"لا توجد مباريات منشورة.", game_results_help:"تُقترح نتيجة المورد، ولا تُصرف مكافآت دون تأكيد.", game_api_score:"نتيجة API", game_proposed_result:"النتيجة المقترحة", game_no_pending:"لا توجد نتائج بانتظار التأكيد.", game_history_help:"المباريات المسوّاة أو الملغاة والنتيجة المطبقة.", game_predictions:"التوقعات", game_no_history:"لا يوجد سجل.",
    broadcast_photo_url:"رابط الصورة (اختياري):", broadcast_no_button:"من دون زر", broadcast_product_button:"زر شراء (منتج)", broadcast_select_product:"اختر المنتج:", settings_bep20_address:"عنوان USDT على BEP20 (BNB Chain)", settings_trc20_address:"عنوان USDT على TRC20 (TRON Chain)", settings_save_addresses:"حفظ العناوين"
},
zh: {
    finance_title:"财务管理", finance_all_methods:"所有方式", finance_internal_wallet:"内部钱包", finance_withdraw:"提现", finance_adjust:"调整", finance_topups_30:"钱包充值（30 天）", review_show_archived:"显示已归档记录", review_payment:"付款", review_loading_payments:"正在加载付款...", binance_add_account:"添加账户", binance_no_accounts:"没有 Binance 账户。",
    supplier_external_catalog:"外部目录", supplier_bot:"供应商机器人", supplier_not_configured:"未配置", supplier_balance_label:"供应商余额", supplier_last_sync:"上次同步", supplier_never:"从未", supplier_visible_products:"显示的产品", supplier_pending_deliveries:"待检查交付", supplier_catalog_settings:"目录设置", supplier_display_name:"显示名称", supplier_active_connection:"连接已启用", supplier_active_hint:"禁用时隐藏所有远程产品。", supplier_global_margin:"全局利润", supplier_value:"数值", supplier_units_per_usd:"每美元单位数", supplier_key_hint:"密钥从 Railway 的 SUPPLIER_API_KEY 读取，绝不会发送到浏览器。", supplier_catalog:"供应商目录", supplier_catalog_hint:"可购买库存会根据供应商余额自动限制。可购买量为 0 的产品不会显示在机器人中。", supplier_show:"显示", supplier_source_product:"供应商产品", supplier_source_price:"来源价格", supplier_api_stock:"API 库存", supplier_purchasable:"可购买", supplier_applied_margin:"应用利润", supplier_client_price:"客户价格", supplier_sync_start:"同步目录以开始。", supplier_period_7:"7 天", supplier_period_30:"30 天", supplier_period_90:"90 天", supplier_spent:"支出", supplier_purchase_cost:"供应商采购成本", supplier_sales_by_product:"按产品销售", supplier_sales_help:"识别带来最多销量和利润的产品。",
    game_arena:"比赛竞技场", game_description:"选择将在机器人中显示的供应商比赛。", game_refresh_catalog:"刷新目录", game_open_matches:"开放比赛", game_api_missing:"未配置体育 API", game_api_missing_help:"请在 Railway 变量中添加 FOOTBALL_DATA_API_KEY。没有此密钥不会发起外部调用。", game_catalog:"目录", game_published:"已发布比赛", game_results_confirm:"待确认结果", game_history:"历史", game_search:"搜索", game_available:"可用比赛", game_load_start:"加载目录以开始。", game_competition:"赛事", game_match:"比赛", game_stage:"阶段", game_no_loaded:"未加载比赛。", game_published_help:"只有这些比赛会在后台同步并向客户显示。", game_market:"玩法", game_closing:"截止", game_pot:"奖池", game_no_published:"没有已发布比赛。", game_results_help:"系统会建议供应商结果，但未经确认不会发放奖励。", game_api_score:"API 比分", game_proposed_result:"建议结果", game_no_pending:"没有待确认结果。", game_history_help:"已结算或取消的比赛及应用结果。", game_predictions:"预测", game_no_history:"没有历史记录。",
    broadcast_photo_url:"照片 / 图片 URL（可选）：", broadcast_no_button:"无按钮", broadcast_product_button:"购买按钮（产品）", broadcast_select_product:"选择产品：", settings_bep20_address:"BEP20 USDT 地址（BNB Chain）", settings_trc20_address:"TRC20 USDT 地址（TRON Chain）", settings_save_addresses:"保存地址"
},
vi: {
    finance_title:"Quản lý tài chính", finance_all_methods:"Tất cả phương thức", finance_internal_wallet:"Ví nội bộ", finance_withdraw:"Rút tiền", finance_adjust:"Điều chỉnh", finance_topups_30:"Nạp ví (30 ngày)", review_show_archived:"Hiện hồ sơ đã lưu trữ", review_payment:"Thanh toán", review_loading_payments:"Đang tải thanh toán...", binance_add_account:"Thêm tài khoản", binance_no_accounts:"Không có tài khoản Binance.",
    supplier_external_catalog:"Danh mục bên ngoài", supplier_bot:"Bot nhà cung cấp", supplier_not_configured:"Chưa cấu hình", supplier_balance_label:"Số dư nhà cung cấp", supplier_last_sync:"Lần đồng bộ cuối", supplier_never:"Chưa bao giờ", supplier_visible_products:"Sản phẩm hiển thị", supplier_pending_deliveries:"Giao hàng cần kiểm tra", supplier_catalog_settings:"Cấu hình danh mục", supplier_display_name:"Tên hiển thị", supplier_active_connection:"Kết nối hoạt động", supplier_active_hint:"Ẩn tất cả sản phẩm từ xa khi tắt.", supplier_global_margin:"Biên lợi nhuận chung", supplier_value:"Giá trị", supplier_units_per_usd:"Đơn vị trên 1 USD", supplier_key_hint:"Khóa được đọc từ SUPPLIER_API_KEY trên Railway và không bao giờ gửi đến trình duyệt.", supplier_catalog:"Danh mục nhà cung cấp", supplier_catalog_hint:"Tồn kho có thể mua được tự động giới hạn theo số dư nhà cung cấp. Sản phẩm có lượng mua được bằng 0 sẽ không hiện trên bot.", supplier_show:"Hiện", supplier_source_product:"Sản phẩm nhà cung cấp", supplier_source_price:"Giá nguồn", supplier_api_stock:"Tồn kho API", supplier_purchasable:"Có thể mua", supplier_applied_margin:"Biên lợi nhuận áp dụng", supplier_client_price:"Giá khách hàng", supplier_sync_start:"Đồng bộ danh mục để bắt đầu.", supplier_period_7:"7 ngày", supplier_period_30:"30 ngày", supplier_period_90:"90 ngày", supplier_spent:"Đã chi", supplier_purchase_cost:"Chi phí mua từ nhà cung cấp", supplier_sales_by_product:"Doanh số theo sản phẩm", supplier_sales_help:"Xác định sản phẩm tạo nhiều sản lượng và lợi nhuận nhất.",
    game_arena:"Đấu trường trận đấu", game_description:"Chọn trận đấu của nhà cung cấp sẽ hiển thị trong bot.", game_refresh_catalog:"Làm mới danh mục", game_open_matches:"Trận đang mở", game_api_missing:"Chưa cấu hình API thể thao", game_api_missing_help:"Thêm FOOTBALL_DATA_API_KEY vào biến Railway. Không có khóa này sẽ không gọi dịch vụ bên ngoài.", game_catalog:"Danh mục", game_published:"Trận đã đăng", game_results_confirm:"Kết quả cần xác nhận", game_history:"Lịch sử", game_search:"Tìm kiếm", game_available:"Trận có sẵn", game_load_start:"Tải danh mục để bắt đầu.", game_competition:"Giải đấu", game_match:"Trận đấu", game_stage:"Giai đoạn", game_no_loaded:"Chưa tải trận nào.", game_published_help:"Chỉ các trận này được đồng bộ nền và hiển thị cho khách hàng.", game_market:"Kèo", game_closing:"Đóng", game_pot:"Tổng cược", game_no_published:"Chưa có trận đã đăng.", game_results_help:"Kết quả từ nhà cung cấp được đề xuất nhưng không trả thưởng khi chưa xác nhận.", game_api_score:"Tỷ số API", game_proposed_result:"Kết quả đề xuất", game_no_pending:"Không có kết quả chờ xác nhận.", game_history_help:"Các trận đã quyết toán hoặc hủy và kết quả đã áp dụng.", game_predictions:"Dự đoán", game_no_history:"Chưa có lịch sử.",
    broadcast_photo_url:"URL ảnh (không bắt buộc):", broadcast_no_button:"Không có nút", broadcast_product_button:"Nút mua (sản phẩm)", broadcast_select_product:"Chọn sản phẩm:", settings_bep20_address:"Địa chỉ BEP20 USDT (BNB Chain)", settings_trc20_address:"Địa chỉ TRC20 USDT (TRON Chain)", settings_save_addresses:"Lưu địa chỉ"
},
ru: {
    finance_title:"Управление финансами", finance_all_methods:"Все способы", finance_internal_wallet:"Внутренний кошелёк", finance_withdraw:"Вывести", finance_adjust:"Корректировать", finance_topups_30:"Пополнения кошелька (30 дней)", review_show_archived:"Показывать архивные записи", review_payment:"Платёж", review_loading_payments:"Загрузка платежей...", binance_add_account:"Добавить аккаунт", binance_no_accounts:"Нет аккаунтов Binance.",
    supplier_external_catalog:"Внешний каталог", supplier_bot:"Бот поставщика", supplier_not_configured:"Не настроен", supplier_balance_label:"Баланс поставщика", supplier_last_sync:"Последняя синхронизация", supplier_never:"Никогда", supplier_visible_products:"Отображаемые товары", supplier_pending_deliveries:"Доставки для проверки", supplier_catalog_settings:"Настройки каталога", supplier_display_name:"Отображаемое имя", supplier_active_connection:"Подключение активно", supplier_active_hint:"При отключении скрывает все внешние товары.", supplier_global_margin:"Общая наценка", supplier_value:"Значение", supplier_units_per_usd:"Единиц на 1 USD", supplier_key_hint:"Ключ считывается из SUPPLIER_API_KEY в Railway и никогда не передаётся в браузер.", supplier_catalog:"Каталог поставщика", supplier_catalog_hint:"Доступный для покупки остаток автоматически ограничен балансом поставщика. Товар с нулевым остатком не показывается в боте.", supplier_show:"Показывать", supplier_source_product:"Товар поставщика", supplier_source_price:"Исходная цена", supplier_api_stock:"Остаток API", supplier_purchasable:"Можно купить", supplier_applied_margin:"Применённая наценка", supplier_client_price:"Цена клиента", supplier_sync_start:"Синхронизируйте каталог, чтобы начать.", supplier_period_7:"7 дней", supplier_period_30:"30 дней", supplier_period_90:"90 дней", supplier_spent:"Потрачено", supplier_purchase_cost:"Стоимость закупок у поставщика", supplier_sales_by_product:"Продажи по товарам", supplier_sales_help:"Определите товары с наибольшим объёмом и маржой.",
    game_arena:"Арена матчей", game_description:"Выберите матчи поставщика, которые будут видны в боте.", game_refresh_catalog:"Обновить каталог", game_open_matches:"Открытые матчи", game_api_missing:"Спортивный API не настроен", game_api_missing_help:"Добавьте FOOTBALL_DATA_API_KEY в переменные Railway. Без ключа внешние запросы не выполняются.", game_catalog:"Каталог", game_published:"Опубликованные матчи", game_results_confirm:"Результаты для подтверждения", game_history:"История", game_search:"Поиск", game_available:"Доступные матчи", game_load_start:"Загрузите каталог, чтобы начать.", game_competition:"Турнир", game_match:"Матч", game_stage:"Этап", game_no_loaded:"Матчи не загружены.", game_published_help:"Только эти матчи синхронизируются в фоне и видны клиентам.", game_market:"Исход", game_closing:"Закрытие", game_pot:"Банк", game_no_published:"Нет опубликованных матчей.", game_results_help:"Результат поставщика предлагается, но награды не выдаются без подтверждения.", game_api_score:"Счёт API", game_proposed_result:"Предлагаемый результат", game_no_pending:"Нет результатов, ожидающих подтверждения.", game_history_help:"Рассчитанные или отменённые матчи и применённый результат.", game_predictions:"Прогнозы", game_no_history:"Истории нет.",
    broadcast_photo_url:"URL фото / изображения (необязательно):", broadcast_no_button:"Без кнопки", broadcast_product_button:"Кнопка покупки (товар)", broadcast_select_product:"Выберите товар:", settings_bep20_address:"Адрес BEP20 USDT (BNB Chain)", settings_trc20_address:"Адрес TRC20 USDT (TRON Chain)", settings_save_addresses:"Сохранить адреса"
}
};
Object.entries(OPERATIONAL_SCREEN_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
Object.assign(LANG.fr, {supplier_key_prefix:"La clé est lue depuis", supplier_key_suffix:"sur Railway et n'est jamais envoyée au navigateur.", game_api_key_prefix:"Ajoutez", game_api_key_suffix:"dans les variables Railway. Aucun appel externe n'est effectué sans cette clé."});
Object.assign(LANG.en, {supplier_key_prefix:"The key is read from", supplier_key_suffix:"on Railway and is never sent to the browser.", game_api_key_prefix:"Add", game_api_key_suffix:"to the Railway variables. No external call is made without this key."});
Object.assign(LANG.ar, {supplier_key_prefix:"تُقرأ الخانة من", supplier_key_suffix:"على Railway ولا تُرسل إلى المتصفح.", game_api_key_prefix:"أضف", game_api_key_suffix:"إلى متغيرات Railway. لن تُجرى اتصالات خارجية من دون هذا المفتاح."});
Object.assign(LANG.zh, {supplier_key_prefix:"密钥读取自", supplier_key_suffix:"（Railway），且绝不会发送到浏览器。", game_api_key_prefix:"请将", game_api_key_suffix:"添加到 Railway 变量。没有此密钥不会发起外部调用。"});
Object.assign(LANG.vi, {supplier_key_prefix:"Khóa được đọc từ", supplier_key_suffix:"trên Railway và không bao giờ gửi đến trình duyệt.", game_api_key_prefix:"Thêm", game_api_key_suffix:"vào biến Railway. Không có khóa này sẽ không gọi dịch vụ bên ngoài."});
Object.assign(LANG.ru, {supplier_key_prefix:"Ключ считывается из", supplier_key_suffix:"в Railway и никогда не передаётся в браузер.", game_api_key_prefix:"Добавьте", game_api_key_suffix:"в переменные Railway. Без ключа внешние запросы не выполняются."});
const GENERATED_SCREEN_TRANSLATIONS = {
fr: {status_draft:"Brouillon",status_open:"Ouvert",status_locked:"Verrouillé",status_settling:"Règlement",status_settled:"Terminé",status_cancelled:"Annulé",status_scheduled:"Programmé",status_timed:"Planifié",status_in_play:"En cours",status_paused:"Pause",status_finished:"Terminé",status_postponed:"Reporté",status_suspended:"Suspendu",game_result_90:"Résultat après 90 minutes",game_qualified:"Équipe qualifiée",game_draw:"Match nul",game_choose:"À choisir",game_all:"Toutes",game_provider_connected:"football-data.org connecté",game_configure_key:"Configurez la clé du fournisseur dans Railway.",game_found:"{count} match(s) trouvé(s) pour la période sélectionnée.",game_no_filter:"Aucun match ne correspond aux filtres.",game_already_added:"Déjà ajouté",game_configure:"Configurer",common_unavailable:"Indisponible",game_players:"{count} joueur(s)",game_publish:"Publier",game_update_result:"Actualiser le résultat",game_cancel_refund:"Annuler et rembourser",game_choose_option:"Choisir...",game_predictions_count:"{count} pronostic(s)",game_modal_configure:"Configurer le match",game_modal_publish:"Publier un match",game_save:"Enregistrer",game_publish_bot:"Publier sur le bot",supplier_connected:"Connecté",supplier_disabled:"Désactivé",supplier_key_missing:"Clé absente",supplier_displayed:"{count} affiché(s)",supplier_loading_catalog:"Chargement du catalogue...",supplier_no_product:"Aucun produit fournisseur. Cliquez sur Synchroniser.",supplier_source:"Source : {name}",supplier_balance_limited:"Limité par votre solde fournisseur",supplier_fixed_sale_price:"Prix de vente fixe",supplier_hidden_cost:"Masqué : coût ≥ prix fixe",supplier_secure_fixed:"Prix fixe sécurisé",supplier_customize:"Nom, emoji et traductions",supplier_save_display:"Enregistrer le prix et l'affichage"},
en: {status_draft:"Draft",status_open:"Open",status_locked:"Locked",status_settling:"Settling",status_settled:"Settled",status_cancelled:"Cancelled",status_scheduled:"Scheduled",status_timed:"Scheduled",status_in_play:"In progress",status_paused:"Paused",status_finished:"Finished",status_postponed:"Postponed",status_suspended:"Suspended",game_result_90:"Result after 90 minutes",game_qualified:"Qualified team",game_draw:"Draw",game_choose:"Select",game_all:"All",game_provider_connected:"football-data.org connected",game_configure_key:"Configure the provider key in Railway.",game_found:"{count} match(es) found for the selected period.",game_no_filter:"No matches match these filters.",game_already_added:"Already added",game_configure:"Configure",common_unavailable:"Unavailable",game_players:"{count} player(s)",game_publish:"Publish",game_update_result:"Refresh result",game_cancel_refund:"Cancel and refund",game_choose_option:"Select...",game_predictions_count:"{count} prediction(s)",game_modal_configure:"Configure match",game_modal_publish:"Publish match",game_save:"Save",game_publish_bot:"Publish to bot",supplier_connected:"Connected",supplier_disabled:"Disabled",supplier_key_missing:"Missing key",supplier_displayed:"{count} displayed",supplier_loading_catalog:"Loading catalog...",supplier_no_product:"No supplier products. Select Sync catalog.",supplier_source:"Source: {name}",supplier_balance_limited:"Limited by your supplier balance",supplier_fixed_sale_price:"Fixed sale price",supplier_hidden_cost:"Hidden: cost ≥ fixed price",supplier_secure_fixed:"Protected fixed price",supplier_customize:"Name, emoji and translations",supplier_save_display:"Save price and visibility"},
ar: {status_draft:"مسودة",status_open:"مفتوح",status_locked:"مغلق",status_settling:"قيد التسوية",status_settled:"تمت التسوية",status_cancelled:"ملغى",status_scheduled:"مجدول",status_timed:"مجدول",status_in_play:"جارٍ",status_paused:"متوقف مؤقتًا",status_finished:"منتهٍ",status_postponed:"مؤجل",status_suspended:"معلق",game_result_90:"النتيجة بعد 90 دقيقة",game_qualified:"الفريق المتأهل",game_draw:"تعادل",game_choose:"اختر",game_all:"الكل",game_provider_connected:"متصل بـ football-data.org",game_configure_key:"هيّئ مفتاح المورد في Railway.",game_found:"تم العثور على {count} مباراة للفترة المحددة.",game_no_filter:"لا توجد مباريات مطابقة للفلاتر.",game_already_added:"مضاف مسبقًا",game_configure:"إعداد",common_unavailable:"غير متاح",game_players:"{count} لاعب",game_publish:"نشر",game_update_result:"تحديث النتيجة",game_cancel_refund:"إلغاء ورد الرهانات",game_choose_option:"اختر...",game_predictions_count:"{count} توقع",game_modal_configure:"إعداد المباراة",game_modal_publish:"نشر مباراة",game_save:"حفظ",game_publish_bot:"نشر في البوت",supplier_connected:"متصل",supplier_disabled:"معطل",supplier_key_missing:"المفتاح مفقود",supplier_displayed:"{count} معروض",supplier_loading_catalog:"جارٍ تحميل الكتالوج...",supplier_no_product:"لا توجد منتجات مورد. اختر مزامنة الكتالوج.",supplier_source:"المصدر: {name}",supplier_balance_limited:"محدود برصيد المورد",supplier_fixed_sale_price:"سعر بيع ثابت",supplier_hidden_cost:"مخفي: التكلفة ≥ السعر الثابت",supplier_secure_fixed:"سعر ثابت محمي",supplier_customize:"الاسم والرمز والترجمات",supplier_save_display:"حفظ السعر والظهور"},
zh: {status_draft:"草稿",status_open:"开放",status_locked:"已锁定",status_settling:"结算中",status_settled:"已结算",status_cancelled:"已取消",status_scheduled:"已安排",status_timed:"已安排",status_in_play:"进行中",status_paused:"暂停",status_finished:"已结束",status_postponed:"已推迟",status_suspended:"已暂停",game_result_90:"90 分钟后的结果",game_qualified:"晋级球队",game_draw:"平局",game_choose:"请选择",game_all:"全部",game_provider_connected:"football-data.org 已连接",game_configure_key:"请在 Railway 中配置供应商密钥。",game_found:"所选期间找到 {count} 场比赛。",game_no_filter:"没有符合筛选条件的比赛。",game_already_added:"已添加",game_configure:"配置",common_unavailable:"不可用",game_players:"{count} 名玩家",game_publish:"发布",game_update_result:"刷新结果",game_cancel_refund:"取消并退款",game_choose_option:"请选择...",game_predictions_count:"{count} 次预测",game_modal_configure:"配置比赛",game_modal_publish:"发布比赛",game_save:"保存",game_publish_bot:"发布到机器人",supplier_connected:"已连接",supplier_disabled:"已禁用",supplier_key_missing:"缺少密钥",supplier_displayed:"显示 {count} 个",supplier_loading_catalog:"正在加载目录...",supplier_no_product:"没有供应商产品，请选择同步目录。",supplier_source:"来源：{name}",supplier_balance_limited:"受供应商余额限制",supplier_fixed_sale_price:"固定售价",supplier_hidden_cost:"已隐藏：成本 ≥ 固定价",supplier_secure_fixed:"受保护固定价",supplier_customize:"名称、表情和翻译",supplier_save_display:"保存价格和显示状态"},
vi: {status_draft:"Bản nháp",status_open:"Đang mở",status_locked:"Đã khóa",status_settling:"Đang quyết toán",status_settled:"Đã quyết toán",status_cancelled:"Đã hủy",status_scheduled:"Đã lên lịch",status_timed:"Đã lên lịch",status_in_play:"Đang diễn ra",status_paused:"Tạm dừng",status_finished:"Kết thúc",status_postponed:"Hoãn",status_suspended:"Đình chỉ",game_result_90:"Kết quả sau 90 phút",game_qualified:"Đội đi tiếp",game_draw:"Hòa",game_choose:"Chọn",game_all:"Tất cả",game_provider_connected:"Đã kết nối football-data.org",game_configure_key:"Cấu hình khóa nhà cung cấp trong Railway.",game_found:"Tìm thấy {count} trận trong khoảng đã chọn.",game_no_filter:"Không có trận phù hợp bộ lọc.",game_already_added:"Đã thêm",game_configure:"Cấu hình",common_unavailable:"Không khả dụng",game_players:"{count} người chơi",game_publish:"Đăng",game_update_result:"Làm mới kết quả",game_cancel_refund:"Hủy và hoàn điểm",game_choose_option:"Chọn...",game_predictions_count:"{count} dự đoán",game_modal_configure:"Cấu hình trận đấu",game_modal_publish:"Đăng trận đấu",game_save:"Lưu",game_publish_bot:"Đăng lên bot",supplier_connected:"Đã kết nối",supplier_disabled:"Đã tắt",supplier_key_missing:"Thiếu khóa",supplier_displayed:"Hiện {count}",supplier_loading_catalog:"Đang tải danh mục...",supplier_no_product:"Không có sản phẩm nhà cung cấp. Chọn Đồng bộ danh mục.",supplier_source:"Nguồn: {name}",supplier_balance_limited:"Bị giới hạn bởi số dư nhà cung cấp",supplier_fixed_sale_price:"Giá bán cố định",supplier_hidden_cost:"Đã ẩn: chi phí ≥ giá cố định",supplier_secure_fixed:"Giá cố định được bảo vệ",supplier_customize:"Tên, emoji và bản dịch",supplier_save_display:"Lưu giá và hiển thị"},
ru: {status_draft:"Черновик",status_open:"Открыт",status_locked:"Заблокирован",status_settling:"Расчёт",status_settled:"Рассчитан",status_cancelled:"Отменён",status_scheduled:"Запланирован",status_timed:"Запланирован",status_in_play:"Идёт",status_paused:"Пауза",status_finished:"Завершён",status_postponed:"Перенесён",status_suspended:"Приостановлен",game_result_90:"Результат после 90 минут",game_qualified:"Прошедшая команда",game_draw:"Ничья",game_choose:"Выбрать",game_all:"Все",game_provider_connected:"football-data.org подключён",game_configure_key:"Настройте ключ поставщика в Railway.",game_found:"Найдено матчей за выбранный период: {count}.",game_no_filter:"Нет матчей по этим фильтрам.",game_already_added:"Уже добавлен",game_configure:"Настроить",common_unavailable:"Недоступно",game_players:"Игроков: {count}",game_publish:"Опубликовать",game_update_result:"Обновить результат",game_cancel_refund:"Отменить и вернуть ставки",game_choose_option:"Выбрать...",game_predictions_count:"Прогнозов: {count}",game_modal_configure:"Настроить матч",game_modal_publish:"Опубликовать матч",game_save:"Сохранить",game_publish_bot:"Опубликовать в боте",supplier_connected:"Подключён",supplier_disabled:"Отключён",supplier_key_missing:"Нет ключа",supplier_displayed:"Показано: {count}",supplier_loading_catalog:"Загрузка каталога...",supplier_no_product:"Нет товаров поставщика. Выберите синхронизацию каталога.",supplier_source:"Источник: {name}",supplier_balance_limited:"Ограничено балансом поставщика",supplier_fixed_sale_price:"Фиксированная цена продажи",supplier_hidden_cost:"Скрыто: стоимость ≥ фиксированной цены",supplier_secure_fixed:"Защищённая фиксированная цена",supplier_customize:"Название, эмодзи и переводы",supplier_save_display:"Сохранить цену и видимость"}
};
Object.entries(GENERATED_SCREEN_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
const EXTENDED_SCREEN_TRANSLATIONS = {
fr:{common_statistics:"Statistiques",common_supplier:"Fournisseur",common_from:"Du",common_to:"Au",common_filter:"Filtrer",common_result:"Résultat",supplier_smart_router:"Routeur intelligent",supplier_performance:"Performance du fournisseur",supplier_profitability:"Rentabilité réelle des commandes livrées par API.",supplier_year:"1 an",supplier_revenue:"Chiffre d'affaires",supplier_customer_paid:"Montant payé par les clients",supplier_gross_profit:"Bénéfice brut",supplier_items_sold:"Articles vendus",supplier_units_delivered:"Unités livrées",supplier_orders_label:"Commandes",supplier_average_order:"Panier moyen $0.00",supplier_success_rate:"Taux de réussite",supplier_api_completed:"Livraisons API terminées",supplier_financial_momentum:"Momentum financier",supplier_financial_daily:"Revenus, dépenses et bénéfices quotidiens.",supplier_articles:"Articles",supplier_profit:"Bénéfice",supplier_margin:"Marge",supplier_no_sales_period:"Aucune vente sur cette période.",supplier_equivalent_products:"Produits équivalents",supplier_equivalent_help:"Gemini propose les rapprochements. Seules les lignes confirmées servent aux commandes.",supplier_analyze_catalogs:"Analyser les catalogues",supplier_to_review:"À vérifier",supplier_active_routes:"Routes actives",supplier_security_label:"Sécurité",supplier_manual_validation:"Validation manuelle",supplier_your_product:"Votre produit",supplier_candidate_offer:"Offre candidate",supplier_confidence:"Confiance",supplier_run_analysis:"Lancez une analyse pour rechercher les produits équivalents.",game_to_settle:"À régler",game_coins_staked:"Batman Coins engagés",game_search_placeholder:"Équipe, compétition, phase..."},
en:{common_statistics:"Statistics",common_supplier:"Supplier",common_from:"From",common_to:"To",common_filter:"Filter",common_result:"Result",supplier_smart_router:"Smart router",supplier_performance:"Supplier performance",supplier_profitability:"Actual profitability of orders delivered through the API.",supplier_year:"1 year",supplier_revenue:"Revenue",supplier_customer_paid:"Amount paid by customers",supplier_gross_profit:"Gross profit",supplier_items_sold:"Items sold",supplier_units_delivered:"Units delivered",supplier_orders_label:"Orders",supplier_average_order:"Average order $0.00",supplier_success_rate:"Success rate",supplier_api_completed:"Completed API deliveries",supplier_financial_momentum:"Financial momentum",supplier_financial_daily:"Daily revenue, spend and profit.",supplier_articles:"Items",supplier_profit:"Profit",supplier_margin:"Margin",supplier_no_sales_period:"No sales during this period.",supplier_equivalent_products:"Equivalent products",supplier_equivalent_help:"Gemini suggests matches. Only confirmed routes are used for orders.",supplier_analyze_catalogs:"Analyze catalogs",supplier_to_review:"To review",supplier_active_routes:"Active routes",supplier_security_label:"Security",supplier_manual_validation:"Manual validation",supplier_your_product:"Your product",supplier_candidate_offer:"Candidate offer",supplier_confidence:"Confidence",supplier_run_analysis:"Run an analysis to find equivalent products.",game_to_settle:"To settle",game_coins_staked:"Batman Coins staked",game_search_placeholder:"Team, competition, stage..."},
ar:{common_statistics:"الإحصائيات",common_supplier:"المورد",common_from:"من",common_to:"إلى",common_filter:"تصفية",common_result:"النتيجة",supplier_smart_router:"الموجّه الذكي",supplier_performance:"أداء المورد",supplier_profitability:"الربحية الفعلية للطلبات المسلّمة عبر API.",supplier_year:"سنة",supplier_revenue:"الإيرادات",supplier_customer_paid:"المبلغ المدفوع من العملاء",supplier_gross_profit:"الربح الإجمالي",supplier_items_sold:"العناصر المباعة",supplier_units_delivered:"الوحدات المسلّمة",supplier_orders_label:"الطلبات",supplier_average_order:"متوسط الطلب 0.00 $",supplier_success_rate:"نسبة النجاح",supplier_api_completed:"تسليمات API المكتملة",supplier_financial_momentum:"الزخم المالي",supplier_financial_daily:"الإيرادات والمصروفات والأرباح اليومية.",supplier_articles:"العناصر",supplier_profit:"الربح",supplier_margin:"الهامش",supplier_no_sales_period:"لا توجد مبيعات في هذه الفترة.",supplier_equivalent_products:"منتجات مكافئة",supplier_equivalent_help:"يقترح Gemini المطابقات. لا تُستخدم في الطلبات إلا المسارات المؤكدة.",supplier_analyze_catalogs:"تحليل الكتالوجات",supplier_to_review:"تحتاج مراجعة",supplier_active_routes:"المسارات الفعالة",supplier_security_label:"الأمان",supplier_manual_validation:"تحقق يدوي",supplier_your_product:"منتجك",supplier_candidate_offer:"العرض المرشح",supplier_confidence:"الثقة",supplier_run_analysis:"شغّل التحليل للبحث عن المنتجات المكافئة.",game_to_settle:"للتسوية",game_coins_staked:"Batman Coins المرهونة",game_search_placeholder:"الفريق، المسابقة، المرحلة..."},
zh:{common_statistics:"统计",common_supplier:"供应商",common_from:"从",common_to:"到",common_filter:"筛选",common_result:"结果",supplier_smart_router:"智能路由",supplier_performance:"供应商表现",supplier_profitability:"通过 API 交付订单的实际盈利能力。",supplier_year:"1 年",supplier_revenue:"收入",supplier_customer_paid:"客户支付金额",supplier_gross_profit:"毛利润",supplier_items_sold:"售出项目",supplier_units_delivered:"已交付单位",supplier_orders_label:"订单",supplier_average_order:"平均订单 $0.00",supplier_success_rate:"成功率",supplier_api_completed:"已完成 API 交付",supplier_financial_momentum:"财务趋势",supplier_financial_daily:"每日收入、支出和利润。",supplier_articles:"项目",supplier_profit:"利润",supplier_margin:"利润率",supplier_no_sales_period:"此期间没有销售。",supplier_equivalent_products:"等价产品",supplier_equivalent_help:"Gemini 会建议匹配项，只有确认的路由会用于订单。",supplier_analyze_catalogs:"分析目录",supplier_to_review:"待检查",supplier_active_routes:"有效路由",supplier_security_label:"安全",supplier_manual_validation:"人工验证",supplier_your_product:"您的产品",supplier_candidate_offer:"候选报价",supplier_confidence:"置信度",supplier_run_analysis:"运行分析以查找等价产品。",game_to_settle:"待结算",game_coins_staked:"已投注 Batman Coins",game_search_placeholder:"球队、赛事、阶段..."},
vi:{common_statistics:"Thống kê",common_supplier:"Nhà cung cấp",common_from:"Từ",common_to:"Đến",common_filter:"Lọc",common_result:"Kết quả",supplier_smart_router:"Bộ định tuyến thông minh",supplier_performance:"Hiệu suất nhà cung cấp",supplier_profitability:"Lợi nhuận thực tế của đơn hàng giao qua API.",supplier_year:"1 năm",supplier_revenue:"Doanh thu",supplier_customer_paid:"Số tiền khách hàng thanh toán",supplier_gross_profit:"Lợi nhuận gộp",supplier_items_sold:"Mặt hàng đã bán",supplier_units_delivered:"Đơn vị đã giao",supplier_orders_label:"Đơn hàng",supplier_average_order:"Đơn trung bình $0.00",supplier_success_rate:"Tỷ lệ thành công",supplier_api_completed:"Giao hàng API hoàn tất",supplier_financial_momentum:"Đà tài chính",supplier_financial_daily:"Doanh thu, chi phí và lợi nhuận hằng ngày.",supplier_articles:"Mặt hàng",supplier_profit:"Lợi nhuận",supplier_margin:"Biên lợi nhuận",supplier_no_sales_period:"Không có doanh số trong giai đoạn này.",supplier_equivalent_products:"Sản phẩm tương đương",supplier_equivalent_help:"Gemini đề xuất đối sánh. Chỉ tuyến đã xác nhận mới dùng cho đơn hàng.",supplier_analyze_catalogs:"Phân tích danh mục",supplier_to_review:"Cần kiểm tra",supplier_active_routes:"Tuyến hoạt động",supplier_security_label:"Bảo mật",supplier_manual_validation:"Xác minh thủ công",supplier_your_product:"Sản phẩm của bạn",supplier_candidate_offer:"Ưu đãi ứng viên",supplier_confidence:"Độ tin cậy",supplier_run_analysis:"Chạy phân tích để tìm sản phẩm tương đương.",game_to_settle:"Cần quyết toán",game_coins_staked:"Batman Coins đã cược",game_search_placeholder:"Đội, giải đấu, giai đoạn..."},
ru:{common_statistics:"Статистика",common_supplier:"Поставщик",common_from:"С",common_to:"По",common_filter:"Фильтр",common_result:"Результат",supplier_smart_router:"Умный маршрутизатор",supplier_performance:"Эффективность поставщика",supplier_profitability:"Фактическая рентабельность заказов, доставленных через API.",supplier_year:"1 год",supplier_revenue:"Выручка",supplier_customer_paid:"Сумма, уплаченная клиентами",supplier_gross_profit:"Валовая прибыль",supplier_items_sold:"Продано позиций",supplier_units_delivered:"Доставлено единиц",supplier_orders_label:"Заказы",supplier_average_order:"Средний заказ $0.00",supplier_success_rate:"Успешность",supplier_api_completed:"Завершённые API-доставки",supplier_financial_momentum:"Финансовая динамика",supplier_financial_daily:"Ежедневная выручка, расходы и прибыль.",supplier_articles:"Позиции",supplier_profit:"Прибыль",supplier_margin:"Маржа",supplier_no_sales_period:"За этот период продаж нет.",supplier_equivalent_products:"Эквивалентные товары",supplier_equivalent_help:"Gemini предлагает совпадения. В заказах используются только подтверждённые маршруты.",supplier_analyze_catalogs:"Анализировать каталоги",supplier_to_review:"На проверку",supplier_active_routes:"Активные маршруты",supplier_security_label:"Безопасность",supplier_manual_validation:"Ручная проверка",supplier_your_product:"Ваш товар",supplier_candidate_offer:"Предложение-кандидат",supplier_confidence:"Уверенность",supplier_run_analysis:"Запустите анализ для поиска эквивалентных товаров.",game_to_settle:"К расчёту",game_coins_staked:"Поставлено Batman Coins",game_search_placeholder:"Команда, турнир, этап..."}
};
Object.entries(EXTENDED_SCREEN_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
const MODAL_SCREEN_TRANSLATIONS = {
fr:{game_min_stake:"Mise minimum",game_max_stake:"Mise maximum",supplier_customize_product:"Personnaliser le produit",supplier_image_link:"Lien de l'image affichée",supplier_image_inherit:"Vide = image reçue du fournisseur.",supplier_received_description:"Description reçue du fournisseur",supplier_no_description:"Aucune description fournisseur.",supplier_english_hint:"Laissez l'anglais vide pour utiliser la description fournisseur.",supplier_auto_translate:"Traduire automatiquement",supplier_save_customization:"Enregistrer la personnalisation",dynamic_min_price:"Prix minimum ($)",dynamic_max_price:"Prix maximum ($)",dynamic_target:"Objectif ventes/jour",dynamic_weekly_cap:"Plafond 7 jours (%)",dynamic_min_confidence:"Confiance minimum (%)",dynamic_psychological:"Arrondir vers un prix psychologique proche",dynamic_bounds_hint:"Le prix restera entre les limites et une commande créée conservera toujours son montant.",product_delivery_type:"Type de livraison",product_auto_stock:"Stock automatique",product_supplier_auto:"Fournisseur API (géré automatiquement)",description_en:"Description principale (anglais)",description_fr:"Description française",description_ar:"Description arabe",description_zh:"Description chinoise",description_vi:"Description vietnamienne",description_ru:"Description russe",activation_en:"Message d'activation (anglais)",activation_fr:"Message d'activation (français)",activation_ar:"Message d'activation (arabe)",activation_zh:"Message d'activation (chinois)",activation_vi:"Message d'activation (vietnamien)",activation_ru:"Message d'activation (russe)",confirmation_en:"Message de confirmation (anglais)",confirmation_fr:"Message de confirmation (français)",confirmation_ar:"Message de confirmation (arabe)",confirmation_zh:"Message de confirmation (chinois)",confirmation_vi:"Message de confirmation (vietnamien)",confirmation_ru:"Message de confirmation (russe)",translate_message:"Traduire le message",image_url_optional:"URL de l'image (optionnel)",promo_fixed_product:"Prix fixe du produit",tiers_help:"Définissez des prix unitaires différents selon la quantité commandée. Le prix de base est utilisé si aucun palier ne correspond.",tiers_add:"Ajouter un palier",order_detail:"Détail de la commande",common_no_item:"Aucun article.",product_edit_title:"Modifier le produit",dynamic_current_price:"Prix actuel",dynamic_recommended_price:"Prix recommandé",dynamic_recommend_hint:"Calculez une recommandation pour afficher les facteurs de décision.",dynamic_simulate:"Simuler 30 jours",finance_withdraw_intro:"Vous êtes sur le point de retirer des fonds du solde virtuel du bot.",finance_current_balance:"Solde actuel : $0.00",finance_confirm_withdraw:"Confirmer le retrait",finance_adjust_balance:"Ajuster le solde virtuel",binance_add_modal:"Ajouter un compte Binance",binance_api_optional:"Clé API (optionnel, pour vérification automatique)",binance_default:"Définir comme compte par défaut",customer_purchases:"Achats du client"},
en:{game_min_stake:"Minimum stake",game_max_stake:"Maximum stake",supplier_customize_product:"Customize product",supplier_image_link:"Displayed image URL",supplier_image_inherit:"Leave empty to use the supplier image.",supplier_received_description:"Description received from supplier",supplier_no_description:"No supplier description.",supplier_english_hint:"Leave English empty to use the supplier description.",supplier_auto_translate:"Translate automatically",supplier_save_customization:"Save customization",dynamic_min_price:"Minimum price ($)",dynamic_max_price:"Maximum price ($)",dynamic_target:"Target sales/day",dynamic_weekly_cap:"7-day limit (%)",dynamic_min_confidence:"Minimum confidence (%)",dynamic_psychological:"Round to a nearby psychological price",dynamic_bounds_hint:"The price stays within its limits and an existing order always keeps its original amount.",product_delivery_type:"Delivery type",product_auto_stock:"Automatic stock",product_supplier_auto:"API supplier (managed automatically)",description_en:"Main description (English)",description_fr:"French description",description_ar:"Arabic description",description_zh:"Chinese description",description_vi:"Vietnamese description",description_ru:"Russian description",activation_en:"Activation message (English)",activation_fr:"Activation message (French)",activation_ar:"Activation message (Arabic)",activation_zh:"Activation message (Chinese)",activation_vi:"Activation message (Vietnamese)",activation_ru:"Activation message (Russian)",confirmation_en:"Confirmation message (English)",confirmation_fr:"Confirmation message (French)",confirmation_ar:"Confirmation message (Arabic)",confirmation_zh:"Confirmation message (Chinese)",confirmation_vi:"Confirmation message (Vietnamese)",confirmation_ru:"Confirmation message (Russian)",translate_message:"Translate message",image_url_optional:"Image URL (optional)",promo_fixed_product:"Fixed product price",tiers_help:"Set different unit prices by ordered quantity. The base price is used when no tier matches.",tiers_add:"Add tier",order_detail:"Order details",common_no_item:"No items.",product_edit_title:"Edit product",dynamic_current_price:"Current price",dynamic_recommended_price:"Recommended price",dynamic_recommend_hint:"Calculate a recommendation to display its decision factors.",dynamic_simulate:"Simulate 30 days",finance_withdraw_intro:"You are about to withdraw funds from the bot's virtual balance.",finance_current_balance:"Current balance: $0.00",finance_confirm_withdraw:"Confirm withdrawal",finance_adjust_balance:"Adjust virtual balance",binance_add_modal:"Add Binance account",binance_api_optional:"API key (optional, for automatic verification)",binance_default:"Set as default account",customer_purchases:"Customer purchases"},
ar:{game_min_stake:"الحد الأدنى للرهان",game_max_stake:"الحد الأقصى للرهان",supplier_customize_product:"تخصيص المنتج",supplier_image_link:"رابط الصورة المعروضة",supplier_image_inherit:"اتركه فارغًا لاستخدام صورة المورد.",supplier_received_description:"الوصف المستلم من المورد",supplier_no_description:"لا يوجد وصف من المورد.",supplier_english_hint:"اترك الإنجليزية فارغة لاستخدام وصف المورد.",supplier_auto_translate:"ترجمة تلقائية",supplier_save_customization:"حفظ التخصيص",dynamic_min_price:"السعر الأدنى ($)",dynamic_max_price:"السعر الأقصى ($)",dynamic_target:"هدف المبيعات/اليوم",dynamic_weekly_cap:"حد 7 أيام (%)",dynamic_min_confidence:"الحد الأدنى للثقة (%)",dynamic_psychological:"التقريب إلى سعر نفسي قريب",dynamic_bounds_hint:"يبقى السعر ضمن الحدود وتحتفظ الطلبات الحالية بمبلغها الأصلي.",product_delivery_type:"نوع التسليم",product_auto_stock:"مخزون تلقائي",product_supplier_auto:"مورد API (يُدار تلقائيًا)",description_en:"الوصف الرئيسي (الإنجليزية)",description_fr:"الوصف الفرنسي",description_ar:"الوصف العربي",description_zh:"الوصف الصيني",description_vi:"الوصف الفيتنامي",description_ru:"الوصف الروسي",activation_en:"رسالة التفعيل (الإنجليزية)",activation_fr:"رسالة التفعيل (الفرنسية)",activation_ar:"رسالة التفعيل (العربية)",activation_zh:"رسالة التفعيل (الصينية)",activation_vi:"رسالة التفعيل (الفيتنامية)",activation_ru:"رسالة التفعيل (الروسية)",confirmation_en:"رسالة التأكيد (الإنجليزية)",confirmation_fr:"رسالة التأكيد (الفرنسية)",confirmation_ar:"رسالة التأكيد (العربية)",confirmation_zh:"رسالة التأكيد (الصينية)",confirmation_vi:"رسالة التأكيد (الفيتنامية)",confirmation_ru:"رسالة التأكيد (الروسية)",translate_message:"ترجمة الرسالة",image_url_optional:"رابط الصورة (اختياري)",promo_fixed_product:"سعر المنتج الثابت",tiers_help:"حدد أسعار وحدات مختلفة حسب الكمية المطلوبة. يُستخدم السعر الأساسي عند عدم مطابقة أي شريحة.",tiers_add:"إضافة شريحة",order_detail:"تفاصيل الطلب",common_no_item:"لا توجد عناصر.",product_edit_title:"تعديل المنتج",dynamic_current_price:"السعر الحالي",dynamic_recommended_price:"السعر الموصى به",dynamic_recommend_hint:"احسب توصية لعرض عوامل القرار.",dynamic_simulate:"محاكاة 30 يومًا",finance_withdraw_intro:"أنت على وشك سحب أموال من الرصيد الافتراضي للبوت.",finance_current_balance:"الرصيد الحالي: 0.00 $",finance_confirm_withdraw:"تأكيد السحب",finance_adjust_balance:"تعديل الرصيد الافتراضي",binance_add_modal:"إضافة حساب Binance",binance_api_optional:"مفتاح API (اختياري للتحقق التلقائي)",binance_default:"تعيينه كحساب افتراضي",customer_purchases:"مشتريات العميل"},
zh:{game_min_stake:"最低投注",game_max_stake:"最高投注",supplier_customize_product:"自定义产品",supplier_image_link:"显示图片 URL",supplier_image_inherit:"留空以使用供应商图片。",supplier_received_description:"供应商提供的描述",supplier_no_description:"供应商没有描述。",supplier_english_hint:"英文留空时使用供应商描述。",supplier_auto_translate:"自动翻译",supplier_save_customization:"保存自定义",dynamic_min_price:"最低价格（$）",dynamic_max_price:"最高价格（$）",dynamic_target:"目标销量/天",dynamic_weekly_cap:"7 天上限（%）",dynamic_min_confidence:"最低置信度（%）",dynamic_psychological:"取邻近的心理价格",dynamic_bounds_hint:"价格会保持在限制内，已有订单始终保留原金额。",product_delivery_type:"交付类型",product_auto_stock:"自动库存",product_supplier_auto:"API 供应商（自动管理）",description_en:"主要描述（英文）",description_fr:"法文描述",description_ar:"阿拉伯文描述",description_zh:"中文描述",description_vi:"越南文描述",description_ru:"俄文描述",activation_en:"激活消息（英文）",activation_fr:"激活消息（法文）",activation_ar:"激活消息（阿拉伯文）",activation_zh:"激活消息（中文）",activation_vi:"激活消息（越南文）",activation_ru:"激活消息（俄文）",confirmation_en:"确认消息（英文）",confirmation_fr:"确认消息（法文）",confirmation_ar:"确认消息（阿拉伯文）",confirmation_zh:"确认消息（中文）",confirmation_vi:"确认消息（越南文）",confirmation_ru:"确认消息（俄文）",translate_message:"翻译消息",image_url_optional:"图片 URL（可选）",promo_fixed_product:"固定产品价格",tiers_help:"可按订购数量设置不同单价。没有匹配阶梯时使用基础价格。",tiers_add:"添加阶梯",order_detail:"订单详情",common_no_item:"没有项目。",product_edit_title:"编辑产品",dynamic_current_price:"当前价格",dynamic_recommended_price:"推荐价格",dynamic_recommend_hint:"计算建议以显示决策因素。",dynamic_simulate:"模拟 30 天",finance_withdraw_intro:"您即将从机器人的虚拟余额中提取资金。",finance_current_balance:"当前余额：$0.00",finance_confirm_withdraw:"确认提现",finance_adjust_balance:"调整虚拟余额",binance_add_modal:"添加 Binance 账户",binance_api_optional:"API 密钥（可选，用于自动验证）",binance_default:"设为默认账户",customer_purchases:"客户购买记录"},
vi:{game_min_stake:"Mức cược tối thiểu",game_max_stake:"Mức cược tối đa",supplier_customize_product:"Tùy chỉnh sản phẩm",supplier_image_link:"URL ảnh hiển thị",supplier_image_inherit:"Để trống để dùng ảnh nhà cung cấp.",supplier_received_description:"Mô tả nhận từ nhà cung cấp",supplier_no_description:"Nhà cung cấp không có mô tả.",supplier_english_hint:"Để trống tiếng Anh để dùng mô tả nhà cung cấp.",supplier_auto_translate:"Dịch tự động",supplier_save_customization:"Lưu tùy chỉnh",dynamic_min_price:"Giá tối thiểu ($)",dynamic_max_price:"Giá tối đa ($)",dynamic_target:"Mục tiêu bán/ngày",dynamic_weekly_cap:"Giới hạn 7 ngày (%)",dynamic_min_confidence:"Độ tin cậy tối thiểu (%)",dynamic_psychological:"Làm tròn đến giá tâm lý gần nhất",dynamic_bounds_hint:"Giá luôn trong giới hạn và đơn hàng hiện có giữ nguyên số tiền ban đầu.",product_delivery_type:"Hình thức giao",product_auto_stock:"Tồn kho tự động",product_supplier_auto:"Nhà cung cấp API (quản lý tự động)",description_en:"Mô tả chính (tiếng Anh)",description_fr:"Mô tả tiếng Pháp",description_ar:"Mô tả tiếng Ả Rập",description_zh:"Mô tả tiếng Trung",description_vi:"Mô tả tiếng Việt",description_ru:"Mô tả tiếng Nga",activation_en:"Tin nhắn kích hoạt (tiếng Anh)",activation_fr:"Tin nhắn kích hoạt (tiếng Pháp)",activation_ar:"Tin nhắn kích hoạt (tiếng Ả Rập)",activation_zh:"Tin nhắn kích hoạt (tiếng Trung)",activation_vi:"Tin nhắn kích hoạt (tiếng Việt)",activation_ru:"Tin nhắn kích hoạt (tiếng Nga)",confirmation_en:"Tin nhắn xác nhận (tiếng Anh)",confirmation_fr:"Tin nhắn xác nhận (tiếng Pháp)",confirmation_ar:"Tin nhắn xác nhận (tiếng Ả Rập)",confirmation_zh:"Tin nhắn xác nhận (tiếng Trung)",confirmation_vi:"Tin nhắn xác nhận (tiếng Việt)",confirmation_ru:"Tin nhắn xác nhận (tiếng Nga)",translate_message:"Dịch tin nhắn",image_url_optional:"URL ảnh (không bắt buộc)",promo_fixed_product:"Giá cố định của sản phẩm",tiers_help:"Đặt đơn giá khác nhau theo số lượng đặt. Giá cơ bản được dùng khi không khớp bậc nào.",tiers_add:"Thêm bậc",order_detail:"Chi tiết đơn hàng",common_no_item:"Không có mặt hàng.",product_edit_title:"Sửa sản phẩm",dynamic_current_price:"Giá hiện tại",dynamic_recommended_price:"Giá đề xuất",dynamic_recommend_hint:"Tính đề xuất để hiển thị các yếu tố quyết định.",dynamic_simulate:"Mô phỏng 30 ngày",finance_withdraw_intro:"Bạn sắp rút tiền khỏi số dư ảo của bot.",finance_current_balance:"Số dư hiện tại: $0.00",finance_confirm_withdraw:"Xác nhận rút",finance_adjust_balance:"Điều chỉnh số dư ảo",binance_add_modal:"Thêm tài khoản Binance",binance_api_optional:"Khóa API (không bắt buộc, để xác minh tự động)",binance_default:"Đặt làm tài khoản mặc định",customer_purchases:"Giao dịch mua của khách"},
ru:{game_min_stake:"Минимальная ставка",game_max_stake:"Максимальная ставка",supplier_customize_product:"Настроить товар",supplier_image_link:"URL отображаемого изображения",supplier_image_inherit:"Оставьте пустым, чтобы использовать изображение поставщика.",supplier_received_description:"Описание от поставщика",supplier_no_description:"У поставщика нет описания.",supplier_english_hint:"Оставьте английский пустым, чтобы использовать описание поставщика.",supplier_auto_translate:"Перевести автоматически",supplier_save_customization:"Сохранить настройку",dynamic_min_price:"Минимальная цена ($)",dynamic_max_price:"Максимальная цена ($)",dynamic_target:"Цель продаж/день",dynamic_weekly_cap:"Лимит за 7 дней (%)",dynamic_min_confidence:"Минимальная уверенность (%)",dynamic_psychological:"Округлять до ближайшей психологической цены",dynamic_bounds_hint:"Цена останется в пределах, а созданный заказ всегда сохранит исходную сумму.",product_delivery_type:"Тип доставки",product_auto_stock:"Автоматический склад",product_supplier_auto:"API-поставщик (управляется автоматически)",description_en:"Основное описание (английский)",description_fr:"Описание на французском",description_ar:"Описание на арабском",description_zh:"Описание на китайском",description_vi:"Описание на вьетнамском",description_ru:"Описание на русском",activation_en:"Сообщение активации (английский)",activation_fr:"Сообщение активации (французский)",activation_ar:"Сообщение активации (арабский)",activation_zh:"Сообщение активации (китайский)",activation_vi:"Сообщение активации (вьетнамский)",activation_ru:"Сообщение активации (русский)",confirmation_en:"Сообщение подтверждения (английский)",confirmation_fr:"Сообщение подтверждения (французский)",confirmation_ar:"Сообщение подтверждения (арабский)",confirmation_zh:"Сообщение подтверждения (китайский)",confirmation_vi:"Сообщение подтверждения (вьетнамский)",confirmation_ru:"Сообщение подтверждения (русский)",translate_message:"Перевести сообщение",image_url_optional:"URL изображения (необязательно)",promo_fixed_product:"Фиксированная цена товара",tiers_help:"Задайте разные цены за единицу в зависимости от количества. Если уровень не подходит, используется базовая цена.",tiers_add:"Добавить уровень",order_detail:"Детали заказа",common_no_item:"Нет позиций.",product_edit_title:"Изменить товар",dynamic_current_price:"Текущая цена",dynamic_recommended_price:"Рекомендуемая цена",dynamic_recommend_hint:"Рассчитайте рекомендацию, чтобы увидеть факторы решения.",dynamic_simulate:"Смоделировать 30 дней",finance_withdraw_intro:"Вы собираетесь вывести средства с виртуального баланса бота.",finance_current_balance:"Текущий баланс: $0.00",finance_confirm_withdraw:"Подтвердить вывод",finance_adjust_balance:"Изменить виртуальный баланс",binance_add_modal:"Добавить аккаунт Binance",binance_api_optional:"Ключ API (необязательно, для автоматической проверки)",binance_default:"Сделать аккаунтом по умолчанию",customer_purchases:"Покупки клиента"}
};
Object.entries(MODAL_SCREEN_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
Object.assign(LANG.fr, {dynamic_daily_cap:"Plafond 24 h (%)", product_binance_optional:"Compte Binance Pay (optionnel)", translate_short:"✨ Traduire", product_warranty_days:"Garantie (jours)", reseller_secret_revoked:"Le secret actuel cessera de fonctionner."});
Object.assign(LANG.en, {dynamic_daily_cap:"24-hour limit (%)", product_binance_optional:"Binance Pay account (optional)", translate_short:"✨ Translate", product_warranty_days:"Warranty (days)", reseller_secret_revoked:"The current secret will stop working."});
Object.assign(LANG.ar, {dynamic_daily_cap:"حد 24 ساعة (%)", product_binance_optional:"حساب Binance Pay (اختياري)", translate_short:"✨ ترجمة", product_warranty_days:"الضمان (أيام)", reseller_secret_revoked:"سيتوقف المفتاح السري الحالي عن العمل."});
Object.assign(LANG.zh, {dynamic_daily_cap:"24 小时上限（%）", product_binance_optional:"Binance Pay 账户（可选）", translate_short:"✨ 翻译", product_warranty_days:"保修（天）", reseller_secret_revoked:"当前签名密钥将停止工作。"});
Object.assign(LANG.vi, {dynamic_daily_cap:"Giới hạn 24 giờ (%)", product_binance_optional:"Tài khoản Binance Pay (không bắt buộc)", translate_short:"✨ Dịch", product_warranty_days:"Bảo hành (ngày)", reseller_secret_revoked:"Mã bí mật hiện tại sẽ ngừng hoạt động."});
Object.assign(LANG.ru, {dynamic_daily_cap:"Лимит за 24 часа (%)", product_binance_optional:"Аккаунт Binance Pay (необязательно)", translate_short:"✨ Перевести", product_warranty_days:"Гарантия (дни)", reseller_secret_revoked:"Текущий секрет перестанет работать."});
const MISC_UI_TRANSLATIONS = {
fr:{game_configuration:"Configuration",game_close_before:"Fermer avant le début",game_hour:"1 heure",game_burned:"Batman Coins brûlés (%)",game_publish_now:"Publier maintenant",game_draft_hint:"Sinon le match restera en brouillon.",common_emoji:"Emoji",classic_emoji:"Emoji classique",custom_emoji_optional:"ID emoji personnalisé (optionnel)",custom_emoji_telegram:"ID emoji personnalisé Telegram",language_english_default:"Anglais (défaut)",language_french:"Français",language_arabic:"Arabe",language_chinese:"Chinois",language_vietnamese:"Vietnamien",language_russian:"Russe",dynamic_mode:"Mode",dynamic_auto_delay:"Automatique après délai",dynamic_suggestion_only:"Suggestion uniquement",dynamic_sensitivity:"Sensibilité",dynamic_cautious:"Prudente",dynamic_normal:"Normale",dynamic_aggressive:"Agressive",dynamic_max_variation:"Variation max (%)",dynamic_cooldown:"Délai (heures)",common_default:"Par défaut",stock_restock_alert:"Diffuser une alerte de restock (Telegram)",promo_percent:"Pourcentage",promo_discount_amount:"Montant de réduction",promo_max_user:"Max / util.",promo_max_order:"Max articles / commande",promo_specific_products:"Produits spécifiques",promo_optional_classic:"Optionnel pour les réductions classiques.",tiers_title:"Tarifs par palier",order_delivered_items:"Articles livrés",stock_available_items:"Articles disponibles",dynamic_calculate:"Calculer maintenant",dynamic_apply:"Appliquer la suggestion",dynamic_existing_orders:"Les commandes existantes ne changent jamais de montant.",dynamic_latest:"Dernières décisions",common_no_history:"Aucun historique.",finance_withdraw_title:"Retirer des fonds",finance_withdraw_amount:"Montant à retirer ($)",finance_withdraw_all:"Tout retirer",finance_adjust_help:"Ajoutez ou retirez manuellement un montant (utilisez un nombre négatif pour retirer).",common_amount_usd:"Montant ($)",binance_label:"Libellé (nom affiché)",binance_api_secret_optional:"Secret API (optionnel)",common_spent:"Dépenses",common_registration:"Inscription",common_order:"Commande",common_quantity:"Qté",common_payment:"Paiement",reseller_webhook_help:"Événements signés et relancés automatiquement.",export_transactions:"Exporter les transactions",export_format:"Format d'export",export_start_date:"Date de début",export_end_date:"Date de fin",export_button:"Exporter"},
en:{game_configuration:"Configuration",game_close_before:"Close before kickoff",game_hour:"1 hour",game_burned:"Batman Coins burned (%)",game_publish_now:"Publish now",game_draft_hint:"Otherwise the match remains a draft.",common_emoji:"Emoji",classic_emoji:"Standard emoji",custom_emoji_optional:"Custom emoji ID (optional)",custom_emoji_telegram:"Telegram custom emoji ID",language_english_default:"English (default)",language_french:"French",language_arabic:"Arabic",language_chinese:"Chinese",language_vietnamese:"Vietnamese",language_russian:"Russian",dynamic_mode:"Mode",dynamic_auto_delay:"Automatic after delay",dynamic_suggestion_only:"Suggestion only",dynamic_sensitivity:"Sensitivity",dynamic_cautious:"Cautious",dynamic_normal:"Normal",dynamic_aggressive:"Aggressive",dynamic_max_variation:"Maximum change (%)",dynamic_cooldown:"Delay (hours)",common_default:"Default",stock_restock_alert:"Send a restock alert (Telegram)",promo_percent:"Percentage",promo_discount_amount:"Discount amount",promo_max_user:"Max / user",promo_max_order:"Max items / order",promo_specific_products:"Specific products",promo_optional_classic:"Optional for standard discounts.",tiers_title:"Pricing tiers",order_delivered_items:"Delivered items",stock_available_items:"Available items",dynamic_calculate:"Calculate now",dynamic_apply:"Apply suggestion",dynamic_existing_orders:"Existing orders never change amount.",dynamic_latest:"Latest decisions",common_no_history:"No history.",finance_withdraw_title:"Withdraw funds",finance_withdraw_amount:"Amount to withdraw ($)",finance_withdraw_all:"Withdraw all",finance_adjust_help:"Add or remove an amount manually (use a negative number to withdraw).",common_amount_usd:"Amount ($)",binance_label:"Label (display name)",binance_api_secret_optional:"API secret (optional)",common_spent:"Spent",common_registration:"Joined",common_order:"Order",common_quantity:"Qty",common_payment:"Payment",reseller_webhook_help:"Signed events with automatic retries.",export_transactions:"Export transactions",export_format:"Export format",export_start_date:"Start date",export_end_date:"End date",export_button:"Export"},
ar:{game_configuration:"الإعداد",game_close_before:"الإغلاق قبل البداية",game_hour:"ساعة",game_burned:"Batman Coins المحروقة (%)",game_publish_now:"النشر الآن",game_draft_hint:"وإلا ستبقى المباراة مسودة.",common_emoji:"الرمز",classic_emoji:"رمز عادي",custom_emoji_optional:"معرّف رمز مخصص (اختياري)",custom_emoji_telegram:"معرّف رمز Telegram المخصص",language_english_default:"الإنجليزية (افتراضي)",language_french:"الفرنسية",language_arabic:"العربية",language_chinese:"الصينية",language_vietnamese:"الفيتنامية",language_russian:"الروسية",dynamic_mode:"الوضع",dynamic_auto_delay:"تلقائي بعد التأخير",dynamic_suggestion_only:"اقتراح فقط",dynamic_sensitivity:"الحساسية",dynamic_cautious:"حذر",dynamic_normal:"عادي",dynamic_aggressive:"قوي",dynamic_max_variation:"أقصى تغيير (%)",dynamic_cooldown:"التأخير (ساعات)",common_default:"افتراضي",stock_restock_alert:"إرسال تنبيه إعادة التخزين (Telegram)",promo_percent:"النسبة",promo_discount_amount:"مبلغ الخصم",promo_max_user:"الحد لكل مستخدم",promo_max_order:"أقصى عناصر لكل طلب",promo_specific_products:"منتجات محددة",promo_optional_classic:"اختياري للخصومات العادية.",tiers_title:"شرائح الأسعار",order_delivered_items:"العناصر المسلّمة",stock_available_items:"العناصر المتاحة",dynamic_calculate:"احسب الآن",dynamic_apply:"تطبيق الاقتراح",dynamic_existing_orders:"لا تتغير مبالغ الطلبات الحالية.",dynamic_latest:"أحدث القرارات",common_no_history:"لا يوجد سجل.",finance_withdraw_title:"سحب الأموال",finance_withdraw_amount:"المبلغ المراد سحبه ($)",finance_withdraw_all:"سحب الكل",finance_adjust_help:"أضف أو اسحب مبلغًا يدويًا (استخدم رقمًا سالبًا للسحب).",common_amount_usd:"المبلغ ($)",binance_label:"الاسم المعروض",binance_api_secret_optional:"سر API (اختياري)",common_spent:"الإنفاق",common_registration:"الانضمام",common_order:"الطلب",common_quantity:"الكمية",common_payment:"الدفع",reseller_webhook_help:"أحداث موقعة مع إعادة محاولة تلقائية.",export_transactions:"تصدير المعاملات",export_format:"صيغة التصدير",export_start_date:"تاريخ البداية",export_end_date:"تاريخ النهاية",export_button:"تصدير"},
zh:{game_configuration:"配置",game_close_before:"开赛前关闭",game_hour:"1 小时",game_burned:"销毁 Batman Coins（%）",game_publish_now:"立即发布",game_draft_hint:"否则比赛将保留为草稿。",common_emoji:"表情",classic_emoji:"标准表情",custom_emoji_optional:"自定义表情 ID（可选）",custom_emoji_telegram:"Telegram 自定义表情 ID",language_english_default:"英文（默认）",language_french:"法文",language_arabic:"阿拉伯文",language_chinese:"中文",language_vietnamese:"越南文",language_russian:"俄文",dynamic_mode:"模式",dynamic_auto_delay:"延迟后自动",dynamic_suggestion_only:"仅建议",dynamic_sensitivity:"敏感度",dynamic_cautious:"谨慎",dynamic_normal:"正常",dynamic_aggressive:"激进",dynamic_max_variation:"最大变化（%）",dynamic_cooldown:"延迟（小时）",common_default:"默认",stock_restock_alert:"发送补货提醒（Telegram）",promo_percent:"百分比",promo_discount_amount:"折扣金额",promo_max_user:"每用户上限",promo_max_order:"每单最大项目",promo_specific_products:"指定产品",promo_optional_classic:"标准折扣可选。",tiers_title:"价格阶梯",order_delivered_items:"已交付项目",stock_available_items:"可用项目",dynamic_calculate:"立即计算",dynamic_apply:"应用建议",dynamic_existing_orders:"已有订单金额永不改变。",dynamic_latest:"最近决策",common_no_history:"没有历史记录。",finance_withdraw_title:"提取资金",finance_withdraw_amount:"提现金额（$）",finance_withdraw_all:"全部提现",finance_adjust_help:"手动增加或减少金额（提现请输入负数）。",common_amount_usd:"金额（$）",binance_label:"标签（显示名称）",binance_api_secret_optional:"API 密钥（可选）",common_spent:"支出",common_registration:"加入时间",common_order:"订单",common_quantity:"数量",common_payment:"付款",reseller_webhook_help:"签名事件并自动重试。",export_transactions:"导出交易",export_format:"导出格式",export_start_date:"开始日期",export_end_date:"结束日期",export_button:"导出"},
vi:{game_configuration:"Cấu hình",game_close_before:"Đóng trước giờ bắt đầu",game_hour:"1 giờ",game_burned:"Batman Coins bị đốt (%)",game_publish_now:"Đăng ngay",game_draft_hint:"Nếu không, trận sẽ ở dạng nháp.",common_emoji:"Emoji",classic_emoji:"Emoji thường",custom_emoji_optional:"ID emoji tùy chỉnh (không bắt buộc)",custom_emoji_telegram:"ID emoji Telegram tùy chỉnh",language_english_default:"Tiếng Anh (mặc định)",language_french:"Tiếng Pháp",language_arabic:"Tiếng Ả Rập",language_chinese:"Tiếng Trung",language_vietnamese:"Tiếng Việt",language_russian:"Tiếng Nga",dynamic_mode:"Chế độ",dynamic_auto_delay:"Tự động sau độ trễ",dynamic_suggestion_only:"Chỉ đề xuất",dynamic_sensitivity:"Độ nhạy",dynamic_cautious:"Thận trọng",dynamic_normal:"Bình thường",dynamic_aggressive:"Mạnh",dynamic_max_variation:"Thay đổi tối đa (%)",dynamic_cooldown:"Độ trễ (giờ)",common_default:"Mặc định",stock_restock_alert:"Gửi cảnh báo nhập lại hàng (Telegram)",promo_percent:"Phần trăm",promo_discount_amount:"Số tiền giảm",promo_max_user:"Tối đa / người dùng",promo_max_order:"Tối đa mặt hàng / đơn",promo_specific_products:"Sản phẩm cụ thể",promo_optional_classic:"Không bắt buộc với giảm giá tiêu chuẩn.",tiers_title:"Bậc giá",order_delivered_items:"Mặt hàng đã giao",stock_available_items:"Mặt hàng có sẵn",dynamic_calculate:"Tính ngay",dynamic_apply:"Áp dụng đề xuất",dynamic_existing_orders:"Đơn hàng hiện có không bao giờ đổi số tiền.",dynamic_latest:"Quyết định gần đây",common_no_history:"Chưa có lịch sử.",finance_withdraw_title:"Rút tiền",finance_withdraw_amount:"Số tiền rút ($)",finance_withdraw_all:"Rút tất cả",finance_adjust_help:"Thêm hoặc bớt tiền thủ công (dùng số âm để rút).",common_amount_usd:"Số tiền ($)",binance_label:"Nhãn (tên hiển thị)",binance_api_secret_optional:"API secret (không bắt buộc)",common_spent:"Đã chi",common_registration:"Tham gia",common_order:"Đơn hàng",common_quantity:"SL",common_payment:"Thanh toán",reseller_webhook_help:"Sự kiện có chữ ký và tự động thử lại.",export_transactions:"Xuất giao dịch",export_format:"Định dạng xuất",export_start_date:"Ngày bắt đầu",export_end_date:"Ngày kết thúc",export_button:"Xuất"},
ru:{game_configuration:"Настройка",game_close_before:"Закрыть до начала",game_hour:"1 час",game_burned:"Сжигается Batman Coins (%)",game_publish_now:"Опубликовать сейчас",game_draft_hint:"Иначе матч останется черновиком.",common_emoji:"Эмодзи",classic_emoji:"Обычный эмодзи",custom_emoji_optional:"ID пользовательского эмодзи (необязательно)",custom_emoji_telegram:"ID пользовательского эмодзи Telegram",language_english_default:"Английский (по умолчанию)",language_french:"Французский",language_arabic:"Арабский",language_chinese:"Китайский",language_vietnamese:"Вьетнамский",language_russian:"Русский",dynamic_mode:"Режим",dynamic_auto_delay:"Автоматически после задержки",dynamic_suggestion_only:"Только рекомендация",dynamic_sensitivity:"Чувствительность",dynamic_cautious:"Осторожная",dynamic_normal:"Нормальная",dynamic_aggressive:"Агрессивная",dynamic_max_variation:"Макс. изменение (%)",dynamic_cooldown:"Задержка (часы)",common_default:"По умолчанию",stock_restock_alert:"Отправить уведомление о пополнении (Telegram)",promo_percent:"Процент",promo_discount_amount:"Сумма скидки",promo_max_user:"Макс. на пользователя",promo_max_order:"Макс. позиций в заказе",promo_specific_products:"Определённые товары",promo_optional_classic:"Необязательно для обычных скидок.",tiers_title:"Ценовые уровни",order_delivered_items:"Доставленные позиции",stock_available_items:"Доступные позиции",dynamic_calculate:"Рассчитать сейчас",dynamic_apply:"Применить рекомендацию",dynamic_existing_orders:"Сумма существующих заказов никогда не меняется.",dynamic_latest:"Последние решения",common_no_history:"Истории нет.",finance_withdraw_title:"Вывести средства",finance_withdraw_amount:"Сумма вывода ($)",finance_withdraw_all:"Вывести всё",finance_adjust_help:"Добавьте или уберите сумму вручную (для вывода используйте отрицательное число).",common_amount_usd:"Сумма ($)",binance_label:"Метка (отображаемое имя)",binance_api_secret_optional:"Секрет API (необязательно)",common_spent:"Расходы",common_registration:"Регистрация",common_order:"Заказ",common_quantity:"Кол-во",common_payment:"Платёж",reseller_webhook_help:"Подписанные события с автоматическими повторами.",export_transactions:"Экспорт транзакций",export_format:"Формат экспорта",export_start_date:"Дата начала",export_end_date:"Дата окончания",export_button:"Экспорт"}
};
Object.entries(MISC_UI_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));
Object.assign(LANG.fr, {common_optional:"optionnel", finance_current_balance_label:"Solde actuel :", binance_api_optional_suffix:"Optionnel, pour vérification automatique"});
Object.assign(LANG.en, {common_optional:"optional", finance_current_balance_label:"Current balance:", binance_api_optional_suffix:"Optional, for automatic verification"});
Object.assign(LANG.ar, {common_optional:"اختياري", finance_current_balance_label:"الرصيد الحالي:", binance_api_optional_suffix:"اختياري، للتحقق التلقائي"});
Object.assign(LANG.zh, {common_optional:"可选", finance_current_balance_label:"当前余额：", binance_api_optional_suffix:"可选，用于自动验证"});
Object.assign(LANG.vi, {common_optional:"không bắt buộc", finance_current_balance_label:"Số dư hiện tại:", binance_api_optional_suffix:"Không bắt buộc, để xác minh tự động"});
Object.assign(LANG.ru, {common_optional:"необязательно", finance_current_balance_label:"Текущий баланс:", binance_api_optional_suffix:"Необязательно, для автоматической проверки"});
Object.assign(LANG.fr, {product_binance_account:"Compte Binance Pay", order_delivered_items_count:"Articles livrés —", stock_available_items_count:"Articles disponibles —"});
Object.assign(LANG.en, {product_binance_account:"Binance Pay account", order_delivered_items_count:"Delivered items —", stock_available_items_count:"Available items —"});
Object.assign(LANG.ar, {product_binance_account:"حساب Binance Pay", order_delivered_items_count:"العناصر المسلّمة —", stock_available_items_count:"العناصر المتاحة —"});
Object.assign(LANG.zh, {product_binance_account:"Binance Pay 账户", order_delivered_items_count:"已交付项目 —", stock_available_items_count:"可用项目 —"});
Object.assign(LANG.vi, {product_binance_account:"Tài khoản Binance Pay", order_delivered_items_count:"Mặt hàng đã giao —", stock_available_items_count:"Mặt hàng có sẵn —"});
Object.assign(LANG.ru, {product_binance_account:"Аккаунт Binance Pay", order_delivered_items_count:"Доставленные позиции —", stock_available_items_count:"Доступные позиции —"});
const LEGACY_STATIC_SOURCE_KEYS = new Map(Object.entries({
    "✨ Traduire tout":"translate_all", "Stock":"table_stock", "Actions":"table_actions", "Code":"table_code", "N° Commande":"table_order_number", "Fournisseur":"table_supplier", "Reçu / attendu":"table_received_expected", "Problème":"table_issue", "Mis à jour":"table_updated",
    "Analyse & Statistiques":"tab_stats", "Meilleur Produit":"stats_best_product", "0 vente(s)":"stats_zero_sales", "$0.00 de revenus":"stats_zero_revenue", "Volume de Ventes":"stats_sales_volume", "Alertes de Stock":"stats_stock_alerts", "Produits à restocker (< 3)":"stats_restock_help", "Chiffre d'affaires par produit":"stats_revenue_by_product", "Momentum des ventes par produit":"stats_momentum_title", "Ventes quotidiennes sur 30 jours. Cliquez sur un produit pour l'afficher ou le masquer.":"stats_momentum_description", "Vue: 30 jours":"stats_view_30", "Hier: -":"stats_yesterday_none", "Mesure comparable depuis le premier clic Acheter suivi.":"conversion_tracking_note", "Conversion: -":"conversion_rate_none", "Chargement du tunnel...":"conversion_loading", "Produits populaires qui convertissent mal":"conversion_popular_low", "Produits à surveiller":"stats_watch_products", "Chargement des alertes...":"stats_alert_loading", "Performances des Produits":"stats_product_performance", "Rechercher un produit...":"stats_search_product", "Chargement des statistiques...":"stats_loading", "Chargement...":"loading",
    "Revenus (Aujourd'hui)":"finance_today", "Revenus (7 Jours)":"finance_7d", "Revenus (30 Jours)":"finance_30d", "Solde opérationnel suivi":"finance_operational_balance", "Répartition des Ventes (30 Jours)":"finance_sales_breakdown", "Achats Binance Pay":"finance_binance_sales", "Achats BEP20":"finance_bep20_sales", "Achats TRC20":"finance_trc20_sales", "Achats par Wallet":"finance_wallet_sales", "Montant Total Rechargé":"finance_total_topup", "Nombre de Recharges":"finance_topup_count",
    "Sous-paiements, confirmations, expirations et paiements reçus après annulation.":"review_description", "À traiter":"review_to_process", "Sous-payés":"review_underpaid", "En confirmation":"review_confirming", "Après annulation":"review_after_cancel", "Expirés":"review_expired", "Tous":"review_all", "Confirmations":"review_confirmations", "Validation":"review_validation", "Aucun paiement dans cette categorie.":"review_empty",
    "Produit":"common_product", "Vues":"common_views", "Clics Acheter":"common_buy_clicks", "Paiements créés":"common_payments_created", "Terminés":"common_completed", "Conversion":"common_conversion", "Prix":"common_price", "Quantité vendue":"common_quantity_sold", "Chiffre d'affaires":"common_revenue", "Stock restant":"common_stock_remaining", "Performance / Statut":"common_performance_status", "Client":"common_client", "État":"common_status", "Date":"common_date", "Action":"common_action",
    "Gestion Financière":"finance_title", "Toutes les méthodes":"finance_all_methods", "Portefeuille Interne":"finance_internal_wallet", "Withdraw":"finance_withdraw", "Ajuster":"finance_adjust", "Rechargements Wallet (30 Jours)":"finance_topups_30", "Afficher les dossiers classés":"review_show_archived", "Paiement":"review_payment", "Chargement des paiements...":"review_loading_payments", "Ajouter un compte":"binance_add_account", "Aucun compte Binance.":"binance_no_accounts",
    "Catalogue externe":"supplier_external_catalog", "Bot fournisseur":"supplier_bot", "Non configuré":"supplier_not_configured", "Solde fournisseur":"supplier_balance_label", "Dernière synchronisation":"supplier_last_sync", "Jamais":"supplier_never", "Produits affichés":"supplier_visible_products", "Livraisons à vérifier":"supplier_pending_deliveries", "Configuration du catalogue":"supplier_catalog_settings", "Nom affiche":"supplier_display_name", "Nom affiché":"supplier_display_name", "Connexion active":"supplier_active_connection", "Masque tous les produits distants lorsqu'elle est désactivée.":"supplier_active_hint", "Marge globale":"supplier_global_margin", "Valeur":"supplier_value", "Unités pour 1 USD":"supplier_units_per_usd", "La clé est lue depuis SUPPLIER_API_KEY sur Railway et n'est jamais envoyée au navigateur.":"supplier_key_hint", "Catalogue fournisseur":"supplier_catalog", "Le stock achetable est automatiquement limité par votre solde fournisseur. Un produit à 0 n'apparaît pas sur le bot.":"supplier_catalog_hint", "Afficher":"supplier_show", "Produit fournisseur":"supplier_source_product", "Prix source":"supplier_source_price", "Stock API":"supplier_api_stock", "Achetable":"supplier_purchasable", "Marge appliquée":"supplier_applied_margin", "Prix client":"supplier_client_price", "Synchronisez le catalogue pour commencer.":"supplier_sync_start", "7 jours":"supplier_period_7", "30 jours":"supplier_period_30", "90 jours":"supplier_period_90", "Dépensé":"supplier_spent", "Coût des achats fournisseur":"supplier_purchase_cost", "Ventes par produit":"supplier_sales_by_product", "Identifiez les produits qui génèrent le plus de volume et de marge.":"supplier_sales_help",
    "Match Arena":"game_arena", "Choisissez les matchs du fournisseur qui seront visibles dans le bot.":"game_description", "Actualiser le catalogue":"game_refresh_catalog", "Matchs ouverts":"game_open_matches", "API sportive non configurée":"game_api_missing", "Ajoutez FOOTBALL_DATA_API_KEY dans les variables Railway. Aucun appel externe n'est effectué sans cette clé.":"game_api_missing_help", "Catalogue":"game_catalog", "Matchs publiés":"game_published", "Résultats à confirmer":"game_results_confirm", "Historique":"game_history", "Recherche":"game_search", "Matchs disponibles":"game_available", "Chargez le catalogue pour commencer.":"game_load_start", "Compétition":"game_competition", "Match":"game_match", "Phase":"game_stage", "Aucun match chargé.":"game_no_loaded", "Seuls ces matchs sont synchronisés en arrière-plan et visibles par les clients.":"game_published_help", "Marché":"game_market", "Fermeture":"game_closing", "Pot":"game_pot", "Aucun match publié.":"game_no_published", "Le résultat du fournisseur est proposé, mais aucun gain ne part sans confirmation.":"game_results_help", "Score API":"game_api_score", "Résultat proposé":"game_proposed_result", "Aucun résultat en attente.":"game_no_pending", "Matchs réglés ou annulés et résultat appliqué.":"game_history_help", "Pronostics":"game_predictions", "Aucun historique.":"game_no_history",
    "URL de la Photo / Image (optionnel) :":"broadcast_photo_url", "Aucun bouton":"broadcast_no_button", "Bouton d'achat (Produit)":"broadcast_product_button", "Sélectionner le produit :":"broadcast_select_product", "Adresse BEP20 USDT (BNB Chain)":"settings_bep20_address", "Adresse TRC20 USDT (TRON Chain)":"settings_trc20_address", "Enregistrer les adresses":"settings_save_addresses",
    "Statistiques":"common_statistics", "Fournisseur":"common_supplier", "Du":"common_from", "Au":"common_to", "Filtrer":"common_filter", "Résultat":"common_result", "Routeur intelligent":"supplier_smart_router", "Performance du fournisseur":"supplier_performance", "Rentabilité réelle des commandes livrées par API.":"supplier_profitability", "1 an":"supplier_year", "Chiffre d’affaires":"supplier_revenue", "Montant payé par les clients":"supplier_customer_paid", "Bénéfice brut":"supplier_gross_profit", "Articles vendus":"supplier_items_sold", "Unités livrées":"supplier_units_delivered", "Commandes":"supplier_orders_label", "Panier moyen $0.00":"supplier_average_order", "Taux de réussite":"supplier_success_rate", "Livraisons API terminées":"supplier_api_completed", "Momentum financier":"supplier_financial_momentum", "Revenus, dépenses et bénéfices quotidiens.":"supplier_financial_daily", "Articles":"supplier_articles", "Bénéfice":"supplier_profit", "Marge":"supplier_margin", "Aucune vente sur cette période.":"supplier_no_sales_period", "Produits equivalents":"supplier_equivalent_products", "Gemini propose les rapprochements. Seules les lignes confirmees servent aux commandes.":"supplier_equivalent_help", "Analyser les catalogues":"supplier_analyze_catalogs", "A verifier":"supplier_to_review", "Routes actives":"supplier_active_routes", "Securite":"supplier_security_label", "Validation manuelle":"supplier_manual_validation", "Votre produit":"supplier_your_product", "Offre candidate":"supplier_candidate_offer", "Confiance":"supplier_confidence", "Lancez une analyse pour rechercher les produits equivalents.":"supplier_run_analysis", "À régler":"game_to_settle", "Batman Coins engagés":"game_coins_staked", "Équipe, compétition, phase...":"game_search_placeholder",
    "Annuler":"btn_cancel", "Enregistrer":"btn_save", "Mise minimum":"game_min_stake", "Mise maximum":"game_max_stake", "Personnaliser le produit":"supplier_customize_product", "Lien de l'image affichée":"supplier_image_link", "Vide = image reçue du fournisseur.":"supplier_image_inherit", "Description reçue du fournisseur":"supplier_received_description", "Aucune description fournisseur.":"supplier_no_description", "Laissez l'anglais vide pour utiliser la description fournisseur.":"supplier_english_hint", "Traduire automatiquement":"supplier_auto_translate", "Enregistrer la personnalisation":"supplier_save_customization", "Prix minimum ($)":"dynamic_min_price", "Prix maximum ($)":"dynamic_max_price", "Objectif ventes/jour":"dynamic_target", "Plafond 24 h (%)":"dynamic_daily_cap", "Plafond 7 jours (%)":"dynamic_weekly_cap", "Confiance minimum (%)":"dynamic_min_confidence", "Arrondir vers un prix psychologique proche":"dynamic_psychological", "Le prix restera entre les limites et une commande créée conservera toujours son montant.":"dynamic_bounds_hint", "Type de livraison":"product_delivery_type", "Stock automatique":"product_auto_stock", "Fournisseur API (géré automatiquement)":"product_supplier_auto", "Compte Binance Pay (optionnel)":"product_binance_optional", "Description Principale (Anglais)":"description_en", "Description Française":"description_fr", "Description Arabe":"description_ar", "Description Chinoise":"description_zh", "Description Vietnamienne":"description_vi", "Description Russe":"description_ru", "Message d'activation (Anglais)":"activation_en", "Message d'activation (Français)":"activation_fr", "Message d'activation (Arabe)":"activation_ar", "Message d'activation (Chinois)":"activation_zh", "Message d'activation (Vietnamien)":"activation_vi", "Message d'activation (Russe)":"activation_ru", "Message de confirmation (Anglais)":"confirmation_en", "Message de confirmation (Français)":"confirmation_fr", "Message de confirmation (Arabe)":"confirmation_ar", "Message de confirmation (Chinois)":"confirmation_zh", "Message de confirmation (Vietnamien)":"confirmation_vi", "Message de confirmation (Russe)":"confirmation_ru", "✨ Traduire":"translate_short", "✨ Traduire Message":"translate_message", "Image URL (Optionnel)":"image_url_optional", "$ Prix fixe du produit":"promo_fixed_product", "Définissez des prix unitaires différents selon la quantité commandée. Le prix de base est utilisé si aucun palier ne correspond.":"tiers_help", "Ajouter un palier":"tiers_add", "Détail Commande":"order_detail", "Aucun article.":"common_no_item", "Modifier le Produit":"product_edit_title", "Prix USD ($)":"lbl_price", "Garantie (jours)":"product_warranty_days", "Prix actuel":"dynamic_current_price", "Prix recommandé":"dynamic_recommended_price", "Calculez une recommandation pour afficher les facteurs de décision.":"dynamic_recommend_hint", "Simuler 30 jours":"dynamic_simulate", "Vous êtes sur le point de retirer des fonds du solde virtuel du bot.":"finance_withdraw_intro", "Solde actuel : $0.00":"finance_current_balance", "Confirmer le retrait":"finance_confirm_withdraw", "Ajuster le solde virtuel":"finance_adjust_balance", "Ajouter un compte Binance":"binance_add_modal", "API Key (Optionnel, pour vérification automatique)":"binance_api_optional", "Définir comme compte par défaut":"binance_default", "Achats du client":"customer_purchases", "Le secret actuel cessera de fonctionner.":"reseller_secret_revoked",
    "Configuration":"game_configuration", "Publier un match":"game_modal_publish", "Équipe qualifiée":"game_qualified", "Résultat après 90 minutes":"game_result_90", "Fermer avant le début":"game_close_before", "1 heure":"game_hour", "Batman Coins brûlés (%)":"game_burned", "Publier maintenant":"game_publish_now", "Sinon le match restera en brouillon.":"game_draft_hint", "Publier sur le bot":"game_publish_bot", "Nom":"lbl_name", "Emoji":"common_emoji", "Émoji":"common_emoji", "Emoji classique":"classic_emoji", "Custom Emoji ID (optionnel)":"custom_emoji_optional", "ID emoji personnalisé Telegram":"custom_emoji_telegram", "Anglais (défaut)":"language_english_default", "Français":"language_french", "Arabe":"language_arabic", "Chinois":"language_chinese", "Vietnamien":"language_vietnamese", "Russe":"language_russian", "Dynamic Price":"product_dynamic", "Désactivé":"inactive", "Mode":"dynamic_mode", "Automatique après délai":"dynamic_auto_delay", "Suggestion uniquement":"dynamic_suggestion_only", "Sensibilité":"dynamic_sensitivity", "Prudente":"dynamic_cautious", "Normale":"dynamic_normal", "Agressive":"dynamic_aggressive", "Variation max (%)":"dynamic_max_variation", "Délai (heures)":"dynamic_cooldown", "Compte Binance Pay":"product_binance_account", "(optionnel)":"common_optional", "(Optionnel)":"common_optional", "Optionnel...":"common_optional_placeholder", "Optionnel. Utilisez {product} et {order_id}":"message_optional_placeholder", "(Optionnel, pour vérification automatique)":"binance_api_optional_suffix", "-- Par défaut --":"common_default", "Diffuser une alerte de restock (Telegram)":"stock_restock_alert", "% Pourcentage":"promo_percent", "$ Montant de reduction":"promo_discount_amount", "Max / util.":"promo_max_user", "Max Articles / Cmd":"promo_max_order", "Produits spécifiques":"promo_specific_products", "Optionnel pour les reductions classiques.":"promo_optional_classic", "Tarifs par palier":"tiers_title", "Articles livrés":"order_delivered_items", "Articles livrés —":"order_delivered_items_count", "Articles disponibles":"stock_available_items", "Articles disponibles —":"stock_available_items_count", "Fermer":"close", "Calculer maintenant":"dynamic_calculate", "Appliquer la suggestion":"dynamic_apply", "Les commandes existantes ne changent jamais de montant.":"dynamic_existing_orders", "Dernières décisions":"dynamic_latest", "Aucun historique.":"common_no_history", "Retirer des fonds":"finance_withdraw_title", "Solde actuel :":"finance_current_balance_label", "Montant à retirer ($)":"finance_withdraw_amount", "Tout retirer":"finance_withdraw_all", "Ajoutez ou retirez manuellement un montant (utilisez un nombre négatif pour retirer).":"finance_adjust_help", "Montant ($)":"common_amount_usd", "Montant":"th_amount", "Statut":"th_status", "Label (Nom affiché)":"binance_label", "API Secret (Optionnel)":"binance_api_secret_optional", "Dépenses":"common_spent", "Inscription":"common_registration", "Commande":"common_order", "Qté":"common_quantity", "Payment":"common_payment", "Evenements signes et relances automatiquement.":"reseller_webhook_help", "Exporter les Transactions":"export_transactions", "Format d'export":"export_format", "Date de début":"export_start_date", "Date de fin":"export_end_date", "Exporter":"export_button"
}));
Object.assign(LANG.fr, {
    trend_stable:"Stable vs hier", trend_new:"Nouveau vs hier", trend_percent:"{percent}% vs hier",
    perf_healthy:"Fluide", perf_healthy_desc:"La capacité actuelle suffit pour le trafic observé.", perf_workers_desc:"Les demandes attendent un worker libre. Augmentez progressivement le nombre de workers.", perf_single_user:"Utilisateur actif", perf_single_user_desc:"Un utilisateur envoie des actions plus vite que sa file ordonnée ne peut les traiter. Les autres workers restent disponibles.", perf_database_desc:"Turso limite le débit. Ajouter des workers augmenterait la contention.", perf_external:"API externe", perf_external_handler_desc:"Un handler ou une API externe ralentit le traitement. Ajouter des workers ne corrigerait pas la cause.", perf_external_desc:"Une dépendance externe ralentit le traitement. La croissance des workers est bloquée.", perf_event_loop:"Boucle chargée", perf_event_loop_desc:"La boucle principale répond en retard. L'autoscaling est bloqué.", perf_memory:"Mémoire", perf_memory_desc:"La mémoire approche la limite de sécurité. L'autoscaling est bloqué.", perf_insufficient:"Collecte", perf_insufficient_desc:"Au moins 20 actions sont nécessaires pour une recommandation fiable.",
    perf_recommended:"Recommandé : {count}", perf_queue_detail:"File p95 : {queue} ms · utilisateur : {user} ms", perf_throughput:"{count} actions/min", perf_database_detail:"{errors} erreur(s) connexion · écriture p95 {write} ms · {timeouts} timeout(s)", perf_slowest:"Action la plus lente : {action} · p95 {latency} ms ({count} appel(s))", perf_slowest_collecting:"Action la plus lente : collecte en cours", perf_history:"24 h : {action} · moyenne {latency} ms ({count} appel(s))", perf_history_collecting:"24 h : collecte en cours", perf_autoscale_state:"{state} · {count} worker(s)", perf_next_analysis:"Prochaine analyse : {seconds}s · proposition {count}"
});
Object.assign(LANG.en, {
    trend_stable:"Stable vs yesterday", trend_new:"New vs yesterday", trend_percent:"{percent}% vs yesterday",
    perf_healthy:"Smooth", perf_healthy_desc:"Current capacity is sufficient for observed traffic.", perf_workers_desc:"Requests are waiting for a free worker. Increase workers gradually.", perf_single_user:"Active user", perf_single_user_desc:"One user is sending actions faster than their ordered queue can process them. Other workers remain available.", perf_database_desc:"Turso is limiting throughput. Adding workers would increase contention.", perf_external:"External API", perf_external_handler_desc:"A handler or external API is slowing processing. More workers would not fix the cause.", perf_external_desc:"An external dependency is slowing processing. Worker growth is blocked.", perf_event_loop:"Busy event loop", perf_event_loop_desc:"The main loop is responding late. Autoscaling is blocked.", perf_memory:"Memory", perf_memory_desc:"Memory is approaching the safety limit. Autoscaling is blocked.", perf_insufficient:"Collecting", perf_insufficient_desc:"At least 20 actions are required for a reliable recommendation.",
    perf_recommended:"Recommended: {count}", perf_queue_detail:"Queue p95: {queue} ms · user: {user} ms", perf_throughput:"{count} actions/min", perf_database_detail:"{errors} connection error(s) · write p95 {write} ms · {timeouts} timeout(s)", perf_slowest:"Slowest action: {action} · p95 {latency} ms ({count} call(s))", perf_slowest_collecting:"Slowest action: collecting", perf_history:"24 h: {action} · average {latency} ms ({count} call(s))", perf_history_collecting:"24 h: collecting", perf_autoscale_state:"{state} · {count} worker(s)", perf_next_analysis:"Next analysis: {seconds}s · proposed {count}"
});
Object.assign(LANG.ar, {
    trend_stable:"مستقر مقارنة بالأمس", trend_new:"جديد مقارنة بالأمس", trend_percent:"{percent}% مقارنة بالأمس", perf_healthy:"سلس", perf_healthy_desc:"السعة الحالية كافية لحركة المرور المرصودة.", perf_workers_desc:"الطلبات تنتظر عاملاً متاحًا. زد عدد العمال تدريجيًا.", perf_single_user:"مستخدم نشط", perf_single_user_desc:"يرسل مستخدم واحد إجراءات أسرع من قدرة قائمته المرتبة على المعالجة، بينما يبقى العمال الآخرون متاحين.", perf_database_desc:"يحد Turso من معدل المعالجة، وإضافة عمال ستزيد التنافس.", perf_external:"API خارجي", perf_external_handler_desc:"تؤدي وحدة معالجة أو API خارجي إلى إبطاء التنفيذ، ولن تحل زيادة العمال السبب.", perf_external_desc:"تؤدي خدمة خارجية إلى إبطاء التنفيذ، وتم إيقاف زيادة العمال.", perf_event_loop:"حلقة أحداث مشغولة", perf_event_loop_desc:"تستجيب الحلقة الرئيسية بتأخير، وتم إيقاف التوسع التلقائي.", perf_memory:"الذاكرة", perf_memory_desc:"تقترب الذاكرة من حد الأمان، وتم إيقاف التوسع التلقائي.", perf_insufficient:"جمع البيانات", perf_insufficient_desc:"يلزم 20 إجراءً على الأقل للحصول على توصية موثوقة.", perf_recommended:"الموصى به: {count}", perf_queue_detail:"انتظار p95: {queue} مللي ثانية · المستخدم: {user} مللي ثانية", perf_throughput:"{count} إجراء/دقيقة", perf_database_detail:"أخطاء الاتصال: {errors} · كتابة p95: {write} مللي ثانية · انتهاء المهلة: {timeouts}", perf_slowest:"أبطأ إجراء: {action} · p95 {latency} مللي ثانية ({count} استدعاء)", perf_slowest_collecting:"أبطأ إجراء: جارٍ جمع البيانات", perf_history:"24 ساعة: {action} · المتوسط {latency} مللي ثانية ({count} استدعاء)", perf_history_collecting:"24 ساعة: جارٍ جمع البيانات", perf_autoscale_state:"{state} · {count} عامل", perf_next_analysis:"التحليل التالي: {seconds} ث · المقترح {count}"
});
Object.assign(LANG.zh, {
    trend_stable:"较昨天持平", trend_new:"较昨天新增", trend_percent:"较昨天 {percent}%", perf_healthy:"流畅", perf_healthy_desc:"当前容量足以应对观察到的流量。", perf_workers_desc:"请求正在等待空闲工作线程，请逐步增加线程数。", perf_single_user:"活跃用户", perf_single_user_desc:"单个用户发送操作的速度超过其顺序队列的处理速度，其他工作线程仍可用。", perf_database_desc:"Turso 限制了吞吐量，增加工作线程会加剧竞争。", perf_external:"外部 API", perf_external_handler_desc:"处理程序或外部 API 正在拖慢处理，增加工作线程无法解决根因。", perf_external_desc:"外部依赖正在拖慢处理，已停止增加工作线程。", perf_event_loop:"事件循环繁忙", perf_event_loop_desc:"主循环响应延迟，自动扩缩已暂停。", perf_memory:"内存", perf_memory_desc:"内存接近安全上限，自动扩缩已暂停。", perf_insufficient:"采集中", perf_insufficient_desc:"至少需要 20 次操作才能给出可靠建议。", perf_recommended:"建议：{count}", perf_queue_detail:"队列 p95：{queue} 毫秒 · 用户：{user} 毫秒", perf_throughput:"{count} 次操作/分钟", perf_database_detail:"{errors} 个连接错误 · 写入 p95 {write} 毫秒 · {timeouts} 次超时", perf_slowest:"最慢操作：{action} · p95 {latency} 毫秒（{count} 次）", perf_slowest_collecting:"最慢操作：采集中", perf_history:"24 小时：{action} · 平均 {latency} 毫秒（{count} 次）", perf_history_collecting:"24 小时：采集中", perf_autoscale_state:"{state} · {count} 个工作线程", perf_next_analysis:"下次分析：{seconds} 秒 · 建议 {count}"
});
Object.assign(LANG.vi, {
    trend_stable:"Ổn định so với hôm qua", trend_new:"Mới so với hôm qua", trend_percent:"{percent}% so với hôm qua", perf_healthy:"Ổn định", perf_healthy_desc:"Công suất hiện tại đủ cho lưu lượng quan sát được.", perf_workers_desc:"Yêu cầu đang chờ worker rảnh. Hãy tăng worker dần dần.", perf_single_user:"Người dùng đang hoạt động", perf_single_user_desc:"Một người dùng gửi thao tác nhanh hơn hàng đợi tuần tự có thể xử lý; các worker khác vẫn sẵn sàng.", perf_database_desc:"Turso đang giới hạn thông lượng. Thêm worker sẽ tăng tranh chấp.", perf_external:"API bên ngoài", perf_external_handler_desc:"Một handler hoặc API bên ngoài làm chậm xử lý; thêm worker không giải quyết được nguyên nhân.", perf_external_desc:"Một phụ thuộc bên ngoài đang làm chậm xử lý; việc tăng worker bị chặn.", perf_event_loop:"Vòng lặp bận", perf_event_loop_desc:"Vòng lặp chính phản hồi chậm; tự động điều chỉnh bị chặn.", perf_memory:"Bộ nhớ", perf_memory_desc:"Bộ nhớ sắp đạt giới hạn an toàn; tự động điều chỉnh bị chặn.", perf_insufficient:"Đang thu thập", perf_insufficient_desc:"Cần ít nhất 20 thao tác để có đề xuất đáng tin cậy.", perf_recommended:"Đề xuất: {count}", perf_queue_detail:"Hàng đợi p95: {queue} ms · người dùng: {user} ms", perf_throughput:"{count} thao tác/phút", perf_database_detail:"{errors} lỗi kết nối · ghi p95 {write} ms · {timeouts} lần timeout", perf_slowest:"Thao tác chậm nhất: {action} · p95 {latency} ms ({count} lần gọi)", perf_slowest_collecting:"Thao tác chậm nhất: đang thu thập", perf_history:"24 giờ: {action} · trung bình {latency} ms ({count} lần gọi)", perf_history_collecting:"24 giờ: đang thu thập", perf_autoscale_state:"{state} · {count} worker", perf_next_analysis:"Phân tích tiếp theo: {seconds}s · đề xuất {count}"
});
Object.assign(LANG.ru, {
    trend_stable:"Без изменений ко вчера", trend_new:"Новое ко вчера", trend_percent:"{percent}% ко вчера", perf_healthy:"Стабильно", perf_healthy_desc:"Текущей мощности достаточно для наблюдаемого трафика.", perf_workers_desc:"Запросы ждут свободного воркера. Увеличивайте число воркеров постепенно.", perf_single_user:"Активный пользователь", perf_single_user_desc:"Один пользователь отправляет действия быстрее, чем их обрабатывает его последовательная очередь. Остальные воркеры доступны.", perf_database_desc:"Turso ограничивает пропускную способность. Дополнительные воркеры усилят конкуренцию.", perf_external:"Внешний API", perf_external_handler_desc:"Обработчик или внешний API замедляет работу. Дополнительные воркеры не устранят причину.", perf_external_desc:"Внешняя зависимость замедляет работу. Увеличение воркеров заблокировано.", perf_event_loop:"Цикл событий занят", perf_event_loop_desc:"Главный цикл отвечает с задержкой. Автомасштабирование заблокировано.", perf_memory:"Память", perf_memory_desc:"Память приближается к безопасному пределу. Автомасштабирование заблокировано.", perf_insufficient:"Сбор данных", perf_insufficient_desc:"Для надёжной рекомендации требуется не менее 20 действий.", perf_recommended:"Рекомендуется: {count}", perf_queue_detail:"Очередь p95: {queue} мс · пользователь: {user} мс", perf_throughput:"{count} действий/мин", perf_database_detail:"Ошибок соединения: {errors} · запись p95 {write} мс · тайм-аутов: {timeouts}", perf_slowest:"Самое медленное действие: {action} · p95 {latency} мс ({count} выз.)", perf_slowest_collecting:"Самое медленное действие: сбор данных", perf_history:"24 ч: {action} · среднее {latency} мс ({count} выз.)", perf_history_collecting:"24 ч: сбор данных", perf_autoscale_state:"{state} · воркеров: {count}", perf_next_analysis:"Следующий анализ: {seconds} с · предложено {count}"
});

const ACTION_FEEDBACK_TRANSLATIONS = {
fr: {
    settings_crypto_addresses:"Adresses crypto de réception", settings_crypto_help:"Configurez vos adresses de réception USDT. Laissez un champ vide pour désactiver le mode de paiement correspondant dans le bot Telegram.", common_optional_placeholder:"Optionnel...", message_optional_placeholder:"Optionnel. Utilisez {product} et {order_id}",
    supplier_margin_value:"Marge {value}%", supplier_average_order_value:"Panier moyen ${value}", supplier_quality_title:"Qualité des données historiques", supplier_quality_estimated:"{count} ancienne(s) commande(s) utilisent le dernier coût fournisseur connu.", supplier_quality_missing:"{count} commande(s) n'ont pas de coût récupérable; leur bénéfice est potentiellement surestimé.", supplier_cost_incomplete:"Coût historique incomplet", supplier_cost_estimated:"Coût historique estimé", supplier_stats_load_failed:"Impossible de charger les statistiques.",
    game_stake_invalid:"La mise maximum doit être supérieure à la mise minimum.", game_config_saved:"Configuration du match enregistrée.", game_published_success:"Match publié sur le bot.", game_draft_saved:"Match enregistré en brouillon.", game_save_failed:"Impossible d'enregistrer le match : {message}", game_result_refreshed:"Résultat actualisé depuis l'API sportive.", game_cancel_confirm:"Annuler {match} et rembourser toutes les mises ?", game_cancelled:"Match annulé et mises remboursées.", game_choose_result:"Choisissez le résultat à appliquer.", game_settle_confirm:"Distribuer les gains avec le résultat « {result} » ? Cette opération est définitive.", game_settled:"Résultat confirmé et gains distribués.", game_action_failed:"Action impossible : {message}",
    supplier_product_updated:"Produit fournisseur mis à jour.", supplier_product_missing:"Produit fournisseur introuvable.", supplier_customize_title:"Personnaliser - {product}", supplier_nothing_translate:"Aucune description à traduire.", supplier_translating:"Traduction en cours", supplier_translation_done:"Descriptions traduites. Vérifiez-les puis enregistrez.", supplier_translation_failed:"Traduction impossible : {message}", supplier_customization_saved:"Personnalisation du produit enregistrée.", supplier_settings_saved:"Configuration fournisseur enregistrée.", supplier_sync_done:"{count} produit(s) synchronisé(s).", supplier_load_failed:"Impossible de charger le fournisseur.", supplier_routes_load_failed:"Impossible de charger les routes.", supplier_no_routes:"Aucune équivalence proposée.", supplier_route_active:"Active", supplier_route_rejected:"Refusée", supplier_route_review:"À vérifier", supplier_route_confirm:"Confirmer", supplier_route_reject:"Refuser", supplier_route_disable:"Désactiver"
},
en: {
    settings_crypto_addresses:"Crypto receiving addresses", settings_crypto_help:"Configure your USDT receiving addresses. Leave a field blank to disable the corresponding payment method in the Telegram bot.", common_optional_placeholder:"Optional...", message_optional_placeholder:"Optional. Use {product} and {order_id}",
    supplier_margin_value:"Margin {value}%", supplier_average_order_value:"Average order ${value}", supplier_quality_title:"Historical data quality", supplier_quality_estimated:"{count} older order(s) use the latest known supplier cost.", supplier_quality_missing:"{count} order(s) have no recoverable cost; their profit may be overstated.", supplier_cost_incomplete:"Incomplete historical cost", supplier_cost_estimated:"Estimated historical cost", supplier_stats_load_failed:"Unable to load statistics.",
    game_stake_invalid:"The maximum stake must be greater than the minimum stake.", game_config_saved:"Match settings saved.", game_published_success:"Match published to the bot.", game_draft_saved:"Match saved as a draft.", game_save_failed:"Unable to save the match: {message}", game_result_refreshed:"Result refreshed from the sports API.", game_cancel_confirm:"Cancel {match} and refund every stake?", game_cancelled:"Match cancelled and stakes refunded.", game_choose_result:"Choose the result to apply.", game_settle_confirm:"Distribute rewards using “{result}”? This action is final.", game_settled:"Result confirmed and rewards distributed.", game_action_failed:"Action failed: {message}",
    supplier_product_updated:"Supplier product updated.", supplier_product_missing:"Supplier product not found.", supplier_customize_title:"Customize - {product}", supplier_nothing_translate:"There is no description to translate.", supplier_translating:"Translating", supplier_translation_done:"Descriptions translated. Review and save them.", supplier_translation_failed:"Translation failed: {message}", supplier_customization_saved:"Product customization saved.", supplier_settings_saved:"Supplier settings saved.", supplier_sync_done:"{count} product(s) synchronized.", supplier_load_failed:"Unable to load the supplier.", supplier_routes_load_failed:"Unable to load routes.", supplier_no_routes:"No matching products proposed.", supplier_route_active:"Active", supplier_route_rejected:"Rejected", supplier_route_review:"Review", supplier_route_confirm:"Confirm", supplier_route_reject:"Reject", supplier_route_disable:"Disable"
},
ar: {
    settings_crypto_addresses:"عناوين استقبال العملات الرقمية", settings_crypto_help:"قم بإعداد عناوين استلام USDT. اترك الحقل فارغًا لتعطيل طريقة الدفع المقابلة في بوت Telegram.", common_optional_placeholder:"اختياري...", message_optional_placeholder:"اختياري. استخدم {product} و {order_id}",
    supplier_margin_value:"الهامش {value}%", supplier_average_order_value:"متوسط الطلب ${value}", supplier_quality_title:"جودة البيانات التاريخية", supplier_quality_estimated:"تستخدم {count} طلبات قديمة أحدث تكلفة معروفة للمورد.", supplier_quality_missing:"لا تتوفر تكلفة قابلة للاسترجاع لـ {count} طلبات؛ وقد يكون الربح مبالغًا فيه.", supplier_cost_incomplete:"التكلفة التاريخية غير مكتملة", supplier_cost_estimated:"التكلفة التاريخية تقديرية", supplier_stats_load_failed:"تعذر تحميل الإحصاءات.",
    game_stake_invalid:"يجب أن يكون الحد الأقصى للرهان أكبر من الحد الأدنى.", game_config_saved:"تم حفظ إعدادات المباراة.", game_published_success:"تم نشر المباراة في البوت.", game_draft_saved:"تم حفظ المباراة كمسودة.", game_save_failed:"تعذر حفظ المباراة: {message}", game_result_refreshed:"تم تحديث النتيجة من API الرياضي.", game_cancel_confirm:"هل تريد إلغاء {match} وإعادة جميع الرهانات؟", game_cancelled:"أُلغيت المباراة وأُعيدت الرهانات.", game_choose_result:"اختر النتيجة التي تريد تطبيقها.", game_settle_confirm:"هل تريد توزيع الجوائز حسب النتيجة «{result}»؟ هذا الإجراء نهائي.", game_settled:"تم تأكيد النتيجة وتوزيع الجوائز.", game_action_failed:"تعذر تنفيذ الإجراء: {message}",
    supplier_product_updated:"تم تحديث منتج المورد.", supplier_product_missing:"تعذر العثور على منتج المورد.", supplier_customize_title:"تخصيص - {product}", supplier_nothing_translate:"لا يوجد وصف لترجمته.", supplier_translating:"جارٍ الترجمة", supplier_translation_done:"تمت ترجمة الأوصاف. راجعها ثم احفظها.", supplier_translation_failed:"تعذرت الترجمة: {message}", supplier_customization_saved:"تم حفظ تخصيص المنتج.", supplier_settings_saved:"تم حفظ إعدادات المورد.", supplier_sync_done:"تمت مزامنة {count} منتج.", supplier_load_failed:"تعذر تحميل المورد.", supplier_routes_load_failed:"تعذر تحميل المسارات.", supplier_no_routes:"لا توجد منتجات متطابقة مقترحة.", supplier_route_active:"نشط", supplier_route_rejected:"مرفوض", supplier_route_review:"للمراجعة", supplier_route_confirm:"تأكيد", supplier_route_reject:"رفض", supplier_route_disable:"تعطيل"
},
zh: {
    settings_crypto_addresses:"加密货币收款地址", settings_crypto_help:"配置您的 USDT 收款地址。留空某个字段即可在 Telegram 机器人中禁用对应的支付方式。", common_optional_placeholder:"可选...", message_optional_placeholder:"可选。使用 {product} 和 {order_id}",
    supplier_margin_value:"利润率 {value}%", supplier_average_order_value:"平均订单 ${value}", supplier_quality_title:"历史数据质量", supplier_quality_estimated:"{count} 个旧订单使用了最新已知供应商成本。", supplier_quality_missing:"{count} 个订单没有可恢复的成本，其利润可能被高估。", supplier_cost_incomplete:"历史成本不完整", supplier_cost_estimated:"历史成本为估算值", supplier_stats_load_failed:"无法加载统计数据。",
    game_stake_invalid:"最大投注必须大于最小投注。", game_config_saved:"比赛设置已保存。", game_published_success:"比赛已发布到机器人。", game_draft_saved:"比赛已保存为草稿。", game_save_failed:"无法保存比赛：{message}", game_result_refreshed:"已从体育 API 更新结果。", game_cancel_confirm:"取消 {match} 并退还所有投注？", game_cancelled:"比赛已取消，投注已退还。", game_choose_result:"请选择要应用的结果。", game_settle_confirm:"按“{result}”分配奖励？此操作不可撤销。", game_settled:"结果已确认，奖励已分配。", game_action_failed:"操作失败：{message}",
    supplier_product_updated:"供应商产品已更新。", supplier_product_missing:"未找到供应商产品。", supplier_customize_title:"自定义 - {product}", supplier_nothing_translate:"没有可翻译的描述。", supplier_translating:"正在翻译", supplier_translation_done:"描述已翻译，请检查后保存。", supplier_translation_failed:"翻译失败：{message}", supplier_customization_saved:"产品自定义已保存。", supplier_settings_saved:"供应商设置已保存。", supplier_sync_done:"已同步 {count} 个产品。", supplier_load_failed:"无法加载供应商。", supplier_routes_load_failed:"无法加载路由。", supplier_no_routes:"没有建议的匹配产品。", supplier_route_active:"启用", supplier_route_rejected:"已拒绝", supplier_route_review:"待审核", supplier_route_confirm:"确认", supplier_route_reject:"拒绝", supplier_route_disable:"禁用"
},
vi: {
    settings_crypto_addresses:"Địa chỉ nhận tiền mã hóa", settings_crypto_help:"Cấu hình địa chỉ nhận USDT. Để trống một trường để tắt phương thức thanh toán tương ứng trong bot Telegram.", common_optional_placeholder:"Không bắt buộc...", message_optional_placeholder:"Không bắt buộc. Dùng {product} và {order_id}",
    supplier_margin_value:"Biên lợi nhuận {value}%", supplier_average_order_value:"Đơn hàng trung bình ${value}", supplier_quality_title:"Chất lượng dữ liệu lịch sử", supplier_quality_estimated:"{count} đơn hàng cũ dùng chi phí nhà cung cấp gần nhất.", supplier_quality_missing:"{count} đơn hàng không có chi phí có thể khôi phục; lợi nhuận có thể bị tính cao.", supplier_cost_incomplete:"Chi phí lịch sử chưa đầy đủ", supplier_cost_estimated:"Chi phí lịch sử ước tính", supplier_stats_load_failed:"Không thể tải thống kê.",
    game_stake_invalid:"Mức cược tối đa phải lớn hơn mức cược tối thiểu.", game_config_saved:"Đã lưu cài đặt trận đấu.", game_published_success:"Đã đăng trận đấu lên bot.", game_draft_saved:"Đã lưu trận đấu dưới dạng bản nháp.", game_save_failed:"Không thể lưu trận đấu: {message}", game_result_refreshed:"Đã cập nhật kết quả từ API thể thao.", game_cancel_confirm:"Hủy {match} và hoàn lại mọi mức cược?", game_cancelled:"Đã hủy trận đấu và hoàn lại tiền cược.", game_choose_result:"Chọn kết quả cần áp dụng.", game_settle_confirm:"Phân phối phần thưởng theo kết quả “{result}”? Thao tác này là cuối cùng.", game_settled:"Đã xác nhận kết quả và phân phối phần thưởng.", game_action_failed:"Không thể thực hiện thao tác: {message}",
    supplier_product_updated:"Đã cập nhật sản phẩm nhà cung cấp.", supplier_product_missing:"Không tìm thấy sản phẩm nhà cung cấp.", supplier_customize_title:"Tùy chỉnh - {product}", supplier_nothing_translate:"Không có mô tả để dịch.", supplier_translating:"Đang dịch", supplier_translation_done:"Đã dịch mô tả. Hãy kiểm tra rồi lưu.", supplier_translation_failed:"Không thể dịch: {message}", supplier_customization_saved:"Đã lưu tùy chỉnh sản phẩm.", supplier_settings_saved:"Đã lưu cài đặt nhà cung cấp.", supplier_sync_done:"Đã đồng bộ {count} sản phẩm.", supplier_load_failed:"Không thể tải nhà cung cấp.", supplier_routes_load_failed:"Không thể tải tuyến.", supplier_no_routes:"Không có sản phẩm tương ứng được đề xuất.", supplier_route_active:"Đang hoạt động", supplier_route_rejected:"Đã từ chối", supplier_route_review:"Cần xem xét", supplier_route_confirm:"Xác nhận", supplier_route_reject:"Từ chối", supplier_route_disable:"Tắt"
},
ru: {
    settings_crypto_addresses:"Адреса для приёма криптовалюты", settings_crypto_help:"Настройте адреса получения USDT. Оставьте поле пустым, чтобы отключить соответствующий способ оплаты в Telegram-боте.", common_optional_placeholder:"Необязательно...", message_optional_placeholder:"Необязательно. Используйте {product} и {order_id}",
    supplier_margin_value:"Маржа {value}%", supplier_average_order_value:"Средний заказ ${value}", supplier_quality_title:"Качество исторических данных", supplier_quality_estimated:"{count} старых заказов используют последнюю известную стоимость поставщика.", supplier_quality_missing:"Для {count} заказов невозможно восстановить стоимость; прибыль может быть завышена.", supplier_cost_incomplete:"Неполная историческая стоимость", supplier_cost_estimated:"Оценочная историческая стоимость", supplier_stats_load_failed:"Не удалось загрузить статистику.",
    game_stake_invalid:"Максимальная ставка должна быть больше минимальной.", game_config_saved:"Настройки матча сохранены.", game_published_success:"Матч опубликован в боте.", game_draft_saved:"Матч сохранён как черновик.", game_save_failed:"Не удалось сохранить матч: {message}", game_result_refreshed:"Результат обновлён через спортивный API.", game_cancel_confirm:"Отменить {match} и вернуть все ставки?", game_cancelled:"Матч отменён, ставки возвращены.", game_choose_result:"Выберите результат для применения.", game_settle_confirm:"Распределить награды по результату «{result}»? Это действие необратимо.", game_settled:"Результат подтверждён, награды распределены.", game_action_failed:"Не удалось выполнить действие: {message}",
    supplier_product_updated:"Товар поставщика обновлён.", supplier_product_missing:"Товар поставщика не найден.", supplier_customize_title:"Настроить - {product}", supplier_nothing_translate:"Нет описания для перевода.", supplier_translating:"Перевод", supplier_translation_done:"Описания переведены. Проверьте и сохраните их.", supplier_translation_failed:"Ошибка перевода: {message}", supplier_customization_saved:"Настройки товара сохранены.", supplier_settings_saved:"Настройки поставщика сохранены.", supplier_sync_done:"Синхронизировано товаров: {count}.", supplier_load_failed:"Не удалось загрузить поставщика.", supplier_routes_load_failed:"Не удалось загрузить маршруты.", supplier_no_routes:"Подходящие товары не предложены.", supplier_route_active:"Активен", supplier_route_rejected:"Отклонён", supplier_route_review:"На проверке", supplier_route_confirm:"Подтвердить", supplier_route_reject:"Отклонить", supplier_route_disable:"Отключить"
}
};
Object.entries(ACTION_FEEDBACK_TRANSLATIONS).forEach(([language, strings]) => Object.assign(LANG[language], strings));

const state = {
    botUrl:'', apiKey:'', currentLang:'fr', currentTab:'dashboard-tab',
    categories:[], products:[], orders:[], activations:[], resellers:[], users:[], promos:[], tickets:[], walletHistory:[], binanceAccounts:[],
    orderFilter:'all', orderPage:0, orderTotal:0,
    whFilter:'all', whPage:0, whTotal:0,
    usersPage:0, usersPerPage:20, usersSearch:'', usersTotal:0, usersSort:'joined', usersOrder:'desc',
    userPurchasesTelegramId:null, userPurchasesPage:0, userPurchasesPerPage:10,
    currentStockProductId:null, autoRefresh:false, autoRefreshTimer:null,
    chartDays:30, refreshing:false, lastRefreshAt:null, pendingRefresh:null, tabLoadedAt:{}, tabScrollPositions:{},
    revenueChart:null, ordersChart:null, productSalesChart:null, productMomentumChart:null,
    paymentReviewCategory:'all', paymentReviewIncludeResolved:false, paymentReviewItems:[],
    dynamicPriceChart:null, dynamicSimulationChart:null,
    productStats:[], productMomentum:null, productMomentumSelected:[], deadProductAlerts:[], supplierBot:null, supplierBots:[], activeSupplierCode:'canboso', supplierView:'catalog', supplierStats:null, supplierStatsDays:30, supplierStatsChart:null, supplierRoutes:[],
    aiSupplierStatus:null, aiSupplierResults:[], aiSupplierGroups:[], aiSupplierResultData:null, aiSupplierGroupData:null, aiSupplierJobId:null, aiSupplierSyncTimer:null,
    gameProvider:null, gameCatalog:[], gameMatches:[], gameCompetitions:[], gameView:'catalog', currentGameMatch:null,
    autoscaleChart:null, autoscaleStatus:null,
    resellerSpecialPrices:[], resellerSpecialPriceUserId:null,
    orderDetailItems:[], orderDetailTimeline:[], orderDetailId:null
};

function $(id) { return document.getElementById(id); }
function $$(sel) { return document.querySelectorAll(sel); }

const DOM = {
    loginScreen:$('login-screen'), loginForm:$('login-form'), botUrlInput:$('bot-url'), apiKeyInput:$('api-key'), loginError:$('login-error'),
    appContainer:$('app-container'), mainContent:$('dashboard-workspace'), currentTabTitle:$('current-tab-title'),
    btnRefresh:$('btn-refresh'), btnLogout:$('btn-logout'), btnTheme:$('btn-theme'), btnAutoRefresh:$('btn-auto-refresh'), btnInstallApp:$('btn-install-app'),
    loadingOverlay:$('loading-overlay'), pageStatusRegion:$('page-status-region'), sidebar:$('dashboard-sidebar'),
    statRevenue:$('stat-revenue'), statOrders:$('stat-orders'), statUsers:$('stat-users'), statPending:$('stat-pending'),
    statNewUsers:$('stat-new-users'), statReturningUsers:$('stat-returning-users'),
    stockSummaryList:$('stock-summary-list'),
    todayRevenue:$('today-revenue'), todayOrders:$('today-orders'),
    todayRevenueDelta:$('today-revenue-delta'), todayOrdersDelta:$('today-orders-delta'),
    actionCenterList:$('action-center-list'), recentOrdersList:$('recent-orders-list'),
    perfStatus:$('perf-status'), perfWorkers:$('perf-workers'), perfWorkersRec:$('perf-workers-rec'), perfSlowestAction:$('perf-slowest-action'),
    perfQueue:$('perf-queue'), perfQueueWait:$('perf-queue-wait'), perfProcessing:$('perf-processing'),
    perfThroughput:$('perf-throughput'), perfDatabase:$('perf-database'), perfDbErrors:$('perf-db-errors'),
    perfDiagnosis:$('perf-diagnosis'), btnExportPerformance:$('btn-export-performance'),
    autoscaleState:$('autoscale-state'), autoscaleMode:$('autoscale-mode'), autoscaleObserve:$('autoscale-observe'),
    autoscaleMin:$('autoscale-min'), autoscaleMax:$('autoscale-max'), autoscaleSave:$('autoscale-save'),
    autoscaleStop:$('autoscale-stop'), autoscaleNext:$('autoscale-next'), autoscaleChart:$('autoscale-chart'),
    autoscaleHistory:$('autoscale-history'),
    dashboardRange:$('dashboard-range'), pageContext:$('page-context'), toastRegion:$('toast-region'),
    badgeOrders:$('badge-orders'), badgePaymentReview:$('badge-payment-review'), badgeActivations:$('badge-activations'), badgeTickets:$('badge-tickets'), apiStatusBadge:$('api-status-badge'),
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
    conversionFunnelStages:$('conversion-funnel-stages'), conversionProductsBody:$('conversion-products-body'),
    conversionTrackingNote:$('conversion-tracking-note'), conversionOverallRate:$('conversion-overall-rate'),
    paymentReviewTableBody:$('payment-review-table-body'), paymentReviewIncludeResolved:$('payment-review-include-resolved'),
    btnPaymentReviewRefresh:$('btn-payment-review-refresh'), paymentReviewTotal:$('payment-review-total'),
    paymentReviewUnderpaid:$('payment-review-underpaid'), paymentReviewConfirming:$('payment-review-confirming'),
    paymentReviewLate:$('payment-review-late'), paymentReviewExpired:$('payment-review-expired'),
    promosTableBody:$('promos-table-body'),
    ordersTableBody:$('orders-table-body'), activationsTableBody:$('activations-table-body'), ordersPagination:$('orders-pagination'),
    ordersPrev:$('orders-prev'), ordersNext:$('orders-next'), ordersPageInfo:$('orders-page-info'),
    usersTableBody:$('users-table-body'), usersSearch:$('users-search'), usersLimitSelector:$('users-limit-selector'),
    usersPagination:$('users-pagination'), usersPrev:$('users-prev'), usersNext:$('users-next'), usersPageInfo:$('users-page-info'),
    userPurchasesModal:$('user-purchases-modal'), userPurchasesIdentity:$('user-purchases-identity'),
    userPurchasesSummary:$('user-purchases-summary'), userPurchasesTotal:$('user-purchases-total'),
    userPurchasesSpent:$('user-purchases-spent'), userPurchasesWallet:$('user-purchases-wallet'),
    userPurchasesJoined:$('user-purchases-joined'), userPurchasesBody:$('user-purchases-body'),
    userPurchasesPagination:$('user-purchases-pagination'), userPurchasesPrev:$('user-purchases-prev'),
    userPurchasesNext:$('user-purchases-next'), userPurchasesPageInfo:$('user-purchases-page-info'),
    openTicketsContainer:$('open-tickets-container'),
    resellersTableBody:$('resellers-table-body'), resellerUserId:$('reseller-user-id'), resellerKeyName:$('reseller-key-name'),
    btnCreateResellerKey:$('btn-create-reseller-key'), resellerKeyOutput:$('reseller-key-output'), resellerNewKey:$('reseller-new-key'),
    resellerSecurityModal:$('reseller-security-modal'), resellerSecurityForm:$('reseller-security-form'), resellerSecurityKeyId:$('reseller-security-key-id'),
    resellerIpAllowlist:$('reseller-ip-allowlist'), resellerWebhookUrl:$('reseller-webhook-url'), resellerWebhookEnabled:$('reseller-webhook-enabled'),
    resellerWebhookRotate:$('reseller-webhook-rotate'), resellerWebhookSecretOutput:$('reseller-webhook-secret-output'), resellerWebhookSecret:$('reseller-webhook-secret'),
    resellerSpecialPricesModal:$('reseller-special-prices-modal'), resellerSpecialPricesForm:$('reseller-special-prices-form'), resellerSpecialPricesIdentity:$('reseller-special-prices-identity'),
    resellerSpecialProduct:$('reseller-special-product'), resellerSpecialPrice:$('reseller-special-price'), resellerSpecialActive:$('reseller-special-active'), resellerSpecialTelegram:$('reseller-special-telegram'),
    resellerSpecialCostProtection:$('reseller-special-cost-protection'), resellerSpecialExpiry:$('reseller-special-expiry'), resellerSpecialStandardHint:$('reseller-special-standard-hint'), resellerSpecialPricesList:$('reseller-special-prices-list'),
    supplierSettingsForm:$('supplier-settings-form'), supplierEnabled:$('supplier-enabled'), supplierDisplayName:$('supplier-display-name'), supplierMarginType:$('supplier-margin-type'), supplierMarginValue:$('supplier-margin-value'),
    supplierProviderSwitcher:$('supplier-provider-switcher'), supplierProviderName:$('supplier-provider-name'), supplierRateGroup:$('supplier-rate-group'), supplierRateLabel:$('supplier-rate-label'), supplierUnitsPerUsd:$('supplier-units-per-usd'), supplierCredentialEnv:$('supplier-credential-env'),
    btnSupplierSync:$('btn-supplier-sync'), supplierConnection:$('supplier-connection'), supplierWalletBalance:$('supplier-wallet-balance'), supplierLastSync:$('supplier-last-sync'), supplierSelectedCount:$('supplier-selected-count'), supplierReviewCount:$('supplier-review-count'),
    supplierProductSearch:$('supplier-product-search'), supplierProductsTableBody:$('supplier-products-table-body'),
    supplierCatalogView:$('supplier-catalog-view'), supplierStatsView:$('supplier-stats-view'), supplierRouterView:$('supplier-router-view'), supplierRouterBody:$('supplier-router-body'), supplierRouterProposed:$('supplier-router-proposed'), supplierRouterConfirmed:$('supplier-router-confirmed'), btnSupplierRouterScan:$('btn-supplier-router-scan'), supplierStatsRevenue:$('supplier-stats-revenue'), supplierStatsCost:$('supplier-stats-cost'), supplierStatsProfit:$('supplier-stats-profit'), supplierStatsMargin:$('supplier-stats-margin'),
    supplierStatsItems:$('supplier-stats-items'), supplierStatsOrders:$('supplier-stats-orders'), supplierStatsOrdersSub:$('supplier-stats-orders-sub'), supplierStatsSuccess:$('supplier-stats-success'), supplierStatsQuality:$('supplier-stats-quality'), supplierStatsChart:$('supplier-stats-chart'), supplierStatsProductsBody:$('supplier-stats-products-body'),
    btnAiSupplierSync:$('btn-ai-supplier-sync'), btnAiSupplierAnalyze:$('btn-ai-supplier-analyze'), btnAiGroupsRefresh:$('btn-ai-groups-refresh'), aiSupplierCount:$('ai-supplier-count'), aiProductCount:$('ai-product-count'), aiLastAnalysis:$('ai-last-analysis'), aiSyncState:$('ai-sync-state'),
    aiSyncProgressPanel:$('ai-sync-progress-panel'), aiSyncProgressLabel:$('ai-sync-progress-label'), aiSyncProgressValue:$('ai-sync-progress-value'), aiSyncProgressBar:$('ai-sync-progress-bar'),
    aiGroupsSummary:$('ai-groups-summary'), aiGroupsBody:$('ai-groups-body'),
    aiSupplierSearchForm:$('ai-supplier-search-form'), aiSupplierQuery:$('ai-supplier-query'), aiDurationValue:$('ai-duration-value'), aiDurationUnit:$('ai-duration-unit'), aiWarrantyFilter:$('ai-warranty-filter'),
    aiDeliveryFilter:$('ai-delivery-filter'), aiAccessFilter:$('ai-access-filter'), aiMaxPrice:$('ai-max-price'), aiIncludeUnfunded:$('ai-include-unfunded'), aiResultsSummary:$('ai-results-summary'), aiResultsBody:$('ai-results-body'),
    supplierDescriptionModal:$('supplier-description-modal'), supplierDescriptionForm:$('supplier-description-form'), supplierDescriptionProductId:$('supplier-description-product-id'),
    supplierDescriptionTitle:$('supplier-description-title'), supplierDescriptionSource:$('supplier-description-source'),
    supplierCustomName:$('supplier-custom-name'), supplierCustomEmoji:$('supplier-custom-emoji'), supplierCustomEmojiId:$('supplier-custom-emoji-id'), supplierCustomImageUrl:$('supplier-custom-image-url'), supplierAutoTranslate:$('supplier-auto-translate'),
    supplierDescriptionEn:$('supplier-description-en'), supplierDescriptionFr:$('supplier-description-fr'), supplierDescriptionAr:$('supplier-description-ar'),
    supplierDescriptionZh:$('supplier-description-zh'), supplierDescriptionVi:$('supplier-description-vi'), supplierDescriptionRu:$('supplier-description-ru'),
    btnGameRefresh:$('btn-game-refresh'), gameProviderStatus:$('game-provider-status'), gameProviderWarning:$('game-provider-warning'),
    gameOpenCount:$('game-open-count'), gameSettleCount:$('game-settle-count'), gameBetCount:$('game-bet-count'), gameCoinsStaked:$('game-coins-staked'),
    gameCatalogFilters:$('game-catalog-filters'), gameDateFrom:$('game-date-from'), gameDateTo:$('game-date-to'),
    gameCompetitionFilter:$('game-competition-filter'), gameStatusFilter:$('game-status-filter'), gameSearch:$('game-search'),
    gameCatalogBody:$('game-catalog-body'), gameCatalogMeta:$('game-catalog-meta'), gamePublishedBody:$('game-published-body'),
    gameSettlementBody:$('game-settlement-body'), gameHistoryBody:$('game-history-body'), badgeGameResults:$('badge-game-results'),
    gameMatchModal:$('game-match-modal'), gameMatchForm:$('game-match-form'), gameExternalMatchId:$('game-external-match-id'),
    gameLocalMatchId:$('game-local-match-id'), gameModalTitle:$('game-modal-title'), gameModalPreview:$('game-modal-preview'),
    gameMarketType:$('game-market-type'), gameLockMinutes:$('game-lock-minutes'), gameMinStake:$('game-min-stake'),
    gameMaxStake:$('game-max-stake'), gameFeePercent:$('game-fee-percent'), gamePublishNow:$('game-publish-now'),
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
    financeReconcileStatus:$('finance-reconcile-status'), financeReconcileSummary:$('finance-reconcile-summary'), financeReconcileUpdated:$('finance-reconcile-updated'), financeReconcileChecks:$('finance-reconcile-checks'), financeReconcileRun:$('btn-finance-reconcile'), financeReconcileRunLabel:$('finance-reconcile-run-label'),
    orderTimelineList:$('order-timeline-list'),
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  i18n HELPERS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function t(key) { return LANG[state.currentLang]?.[key] || LANG.fr[key] || key; }

function tf(key, values={}) {
    return Object.entries(values).reduce(
        (message, [name, value]) => message.replaceAll(`{${name}}`, String(value)),
        t(key),
    );
}

const legacyTextBindings = new WeakMap();
const legacyAttributeBindings = new WeakMap();

function applyLegacyStaticTranslations(root=document) {
    const elements = [];
    if (root instanceof Element) elements.push(root);
    if (root?.querySelectorAll) elements.push(...root.querySelectorAll('*'));
    elements.forEach(element => {
        if (element.closest('[data-i18n]')) return;
        Array.from(element.childNodes).forEach(node => {
            if (node.nodeType !== 3) return;
            const sourceText = node.nodeValue.trim();
            const key = legacyTextBindings.get(node) || LEGACY_STATIC_SOURCE_KEYS.get(sourceText);
            if (!key) return;
            legacyTextBindings.set(node, key);
            node.nodeValue = node.nodeValue.replace(sourceText, t(key));
        });
        const bindings = legacyAttributeBindings.get(element) || {};
        ['placeholder', 'title', 'aria-label'].forEach(attribute => {
            if (element.hasAttribute(`data-i18n-${attribute}`)) return;
            const current = element.getAttribute(attribute);
            const key = bindings[attribute] || LEGACY_STATIC_SOURCE_KEYS.get(String(current || '').trim());
            if (!key) return;
            bindings[attribute] = key;
            element.setAttribute(attribute, t(key));
        });
        if (Object.keys(bindings).length) legacyAttributeBindings.set(element, bindings);
    });
}

function currentLocale() {
    return {fr:'fr-FR', en:'en-GB', ar:'ar', zh:'zh-CN', vi:'vi-VN', ru:'ru-RU'}[state.currentLang] || 'fr-FR';
}

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
    $$('[data-i18n-title]').forEach(el => { const k = el.getAttribute('data-i18n-title'); const v = t(k); if (v) el.title = v; });
    $$('[data-i18n-aria-label]').forEach(el => { const k = el.getAttribute('data-i18n-aria-label'); const v = t(k); if (v) el.setAttribute('aria-label', v); });
    applyLegacyStaticTranslations();
    document.documentElement.dir = state.currentLang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = state.currentLang;
    $$('.lang-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-lang') === state.currentLang));
    const mobileLanguageSelect = $('mobile-language-select');
    if (mobileLanguageSelect) mobileLanguageSelect.value = state.currentLang;
    updatePwaInstallButton();
    enhanceResponsiveTables();
}

function setLang(lang) {
    state.currentLang = lang;
    localStorage.setItem('vb_lang', lang);
    applyTranslations();
    document.querySelector('.menu-item.active[data-tab]')?.setAttribute('aria-current', 'page');
    updateCurrentTabLabels();
    rerenderAiSupplierContent();
    if (!DOM.appContainer.classList.contains('hidden')) refreshData();
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  THEME
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// PWA installation stays separate from dashboard data. The service worker only
// controls static files below /dashboard and never handles API mutations.
let deferredPwaInstallPrompt = null;
let dashboardServiceWorkerRegistration = null;
let pwaUpdateAnnounced = false;
let pwaInstalledInSession = false;
let pwaLastUpdateCheck = 0;

function isStandalonePwa() {
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

function isIosDevice() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent)
        || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

function updatePwaInstallButton() {
    const button = DOM.btnInstallApp || $('btn-install-app');
    if (!button) return;
    const installed = isStandalonePwa() || pwaInstalledInSession;
    const translationKey = installed ? 'app_installed' : 'install_app';
    button.disabled = installed;
    button.classList.toggle('pwa-installed', installed);
    button.setAttribute('data-i18n-title', translationKey);
    button.setAttribute('data-i18n-aria-label', translationKey);
    button.title = t(translationKey);
    button.setAttribute('aria-label', t(translationKey));
    button.innerHTML = installed
        ? '<i class="fa-solid fa-circle-check"></i>'
        : '<i class="fa-solid fa-mobile-screen-button"></i>';
}

async function handlePwaInstall() {
    if (isStandalonePwa() || pwaInstalledInSession) {
        showToast(t('app_installed'), 'success');
        return;
    }
    if (deferredPwaInstallPrompt) {
        const prompt = deferredPwaInstallPrompt;
        deferredPwaInstallPrompt = null;
        await prompt.prompt();
        const choice = await prompt.userChoice;
        if (choice?.outcome === 'accepted') {
            pwaInstalledInSession = true;
            updatePwaInstallButton();
        }
        return;
    }
    showToast(t(isIosDevice() ? 'pwa_ios_instructions' : 'pwa_install_unavailable'), 'info');
}

function announcePwaUpdate() {
    if (pwaUpdateAnnounced) return;
    pwaUpdateAnnounced = true;
    showToast(t('pwa_update_ready'), 'info');
}

function watchServiceWorkerUpdate(registration) {
    if (registration.waiting && navigator.serviceWorker.controller) announcePwaUpdate();
    registration.addEventListener('updatefound', () => {
        const worker = registration.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
            if (worker.state === 'installed' && navigator.serviceWorker.controller) announcePwaUpdate();
        });
    });
}

async function registerDashboardServiceWorker() {
    const secureContext = window.isSecureContext
        || window.location.hostname === 'localhost'
        || window.location.hostname === '127.0.0.1';
    if (!secureContext || !('serviceWorker' in navigator)) return;
    try {
        dashboardServiceWorkerRegistration = await navigator.serviceWorker.register(
            './service-worker.js',
            {scope:'./', updateViaCache:'none'}
        );
        pwaLastUpdateCheck = Date.now();
        watchServiceWorkerUpdate(dashboardServiceWorkerRegistration);
    } catch (error) {
        console.warn('Dashboard service worker registration failed.', error);
    }
}

function setupPwa() {
    updatePwaInstallButton();
    DOM.btnInstallApp?.addEventListener('click', handlePwaInstall);
    registerDashboardServiceWorker();
    document.addEventListener('visibilitychange', () => {
        if (document.hidden || !dashboardServiceWorkerRegistration) return;
        if (Date.now() - pwaLastUpdateCheck < 60 * 60 * 1000) return;
        pwaLastUpdateCheck = Date.now();
        dashboardServiceWorkerRegistration.update().catch(error => {
            console.warn('Dashboard service worker update check failed.', error);
        });
    });
}

window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredPwaInstallPrompt = event;
    updatePwaInstallButton();
});

window.addEventListener('appinstalled', () => {
    deferredPwaInstallPrompt = null;
    pwaInstalledInSession = true;
    updatePwaInstallButton();
    showToast(t('pwa_install_success'), 'success');
});

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
    setupPwa();

    localStorage.removeItem('vb_turbo');
    document.body.classList.remove('turbo-mode');

    const savedUrl = localStorage.getItem('ventebot_url') || '';
    const legacyKey = localStorage.getItem('ventebot_key') || '';
    if (legacyKey) {
        sessionStorage.setItem('ventebot_key', legacyKey);
        localStorage.removeItem('ventebot_key');
    }
    const savedKey = sessionStorage.getItem('ventebot_key') || '';
    state.botUrl = resolveBotUrl(savedUrl);
    state.apiKey = savedKey;
    DOM.settingsBotUrl.value = state.botUrl || '';
    if (DOM.botUrlInput) DOM.botUrlInput.value = state.botUrl || '';
    DOM.settingsApiKey.value = savedKey;
    if (savedKey || isSameOriginApi(state.botUrl)) {
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
function dashboardActionId(element, key='id') {
    const value = Number(element.dataset[key]);
    return Number.isSafeInteger(value) && value > 0 ? value : null;
}

function handleDelegatedDashboardClick(event) {
    const element = event.target.closest('[data-action]');
    if (!element) return;
    const action = element.dataset.action;
    const id = dashboardActionId(element);
    if (element.dataset.stopPropagation === 'true') event.stopPropagation();
    if (element.tagName === 'A' || element.tagName === 'BUTTON') event.preventDefault();

    switch (action) {
        case 'retry-tab': return void refreshData({force:true});
        case 'show-revenue-details': return showRevenueDetails();
        case 'sort-users': return sortUsers(element.dataset.field || 'joined');
        case 'close-binance': return closeBinanceModal();
        case 'save-binance': return void saveBinanceAccount();
        case 'close-ban': return closeBanModal();
        case 'confirm-ban': return void confirmBanUser();
        case 'edit-binance': if (id) return editBinanceAccount(id); break;
        case 'delete-binance': if (id) return void deleteBinanceAccount(id); break;
        case 'toggle-momentum': if (id) return toggleMomentumProduct(id); break;
        case 'switch-tab': return switchTab(element.dataset.tabTarget || 'dashboard-tab');
        case 'view-product-stock': if (id) return void viewProductStock(id); break;
        case 'open-stock': if (id) return void openStockModal(id); break;
        case 'toggle-product': if (id) return void toggleProductVisibility(id); break;
        case 'edit-product': if (id) return void openEditProduct(id); break;
        case 'open-tiers': if (id) return void openTiersModal(id); break;
        case 'delete-product': if (id) return void deleteProduct(id); break;
        case 'confirm-order': if (id) return void confirmOrderPayment(id); break;
        case 'cancel-order': if (id) return void cancelOrder(id); break;
        case 'complete-activation': if (id) return void completeActivation(id); break;
        case 'order-detail': if (id) return void openOrderDetail(id); break;
        case 'reseller-security': if (id) return void openResellerSecurity(id); break;
        case 'reseller-special': if (id) return void openResellerSpecialPrices(id); break;
        case 'reseller-revoke': if (id) return void revokeResellerKey(id); break;
        case 'reseller-special-edit': if (id) return void editResellerSpecialPrice(id); break;
        case 'reseller-special-delete': if (id) return void deleteResellerSpecialPrice(id); break;
        case 'supplier-select': return void selectSupplierBot(element.dataset.code || '');
        case 'supplier-description': if (id) return void openSupplierDescriptionEditor(id); break;
        case 'supplier-save': if (id) return void saveSupplierProduct(id); break;
        case 'supplier-route': if (id) return void reviewSupplierRoute(id, element.dataset.status || ''); break;
        case 'ai-open-supplier': return openAiSupplier(element.dataset.code || '');
        case 'ai-toggle-group': {
            const index = Number(element.dataset.index);
            if (Number.isSafeInteger(index) && index >= 0) return toggleAiSupplierGroup(index);
            break;
        }
        case 'user-referrals': if (id) return void viewUserReferrals(id); break;
        case 'user-purchases': if (id) return void openUserPurchases(id); break;
        case 'user-credit': if (id) return void creditWallet(id); break;
        case 'user-debit': if (id) return void debitWallet(id); break;
        case 'user-unban': if (id) return void unbanUser(id); break;
        case 'user-ban': if (id) return void banUser(id); break;
        case 'user-purchase-order': if (id) return void openUserPurchaseOrderDetail(id); break;
        case 'delete-promo': if (id) return void deletePromo(id); break;
        case 'download-order-txt': return downloadCurrentOrderTxt();
        case 'run-financial-reconciliation': return void runFinancialReconciliation();
        case 'delete-tier': return element.closest('.tier-row')?.remove();
        case 'expand-stock': return element.closest('.stock-item-row')?.querySelector('.stock-item-data')?.classList.toggle('expanded');
        case 'delete-stock': if (id) return void deleteStockItem(id); break;
        case 'load-more-stock': {
            const productId = dashboardActionId(element, 'productId');
            const target = element.dataset.target === 'manage' ? 'manage' : 'view';
            if (productId) return void loadMoreProductStock(productId, target);
            break;
        }
        default: return;
    }
}

function handleDelegatedDashboardChange(event) {
    const element = event.target.closest('[data-change-action]');
    if (!element) return;
    if (element.dataset.changeAction === 'supplier-margin') {
        const id = dashboardActionId(element);
        if (id) toggleSupplierMarginInput(id);
    }
}

function handleDelegatedDashboardSubmit(event) {
    const form = event.target.closest('form[data-submit-action]');
    if (!form) return;
    if (form.dataset.submitAction === 'ticket-reply') {
        const id = dashboardActionId(form);
        if (id) void submitTicketReply(event, id);
    }
}

function setupMobileSidebar() {
    const menuBtn = $('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const backdrop = $('sidebar-backdrop');
    if (!menuBtn || !sidebar || !backdrop) return;
    const close = (restoreFocus=false) => {
        sidebar.classList.remove('open');
        backdrop.classList.remove('active');
        backdrop.setAttribute('aria-hidden', 'true');
        menuBtn.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('sidebar-open');
        const icon = menuBtn.querySelector('i');
        if (icon) icon.className = 'fa-solid fa-bars';
        if (restoreFocus) menuBtn.focus();
    };
    menuBtn.addEventListener('click', () => {
        const opening = !sidebar.classList.contains('open');
        sidebar.classList.toggle('open', opening);
        backdrop.classList.toggle('active', opening);
        backdrop.setAttribute('aria-hidden', opening ? 'false' : 'true');
        menuBtn.setAttribute('aria-expanded', String(opening));
        document.body.classList.toggle('sidebar-open', opening);
        const icon = menuBtn.querySelector('i');
        if (icon) icon.className = opening ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
        if (opening) requestAnimationFrame(() => sidebar.querySelector('.menu-item.active, .menu-item')?.focus());
    });
    backdrop.addEventListener('click', () => close(true));
    sidebar.querySelectorAll('.menu-item').forEach(item => item.addEventListener('click', () => {
        if (window.innerWidth <= 768) close();
    }));
    window.addEventListener('resize', () => { if (window.innerWidth > 768) close(); });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && sidebar.classList.contains('open')) close(true);
    });
}

let responsiveTableObserver = null;
const pendingResponsiveTables = new Set();
let responsiveTableFrame = null;

function enhanceResponsiveTable(table) {
    if (!(table instanceof HTMLTableElement) || !table.classList.contains('data-table')) return;
    if (table.matches('.ai-results-table, .ai-groups-table, [data-responsive="scroll"]')) return;
    const headerRow = table.tHead?.rows?.[table.tHead.rows.length - 1];
    if (!headerRow) return;
    const labels = Array.from(headerRow.cells, cell => cell.textContent.trim());
    table.classList.add('responsive-table-cards');
    const shell = table.parentElement;
    if (shell) shell.classList.add('has-responsive-table');
    Array.from(table.tBodies).forEach(body => Array.from(body.rows).forEach(row => {
        Array.from(row.cells).forEach((cell, index) => {
            if (cell.colSpan > 1) return;
            cell.dataset.label = labels[index] || '';
        });
    }));
}

function flushResponsiveTables() {
    responsiveTableFrame = null;
    pendingResponsiveTables.forEach(enhanceResponsiveTable);
    pendingResponsiveTables.clear();
}

function queueResponsiveTable(table) {
    if (!(table instanceof HTMLTableElement)) return;
    pendingResponsiveTables.add(table);
    if (!responsiveTableFrame) responsiveTableFrame = requestAnimationFrame(flushResponsiveTables);
}

function enhanceResponsiveTables(root=document) {
    if (root instanceof HTMLTableElement) queueResponsiveTable(root);
    if (root?.querySelectorAll) root.querySelectorAll('table.data-table').forEach(queueResponsiveTable);
}

function setupResponsiveTables() {
    enhanceResponsiveTables();
    if (responsiveTableObserver) return;
    responsiveTableObserver = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            const table = mutation.target instanceof Element ? mutation.target.closest('table.data-table') : null;
            if (table) queueResponsiveTable(table);
            mutation.addedNodes.forEach(node => {
                if (!(node instanceof Element)) return;
                if (node.matches('table.data-table')) queueResponsiveTable(node);
                node.querySelectorAll?.('table.data-table').forEach(queueResponsiveTable);
            });
        });
    });
    responsiveTableObserver.observe(document.body, {childList:true, subtree:true});
}

function setupEvents() {
    document.addEventListener('click', handleDelegatedDashboardClick);
    document.addEventListener('change', handleDelegatedDashboardChange);
    document.addEventListener('submit', handleDelegatedDashboardSubmit);
    setupMobileSidebar();
    setupResponsiveTables();
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
    DOM.btnRefresh.addEventListener('click', () => refreshData({force:true}));
    DOM.btnTheme.addEventListener('click', toggleTheme);
    DOM.btnAutoRefresh.addEventListener('click', toggleAutoRefresh);
    $('btn-export').addEventListener('click', () => showModal($('exportModal')));
    if (DOM.btnExportPerformance) DOM.btnExportPerformance.addEventListener('click', exportPerformanceDiagnostic);
    if (DOM.autoscaleSave) DOM.autoscaleSave.addEventListener('click', saveAutoscaleConfiguration);
    if (DOM.autoscaleStop) DOM.autoscaleStop.addEventListener('click', stopAutoscaling);
    $$('[data-autoscale-mode]').forEach(button => button.addEventListener('click', () => selectAutoscaleMode(button.dataset.autoscaleMode)));
    $$('[data-worker-adjust]').forEach(button => button.addEventListener('click', () => adjustWebhookWorkers(Number(button.dataset.workerAdjust || 0))));
    $$('[data-worker-reset]').forEach(button => button.addEventListener('click', () => setManualWebhookWorkers(Number(button.dataset.workerReset || 8))));
    if (DOM.btnCreateResellerKey) DOM.btnCreateResellerKey.addEventListener('click', createResellerKey);
    if (DOM.resellerSecurityForm) DOM.resellerSecurityForm.addEventListener('submit', saveResellerSecurity);
    if (DOM.resellerSpecialPricesForm) DOM.resellerSpecialPricesForm.addEventListener('submit', saveResellerSpecialPrice);
    if (DOM.resellerSpecialProduct) DOM.resellerSpecialProduct.addEventListener('change', updateResellerSpecialStandardHint);
    if (DOM.btnSupplierSync) DOM.btnSupplierSync.addEventListener('click', syncSupplierBot);
    if (DOM.btnAiSupplierSync) DOM.btnAiSupplierSync.addEventListener('click', syncAllAiSuppliers);
    if (DOM.btnAiSupplierAnalyze) DOM.btnAiSupplierAnalyze.addEventListener('click', analyzeAllAiSuppliers);
    if (DOM.btnAiGroupsRefresh) DOM.btnAiGroupsRefresh.addEventListener('click', loadAiSupplierGroups);
    if (DOM.aiSupplierSearchForm) DOM.aiSupplierSearchForm.addEventListener('submit', searchAiSuppliers);
    if (DOM.btnSupplierRouterScan) DOM.btnSupplierRouterScan.addEventListener('click', scanSupplierRoutes);
    if (DOM.supplierSettingsForm) DOM.supplierSettingsForm.addEventListener('submit', saveSupplierSettings);
    if (DOM.supplierProductSearch) DOM.supplierProductSearch.addEventListener('input', renderSupplierProducts);
    $$('[data-supplier-view]').forEach(button => button.addEventListener('click', () => setSupplierView(button.dataset.supplierView)));
    $$('[data-supplier-days]').forEach(button => button.addEventListener('click', () => setSupplierStatsDays(button.dataset.supplierDays)));
    if (DOM.supplierDescriptionForm) DOM.supplierDescriptionForm.addEventListener('submit', saveSupplierDescriptions);
    if (DOM.supplierAutoTranslate) DOM.supplierAutoTranslate.addEventListener('click', autoTranslateSupplierDescription);
    if (DOM.btnGameRefresh) DOM.btnGameRefresh.addEventListener('click', () => loadGameManagement({forceCatalog:true}));
    if (DOM.gameCatalogFilters) DOM.gameCatalogFilters.addEventListener('submit', event => {
        event.preventDefault();
        loadGameCatalog({force:false});
    });
    if (DOM.gameMatchForm) DOM.gameMatchForm.addEventListener('submit', saveGameMatch);
    $$('.game-view-tab').forEach(button => button.addEventListener('click', () => setGameView(button.dataset.gameView)));
    [DOM.gameCatalogBody, DOM.gamePublishedBody, DOM.gameSettlementBody].filter(Boolean).forEach(container => {
        container.addEventListener('click', handleGameTableAction);
    });
    
    if (DOM.statsProductSearch) {
        DOM.statsProductSearch.addEventListener('input', () => {
            renderStatsTable();
        });
    }
    $$('.payment-review-filter').forEach(button => button.addEventListener('click', () => {
        $$('.payment-review-filter').forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        state.paymentReviewCategory = button.dataset.category || 'all';
        loadPaymentReview();
    }));
    if (DOM.paymentReviewIncludeResolved) DOM.paymentReviewIncludeResolved.addEventListener('change', () => {
        state.paymentReviewIncludeResolved = DOM.paymentReviewIncludeResolved.checked;
        loadPaymentReview();
    });
    if (DOM.btnPaymentReviewRefresh) DOM.btnPaymentReviewRefresh.addEventListener('click', loadPaymentReview);
    if (DOM.paymentReviewTableBody) DOM.paymentReviewTableBody.addEventListener('click', event => {
        const button = event.target.closest('[data-payment-review-action]');
        if (button) handlePaymentReviewAction(button);
    });

    $$('.sub-tab[data-sub]').forEach(tabButton => tabButton.addEventListener('click', () => {
        const actionBar = tabButton.closest('.action-bar');
        const section = tabButton.closest('section');
        const targetId = tabButton.getAttribute('data-sub')?.replace(/^#/, '');
        const targetContent = targetId ? document.getElementById(targetId) : null;
        if (!actionBar || !section || !targetContent) return;

        actionBar.querySelectorAll('.sub-tab[data-sub]').forEach(button => button.classList.remove('active'));
        section.querySelectorAll('.sub-tab-content').forEach(content => content.classList.remove('active'));
        tabButton.classList.add('active');
        targetContent.classList.add('active');
        if (targetId === 'promos-sub') void loadPromos();
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
    const btnMassTranslateCancel = $('btn-mass-translate-cancel');
    if (btnMassTranslateCancel) btnMassTranslateCancel.addEventListener('click', () => {
        massTranslateCancel = true;
        btnMassTranslateCancel.textContent = 'Annulation en cours...';
        btnMassTranslateCancel.disabled = true;
    });
    const promoType = $('promo-type');
    if (promoType) promoType.addEventListener('change', syncPromoTypeUI);
    $('btn-open-promo-modal').addEventListener('click', async () => {
        DOM.addPromoForm.reset();
        syncPromoTypeUI();
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
            cb.addEventListener('change', () => enforceSinglePromoProduct(cb));
            lbl.appendChild(cb);
            lbl.appendChild(document.createTextNode(' ' + p.name));
            sel.appendChild(lbl);
        });
        showModal(DOM.promoModal);
    });
    $('btn-open-binance-modal').addEventListener('click', openBinanceModal);
    $$('.btn-close-modal').forEach(b => b.addEventListener('click', () => { [DOM.prodModal,DOM.stockModal,DOM.promoModal,DOM.tiersModal,DOM.orderDetailModal,DOM.viewStockModal,DOM.editProdModal,DOM.revenueModal,DOM.binanceModal,DOM.gameMatchModal,DOM.supplierDescriptionModal,DOM.userPurchasesModal,DOM.resellerSecurityModal,DOM.resellerSpecialPricesModal,$('banModal'),$('finance-withdraw-modal'),$('finance-adjust-modal'), $('exportModal')].forEach(m => { if (m) hideModal(m); }); }));

    
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
    if (DOM.userPurchasesPrev) DOM.userPurchasesPrev.addEventListener('click', () => {
        if (state.userPurchasesPage > 0) {
            state.userPurchasesPage--;
            loadUserPurchases();
        }
    });
    if (DOM.userPurchasesNext) DOM.userPurchasesNext.addEventListener('click', () => {
        state.userPurchasesPage++;
        loadUserPurchases();
    });
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
    status.textContent = enabled ? t('active') : t('inactive');
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

function isSameOriginApi(baseUrl=state.botUrl) {
    try {
        return window.location.protocol !== 'file:'
            && new URL(resolveBotUrl(baseUrl)).origin === window.location.origin;
    } catch(e) {
        return false;
    }
}

const inFlightApiRequests = new Map();

function actionControlForRequest(method) {
    if (method === 'GET' || method === 'HEAD') return null;
    const active = document.activeElement;
    if (active instanceof HTMLButtonElement || active instanceof HTMLInputElement && ['submit', 'button'].includes(active.type)) return active;
    return null;
}

function setActionControlBusy(control, busy) {
    if (!control) return;
    if (busy) {
        control.dataset.wasDisabled = control.disabled ? 'true' : 'false';
        control.dataset.originalAriaLabel = control.getAttribute('aria-label') || '';
        control.disabled = true;
        control.setAttribute('aria-busy', 'true');
        control.setAttribute('aria-label', control.getAttribute('aria-label') || t('action_in_progress'));
    } else {
        control.disabled = control.dataset.wasDisabled === 'true';
        if (control.dataset.originalAriaLabel) control.setAttribute('aria-label', control.dataset.originalAriaLabel);
        else control.removeAttribute('aria-label');
        delete control.dataset.wasDisabled;
        delete control.dataset.originalAriaLabel;
        control.removeAttribute('aria-busy');
    }
}

async function apiCall(endpoint, method='GET', body=null) {
    if (method && typeof method === 'object') {
        const options = method;
        method = options.method || 'GET';
        body = options.body ?? null;
    }
    method = String(method || 'GET').toUpperCase();
    const base = resolveBotUrl(state.botUrl);
    const url = `${base}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    const serializedBody = body ? (typeof body === 'string' ? body : JSON.stringify(body)) : '';
    const requestKey = `${method}:${url}:${serializedBody}`;
    const existingRequest = inFlightApiRequests.get(requestKey);
    if (existingRequest) return existingRequest;

    const headers = {};
    if (state.apiKey) headers['X-API-Key'] = state.apiKey;
    if (body) headers['Content-Type'] = 'application/json';
    const ctrl = new AbortController(); const tid = setTimeout(() => ctrl.abort(), 60000);
    const cfg = {
        method,
        headers,
        mode:'cors',
        credentials:isSameOriginApi(base) ? 'same-origin' : 'omit',
        signal:ctrl.signal,
    };
    if (body) cfg.body = serializedBody;
    const actionControl = actionControlForRequest(method);
    setActionControlBusy(actionControl, true);
    const request = (async () => {
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
        } finally {
            inFlightApiRequests.delete(requestKey);
            setActionControlBusy(actionControl, false);
        }
    })();
    inFlightApiRequests.set(requestKey, request);
    return request;
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
        loadProducts(); // Refresh the product list
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
        const sameOrigin = isSameOriginApi(state.botUrl);
        if (state.apiKey && sameOrigin) {
            await apiCall('/api/admin/session', 'POST');
            state.apiKey = '';
            sessionStorage.removeItem('ventebot_key');
        } else if (!state.apiKey && sameOrigin) {
            await apiCall('/api/admin/session');
        } else if (!state.apiKey) {
            throw new Error('MISSING_KEY');
        }

        // /api/stats validates connectivity, database readiness and the admin key
        // in one request. A separate /health request made login less reliable.
        state.initialStats = await apiCall('/api/stats');

        localStorage.setItem('ventebot_url', state.botUrl);
        localStorage.removeItem('ventebot_key');
        if (state.apiKey) sessionStorage.setItem('ventebot_key', state.apiKey);
        else sessionStorage.removeItem('ventebot_key');
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
    'dashboard-tab': [loadDashboardOverview, loadPerformanceMetrics, loadStats, loadCharts, loadPaymentReview],
    'stats-tab': [loadStatsBundle],
    'inventory-tab': [loadProducts, loadBinanceAccounts],
    'orders-tab': [loadProducts, loadAllOrders],
    'payment-review-tab': [loadPaymentReview],
    'activations-tab': [loadProducts, loadActivations],
    'resellers-tab': [loadResellers],
    'supplier-bots-tab': [loadSupplierBot],
    'ai-bot-tab': [loadAiSupplierStatus, loadAiSupplierGroups],
    'game-tab': [loadGameManagement],
    'users-tab': [loadUsers],
    'tickets-tab': [loadTickets],
    'settings-tab': [loadProducts, loadPromos, loadPaymentSettings],
    'wallet-history-tab': [loadWalletHistory],
    'finance-tab': [loadFinance],
    'binance-tab': [loadBinanceAccounts],
};

const fullRefreshLoaders = [
    loadDashboardOverview, loadPerformanceMetrics, loadFinance, loadProducts, loadAllOrders, loadActivations, loadResellers, loadSupplierBot, loadAiSupplierStatus, loadAiSupplierGroups,
    loadTickets, loadUsers, loadPromos, loadWalletHistory, loadBinanceAccounts,
    loadPaymentSettings, loadStatsBundle, loadPaymentReview
];

const TAB_CACHE_TTLS = {
    'dashboard-tab':30000, 'orders-tab':30000, 'payment-review-tab':30000, 'activations-tab':30000,
    'inventory-tab':60000, 'users-tab':60000, 'tickets-tab':60000, 'wallet-history-tab':60000,
    'finance-tab':60000, 'resellers-tab':120000, 'game-tab':120000, 'binance-tab':120000,
    'supplier-bots-tab':180000, 'ai-bot-tab':180000, 'stats-tab':120000, 'settings-tab':300000,
};

function tabDataIsFresh(tabId) {
    const loadedAt = Number(state.tabLoadedAt[tabId] || 0);
    return loadedAt > 0 && Date.now() - loadedAt < Number(TAB_CACHE_TTLS[tabId] || 60000);
}

function uniqueLoaders(loaders) {
    return [...new Set(loaders.filter(Boolean))];
}

async function refreshData(options={}) {
    if (options instanceof Event) options = {};
    const targetTab = options.tabId || state.currentTab;
    if (options.useCache && !options.force && !options.full && tabDataIsFresh(targetTab)) return;
    if (state.refreshing) {
        state.pendingRefresh = {...options, tabId:targetTab};
        return;
    }
    state.refreshing = true;
    if (!options.silent) showLoading(true);
    DOM.apiStatusBadge.querySelector('.status-indicator').className = 'status-indicator';
    try {
        const loaders = options.full
            ? fullRefreshLoaders
            : uniqueLoaders(tabRefreshLoaders[targetTab] || tabRefreshLoaders['dashboard-tab']);
        const results = await Promise.allSettled(loaders.map(loader => loader()));
        const failures = results.filter(result => result.status === 'rejected');
        failures.forEach(result => console.error(result.reason));
        const status = DOM.apiStatusBadge.querySelector('.status-indicator');
        status.classList.add(failures.length === results.length ? 'offline' : 'online');
        if (!failures.length) {
            if (options.full) Object.keys(tabRefreshLoaders).forEach(tabId => { state.tabLoadedAt[tabId] = Date.now(); });
            else state.tabLoadedAt[targetTab] = Date.now();
            if (targetTab === state.currentTab) clearPageStatus();
        } else if (targetTab === state.currentTab) {
            const totalFailure = failures.length === results.length;
            renderPageStatus('error', t(totalFailure ? 'refresh_total_error' : 'refresh_partial_error'));
            if (!options.silent) showToast(t(totalFailure ? 'refresh_total_error' : 'refresh_partial_error'), 'error');
        }
        state.lastRefreshAt = new Date();
    } finally {
        state.refreshing = false;
        if (!options.silent) showLoading(false);
        const pending = state.pendingRefresh;
        state.pendingRefresh = null;
        if (pending) queueMicrotask(() => refreshData(pending));
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
                        <button class="btn-secondary btn-sm" data-action="edit-binance" data-id="${Number(a.id)}" title="Modifier"><i class="fa-solid fa-pen"></i></button>
                        <button class="btn-secondary btn-sm" data-action="delete-binance" data-id="${Number(a.id)}" title="Supprimer" style="color:#ef4444"><i class="fa-solid fa-trash"></i></button>
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
    if (before === 0) return now === 0 ? {text:t('trend_stable'), className:''} : {text:t('trend_new'), className:'positive'};
    const percent = Math.round(((now - before) / before) * 100);
    return {text:tf('trend_percent', {percent:`${percent >= 0 ? '+' : ''}${percent}`}), className:percent > 0 ? 'positive' : percent < 0 ? 'negative' : ''};
}

async function loadPerformanceMetrics() {
    if (!DOM.perfStatus) return;
    const data = await apiCall('/api/performance');
    const workers = data.workers || {};
    const queue = data.queue || {};
    const traffic = data.traffic || {};
    const latency = data.latency || {};
    const database = data.database || {};
    const databaseWrites = database.write_serialization || {};
    const diagnosis = data.diagnosis || {};
    const labels = {
        healthy:[t('perf_healthy'), t('perf_healthy_desc'), 'success'],
        workers:[t('workers'), t('perf_workers_desc'), 'warning'],
        single_user_backlog:[t('perf_single_user'), t('perf_single_user_desc'), 'warning'],
        database:['Turso', t('perf_database_desc'), 'danger'],
        external_api_or_handler:[t('perf_external'), t('perf_external_handler_desc'), 'warning'],
        external_api:[t('perf_external'), t('perf_external_desc'), 'warning'],
        event_loop:[t('perf_event_loop'), t('perf_event_loop_desc'), 'danger'],
        memory:[t('perf_memory'), t('perf_memory_desc'), 'danger'],
        insufficient_data:[t('perf_insufficient'), t('perf_insufficient_desc'), 'neutral']
    };
    const [statusLabel, diagnosisText, statusClass] = labels[diagnosis.bottleneck] || labels.insufficient_data;

    DOM.perfStatus.textContent = statusLabel;
    DOM.perfStatus.className = `status-badge ${statusClass}`;
    DOM.perfWorkers.textContent = `${Number(workers.active || 0)} / ${Number(workers.configured || 0)}`;
    DOM.perfWorkersRec.textContent = tf('perf_recommended', {count:Number(workers.recommended || workers.configured || 0)});
    DOM.perfQueue.textContent = `${Number(queue.current || 0)} / ${Number(queue.peak_5m || 0)}`;
    DOM.perfQueueWait.textContent = tf('perf_queue_detail', {queue:Number(queue.p95_wait_ms || 0).toFixed(0), user:Number(latency.p95_user_wait_ms || 0).toFixed(0)});
    DOM.perfProcessing.textContent = `${Number(latency.p95_processing_ms || 0).toFixed(0)} ms`;
    DOM.perfThroughput.textContent = tf('perf_throughput', {count:Number(traffic.throughput_per_minute || 0).toFixed(1)});
    DOM.perfDatabase.textContent = `${Number(database.p95_ms || 0).toFixed(0)} ms`;
    DOM.perfDbErrors.textContent = tf('perf_database_detail', {errors:Number(database.connection_errors || 0), write:Number(databaseWrites.p95_wait_ms || 0).toFixed(0), timeouts:Number(databaseWrites.timeouts || 0)});
    const slowestAction = (data.actions_5m || [])[0];
    const slowestAction24h = (((data.history_24h || {}).actions) || [])[0];
    if (DOM.perfSlowestAction) {
        const recentText = slowestAction
            ? tf('perf_slowest', {action:slowestAction.action, latency:Number(slowestAction.p95_ms || 0).toFixed(0), count:Number(slowestAction.count || 0)})
            : t('perf_slowest_collecting');
        const historyText = slowestAction24h
            ? tf('perf_history', {action:slowestAction24h.action, latency:Number(slowestAction24h.average_ms || 0).toFixed(0), count:Number(slowestAction24h.count || 0)})
            : t('perf_history_collecting');
        DOM.perfSlowestAction.textContent = `${recentText} | ${historyText}`;
    }
    DOM.perfDiagnosis.textContent = diagnosisText;
    renderAutoscaling(data.autoscaling || {});
}

function selectAutoscaleMode(mode) {
    $$('[data-autoscale-mode]').forEach(button => button.classList.toggle('active', button.dataset.autoscaleMode === mode));
    if (state.autoscaleStatus) state.autoscaleStatus.mode = mode;
}

function renderAutoscaling(autoscaling) {
    state.autoscaleStatus = autoscaling;
    const mode = autoscaling.mode || 'off';
    selectAutoscaleMode(mode);
    if (DOM.autoscaleObserve) DOM.autoscaleObserve.checked = Boolean(autoscaling.observe_only);
    if (DOM.autoscaleMin) DOM.autoscaleMin.value = Number(autoscaling.min_workers || 6);
    if (DOM.autoscaleMax) DOM.autoscaleMax.value = Number(autoscaling.max_workers || 20);
    if (DOM.autoscaleState) {
        const observed = autoscaling.observe_only ? t('observation') : (autoscaling.state || 'CALM');
        DOM.autoscaleState.textContent = tf('perf_autoscale_state', {state:observed, count:Number(autoscaling.current_workers || 0)});
        DOM.autoscaleState.className = `status-badge ${autoscaling.bottleneck && !['healthy','insufficient_data'].includes(autoscaling.bottleneck) ? 'warning' : 'success'}`;
    }
    if (DOM.autoscaleNext) {
        const seconds = Math.max(0, Math.round(Number(autoscaling.next_analysis_at || 0) - Date.now() / 1000));
        DOM.autoscaleNext.textContent = tf('perf_next_analysis', {seconds, count:Number(autoscaling.proposed_workers || autoscaling.current_workers || 0)});
    }
    renderAutoscaleChart(autoscaling.timeline || []);
    if (DOM.autoscaleHistory) {
        const decisions = autoscaling.decisions || [];
        DOM.autoscaleHistory.innerHTML = decisions.length ? decisions.slice(0, 8).map(item => `
            <div class="autoscale-history-row">
                <strong>${escapeHtml(item.state || 'CALM')}</strong>
                <span>${Number(item.workers_before || 0)} &rarr; ${Number(item.observe_only ? item.proposed_workers : item.workers_after || 0)}</span>
                <span>${escapeHtml(item.bottleneck || 'healthy')}</span>
                <small>${escapeHtml(item.created_at ? parseUTCDate(item.created_at).toLocaleString() : '')}</small>
            </div>`).join('') : `<p class="empty-state">${escapeHtml(t('no_autoscale_decisions'))}</p>`;
    }
}

function renderAutoscaleChart(timeline) {
    if (!DOM.autoscaleChart || typeof Chart === 'undefined') return;
    const labels = timeline.map(item => new Date(Number(item.timestamp || 0) * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'}));
    const data = {
        labels,
        datasets:[
            {label:t('workers'), data:timeline.map(item => Number(item.workers || 0)), borderColor:'#22c55e', yAxisID:'workers', tension:.25, pointRadius:1},
            {label:t('queue'), data:timeline.map(item => Number(item.queue || 0)), borderColor:'#f59e0b', yAxisID:'workers', tension:.25, pointRadius:1},
            {label:`p95 ${t('queue')}`, data:timeline.map(item => Number(item.queue_p95_ms || 0)), borderColor:'#ef4444', yAxisID:'latency', tension:.25, pointRadius:1},
            {label:'Turso p95', data:timeline.map(item => Number(item.database_p95_ms || 0)), borderColor:'#3b82f6', yAxisID:'latency', tension:.25, pointRadius:1}
        ]
    };
    if (state.autoscaleChart) {
        state.autoscaleChart.data = data;
        state.autoscaleChart.update('none');
        return;
    }
    state.autoscaleChart = new Chart(DOM.autoscaleChart, {
        type:'line', data,
        options:{responsive:true, maintainAspectRatio:false, animation:false, interaction:{mode:'index',intersect:false}, scales:{workers:{beginAtZero:true,position:'left'},latency:{beginAtZero:true,position:'right',grid:{drawOnChartArea:false}}}}
    });
}

async function saveAutoscaleConfiguration() {
    const mode = state.autoscaleStatus?.mode || 'auto';
    const minimum = Number(DOM.autoscaleMin?.value || 6);
    const maximum = Number(DOM.autoscaleMax?.value || 20);
    if (maximum < minimum) return showToast('Le maximum doit etre superieur ou egal au minimum.', 'error');
    try {
        const result = await apiCall('/api/performance/autoscaling', 'POST', {mode, observe_only:Boolean(DOM.autoscaleObserve?.checked), min_workers:minimum, max_workers:maximum});
        renderAutoscaling(result);
        showToast('Configuration autoscaling enregistree.', 'success');
    } catch (error) {
        showToast(error.message || "Impossible d'enregistrer l'autoscaling.", 'error');
    }
}

async function setManualWebhookWorkers(target) {
    try {
        const result = await apiCall('/api/performance/autoscaling', 'POST', {mode:'manual', target_workers:target});
        renderAutoscaling(result);
        showToast(`Workers regles sur ${Number(result.current_workers || target)}.`, 'success');
    } catch (error) { showToast(error.message || 'Reglage impossible.', 'error'); }
}

function adjustWebhookWorkers(delta) {
    const current = Number(state.autoscaleStatus?.current_workers || 8);
    return setManualWebhookWorkers(current + Number(delta || 0));
}

async function stopAutoscaling() {
    try {
        const result = await apiCall('/api/performance/autoscaling', 'POST', {mode:'off'});
        renderAutoscaling(result);
        showToast('Autoscaling arrete. Les workers actuels restent actifs.', 'success');
    } catch (error) { showToast(error.message || "Impossible d'arreter l'autoscaling.", 'error'); }
}

async function exportPerformanceDiagnostic() {
    if (!DOM.btnExportPerformance) return;
    const button = DOM.btnExportPerformance;
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Export...</span>';
    try {
        const metrics = await apiCall('/api/performance');
        const exportedAt = new Date();
        const diagnostic = {
            export_version: 1,
            exported_at: exportedAt.toISOString(),
            source: 'BatmanBot V2 dashboard',
            metrics
        };
        const blob = new Blob([JSON.stringify(diagnostic, null, 2)], {type:'application/json'});
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `ventebot-performance-${exportedAt.toISOString().replace(/[:.]/g, '-')}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        showToast('Diagnostic de performance exporte.', 'success');
    } catch (error) {
        console.error('Performance export failed', error);
        showToast("Impossible d'exporter le diagnostic.", 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
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
        {count:actions.delivery_issues, icon:'triangle-exclamation', title:t('action_delivery_title'), detail:t('action_delivery_detail'), tab:'orders-tab'},
        {count:actions.pending_activations, icon:'bolt', title:t('action_activation_title'), detail:t('action_activation_detail'), tab:'activations-tab'},
        {count:actions.pending_payments, icon:'clock', title:t('action_payment_title'), detail:t('action_payment_detail'), tab:'orders-tab'},
        {count:actions.open_tickets, icon:'headset', title:t('action_ticket_title'), detail:t('action_ticket_detail'), tab:'tickets-tab'}
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
        const customer = order.username ? `@${order.username}` : (order.user_first_name || order.user_telegram_id || t('generic_customer'));
        const product = `${order.product_emoji || ''} ${order.product_name || tf('generic_order', {id:order.id})}`.trim();
        const date = order.created_at ? parseUTCDate(order.created_at).toLocaleString([], {dateStyle:'short', timeStyle:'short'}) : '';
        return `<button type="button" class="recent-order-item" data-go-tab="orders-tab">
            <span class="recent-order-meta"><strong>${escapeHtml(product)}</strong><span>${escapeHtml(customer)} · ${escapeHtml(date)}</span></span>
            <span class="status-badge status-${escapeHtml(String(order.status || '').toLowerCase())}">${escapeHtml(order.status || '')}</span>
            <span class="recent-order-amount">$${Number(order.amount_usd || 0).toFixed(2)}</span>
        </button>`;
    }).join('') : `<p class="empty-state">${t('recent_orders_empty')}</p>`;
    DOM.recentOrdersList.querySelectorAll('[data-go-tab]').forEach(button => button.addEventListener('click', () => switchTab(button.dataset.goTab)));

    const pendingOrders = Number(actions.pending_payments || 0) + Number(actions.delivery_issues || 0);
    DOM.badgeOrders.textContent = pendingOrders;
    DOM.badgeOrders.classList.toggle('hidden', pendingOrders === 0);
    DOM.badgeActivations.textContent = Number(actions.pending_activations || 0);
    DOM.badgeActivations.classList.toggle('hidden', Number(actions.pending_activations || 0) === 0);
    DOM.badgeTickets.textContent = Number(actions.open_tickets || 0);
    DOM.badgeTickets.classList.toggle('hidden', Number(actions.open_tickets || 0) === 0);
}

async function loadStatsBundle() {
    const bundle = await apiCall(`/api/stats/bundle?days=${state.chartDays}`);
    await Promise.all([
        loadStats(bundle.stats),
        loadCharts(bundle.daily),
        loadProductStats(bundle.products),
        loadProductMomentum(bundle.momentum),
        loadDeadProductAlerts(bundle.dead_alerts),
        loadConversionFunnel(bundle.conversion),
    ]);
}

async function loadStats(providedStats=null) {
    const s = providedStats || state.initialStats || await apiCall('/api/stats');
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
                ? t('stock_activation')
                : i.days_left === null || i.days_left === undefined
                ? t('stock_out_unknown')
                : tf('stock_out_days', {days:Number(i.days_left).toFixed(i.days_left < 10 ? 1 : 0)});
            const velocity = Number(i.avg_daily_sales_7d || 0);
            const stockLabel = isActivation ? t('stock_manual') : `${i.stock} ${t('stock_in')}`;
            const salesPerDay = tf('sales_per_day', {value:velocity.toFixed(1)});
            return `<div class="stock-status-item"><div class="prod-badge"><span class="prod-emoji">${escapeHtml(i.emoji || '📦')}</span><span class="prod-name-lbl">${escapeHtml(i.name)}</span></div><div style="display:flex; gap:0.45rem; align-items:center; flex-wrap:wrap; justify-content:flex-end;"><span class="status-badge neutral" title="${escapeHtml(t('stock_sales_average'))}">${escapeHtml(salesPerDay)}</span><span class="stock-count-badge ${c}">${escapeHtml(daysLeft)}</span><span class="stock-count-badge ${c}">${escapeHtml(stockLabel)}</span></div></div>`;
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

async function loadCharts(providedData=null) {
    try {
        const data = providedData || await apiCall(`/api/stats/daily?days=${state.chartDays}`);
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

async function loadProductStats(providedStats=null) {
    try {
        const stats = providedStats || await apiCall('/api/stats/products');
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
            DOM.statsKpiTopProductSub.textContent = tf('stats_sales_revenue', {count:maxSold, revenue:`$${topProduct.total_revenue.toFixed(2)}`});
        } else {
            DOM.statsKpiTopProduct.textContent = "-";
            DOM.statsKpiTopProductSub.textContent = t('stats_no_sales');
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
            labels.push(t('stats_other_products'));
            revenues.push(othersRevenue);
        }
    }
    
    if (revenues.length === 0) {
        labels.push(t('stats_no_sales'));
        revenues.push(1);
    }
    
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,0.05)';
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#9f9baa';
    const colors = ['#6366f1', '#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'];
    
    if (state.productSalesChart) state.productSalesChart.destroy();
    
    const hasSales = revenues.length > 1 || (revenues.length === 1 && labels[0] !== t('stats_no_sales'));
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
                            if (!hasSales) return t('stats_no_sales_recorded');
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

async function loadProductMomentum(providedData=null) {
    if (!DOM.chartProductMomentum) return;
    try {
        const data = providedData || await apiCall('/api/stats/products/momentum?days=30');
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
                DOM.productMomentumControls.innerHTML = `<span class="empty-state">${t('stats_momentum_unavailable')}</span>`;
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
        DOM.productMomentumControls.innerHTML = `<span class="empty-state">${t('stats_no_product_sales')}</span>`;
        if (DOM.productMomentumYesterday) DOM.productMomentumYesterday.textContent = tf('stats_yesterday_sales', {count:0});
        return;
    }

    const selected = new Set(state.productMomentumSelected);
    const yesterdayTotal = products.reduce((sum, p) => sum + (p.yesterday_sold || 0), 0);
    if (DOM.productMomentumYesterday) {
        DOM.productMomentumYesterday.textContent = tf('stats_yesterday_sales', {count:yesterdayTotal});
    }

    DOM.productMomentumControls.innerHTML = products.map(p => {
        const active = selected.has(p.id);
        const activeStyle = active
            ? 'background:rgba(99,102,241,0.18); border-color:var(--primary-color); color:var(--color-text-main);'
            : 'opacity:0.68;';
        return `
            <button type="button" class="btn-secondary btn-sm" style="${activeStyle}" data-action="toggle-momentum" data-id="${Number(p.id)}" title="${escapeHtml(tf('stats_toggle_product', {product:p.name}))}">
                ${escapeHtml(p.emoji || '📦')} ${escapeHtml(p.name)}
                <small style="display:block; color:var(--color-text-muted); margin-top:2px;">${escapeHtml(tf('stats_product_period', {yesterday:p.yesterday_sold || 0, total:p.total_sold || 0}))}</small>
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
            ? tf('stats_view_range', {start:rawDays[startIndex].slice(5), end:rawDays[endIndex].slice(5)})
            : t('stats_view_30');
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
                            return ` ${context.dataset.label}: ${tf('stats_units_revenue', {count:qty, revenue:`$${revenue.toFixed(2)}`})}`;
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

async function loadDeadProductAlerts(providedData=null) {
    if (!DOM.deadProductsAlerts) return;
    try {
        const data = providedData || await apiCall('/api/stats/products/dead-alerts?days=7&min_views=10&max_conversion=0.05');
        state.deadProductAlerts = data.alerts || [];
        renderDeadProductAlerts();
    } catch (e) {
        console.warn('Dead product alerts failed:', e);
        DOM.deadProductsAlerts.innerHTML = `<p class="empty-state">${t('stats_alerts_unavailable')}</p>`;
    }
}

function renderDeadProductAlerts() {
    if (!DOM.deadProductsAlerts) return;
    const alerts = state.deadProductAlerts || [];
    if (alerts.length === 0) {
        DOM.deadProductsAlerts.innerHTML = `<p class="empty-state">${t('stats_no_low_conversion_alert')}</p>`;
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
                    <span class="status-badge info">${escapeHtml(tf('stats_views_count', {count:item.views || 0}))}</span>
                    <span class="status-badge neutral">${escapeHtml(tf('stats_sales_count', {count:item.sold || 0}))}</span>
                    <span class="stock-count-badge low">${conversion.toFixed(1)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

async function loadConversionFunnel(providedData=null) {
    if (!DOM.conversionFunnelStages) return;
    try {
        const data = providedData || await apiCall(`/api/stats/conversion?days=${state.chartDays}`);
        renderConversionFunnel(data || {});
    } catch (error) {
        console.warn('Conversion funnel failed:', error);
        DOM.conversionFunnelStages.innerHTML = `<p class="empty-state">${t('conversion_unavailable')}</p>`;
        if (DOM.conversionProductsBody) DOM.conversionProductsBody.innerHTML = `<tr><td colspan="6" class="empty-state">${t('data_unavailable')}</td></tr>`;
    }
}

function renderConversionFunnel(data) {
    const summary = data.summary || {};
    const stages = [
        {label:t('conversion_stage_view'), value:Number(summary.views || 0), icon:'eye', rate:null},
        {label:t('conversion_stage_buy'), value:Number(summary.buy_clicks || 0), icon:'cart-shopping', rate:summary.view_to_buy_rate},
        {label:t('conversion_stage_created'), value:Number(summary.payments_created || 0), icon:'file-invoice-dollar', rate:summary.buy_to_payment_rate},
        {label:t('conversion_stage_completed'), value:Number(summary.payments_completed || 0), icon:'circle-check', rate:summary.payment_completion_rate},
    ];
    DOM.conversionFunnelStages.innerHTML = stages.map((stage, index) => {
        const rate = stage.rate === null ? null : Number(stage.rate || 0);
        const rateDetail = rate === null
            ? t('conversion_entry_point')
            : rate > 1
                ? t('conversion_direct_entries')
                : tf('conversion_previous_rate', {rate:(rate * 100).toFixed(1)});
        return `
        <div class="conversion-stage">
            <span class="conversion-stage-icon"><i class="fa-solid fa-${stage.icon}"></i></span>
            <span class="conversion-stage-copy"><small>${stage.label}</small><strong>${stage.value.toLocaleString()}</strong><em>${rateDetail}</em></span>
        </div>${index < stages.length - 1 ? '<i class="fa-solid fa-chevron-right conversion-arrow"></i>' : ''}
    `;
    }).join('');
    const overall = Number(summary.overall_conversion_rate || 0) * 100;
    if (DOM.conversionOverallRate) DOM.conversionOverallRate.textContent = tf('conversion_global', {rate:overall.toFixed(1)});
    if (DOM.conversionTrackingNote) {
        DOM.conversionTrackingNote.textContent = data.tracking_since
            ? tf('conversion_tracking_since', {date:parseUTCDate(data.tracking_since).toLocaleString()})
            : t('conversion_tracking_future');
    }
    const products = (data.products || []).slice(0, 12);
    if (!DOM.conversionProductsBody) return;
    if (!products.length) {
        DOM.conversionProductsBody.innerHTML = `<tr><td colspan="6" class="empty-state">${t('conversion_not_enough')}</td></tr>`;
        return;
    }
    DOM.conversionProductsBody.innerHTML = products.map(product => `
        <tr>
            <td><span class="prod-badge"><span class="prod-emoji">${escapeHtml(product.emoji || '')}</span><span class="prod-name-lbl">${escapeHtml(product.name || `Produit #${product.product_id}`)}</span></span></td>
            <td>${Number(product.views || 0).toLocaleString()}</td>
            <td>${Number(product.buy_clicks || 0).toLocaleString()}</td>
            <td>${Number(product.payments_created || 0).toLocaleString()}</td>
            <td>${Number(product.payments_completed || 0).toLocaleString()}</td>
            <td><span class="status-badge ${Number(product.overall_conversion_rate || 0) < 0.05 ? 'warning' : 'success'}">${(Number(product.overall_conversion_rate || 0) * 100).toFixed(1)}%</span></td>
        </tr>
    `).join('');
}

async function loadPaymentReview() {
    const category = encodeURIComponent(state.paymentReviewCategory || 'all');
    const includeResolved = state.paymentReviewIncludeResolved ? 'true' : 'false';
    const data = await apiCall(`/api/payments/review?category=${category}&include_resolved=${includeResolved}&limit=150`);
    state.paymentReviewItems = data.items || [];
    renderPaymentReview(data);
}

function renderPaymentReview(data) {
    const summary = data.summary || {};
    if (DOM.paymentReviewTotal) DOM.paymentReviewTotal.textContent = Number(summary.all || 0);
    if (DOM.paymentReviewUnderpaid) DOM.paymentReviewUnderpaid.textContent = Number(summary.underpaid || 0);
    if (DOM.paymentReviewConfirming) DOM.paymentReviewConfirming.textContent = Number(summary.confirming || 0);
    if (DOM.paymentReviewLate) DOM.paymentReviewLate.textContent = Number(summary.late_after_cancel || 0);
    if (DOM.paymentReviewExpired) DOM.paymentReviewExpired.textContent = Number(summary.expired || 0);
    if (DOM.badgePaymentReview) {
        const underpaidAlerts = Number(summary.underpaid || 0);
        DOM.badgePaymentReview.textContent = underpaidAlerts;
        DOM.badgePaymentReview.classList.toggle('hidden', underpaidAlerts === 0);
    }
    if (!DOM.paymentReviewTableBody) return;
    const items = data.items || [];
    if (!items.length) {
        DOM.paymentReviewTableBody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(t('review_empty'))}</td></tr>`;
        return;
    }
    const categoryLabels = {
        underpaid:t('review_category_underpaid'), expired:t('review_category_expired'), confirming:t('review_category_confirming'),
        late_after_cancel:t('review_category_late'), validation_error:t('review_category_validation'),
        accepted:t('review_category_accepted'),
    };
    DOM.paymentReviewTableBody.innerHTML = items.map(item => {
        const received = Number(item.actually_paid || 0);
        const expected = Number(item.pay_amount || 0);
        const canAccept = !item.resolved && ['underpaid', 'late_after_cancel'].includes(item.category);
        const acceptancePending = item.last_action === 'accept_requested';
        const buttons = item.resolved
            ? item.last_action === 'accept'
                ? `<span class="status-badge success"><i class="fa-solid fa-lock"></i> ${escapeHtml(t('review_finalized'))}</span>`
                : `<button class="btn-secondary btn-sm" data-payment-review-action="reopen" data-kind="${escapeHtml(item.payment_kind)}" data-payment-id="${escapeHtml(item.payment_id)}"><i class="fa-solid fa-folder-open"></i> ${escapeHtml(t('review_reopen'))}</button>`
            : acceptancePending
                ? item.processed_at
                    ? `<span class="status-badge warning"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(t('review_audit_required'))}</span>`
                    : `<button class="btn-secondary btn-sm" data-payment-review-action="reopen" data-kind="${escapeHtml(item.payment_kind)}" data-payment-id="${escapeHtml(item.payment_id)}"><i class="fa-solid fa-rotate-left"></i> ${escapeHtml(t('review_reset'))}</button>`
                : `<button class="btn-secondary btn-sm" data-payment-review-action="recheck" data-kind="${escapeHtml(item.payment_kind)}" data-payment-id="${escapeHtml(item.payment_id)}" title="${escapeHtml(t('review_recheck'))}"><i class="fa-solid fa-rotate"></i></button>
                   ${canAccept ? `<button class="btn-primary btn-sm" data-payment-review-action="accept" data-kind="${escapeHtml(item.payment_kind)}" data-payment-id="${escapeHtml(item.payment_id)}"><i class="fa-solid fa-check"></i> ${escapeHtml(t('review_accept'))}</button>` : ''}
                   <button class="btn-secondary btn-sm" data-payment-review-action="dismiss" data-kind="${escapeHtml(item.payment_kind)}" data-payment-id="${escapeHtml(item.payment_id)}"><i class="fa-solid fa-box-archive"></i> ${escapeHtml(t('review_archive'))}</button>`;
        return `<tr>
            <td><strong>${item.payment_kind === 'wallet_topup' ? escapeHtml(t('review_wallet')) : `#${escapeHtml(item.order_id || '')}`}</strong><small class="table-secondary">${escapeHtml(item.payment_id)}</small></td>
            <td><code>${escapeHtml(item.user_telegram_id || '')}</code></td>
            <td>${escapeHtml(item.product_emoji || '')} ${escapeHtml(item.product_name || '-')}</td>
            <td><span class="status-badge ${item.category === 'accepted' ? 'success' : item.category === 'confirming' ? 'info' : item.category === 'expired' ? 'neutral' : 'warning'}">${categoryLabels[item.category] || item.category}</span><small class="table-secondary">${escapeHtml(item.provider_status || '')}</small></td>
            <td><strong>${received.toFixed(8).replace(/0+$/, '').replace(/\.$/, '') || '0'} USDT</strong><small class="table-secondary">${escapeHtml(tf('review_expected', {amount:expected.toFixed(8).replace(/0+$/, '').replace(/\.$/, '') || '0'}))}</small></td>
            <td class="payment-review-reason">${escapeHtml(item.processing_error || item.last_note || '-')}</td>
            <td>${parseUTCDate(item.updated_at || item.created_at).toLocaleString()}</td>
            <td><div class="table-actions">${buttons}</div></td>
        </tr>`;
    }).join('');
}

async function handlePaymentReviewAction(button) {
    const action = button.dataset.paymentReviewAction;
    const kind = button.dataset.kind;
    const paymentId = button.dataset.paymentId;
    let note = '';
    let confirmation = '';
    if (action === 'dismiss') {
        note = prompt(t('review_dismiss_prompt')) || '';
        if (!note.trim()) return;
    } else if (action === 'accept') {
        if (!confirm(tf('review_accept_confirm', {paymentId}))) return;
        const expected = `ACCEPT ${kind} ${paymentId}`;
        confirmation = expected;
        note = t('review_accept_note');
    } else if (action === 'reopen') {
        note = prompt(t('review_reopen_prompt')) || '';
    }
    button.disabled = true;
    try {
        const response = await apiCall(`/api/payments/review/${encodeURIComponent(kind)}/${encodeURIComponent(paymentId)}/action`, 'POST', {action, note, confirmation});
        showToast(response.warning || (action === 'accept' ? t('review_accept_success') : t('review_updated')), response.warning ? 'error' : 'success');
        await Promise.all([loadPaymentReview(), loadStatsBundle()]);
    } catch (error) {
        showToast(error.message || t('review_action_failed'), 'error');
    } finally {
        button.disabled = false;
    }
}

function renderStatsTable() {
    if (!DOM.statsProductsTableBody) return;
    
    const query = DOM.statsProductSearch ? DOM.statsProductSearch.value.trim().toLowerCase() : '';
    const filtered = state.productStats.filter(p => {
        return p.name.toLowerCase().includes(query) || (p.emoji && p.emoji.includes(query));
    });
    
    if (filtered.length === 0) {
        DOM.statsProductsTableBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(t('stats_no_product_found'))}</td></tr>`;
        return;
    }
    
    DOM.statsProductsTableBody.innerHTML = filtered.map(p => {
        let statusBadge = '';
        if (p.total_sold >= 10) {
            statusBadge = `<span class="status-badge success"><i class="fa-solid fa-fire"></i> ${escapeHtml(t('stats_top_sale'))}</span>`;
        } else if (p.total_sold === 0) {
            statusBadge = `<span class="status-badge neutral">${escapeHtml(t('stats_no_sale'))}</span>`;
        } else {
            statusBadge = `<span class="status-badge info">${escapeHtml(t('stats_normal'))}</span>`;
        }
        
        let stockBadge = '';
        if (p.stock === 0) {
            stockBadge = `<span class="stock-count-badge empty">${escapeHtml(t('stock_out'))}</span>`;
        } else if (p.stock < 3) {
            stockBadge = `<span class="stock-count-badge low">${p.stock} (${escapeHtml(t('stock_low'))})</span>`;
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
        DOM.productsTableBody.innerHTML = prods.map(p => {
            const supplierProduct = p.delivery_type === 'supplier_api';
            const stockActions = supplierProduct
                ? `<button class="btn-table-action" data-action="switch-tab" data-tab-target="supplier-bots-tab" title="${escapeHtml(t('product_manage_supplier'))}" style="color:#a78bfa"><i class="fa-solid fa-plug"></i></button>`
                : `<button class="btn-table-action" data-action="view-product-stock" data-id="${Number(p.id)}" title="${escapeHtml(t('product_view_stock'))}" style="color:#f59e0b;"><i class="fa-solid fa-box-open"></i></button><button class="btn-table-action stock" data-action="open-stock" data-id="${Number(p.id)}" title="${escapeHtml(t('stock_manage'))}"><i class="fa-solid fa-warehouse"></i></button>`;
            return `<tr data-id="${p.id}">
            <td class="drag-handle" style="cursor: grab; text-align: center;"><i class="fas fa-bars" style="color:var(--color-primary);"></i></td>
            <td><div class="prod-badge"><span class="prod-emoji">${escapeHtml(p.emoji||'📦')}</span><strong>${escapeHtml(p.name)}</strong>${supplierProduct ? '<span class="status-badge info">API</span>' : ''}</div></td>
            <td><strong>$${parseFloat(p.price_usd).toFixed(2)}</strong>${p.dynamic_pricing_enabled ? `<span class="dynamic-price-badge" title="${escapeHtml(p.dynamic_pricing_mode === 'suggestion' ? t('product_dynamic_suggestion') : t('product_dynamic_auto'))}"><i class="fa-solid fa-wave-square"></i> ${escapeHtml(t('product_dynamic'))}</span>` : ''}</td><td>${p.warranty_days||0} ${t('days')}</td>
            <td>${p.delivery_type === 'activation' ? `<span class="stock-count-badge ok">${escapeHtml(t('product_activation'))}</span>` : `<span class="stock-count-badge ${p.stock===0?'empty':p.stock<3?'low':'ok'}">${p.stock}${supplierProduct ? ' API' : ''}</span>`}</td>
            <td><span class="status-dot ${p.is_active?'online':''}"></span> ${p.is_active?t('active'):t('inactive')}</td>
            <td><button class="btn-table-action" data-action="toggle-product" data-id="${Number(p.id)}" title="${escapeHtml(p.is_active ? t('product_disable') : t('product_enable'))}" style="color:${p.is_active ? '#ef4444' : '#22c55e'};"><i class="fa-solid ${p.is_active ? 'fa-xmark' : 'fa-check'}"></i></button><button class="btn-table-action" data-action="edit-product" data-id="${Number(p.id)}" title="${escapeHtml(t('product_edit'))}" style="color:#3b82f6;"><i class="fa-solid fa-pen"></i></button>${stockActions}<button class="btn-table-action" data-action="open-tiers" data-id="${Number(p.id)}" title="${escapeHtml(t('product_tiers'))}" style="color:#a78bfa;"><i class="fa-solid fa-tags"></i></button><button class="btn-table-action delete" data-action="delete-product" data-id="${Number(p.id)}" title="${escapeHtml(t('product_delete'))}"><i class="fa-solid fa-trash-can"></i></button></td>
        </tr>`;
        }).join('');
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
                        alert(tf('product_sort_error', {message:e.message}) + '\n' + (state.botUrl || 'relative') + '/api/products/update-sort');
                        loadProducts();
                    }
                }
            });
        }
    } else {
        DOM.productsTableBody.innerHTML = `<tr><td colspan="7" class="empty-state">${t('no_products')}</td></tr>`;
        if (DOM.broadcastBtnProductId) {
            DOM.broadcastBtnProductId.innerHTML = `<option value="">${escapeHtml(t('product_none'))}</option>`;
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
                pn = `${o.product_emoji || '📦'} ${o.product_name}${o.product_is_deleted ? ` (${t('order_deleted')})` : ''}`;
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
            } else if (o.payment_method === 'nowpayments_bep20') {
                payMethod = `<span class="pay-method-badge">NOWPayments · BEP20</span>`;
            } else {
                payMethod = `<span class="pay-method-badge">${escapeHtml(o.payment_method)}</span>`;
            }
            let actions = '';
            if (isTopup) {
                actions = `<span style="font-size:0.78rem;color:var(--color-text-muted);">${escapeHtml(tf('order_balance', {amount:`$${parseFloat(o.balance_after||0).toFixed(2)}`}))}</span>`;
            } else if (o.status === 'PENDING' || o.status === 'AWAITING_PAYMENT') {
                actions = `<button class="btn-table-action" data-action="confirm-order" data-id="${Number(o.id)}" title="${escapeHtml(t('order_confirm'))}" style="color:#22c55e;"><i class="fa-solid fa-check"></i></button> <button class="btn-table-action" data-action="cancel-order" data-id="${Number(o.id)}" title="${escapeHtml(t('order_cancel'))}" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`;
            } else if (o.status === 'PAID_PENDING_DELIVERY') {
                actions = `<button class="btn-table-action" data-action="confirm-order" data-id="${Number(o.id)}" title="${escapeHtml(t('order_retry_delivery'))}" style="color:#22c55e;"><i class="fa-solid fa-rotate-right"></i></button>`;
            } else if (o.status === 'AWAITING_ACTIVATION') {
                actions = `<button class="btn-table-action" data-action="complete-activation" data-id="${Number(o.id)}" title="${escapeHtml(t('activation_mark_done'))}" style="color:#22c55e;"><i class="fa-solid fa-bolt"></i></button>`;
            } else if (o.status === 'AWAITING_ACTIVATION_INFO') {
                actions = '—';
            } else if (o.status === 'COMPLETED') {
                actions = `<button class="btn-table-action" data-action="order-detail" data-id="${Number(o.id)}" title="${escapeHtml(t('order_view_items'))}" style="color:#22c55e;"><i class="fa-solid fa-eye"></i></button>`;
            } else {
                actions = '—';
            }
            let statusHtml = escapeHtml(o.status);
            if (o.status === 'PAID_PENDING_DELIVERY') statusHtml = escapeHtml(t('order_paid_pending'));
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
                    statusHtml += `<br><span style="font-size:0.7rem; color:var(--color-text-muted); display:block; margin-top:4px;">${escapeHtml(tf('order_since', {minutes:eM, seconds:eS}))}<br>${escapeHtml(tf('order_remaining', {minutes:lM, seconds:lS}))}</span>`;
                } else {
                    statusHtml += `<br><span style="font-size:0.7rem; color:var(--color-error); display:block; margin-top:4px;">${escapeHtml(tf('order_expired_since', {minutes:eM, seconds:eS}))}</span>`;
                }

                if (o.status === 'AWAITING_PAYMENT' && o.binance_order_id) {
                    statusHtml += `<span style="font-size:0.7rem; color:var(--color-error); font-weight:bold; display:block; margin-top:2px;">⚠️ ${escapeHtml(t('order_invalid_id'))}</span>`;
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
        let pn = prod ? escapeHtml(`${prod.emoji || '📦'} ${prod.name || ''}`) : `#${Number(o.product_id)}`;
        if (!prod && o.product_name) pn = escapeHtml(`${o.product_emoji || '📦'} ${o.product_name}`);
        const uname = o.username ? `@${escapeHtml(o.username)}` : escapeHtml(o.user_first_name || o.user_telegram_id);
        const identifier = o.activation_identifier ? `<code>${escapeHtml(o.activation_identifier)}</code>` : `<span style="color:var(--color-text-muted);">${escapeHtml(t('activation_waiting_client'))}</span>`;
        const d = parseUTCDate(o.created_at).toLocaleDateString();
        const statusLabel = o.status === 'AWAITING_ACTIVATION' ? t('activation_ready') : t('activation_waiting_id');
        const actions = o.status === 'AWAITING_ACTIVATION'
            ? `<button class="btn-table-action" data-action="complete-activation" data-id="${Number(o.id)}" title="${escapeHtml(t('activation_mark_done'))}" style="color:#22c55e;"><i class="fa-solid fa-bolt"></i></button> <button class="btn-table-action" data-action="cancel-order" data-id="${Number(o.id)}" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`
            : `<button class="btn-table-action" data-action="cancel-order" data-id="${Number(o.id)}" title="Annuler" style="color:#ef4444;"><i class="fa-solid fa-xmark"></i></button>`;

        return `<tr>
            <td><strong>#${Number(o.id)}</strong></td>
            <td>${uname}</td>
            <td><code>${escapeHtml(o.user_telegram_id)}</code></td>
            <td>${pn}</td>
            <td>${identifier}</td>
            <td>$${parseFloat(o.amount_usd || 0).toFixed(2)}</td>
            <td><div class="status-badge ${escapeHtml(String(o.status || '').toLowerCase())}">${escapeHtml(statusLabel)}</div></td>
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
        const securityBadges = `${Array.isArray(k.ip_allowlist) && k.ip_allowlist.length ? '<span class="status-badge pending">IP</span>' : ''}${Number(k.webhook_enabled) === 1 ? '<span class="status-badge completed">Webhook</span>' : ''}`;
        const status = `${active ? `<span class="status-badge completed">${t('active')}</span>` : `<span class="status-badge cancelled">${t('inactive')}</span>`}${securityBadges}`;
        const created = k.created_at ? parseUTCDate(k.created_at).toLocaleDateString() : '';
        const securityAction = `<button class="btn-table-action" data-action="reseller-security" data-id="${Number(k.id)}" title="${escapeHtml(t('reseller_security'))}"><i class="fa-solid fa-shield-halved"></i></button>`;
        const specialCount = Number(k.special_price_count || 0);
        const specialPriceAction = `<button class="btn-table-action reseller-price-action" data-action="reseller-special" data-id="${Number(k.user_telegram_id)}" title="${escapeHtml(t('reseller_special_prices'))}"><i class="fa-solid fa-tags"></i>${specialCount ? `<span>${specialCount}</span>` : ''}</button>`;
        const action = active
            ? `${specialPriceAction}${securityAction}<button class="btn-table-action delete" data-action="reseller-revoke" data-id="${Number(k.id)}" title="${escapeHtml(t('reseller_revoke'))}"><i class="fa-solid fa-ban"></i></button>`
            : `${specialPriceAction}${securityAction}`;
        return `<tr>
            <td><strong>#${Number(k.id)}</strong></td>
            <td>${client}<br><code>${escapeHtml(k.user_telegram_id)}</code></td>
            <td>${escapeHtml(k.name || '')}</td>
            <td><code>${escapeHtml(k.key_prefix || '')}</code></td>
            <td>$${parseFloat(k.wallet_balance || 0).toFixed(2)}</td>
            <td>${Number(k.order_count || 0)}</td>
            <td>$${parseFloat(k.total_spent || 0).toFixed(2)}</td>
            <td>${status}</td>
            <td>${created}</td>
            <td>${action}</td>
        </tr>`;
    }).join('');
}

window.openResellerSecurity = function(id) {
    const reseller = (state.resellers || []).find(item => Number(item.id) === Number(id));
    if (!reseller || !DOM.resellerSecurityModal) return;
    DOM.resellerSecurityKeyId.value = String(reseller.id);
    DOM.resellerIpAllowlist.value = Array.isArray(reseller.ip_allowlist) ? reseller.ip_allowlist.join('\n') : '';
    DOM.resellerWebhookUrl.value = reseller.webhook_url || '';
    DOM.resellerWebhookEnabled.checked = Number(reseller.webhook_enabled) === 1 || reseller.webhook_enabled === true;
    DOM.resellerWebhookRotate.checked = false;
    DOM.resellerWebhookSecret.textContent = '';
    DOM.resellerWebhookSecretOutput.classList.add('hidden');
    showModal(DOM.resellerSecurityModal);
};

async function saveResellerSecurity(event) {
    event.preventDefault();
    const keyId = Number(DOM.resellerSecurityKeyId.value || 0);
    if (!keyId) return;
    const ipAllowlist = DOM.resellerIpAllowlist.value
        .split(/[\n,]+/)
        .map(value => value.trim())
        .filter(Boolean);
    showLoading(true);
    try {
        const result = await apiCall(`/api/resellers/keys/${keyId}/security`, 'PATCH', {
            ip_allowlist: ipAllowlist,
            webhook_url: DOM.resellerWebhookUrl.value.trim(),
            webhook_enabled: DOM.resellerWebhookEnabled.checked,
            rotate_webhook_secret: DOM.resellerWebhookRotate.checked
        });
        const secret = result.security && result.security.webhook_signing_secret;
        if (secret) {
            DOM.resellerWebhookSecret.textContent = secret;
            DOM.resellerWebhookSecretOutput.classList.remove('hidden');
            DOM.resellerWebhookRotate.checked = false;
        } else {
            hideModal(DOM.resellerSecurityModal);
        }
        await loadResellers();
    } catch (error) {
        alert(error.message);
    } finally {
        showLoading(false);
    }
}

function resellerSpecialPriceStatus(item) {
    if (!item.is_active) return {label:t('reseller_special_inactive'), cls:'cancelled'};
    if (item.is_expired) return {label:t('reseller_special_expired'), cls:'expired'};
    if (!item.is_cost_safe && item.enforce_cost_floor) return {label:t('reseller_special_blocked'), cls:'cancelled'};
    return {label:t('reseller_special_effective'), cls:'completed'};
}

function updateResellerSpecialStandardHint() {
    if (!DOM.resellerSpecialStandardHint || !DOM.resellerSpecialProduct) return;
    const product = (state.products || []).find(item => Number(item.id) === Number(DOM.resellerSpecialProduct.value));
    DOM.resellerSpecialStandardHint.textContent = product
        ? `${t('reseller_standard_price')}: $${Number(product.price_usd || 0).toFixed(2)}`
        : '';
}

function populateResellerSpecialProductOptions() {
    if (!DOM.resellerSpecialProduct) return;
    DOM.resellerSpecialProduct.innerHTML = (state.products || [])
        .filter(product => !Number(product.is_deleted || 0))
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
        .map(product => `<option value="${Number(product.id)}">${escapeHtml(product.name || `#${product.id}`)} - $${Number(product.price_usd || 0).toFixed(2)}</option>`)
        .join('');
    updateResellerSpecialStandardHint();
}

function renderResellerSpecialPrices() {
    if (!DOM.resellerSpecialPricesList) return;
    const prices = state.resellerSpecialPrices || [];
    if (!prices.length) {
        DOM.resellerSpecialPricesList.innerHTML = `<p class="empty-state">${t('reseller_no_special_prices')}</p>`;
        return;
    }
    DOM.resellerSpecialPricesList.innerHTML = prices.map(item => {
        const status = resellerSpecialPriceStatus(item);
        const expiry = item.expires_at ? parseUTCDate(item.expires_at).toLocaleString() : t('unlimited');
        const floor = item.cost_floor == null ? '' : `<span>${t('reseller_cost_protection')}: $${Number(item.cost_floor).toFixed(2)}</span>`;
        return `<article class="reseller-price-row">
            <div class="reseller-price-product"><strong>${escapeHtml(item.product_name || `#${item.product_id}`)}</strong><span>${t('reseller_standard_price')}: $${Number(item.standard_price_usd || 0).toFixed(2)}</span></div>
            <div class="reseller-price-value"><strong>$${Number(item.price_usd || 0).toFixed(2)}</strong><span>${Number(item.apply_to_telegram) === 1 ? t('reseller_scope_both') : t('reseller_scope_api')}</span><span>${escapeHtml(expiry)}</span>${floor}</div>
            <span class="status-badge ${status.cls}">${status.label}</span>
            <div class="reseller-price-actions">
                <button type="button" class="btn-table-action" data-action="reseller-special-edit" data-id="${Number(item.product_id)}" title="${escapeHtml(t('reseller_special_edit'))}"><i class="fa-solid fa-pen"></i></button>
                <button type="button" class="btn-table-action delete" data-action="reseller-special-delete" data-id="${Number(item.product_id)}" title="${escapeHtml(t('confirm_delete'))}"><i class="fa-solid fa-trash"></i></button>
            </div>
        </article>`;
    }).join('');
}

window.openResellerSpecialPrices = async function(userId) {
    if (!DOM.resellerSpecialPricesModal) return;
    state.resellerSpecialPriceUserId = Number(userId);
    const reseller = (state.resellers || []).find(item => Number(item.user_telegram_id) === Number(userId));
    DOM.resellerSpecialPricesIdentity.textContent = `${t('reseller_special_prices_for')} ${reseller && reseller.username ? `@${reseller.username}` : reseller && reseller.first_name ? reseller.first_name : userId} (${userId})`;
    showLoading(true);
    try {
        if (!state.products || !state.products.length) await loadProducts();
        populateResellerSpecialProductOptions();
        const result = await apiCall(`/api/resellers/${Number(userId)}/special-prices`);
        state.resellerSpecialPrices = result.prices || [];
        DOM.resellerSpecialPricesForm.reset();
        DOM.resellerSpecialActive.checked = true;
        DOM.resellerSpecialTelegram.checked = true;
        DOM.resellerSpecialCostProtection.checked = true;
        populateResellerSpecialProductOptions();
        renderResellerSpecialPrices();
        showModal(DOM.resellerSpecialPricesModal);
    } catch (error) {
        alert(error.message);
    } finally {
        showLoading(false);
    }
};

window.editResellerSpecialPrice = function(productId) {
    const item = (state.resellerSpecialPrices || []).find(price => Number(price.product_id) === Number(productId));
    if (!item) return;
    DOM.resellerSpecialProduct.value = String(item.product_id);
    DOM.resellerSpecialPrice.value = Number(item.price_usd || 0).toFixed(2);
    DOM.resellerSpecialActive.checked = Boolean(item.is_active);
    DOM.resellerSpecialTelegram.checked = Number(item.apply_to_telegram) === 1;
    DOM.resellerSpecialCostProtection.checked = Boolean(item.enforce_cost_floor);
    if (item.expires_at) {
        const date = parseUTCDate(item.expires_at);
        DOM.resellerSpecialExpiry.value = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    } else {
        DOM.resellerSpecialExpiry.value = '';
    }
    updateResellerSpecialStandardHint();
    DOM.resellerSpecialPrice.focus();
};

async function saveResellerSpecialPrice(event) {
    event.preventDefault();
    const userId = Number(state.resellerSpecialPriceUserId || 0);
    if (!userId) return;
    const expiryValue = DOM.resellerSpecialExpiry.value;
    showLoading(true);
    try {
        await apiCall(`/api/resellers/${userId}/special-prices`, 'PUT', {
            product_id: Number(DOM.resellerSpecialProduct.value),
            price_usd: Number(DOM.resellerSpecialPrice.value),
            is_active: DOM.resellerSpecialActive.checked,
            apply_to_telegram: DOM.resellerSpecialTelegram.checked,
            enforce_cost_floor: DOM.resellerSpecialCostProtection.checked,
            expires_at: expiryValue ? new Date(expiryValue).toISOString() : null
        });
        const result = await apiCall(`/api/resellers/${userId}/special-prices`);
        state.resellerSpecialPrices = result.prices || [];
        renderResellerSpecialPrices();
        await loadResellers();
        alert(t('reseller_special_saved'));
    } catch (error) {
        alert(error.message);
    } finally {
        showLoading(false);
    }
}

window.deleteResellerSpecialPrice = async function(productId) {
    if (!confirm(t('reseller_special_delete_confirm'))) return;
    const userId = Number(state.resellerSpecialPriceUserId || 0);
    showLoading(true);
    try {
        await apiCall(`/api/resellers/${userId}/special-prices/${Number(productId)}`, 'DELETE');
        state.resellerSpecialPrices = state.resellerSpecialPrices.filter(item => Number(item.product_id) !== Number(productId));
        renderResellerSpecialPrices();
        await loadResellers();
    } catch (error) {
        alert(error.message);
    } finally {
        showLoading(false);
    }
};

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

function gameDateInputValue(dateValue) {
    const date = dateValue instanceof Date ? dateValue : new Date(dateValue);
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function ensureGameDateRange() {
    if (!DOM.gameDateFrom || !DOM.gameDateTo) return;
    const today = new Date();
    const week = new Date(today);
    week.setDate(week.getDate() + 7);
    if (!DOM.gameDateFrom.value) DOM.gameDateFrom.value = gameDateInputValue(today);
    if (!DOM.gameDateTo.value) DOM.gameDateTo.value = gameDateInputValue(week);
}

function gameStatusBadge(status) {
    const normalized = String(status || 'UNKNOWN').toUpperCase();
    const labels = {
        DRAFT:t('status_draft'), OPEN:t('status_open'), LOCKED:t('status_locked'), SETTLING:t('status_settling'),
        SETTLED:t('status_settled'), CANCELLED:t('status_cancelled'), SCHEDULED:t('status_scheduled'), TIMED:t('status_timed'),
        IN_PLAY:t('status_in_play'), PAUSED:t('status_paused'), FINISHED:t('status_finished'), POSTPONED:t('status_postponed'), SUSPENDED:t('status_suspended')
    };
    const cls = ['SETTLED','FINISHED'].includes(normalized) ? 'status-completed'
        : ['CANCELLED','SUSPENDED'].includes(normalized) ? 'status-cancelled'
        : ['OPEN','IN_PLAY'].includes(normalized) ? 'status-active' : 'status-pending';
    return `<span class="status-badge ${cls}">${escapeHtml(labels[normalized] || normalized)}</span>`;
}

function gameTeamsHtml(match) {
    const homeImage = match.home_crest ? `<img src="${escapeHtml(match.home_crest)}" alt="" loading="lazy">` : '';
    const awayImage = match.away_crest ? `<img src="${escapeHtml(match.away_crest)}" alt="" loading="lazy">` : '';
    return `<div class="game-team-cell">
        <div class="game-team-line">${homeImage}<strong>${escapeHtml(match.home_name || 'Home')}</strong></div>
        <div class="game-team-line">${awayImage}<strong>${escapeHtml(match.away_name || 'Away')}</strong></div>
    </div>`;
}

function gameMarketLabel(market) {
    return market === 'regulation' ? t('game_result_90') : t('game_qualified');
}

function gameSuggestedResult(match) {
    if (match.market_type === 'qualified') return match.provider_winner || '';
    if (match.regular_score_home == null || match.regular_score_away == null) return '';
    const home = Number(match.regular_score_home);
    const away = Number(match.regular_score_away);
    if (!Number.isFinite(home) || !Number.isFinite(away)) return '';
    return home > away ? 'home' : away > home ? 'away' : 'draw';
}

function gameCanConfigure(match) {
    const status = String(match.provider_status || '').toUpperCase();
    const startsAt = parseUTCDate(match.utc_date);
    return ['SCHEDULED', 'TIMED'].includes(status)
        && Number.isFinite(startsAt.getTime())
        && startsAt.getTime() > Date.now();
}

function gameOutcomeLabel(match, outcome) {
    if (outcome === 'home') return match.home_name || 'Home';
    if (outcome === 'away') return match.away_name || 'Away';
    if (outcome === 'draw') return t('game_draw');
    return t('game_choose');
}

function setGameView(view) {
    state.gameView = view || 'catalog';
    $$('.game-view-tab').forEach(button => button.classList.toggle('active', button.dataset.gameView === state.gameView));
    $$('.game-view').forEach(panel => panel.classList.toggle('active', panel.id === `game-${state.gameView}-view`));
}

async function loadGameManagement(options={}) {
    ensureGameDateRange();
    const [provider, saved] = await Promise.all([
        apiCall('/api/game/provider'),
        apiCall('/api/game/matches?include_cancelled=true'),
    ]);
    state.gameProvider = provider;
    state.gameMatches = saved.matches || [];
    renderGameManagement(saved.summary || provider.summary || {});
    if (provider.configured) {
        await loadGameCatalog({force:Boolean(options.forceCatalog)});
    } else {
        state.gameCatalog = [];
        renderGameCatalog();
    }
}

async function loadGameCatalog(options={}) {
    ensureGameDateRange();
    if (!state.gameProvider?.configured) return;
    const params = new URLSearchParams({
        date_from: DOM.gameDateFrom.value,
        date_to: DOM.gameDateTo.value,
    });
    if (DOM.gameCompetitionFilter.value) params.set('competition', DOM.gameCompetitionFilter.value);
    if (DOM.gameStatusFilter.value) params.set('provider_status', DOM.gameStatusFilter.value);
    if (DOM.gameSearch.value.trim()) params.set('search', DOM.gameSearch.value.trim());
    if (options.force) params.set('force', 'true');
    const data = await apiCall(`/api/game/catalog?${params.toString()}`);
    state.gameCatalog = data.matches || [];
    const mergedCompetitions = new Map((state.gameCompetitions || []).map(item => [item.code, item]));
    (data.competitions || []).forEach(item => mergedCompetitions.set(item.code, item));
    state.gameCompetitions = [...mergedCompetitions.values()].sort((a,b) => a.name.localeCompare(b.name));
    const selectedCode = DOM.gameCompetitionFilter.value;
    DOM.gameCompetitionFilter.innerHTML = `<option value="">${escapeHtml(t('game_all'))}</option>` + state.gameCompetitions.map(item =>
        `<option value="${escapeHtml(item.code)}">${escapeHtml(item.name)}</option>`
    ).join('');
    DOM.gameCompetitionFilter.value = selectedCode;
    renderGameCatalog();
}

function renderGameManagement(summary={}) {
    const configured = Boolean(state.gameProvider?.configured);
    DOM.gameProviderStatus.textContent = configured ? t('game_provider_connected') : t('supplier_not_configured');
    DOM.gameProviderWarning.classList.toggle('hidden', configured);
    DOM.gameOpenCount.textContent = Number(summary.open || 0).toLocaleString();
    DOM.gameSettleCount.textContent = Number(summary.locked || 0).toLocaleString();
    DOM.gameBetCount.textContent = Number(summary.bets || 0).toLocaleString();
    DOM.gameCoinsStaked.textContent = Number(summary.coins_staked || 0).toLocaleString();
    renderSavedGameMatches();
}

function renderGameCatalog() {
    if (!state.gameProvider?.configured) {
        DOM.gameCatalogMeta.textContent = t('game_configure_key');
        DOM.gameCatalogBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(t('game_api_missing'))}</td></tr>`;
        return;
    }
    DOM.gameCatalogMeta.textContent = tf('game_found', {count:state.gameCatalog.length});
    if (!state.gameCatalog.length) {
        DOM.gameCatalogBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(t('game_no_filter'))}</td></tr>`;
        return;
    }
    DOM.gameCatalogBody.innerHTML = state.gameCatalog.map(match => `
        <tr>
            <td><strong>${parseUTCDate(match.utc_date).toLocaleDateString()}</strong><span class="table-secondary">${parseUTCDate(match.utc_date).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span></td>
            <td><strong>${escapeHtml(match.competition_name || 'Football')}</strong><span class="table-secondary">${escapeHtml(match.competition_code || '')}</span></td>
            <td>${gameTeamsHtml(match)}</td>
            <td>${escapeHtml(String(match.stage || '—').replaceAll('_', ' '))}</td>
            <td>${gameStatusBadge(match.provider_status)}</td>
            <td>${match.selected
                ? `<span class="status-badge status-completed">${escapeHtml(t('game_already_added'))}</span>`
                : gameCanConfigure(match)
                    ? `<button class="btn-primary btn-sm" type="button" data-game-action="configure" data-external-id="${escapeHtml(match.external_match_id)}"><i class="fa-solid fa-plus"></i> ${escapeHtml(t('game_configure'))}</button>`
                    : `<span class="status-badge status-pending">${escapeHtml(t('common_unavailable'))}</span>`}
            </td>
        </tr>`).join('');
}

function renderSavedGameMatches() {
    const active = state.gameMatches.filter(match => ['DRAFT','OPEN','LOCKED','SETTLING'].includes(match.status));
    const settlement = active.filter(match => ['FINISHED','AWARDED'].includes(String(match.provider_status || '').toUpperCase()));
    const history = state.gameMatches.filter(match => ['SETTLED','CANCELLED'].includes(match.status));
    DOM.gameSettleCount.textContent = settlement.length.toLocaleString();
    DOM.badgeGameResults.textContent = settlement.length;
    DOM.badgeGameResults.classList.toggle('hidden', settlement.length === 0);

    DOM.gamePublishedBody.innerHTML = active.length ? active.map(match => `
        <tr>
            <td>${parseUTCDate(match.utc_date).toLocaleString()}</td>
            <td>${gameTeamsHtml(match)}</td>
            <td>${escapeHtml(gameMarketLabel(match.market_type))}</td>
            <td>${parseUTCDate(match.lock_at).toLocaleString()}</td>
            <td><strong>${Number(match.total_pool || 0).toLocaleString()}</strong><span class="table-secondary">${escapeHtml(tf('game_players', {count:Number(match.bet_count || 0)}))}</span></td>
            <td>${gameStatusBadge(match.status)}<span class="table-secondary">API: ${escapeHtml(match.provider_status || '—')}</span></td>
            <td><div class="table-actions">
                ${match.status === 'DRAFT' ? `<button class="btn-primary btn-sm" data-game-action="publish" data-match-id="${match.id}"><i class="fa-solid fa-paper-plane"></i> ${escapeHtml(t('game_publish'))}</button>` : ''}
                ${match.status !== 'DRAFT' ? `<button class="btn-secondary btn-sm" data-game-action="sync" data-match-id="${match.id}" title="${escapeHtml(t('game_update_result'))}"><i class="fa-solid fa-rotate"></i></button>` : ''}
                ${Number(match.bet_count || 0) === 0 ? `<button class="btn-secondary btn-sm" data-game-action="edit" data-match-id="${match.id}" title="${escapeHtml(t('game_configure'))}"><i class="fa-solid fa-pen"></i></button>` : ''}
                <button class="btn-secondary btn-sm" data-game-action="cancel" data-match-id="${match.id}" title="${escapeHtml(t('game_cancel_refund'))}"><i class="fa-solid fa-ban"></i></button>
            </div></td>
        </tr>`).join('') : `<tr><td colspan="7" class="empty-state">${escapeHtml(t('game_no_published'))}</td></tr>`;

    DOM.gameSettlementBody.innerHTML = settlement.length ? settlement.map(match => {
        const suggestion = gameSuggestedResult(match);
        const drawOption = match.market_type === 'regulation' ? `<option value="draw">${escapeHtml(t('game_draw'))}</option>` : '';
        return `<tr>
            <td>${gameTeamsHtml(match)}</td>
            <td><strong>${match.score_home ?? '—'} - ${match.score_away ?? '—'}</strong><span class="table-secondary">${escapeHtml(match.provider_status || '')}</span></td>
            <td>${escapeHtml(gameMarketLabel(match.market_type))}</td>
            <td><select id="game-result-${match.id}" class="form-control"><option value="">${escapeHtml(t('game_choose_option'))}</option><option value="home" ${suggestion === 'home' ? 'selected' : ''}>${escapeHtml(match.home_name)}</option>${drawOption}<option value="away" ${suggestion === 'away' ? 'selected' : ''}>${escapeHtml(match.away_name)}</option></select></td>
            <td><strong>${Number(match.total_pool || 0).toLocaleString()} Batman Coins</strong><span class="table-secondary">${escapeHtml(tf('game_predictions_count', {count:Number(match.bet_count || 0)}))}</span></td>
            <td><button class="btn-primary btn-sm" data-game-action="settle" data-match-id="${match.id}"><i class="fa-solid fa-check-double"></i> ${escapeHtml(t('btn_confirm'))}</button></td>
        </tr>`;
    }).join('') : `<tr><td colspan="6" class="empty-state">${escapeHtml(t('game_no_pending'))}</td></tr>`;

    DOM.gameHistoryBody.innerHTML = history.length ? history.map(match => `
        <tr><td>${parseUTCDate(match.utc_date).toLocaleString()}</td><td>${gameTeamsHtml(match)}</td>
        <td>${escapeHtml(gameOutcomeLabel(match, match.result_outcome))}</td><td>${Number(match.bet_count || 0).toLocaleString()}</td><td>${gameStatusBadge(match.status)}</td></tr>
    `).join('') : `<tr><td colspan="5" class="empty-state">${escapeHtml(t('game_no_history'))}</td></tr>`;
}

function openGameMatchModal(match, localMatch=null) {
    state.currentGameMatch = match;
    DOM.gameExternalMatchId.value = match.external_match_id || '';
    DOM.gameLocalMatchId.value = localMatch?.id || '';
    DOM.gameModalTitle.textContent = localMatch ? t('game_modal_configure') : t('game_modal_publish');
    DOM.gameModalPreview.innerHTML = `<strong>${escapeHtml(match.home_name)} - ${escapeHtml(match.away_name)}</strong><span>${escapeHtml(match.competition_name || 'Football')} · ${parseUTCDate(match.utc_date).toLocaleString()}</span>`;
    DOM.gameMarketType.value = localMatch?.market_type || 'qualified';
    const start = parseUTCDate(match.utc_date);
    const lock = localMatch ? parseUTCDate(localMatch.lock_at) : new Date(start.getTime() - 10 * 60000);
    const lockMinutes = Math.max(0, Math.round((start.getTime() - lock.getTime()) / 60000));
    if (![...DOM.gameLockMinutes.options].some(option => Number(option.value) === lockMinutes)) {
        DOM.gameLockMinutes.add(new Option(`${lockMinutes} minutes`, String(lockMinutes)));
    }
    DOM.gameLockMinutes.value = String(lockMinutes || 10);
    DOM.gameMinStake.value = localMatch?.min_stake || 25;
    DOM.gameMaxStake.value = localMatch?.max_stake || 500;
    DOM.gameFeePercent.value = Number(localMatch?.fee_bps ?? 500) / 100;
    DOM.gamePublishNow.checked = localMatch ? localMatch.status !== 'DRAFT' : true;
    DOM.gamePublishNow.disabled = Boolean(localMatch);
    $('game-match-submit').innerHTML = localMatch ? `<i class="fa-solid fa-floppy-disk"></i> ${escapeHtml(t('game_save'))}` : `<i class="fa-solid fa-paper-plane"></i> ${escapeHtml(t('game_publish_bot'))}`;
    showModal(DOM.gameMatchModal);
}

async function saveGameMatch(event) {
    event.preventDefault();
    const payload = {
        market_type: DOM.gameMarketType.value,
        lock_minutes: Number(DOM.gameLockMinutes.value),
        min_stake: Number(DOM.gameMinStake.value),
        max_stake: Number(DOM.gameMaxStake.value),
        fee_bps: Math.round(Number(DOM.gameFeePercent.value) * 100),
    };
    if (payload.max_stake < payload.min_stake) {
        showToast(t('game_stake_invalid'), 'error');
        return;
    }
    showLoading(true);
    try {
        if (DOM.gameLocalMatchId.value) {
            await apiCall(`/api/game/matches/${DOM.gameLocalMatchId.value}`, 'PUT', payload);
            showToast(t('game_config_saved'), 'success');
        } else {
            await apiCall('/api/game/matches', 'POST', {
                ...payload,
                external_match_id: DOM.gameExternalMatchId.value,
                publish: DOM.gamePublishNow.checked,
            });
            showToast(DOM.gamePublishNow.checked ? t('game_published_success') : t('game_draft_saved'), 'success');
        }
        hideModal(DOM.gameMatchModal);
        await loadGameManagement();
    } catch (error) {
        showToast(tf('game_save_failed', {message:error.message}), 'error');
    } finally {
        showLoading(false);
    }
}

async function handleGameTableAction(event) {
    const button = event.target.closest('[data-game-action]');
    if (!button) return;
    const action = button.dataset.gameAction;
    const matchId = Number(button.dataset.matchId || 0);
    if (action === 'configure') {
        const match = state.gameCatalog.find(item => String(item.external_match_id) === String(button.dataset.externalId));
        if (match) openGameMatchModal(match);
        return;
    }
    const localMatch = state.gameMatches.find(item => Number(item.id) === matchId);
    if (!localMatch) return;
    if (action === 'edit') {
        openGameMatchModal(localMatch, localMatch);
        return;
    }
    try {
        showLoading(true);
        if (action === 'publish') {
            await apiCall(`/api/game/matches/${matchId}/publish`, 'POST');
            showToast(t('game_published_success'), 'success');
        } else if (action === 'sync') {
            await apiCall(`/api/game/matches/${matchId}/sync`, 'POST');
            showToast(t('game_result_refreshed'), 'success');
        } else if (action === 'cancel') {
            if (!confirm(tf('game_cancel_confirm', {match:`${localMatch.home_name} - ${localMatch.away_name}`}))) return;
            await apiCall(`/api/game/matches/${matchId}/cancel`, 'POST', {confirmation:`CANCEL ${matchId}`});
            showToast(t('game_cancelled'), 'success');
        } else if (action === 'settle') {
            const result = $(`game-result-${matchId}`)?.value || '';
            if (!result) throw new Error(t('game_choose_result'));
            const label = gameOutcomeLabel(localMatch, result);
            if (!confirm(tf('game_settle_confirm', {result:label}))) return;
            await apiCall(`/api/game/matches/${matchId}/settle`, 'POST', {result_outcome:result, confirmation:`SETTLE ${matchId}`});
            showToast(t('game_settled'), 'success');
        }
        await loadGameManagement();
    } catch (error) {
        showToast(tf('game_action_failed', {message:error.message}), 'error');
    } finally {
        showLoading(false);
    }
}

async function setSupplierView(view) {
    const nextView = ['stats', 'router'].includes(view) ? view : 'catalog';
    state.supplierView = nextView;
    DOM.supplierCatalogView?.classList.toggle('hidden', nextView !== 'catalog');
    DOM.supplierStatsView?.classList.toggle('hidden', nextView !== 'stats');
    DOM.supplierRouterView?.classList.toggle('hidden', nextView !== 'router');
    $$('[data-supplier-view]').forEach(button => {
        const active = button.dataset.supplierView === nextView;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
    });
    if (nextView === 'stats') await loadSupplierStats();
    if (nextView === 'router') await loadSupplierRoutes();
}

async function setSupplierStatsDays(rawDays) {
    const days = [7, 30, 90, 365].includes(Number(rawDays)) ? Number(rawDays) : 30;
    state.supplierStatsDays = days;
    $$('[data-supplier-days]').forEach(button => {
        button.classList.toggle('active', Number(button.dataset.supplierDays) === days);
    });
    await loadSupplierStats();
}

async function loadSupplierStats() {
    if (!DOM.supplierStatsProductsBody || !state.activeSupplierCode) return;
    const supplierCode = state.activeSupplierCode;
    DOM.supplierStatsProductsBody.innerHTML = `<tr><td colspan="7" class="empty-state">${escapeHtml(t('loading'))}</td></tr>`;
    try {
        const stats = await apiCall(`/api/supplier-bots/${encodeURIComponent(supplierCode)}/stats?days=${state.supplierStatsDays}`);
        if (supplierCode !== state.activeSupplierCode) return;
        state.supplierStats = stats;
        const summary = stats.summary || {};
        const revenue = Number(summary.revenue || 0);
        const cost = Number(summary.cost || 0);
        const profit = Number(summary.profit || 0);
        DOM.supplierStatsRevenue.textContent = `$${revenue.toFixed(2)}`;
        DOM.supplierStatsCost.textContent = `$${cost.toFixed(2)}`;
        DOM.supplierStatsProfit.textContent = `${profit < 0 ? '-' : ''}$${Math.abs(profit).toFixed(2)}`;
        DOM.supplierStatsProfit.classList.toggle('supplier-profit-positive', profit >= 0);
        DOM.supplierStatsProfit.classList.toggle('supplier-profit-negative', profit < 0);
        DOM.supplierStatsMargin.textContent = tf('supplier_margin_value', {value:Number(summary.margin_percent || 0).toFixed(1)});
        DOM.supplierStatsItems.textContent = Number(summary.items_sold || 0).toLocaleString(currentLocale());
        DOM.supplierStatsOrders.textContent = Number(summary.orders || 0).toLocaleString(currentLocale());
        DOM.supplierStatsOrdersSub.textContent = tf('supplier_average_order_value', {value:Number(summary.average_order || 0).toFixed(2)});
        DOM.supplierStatsSuccess.textContent = `${Number(summary.success_rate || 0).toFixed(1)}%`;

        const quality = stats.data_quality || {};
        const qualityMessages = [];
        if (Number(quality.estimated_cost_orders || 0) > 0) {
            qualityMessages.push(tf('supplier_quality_estimated', {count:Number(quality.estimated_cost_orders)}));
        }
        if (Number(quality.missing_cost_orders || 0) > 0) {
            qualityMessages.push(tf('supplier_quality_missing', {count:Number(quality.missing_cost_orders)}));
        }
        DOM.supplierStatsQuality.classList.toggle('hidden', qualityMessages.length === 0);
        DOM.supplierStatsQuality.innerHTML = qualityMessages.length
            ? `<i class="fa-solid fa-triangle-exclamation"></i><div><strong>${escapeHtml(t('supplier_quality_title'))}</strong><br>${qualityMessages.map(message => escapeHtml(message)).join(' ')}</div>`
            : '';

        const products = stats.products || [];
        DOM.supplierStatsProductsBody.innerHTML = products.length ? products.map(product => {
            const productProfit = Number(product.profit || 0);
            const profitClass = productProfit >= 0 ? 'supplier-profit-positive' : 'supplier-profit-negative';
            const estimate = Number(product.missing_cost_orders || 0) > 0
                ? `<small>${escapeHtml(t('supplier_cost_incomplete'))}</small>`
                : Number(product.estimated_cost_orders || 0) > 0 ? `<small>${escapeHtml(t('supplier_cost_estimated'))}</small>` : '';
            return `<tr>
                <td><div class="supplier-stats-product"><span>${escapeHtml(product.emoji || '📦')}</span><div><strong>${escapeHtml(product.name || product.external_product_id || '?')}</strong><small>ID ${escapeHtml(product.external_product_id || '')}</small></div></div></td>
                <td><strong>${Number(product.items_sold || 0).toLocaleString(currentLocale())}</strong></td>
                <td>${Number(product.orders || 0).toLocaleString(currentLocale())}</td>
                <td><strong>$${Number(product.revenue || 0).toFixed(2)}</strong></td>
                <td>$${Number(product.cost || 0).toFixed(2)}${estimate}</td>
                <td><strong class="${profitClass}">${productProfit < 0 ? '-' : ''}$${Math.abs(productProfit).toFixed(2)}</strong></td>
                <td>${Number(product.margin_percent || 0).toFixed(1)}%</td>
            </tr>`;
        }).join('') : `<tr><td colspan="7" class="empty-state">${escapeHtml(t('supplier_no_sales_period'))}</td></tr>`;
        renderSupplierStatsChart(stats.daily || []);
    } catch (error) {
        if (supplierCode !== state.activeSupplierCode) return;
        state.supplierStats = null;
        DOM.supplierStatsRevenue.textContent = '$0.00';
        DOM.supplierStatsCost.textContent = '$0.00';
        DOM.supplierStatsProfit.textContent = '$0.00';
        DOM.supplierStatsMargin.textContent = tf('supplier_margin_value', {value:'0'});
        DOM.supplierStatsItems.textContent = '0';
        DOM.supplierStatsOrders.textContent = '0';
        DOM.supplierStatsOrdersSub.textContent = tf('supplier_average_order_value', {value:'0.00'});
        DOM.supplierStatsSuccess.textContent = '0%';
        DOM.supplierStatsQuality.classList.add('hidden');
        DOM.supplierStatsQuality.innerHTML = '';
        renderSupplierStatsChart([]);
        DOM.supplierStatsProductsBody.innerHTML = `<tr><td colspan="7" class="empty-state">${escapeHtml(error.message || t('supplier_stats_load_failed'))}</td></tr>`;
    }
}

function renderSupplierStatsChart(daily) {
    if (!DOM.supplierStatsChart || typeof Chart === 'undefined') return;
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--color-text-muted').trim() || '#9f9baa';
    const gridColor = styles.getPropertyValue('--chart-grid').trim() || 'rgba(255,255,255,.06)';
    const data = {
        labels: daily.map(item => String(item.day || '').slice(5)),
        datasets: [
            {label:t('supplier_revenue'),data:daily.map(item=>Number(item.revenue||0)),borderColor:'#22c55e',backgroundColor:'#22c55e22',fill:true,tension:.25,pointRadius:2},
            {label:t('supplier_spent'),data:daily.map(item=>Number(item.cost||0)),borderColor:'#f59e0b',backgroundColor:'#f59e0b18',tension:.25,pointRadius:2},
            {label:t('supplier_profit'),data:daily.map(item=>Number(item.profit||0)),borderColor:'#3b82f6',backgroundColor:'#3b82f622',tension:.25,pointRadius:2},
        ],
    };
    if (state.supplierStatsChart) {
        state.supplierStatsChart.data = data;
        state.supplierStatsChart.update('none');
        return;
    }
    state.supplierStatsChart = new Chart(DOM.supplierStatsChart, {
        type:'line',
        data,
        options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{color:textColor,boxWidth:10,usePointStyle:true}}},scales:{x:{ticks:{color:textColor,maxTicksLimit:12},grid:{color:gridColor}},y:{beginAtZero:true,ticks:{color:textColor,callback:value=>'$'+value},grid:{color:gridColor}}}},
    });
}

async function loadSupplierBot() {
    if (!DOM.supplierProductsTableBody) return;
    try {
        const list = await apiCall('/api/supplier-bots');
        state.supplierBots = list.providers || [];
        if (!state.supplierBots.some(provider => provider.code === state.activeSupplierCode)) {
            state.activeSupplierCode = state.supplierBots[0]?.code || 'canboso';
        }
        renderSupplierProviderSwitcher();
        state.supplierBot = await apiCall(`/api/supplier-bots/${encodeURIComponent(state.activeSupplierCode)}`);
        const supplier = state.supplierBot;
        const providerSummary = state.supplierBots.find(provider => provider.code === state.activeSupplierCode);
        if (providerSummary?.name) supplier.supplier = providerSummary.name;
        DOM.supplierConnection.textContent = `${supplier.supplier || state.activeSupplierCode} · ${supplier.configured ? (supplier.enabled ? t('supplier_connected') : t('supplier_disabled')) : t('supplier_key_missing')}`;
        DOM.supplierConnection.style.color = supplier.configured && supplier.enabled ? 'var(--color-success)' : 'var(--color-warning)';
        DOM.supplierWalletBalance.textContent = supplier.wallet?.balance_text || (supplier.wallet_error ? t('common_unavailable') : '—');
        DOM.supplierWalletBalance.style.color = supplier.wallet && Number(supplier.wallet.balance || 0) > 0 ? 'var(--color-success)' : 'var(--color-warning)';
        DOM.supplierLastSync.textContent = supplier.last_sync ? parseUTCDate(supplier.last_sync).toLocaleString() : t('supplier_never');
        DOM.supplierSelectedCount.textContent = (supplier.products || []).filter(product => product.enabled).length;
        const counts = supplier.order_counts || {};
        DOM.supplierReviewCount.textContent = Number(counts.failed || 0) + Number(counts.unknown || 0);
        DOM.supplierEnabled.checked = Boolean(supplier.enabled);
        if (DOM.supplierDisplayName) DOM.supplierDisplayName.value = supplier.display_name || '';
        DOM.supplierMarginType.value = supplier.margin_type || 'fixed';
        DOM.supplierMarginValue.value = Number(supplier.margin_value || 0);
        if (DOM.supplierProviderName) DOM.supplierProviderName.textContent = supplier.supplier || state.activeSupplierCode;
        if (DOM.supplierCredentialEnv) DOM.supplierCredentialEnv.textContent = supplier.credential_env || 'SUPPLIER_API_KEY';
        const usesExchangeRate = String(supplier.source_currency || 'USD').toUpperCase() !== 'USD';
        DOM.supplierRateGroup?.classList.toggle('hidden', !usesExchangeRate);
        if (DOM.supplierRateLabel) DOM.supplierRateLabel.textContent = supplier.source_currency ? `${supplier.source_currency} / USD` : t('supplier_units_per_usd');
        if (DOM.supplierUnitsPerUsd) DOM.supplierUnitsPerUsd.value = Number(supplier.units_per_usd || 1);
        if (DOM.btnSupplierSync) DOM.btnSupplierSync.disabled = !supplier.configured;
        renderSupplierProducts();
        if (state.supplierView === 'stats') await loadSupplierStats();
        if (state.supplierView === 'router') await loadSupplierRoutes();
    } catch (error) {
        DOM.supplierProductsTableBody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(error.message || t('supplier_load_failed'))}</td></tr>`;
    }
}

function renderSupplierProviderSwitcher() {
    if (!DOM.supplierProviderSwitcher) return;
    DOM.supplierProviderSwitcher.innerHTML = (state.supplierBots || []).map(provider => {
        const active = provider.code === state.activeSupplierCode;
        const status = !provider.configured ? t('supplier_key_missing') : provider.enabled ? tf('supplier_displayed', {count:Number(provider.selected_count || 0)}) : t('supplier_disabled');
        return `<button type="button" role="tab" class="${active ? 'active' : ''}" aria-selected="${active}" data-action="supplier-select" data-code="${escapeHtml(provider.code)}"><i class="fa-solid fa-server"></i><span><strong>${escapeHtml(provider.name || provider.code)}</strong><small>${escapeHtml(status)}</small></span></button>`;
    }).join('');
}

window.selectSupplierBot = async function(supplierCode) {
    state.activeSupplierCode = String(supplierCode || 'canboso');
    state.supplierBot = null;
    state.supplierStats = null;
    if (DOM.supplierProductSearch) DOM.supplierProductSearch.value = '';
    if (DOM.supplierProductsTableBody) DOM.supplierProductsTableBody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(t('supplier_loading_catalog'))}</td></tr>`;
    await loadSupplierBot();
};

function renderSupplierProducts() {
    if (!DOM.supplierProductsTableBody) return;
    const supplier = state.supplierBot || {};
    const query = (DOM.supplierProductSearch?.value || '').trim().toLowerCase();
    const products = (supplier.products || []).filter(product => !query || String(product.display_name || product.name || '').toLowerCase().includes(query) || String(product.name || '').toLowerCase().includes(query) || String(product.external_product_id || '').toLowerCase().includes(query));
    if (!products.length) {
        DOM.supplierProductsTableBody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(t('supplier_no_product'))}</td></tr>`;
        return;
    }
    DOM.supplierProductsTableBody.innerHTML = products.map(product => {
        const id = Number(product.id);
        const marginType = product.margin_type || 'inherit';
        const marginValue = marginType === 'inherit' ? '' : Number(product.margin_value || 0);
        const stockClass = Number(product.remote_stock || 0) === 0 ? 'empty' : Number(product.remote_stock || 0) < 3 ? 'low' : 'ok';
        const affordableStock = Number(product.affordable_stock || 0);
        const affordableClass = affordableStock === 0 ? 'empty' : affordableStock < 3 ? 'low' : 'ok';
        const sourceCurrency = String(product.source_currency || supplier.source_currency || 'USD').toUpperCase();
        const sourcePrice = Number(product.source_price ?? product.base_price ?? 0);
        const displayName = product.display_name || product.name || '?';
        const displayEmoji = product.display_emoji || product.emoji || '📦';
        const sourcePriceHtml = sourceCurrency === 'USD'
            ? `<strong>$${sourcePrice.toFixed(2)}</strong>`
            : `<strong>${new Intl.NumberFormat('fr-FR', {maximumFractionDigits:0}).format(sourcePrice)} ${escapeHtml(sourceCurrency)}</strong><small style="display:block;color:var(--color-text-muted)">~$${Number(product.base_price || 0).toFixed(4)}</small>`;
        return `<tr>
            <td><input class="supplier-product-toggle" type="checkbox" id="supplier-enabled-${id}" ${product.enabled ? 'checked' : ''} aria-label="${escapeHtml(t('supplier_show'))} ${escapeHtml(displayName)}"></td>
            <td><div class="supplier-product-name"><span>${escapeHtml(displayEmoji)}</span><div><strong>${escapeHtml(displayName)}</strong><small>${product.custom_name ? `${escapeHtml(tf('supplier_source', {name:product.name}))} · ` : ''}${escapeHtml(supplier.supplier || state.activeSupplierCode)} · ID ${escapeHtml(product.external_product_id)}</small></div></div></td>
            <td>${sourcePriceHtml}</td>
            <td><span class="stock-count-badge ${stockClass}">${Number(product.remote_stock || 0)}</span></td>
            <td><span class="stock-count-badge ${affordableClass}" title="${escapeHtml(t('supplier_balance_limited'))}">${affordableStock}</span></td>
            <td><div class="supplier-margin-controls"><select id="supplier-margin-type-${id}" data-change-action="supplier-margin" data-id="${id}"><option value="inherit" ${marginType === 'inherit' ? 'selected' : ''}>${escapeHtml(t('supplier_global_margin'))}</option><option value="fixed" ${marginType === 'fixed' ? 'selected' : ''}>+$</option><option value="percent" ${marginType === 'percent' ? 'selected' : ''}>+%</option><option value="sale_price" ${marginType === 'sale_price' ? 'selected' : ''}>${escapeHtml(t('supplier_fixed_sale_price'))}</option></select><input id="supplier-margin-value-${id}" type="number" min="0" step="0.01" value="${marginValue}" ${marginType === 'inherit' ? 'disabled' : ''}></div></td>
            <td><strong>$${Number(product.final_price || 0).toFixed(2)}</strong><small style="display:block;color:${product.price_safe === false ? 'var(--color-error)' : 'var(--color-text-muted)'}">${escapeHtml(product.price_safe === false ? t('supplier_hidden_cost') : product.effective_margin_type === 'sale_price' ? t('supplier_secure_fixed') : product.effective_margin_type === 'percent' ? '+' + Number(product.effective_margin_value || 0).toFixed(2) + '%' : '+$' + Number(product.effective_margin_value || 0).toFixed(2))}</small></td>
            <td><div class="table-actions"><button type="button" class="btn-table-action" data-action="supplier-description" data-id="${id}" title="${escapeHtml(t('supplier_customize'))}"><i class="fa-solid fa-wand-magic-sparkles"></i></button><button type="button" class="btn-table-action" data-action="supplier-save" data-id="${id}" title="${escapeHtml(t('supplier_save_display'))}" style="color:var(--color-success)"><i class="fa-solid fa-floppy-disk"></i></button></div></td>
        </tr>`;
    }).join('');
}

window.toggleSupplierMarginInput = function(id) {
    const select = $(`supplier-margin-type-${id}`);
    const input = $(`supplier-margin-value-${id}`);
    if (select && input) input.disabled = select.value === 'inherit';
};

window.saveSupplierProduct = async function(id) {
    const enabled = Boolean($(`supplier-enabled-${id}`)?.checked);
    const marginType = $(`supplier-margin-type-${id}`)?.value || 'inherit';
    const rawValue = $(`supplier-margin-value-${id}`)?.value;
    try {
        showLoading(true);
        await apiCall(`/api/supplier-bots/${encodeURIComponent(state.activeSupplierCode)}/products/${id}`, 'PUT', {enabled, margin_type: marginType, margin_value: marginType === 'inherit' ? null : Number(rawValue || 0)});
        await Promise.all([loadSupplierBot(), loadProducts()]);
        showToast(t('supplier_product_updated'), 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
};

window.openSupplierDescriptionEditor = function(id) {
    const product = (state.supplierBot?.products || []).find(item => Number(item.id) === Number(id));
    if (!product || !DOM.supplierDescriptionModal) {
        showToast(t('supplier_product_missing'), 'error');
        return;
    }
    DOM.supplierDescriptionProductId.value = String(id);
    DOM.supplierDescriptionTitle.textContent = tf('supplier_customize_title', {product:product.display_name || product.name || t('common_product')});
    DOM.supplierDescriptionSource.textContent = product.description || t('supplier_no_description');
    DOM.supplierCustomName.value = product.custom_name || '';
    DOM.supplierCustomEmoji.value = product.custom_emoji || '';
    DOM.supplierCustomEmojiId.value = product.custom_emoji_id || '';
    DOM.supplierCustomImageUrl.value = product.custom_image_url || '';
    DOM.supplierDescriptionEn.value = product.description_en || '';
    DOM.supplierDescriptionFr.value = product.description_fr || '';
    DOM.supplierDescriptionAr.value = product.description_ar || '';
    DOM.supplierDescriptionZh.value = product.description_zh || '';
    DOM.supplierDescriptionVi.value = product.description_vi || '';
    DOM.supplierDescriptionRu.value = product.description_ru || '';
    showModal(DOM.supplierDescriptionModal);
};

async function autoTranslateSupplierDescription() {
    const source = (DOM.supplierDescriptionEn?.value || DOM.supplierDescriptionSource?.textContent || '').trim();
    if (!source || source === t('supplier_no_description')) {
        showToast(t('supplier_nothing_translate'), 'error');
        return;
    }
    const button = DOM.supplierAutoTranslate;
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtml(t('supplier_translating'))}`;
    try {
        const translated = await apiCall('/api/translate', 'POST', {text: source});
        if (translated.en) DOM.supplierDescriptionEn.value = translated.en;
        if (translated.fr) DOM.supplierDescriptionFr.value = translated.fr;
        if (translated.ar) DOM.supplierDescriptionAr.value = translated.ar;
        if (translated.zh) DOM.supplierDescriptionZh.value = translated.zh;
        if (translated.vi) DOM.supplierDescriptionVi.value = translated.vi;
        if (translated.ru) DOM.supplierDescriptionRu.value = translated.ru;
        showToast(t('supplier_translation_done'), 'success');
    } catch (error) {
        showToast(tf('supplier_translation_failed', {message:error.message}), 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = original;
    }
}

async function saveSupplierDescriptions(event) {
    event.preventDefault();
    const id = Number(DOM.supplierDescriptionProductId?.value || 0);
    if (!id) {
        showToast(t('supplier_product_missing'), 'error');
        return;
    }
    const descriptions = {
        en: DOM.supplierDescriptionEn.value,
        fr: DOM.supplierDescriptionFr.value,
        ar: DOM.supplierDescriptionAr.value,
        zh: DOM.supplierDescriptionZh.value,
        vi: DOM.supplierDescriptionVi.value,
        ru: DOM.supplierDescriptionRu.value,
    };
    try {
        showLoading(true);
        await apiCall(`/api/supplier-bots/${encodeURIComponent(state.activeSupplierCode)}/products/${id}/descriptions`, 'PUT', {
            descriptions,
            custom_name: DOM.supplierCustomName.value,
            custom_emoji: DOM.supplierCustomEmoji.value,
            custom_emoji_id: DOM.supplierCustomEmojiId.value,
            custom_image_url: DOM.supplierCustomImageUrl.value,
        });
        hideModal(DOM.supplierDescriptionModal);
        await Promise.all([loadSupplierBot(), loadProducts()]);
        showToast(t('supplier_customization_saved'), 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function saveSupplierSettings(event) {
    event.preventDefault();
    try {
        showLoading(true);
        const payload = {enabled: Boolean(DOM.supplierEnabled.checked), display_name: DOM.supplierDisplayName?.value || '', margin_type: DOM.supplierMarginType.value, margin_value: Number(DOM.supplierMarginValue.value || 0)};
        if (!DOM.supplierRateGroup?.classList.contains('hidden')) payload.units_per_usd = Number(DOM.supplierUnitsPerUsd.value || 1);
        await apiCall(`/api/supplier-bots/${encodeURIComponent(state.activeSupplierCode)}/settings`, 'PUT', payload);
        await Promise.all([loadSupplierBot(), loadProducts()]);
        showToast(t('supplier_settings_saved'), 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function syncSupplierBot() {
    try {
        showLoading(true);
        const result = await apiCall(`/api/supplier-bots/${encodeURIComponent(state.activeSupplierCode)}/sync`, 'POST');
        await Promise.all([loadSupplierBot(), loadProducts()]);
        showToast(tf('supplier_sync_done', {count:Number(result.synced || 0)}), 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function loadSupplierRoutes() {
    if (!DOM.supplierRouterBody) return;
    try {
        const data = await apiCall('/api/supplier-router/routes');
        state.supplierRoutes = data.routes || [];
        renderSupplierRoutes();
    } catch (error) {
        DOM.supplierRouterBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(error.message || t('supplier_routes_load_failed'))}</td></tr>`;
    }
}

function renderSupplierRoutes() {
    const routes = state.supplierRoutes || [];
    if (DOM.supplierRouterProposed) DOM.supplierRouterProposed.textContent = routes.filter(route => route.status === 'proposed').length;
    if (DOM.supplierRouterConfirmed) DOM.supplierRouterConfirmed.textContent = routes.filter(route => route.status === 'confirmed').length;
    if (!routes.length) {
        DOM.supplierRouterBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(t('supplier_no_routes'))}</td></tr>`;
        return;
    }
    DOM.supplierRouterBody.innerHTML = routes.map(route => {
        const status = String(route.status || 'proposed');
        const statusLabel = status === 'confirmed' ? t('supplier_route_active') : status === 'rejected' ? t('supplier_route_rejected') : t('supplier_route_review');
        const actions = status === 'proposed'
            ? `<div class="table-actions"><button class="btn-table-action router-accept" type="button" data-action="supplier-route" data-id="${Number(route.id)}" data-status="confirmed" title="${escapeHtml(t('supplier_route_confirm'))}"><i class="fa-solid fa-check"></i></button><button class="btn-table-action router-reject" type="button" data-action="supplier-route" data-id="${Number(route.id)}" data-status="rejected" title="${escapeHtml(t('supplier_route_reject'))}"><i class="fa-solid fa-xmark"></i></button></div>`
            : status === 'confirmed'
                ? `<button class="btn-table-action router-reject" type="button" data-action="supplier-route" data-id="${Number(route.id)}" data-status="rejected" title="${escapeHtml(t('supplier_route_disable'))}"><i class="fa-solid fa-ban"></i></button>`
                : '-';
        return `<tr>
            <td><strong>${escapeHtml(route.local_product_name || '?')}</strong><small>${escapeHtml(route.anchor_supplier_code || '')}</small></td>
            <td><strong>${escapeHtml(route.candidate_name || '?')}</strong><small>${escapeHtml(route.candidate_supplier_code || '')} · ID ${escapeHtml(route.external_product_id || '')}</small></td>
            <td><strong>$${Number(route.candidate_price || 0).toFixed(2)}</strong><small>Vente $${Number(route.sale_price || 0).toFixed(2)} · stock ${Number(route.candidate_stock || 0)}</small></td>
            <td><strong>${Math.round(Number(route.confidence || 0) * 100)}%</strong><small>${escapeHtml(route.match_source || '')}</small></td>
            <td><span class="status-badge supplier-route-${escapeHtml(status)}">${statusLabel}</span></td>
            <td>${actions}</td>
        </tr>`;
    }).join('');
}

async function scanSupplierRoutes() {
    const button = DOM.btnSupplierRouterScan;
    const original = button?.innerHTML;
    try {
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyse en cours';
        }
        const result = await apiCall('/api/supplier-router/propose', 'POST', {use_ai:true, max_pairs:80});
        await loadSupplierRoutes();
        showToast(`${Number(result.proposals || 0)} rapprochement(s) propose(s).`, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = original;
        }
    }
}

window.reviewSupplierRoute = async function(routeId, status) {
    const action = status === 'confirmed' ? 'activer' : 'desactiver';
    if (!window.confirm(`Confirmer : ${action} cette route fournisseur ?`)) return;
    try {
        await apiCall(`/api/supplier-router/routes/${Number(routeId)}`, 'PUT', {status});
        await Promise.all([loadSupplierRoutes(), loadProducts()]);
        showToast('Route fournisseur mise a jour.', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
};

function aiSupplierErrorMessage(error, fallbackKey='ai_error_default') {
    const message = String(error?.message || '').trim();
    const translations = {
        SEARCH_QUERY_REQUIRED: 'ai_error_query_required',
        INVALID_DURATION: 'ai_error_duration',
        INVALID_SEARCH_FILTER: 'ai_error_filter',
        NO_CONFIGURED_SUPPLIERS: 'ai_error_no_suppliers',
        SUPPLIER_ANALYSIS_IN_PROGRESS: 'ai_error_analysis_running',
        SUPPLIER_SYNC_IN_PROGRESS: 'ai_error_sync_running',
        'Supplier AI job not found': 'ai_error_job_missing',
        'Sync job not found': 'ai_error_sync_missing',
        'Internal server error': 'ai_error_server',
    };
    const match = Object.entries(translations).find(([technicalMessage]) => message.includes(technicalMessage));
    return t(match ? match[1] : fallbackKey);
}

function renderAiSupplierJob(job) {
    if (!DOM.aiSyncProgressPanel) return;
    const active = job && ['queued', 'running'].includes(String(job.status || ''));
    DOM.aiSyncProgressPanel.classList.toggle('hidden', !active);
    if (DOM.btnAiSupplierSync) DOM.btnAiSupplierSync.disabled = Boolean(active);
    if (DOM.btnAiSupplierAnalyze) DOM.btnAiSupplierAnalyze.disabled = Boolean(active);
    if (!job) {
        DOM.aiSyncState.textContent = t('ai_status_ready');
        return;
    }
    const isAnalysis = job.kind === 'analysis';
    const done = Number(job.done || job.sent || 0);
    const failed = Number(job.failed || 0);
    const total = Math.max(0, Number(job.total || 0));
    const processed = Math.min(total, done + failed);
    const percent = total ? Math.round(processed / total * 100) : 0;
    const statusKeys = {
        completed: 'ai_status_completed',
        failed: 'ai_status_failed',
        queued: 'ai_status_waiting',
    };
    DOM.aiSyncState.textContent = job.status === 'running'
        ? t(isAnalysis ? 'ai_status_analysis_running' : 'ai_status_sync_running')
        : t(statusKeys[job.status] || 'ai_status_waiting');
    const failures = failed ? tf('ai_failures', {count: failed}) : '';
    DOM.aiSyncProgressLabel.textContent = tf('ai_progress', {
        operation: t(isAnalysis ? 'ai_operation_analysis' : 'ai_operation_sync'),
        processed,
        total,
        failures,
    });
    DOM.aiSyncProgressValue.textContent = `${percent}%`;
    DOM.aiSyncProgressBar.style.width = `${percent}%`;
}

function renderAiSupplierStatusData(data) {
    if (!data || !DOM.aiSupplierCount) return;
    DOM.aiSupplierCount.textContent = Number(data.configured_suppliers || 0).toLocaleString(currentLocale());
    DOM.aiProductCount.textContent = Number(data.indexed_products || 0).toLocaleString(currentLocale());
    DOM.aiLastAnalysis.textContent = data.last_analysis
        ? parseUTCDate(data.last_analysis).toLocaleString(currentLocale())
        : t('ai_never');
    renderAiSupplierJob(data.job);
}

async function loadAiSupplierStatus() {
    if (!DOM.aiSupplierCount) return;
    try {
        const data = await apiCall('/api/ai-supplier/status');
        state.aiSupplierStatus = data;
        renderAiSupplierStatusData(data);
        if (data.job && ['queued', 'running'].includes(String(data.job.status || ''))) {
            pollAiSupplierJob(data.job.job_id);
        }
    } catch (error) {
        DOM.aiSyncState.textContent = t('ai_status_unavailable');
        console.error('AI supplier status failed:', error);
    }
}

function pollAiSupplierJob(jobId) {
    if (!jobId) return;
    state.aiSupplierJobId = jobId;
    if (state.aiSupplierSyncTimer) clearInterval(state.aiSupplierSyncTimer);
    const poll = async () => {
        try {
            const job = await apiCall(`/api/ai-supplier/job/${encodeURIComponent(jobId)}`);
            renderAiSupplierJob(job);
            if (['completed', 'failed'].includes(String(job.status || ''))) {
                clearInterval(state.aiSupplierSyncTimer);
                state.aiSupplierSyncTimer = null;
                state.aiSupplierJobId = null;
                await loadAiSupplierStatus();
                if (job.status === 'completed' && job.kind === 'analysis') {
                    await loadAiSupplierGroups();
                    showToast(t('ai_analysis_done'), 'success');
                } else if (job.status === 'completed') {
                    showToast(t('ai_sync_done'), 'success');
                } else {
                    showToast(t(job.kind === 'analysis' ? 'ai_analysis_failed' : 'ai_sync_failed'), 'error');
                }
            }
        } catch (error) {
            console.warn('AI supplier job poll failed:', error);
        }
    };
    void poll();
    state.aiSupplierSyncTimer = setInterval(poll, 2000);
}

async function syncAllAiSuppliers() {
    try {
        const response = await apiCall('/api/ai-supplier/sync', 'POST', {});
        const job = response.job || {};
        renderAiSupplierJob(job);
        pollAiSupplierJob(job.job_id);
        showToast(t(response.created ? 'ai_sync_launched' : 'ai_sync_already'), 'info');
    } catch (error) {
        showToast(aiSupplierErrorMessage(error, 'ai_sync_launch_error'), 'error');
    }
}

async function analyzeAllAiSuppliers() {
    try {
        const response = await apiCall('/api/ai-supplier/analyze', 'POST', {use_ai:true});
        const job = response.job || {};
        renderAiSupplierJob(job);
        pollAiSupplierJob(job.job_id);
        showToast(t(response.created ? 'ai_analysis_launched' : 'ai_analysis_already'), 'info');
    } catch (error) {
        showToast(aiSupplierErrorMessage(error, 'ai_analysis_launch_error'), 'error');
    }
}

function aiDurationLabel(result) {
    if (result.duration_months) {
        const count = Number(result.duration_months);
        const unit = t(count === 1 ? 'ai_month_one' : 'ai_months').toLocaleLowerCase(currentLocale());
        return `${count} ${unit}`;
    }
    if (result.duration_days) {
        const count = Number(result.duration_days);
        const unit = t(count === 1 ? 'ai_day_one' : 'ai_days').toLocaleLowerCase(currentLocale());
        return `${count} ${unit}`;
    }
    return t('ai_duration_unknown');
}

function aiDeliveryLabel(mode) {
    const keys = {
        account: 'ai_account_provided',
        activation: 'ai_customer_activation',
        mixed: 'ai_delivery_mixed',
        unknown: 'ai_delivery_unknown',
    };
    return t(keys[String(mode || 'unknown')] || 'ai_delivery_unknown');
}

function aiAccessLabel(mode) {
    const keys = {
        private: 'ai_private',
        shared: 'ai_shared',
        mixed: 'ai_access_mixed',
        unknown: 'ai_access_unknown',
    };
    return t(keys[String(mode || 'unknown')] || 'ai_access_unknown');
}

function aiWarrantyLabel(days) {
    const warrantyDays = Number(days || 0);
    return warrantyDays ? tf('ai_days_warranty', {days: warrantyDays}) : t('ai_no_warranty');
}

function aiGroupWarrantyLabel(group) {
    const kind = String(group.warranty_kind || 'none');
    if (kind === 'mixed') return t('ai_mixed_warranties');
    if (kind === 'full') return t('ai_full_warranty');
    if (kind === 'none') return t('ai_no_warranty');
    if (kind.startsWith('limited:')) {
        return tf('ai_limited_warranty', {days: Number(kind.split(':')[1] || 0)});
    }
    return t('ai_no_warranty');
}

function aiGroupSignature(group) {
    const parts = [aiDurationLabel(group), aiGroupWarrantyLabel(group)];
    const delivery = String(group.delivery_mode || 'unknown');
    const access = String(group.access_mode || 'unknown');
    const region = String(group.region || '');
    if (delivery !== 'unknown') parts.push(aiDeliveryLabel(delivery));
    if (access !== 'unknown') parts.push(aiAccessLabel(access));
    if (region === 'MIXED') parts.push(t('ai_regions_mixed'));
    else if (region) parts.push(region);
    return parts.filter(Boolean).join(' · ');
}

function renderAiSupplierGroups(data) {
    const groups = data.groups || [];
    state.aiSupplierGroups = groups;
    state.aiSupplierGroupData = data;
    if (!groups.length) {
        DOM.aiGroupsSummary.textContent = t('ai_no_groups');
        DOM.aiGroupsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="6" class="empty-state">${escapeHtml(t('ai_no_products_analyzed'))}</td></tr>`;
        return;
    }
    DOM.aiGroupsSummary.textContent = tf('ai_group_summary', {
        available: Number(data.available_products || 0).toLocaleString(currentLocale()),
        groups: groups.length.toLocaleString(currentLocale()),
        comparison: Number(data.comparison_groups || 0).toLocaleString(currentLocale()),
    });
    DOM.aiGroupsBody.innerHTML = groups.map((group, index) => {
        const offers = group.offers || [];
        const best = offers[0] || {};
        const offerCount = Number(group.offer_count || offers.length);
        const alternatives = Math.max(0, offerCount - 1);
        const details = offers.map((offer, offerIndex) => {
            const affordable = Number(offer.affordable_stock || 0);
            const attributes = [
                aiWarrantyLabel(offer.warranty_days),
                aiDeliveryLabel(offer.delivery_mode),
                aiAccessLabel(offer.access_mode),
                offer.region || '',
            ].filter(Boolean).join(' · ');
            const rank = offerIndex === 0
                ? `<i class="fa-solid fa-crown" title="${escapeHtml(t('ai_cheapest'))}"></i>`
                : `#${offerIndex + 1}`;
            return `<div class="ai-group-offer">
                <span class="ai-group-offer-rank">${rank}</span>
                <span class="ai-group-offer-product"><strong>${escapeHtml(offer.name || '?')}</strong><small>${escapeHtml(attributes)}</small></span>
                <span class="ai-group-offer-supplier"><strong>${escapeHtml(offer.supplier_name || offer.supplier_code || '?')}</strong><small>${escapeHtml(tf('ai_supplier_balance', {balance: Number(offer.wallet_balance || 0).toFixed(2)}))}</small></span>
                <strong class="ai-group-offer-price">$${Number(offer.price || 0).toFixed(2)}</strong>
                <span class="ai-group-offer-stock ${affordable > 0 ? '' : 'is-unfunded'}"><strong>${affordable}/${Number(offer.remote_stock || 0)}</strong><small>${escapeHtml(t('ai_stock_ratio'))}</small></span>
                <button class="btn-table-action ai-group-offer-action" type="button" data-action="ai-open-supplier" data-code="${escapeHtml(offer.supplier_code || '')}" title="${escapeHtml(t('ai_open_supplier'))}"><i class="fa-solid fa-arrow-up-right-from-square"></i><span class="ai-mobile-action-label">${escapeHtml(t('ai_open_supplier'))}</span></button>
            </div>`;
        }).join('');
        const classification = group.comparable
            ? tf('ai_comparable_offers', {count: offerCount})
            : t('ai_classification_incomplete');
        return `<tr id="ai-group-row-${index}" class="ai-group-row">
            <td class="ai-group-title" data-label="${escapeHtml(t('ai_col_group'))}"><strong>${escapeHtml(group.label || t('ai_col_product'))}</strong><small>${escapeHtml(classification)}</small></td>
            <td class="ai-group-signature" data-label="${escapeHtml(t('ai_col_characteristics'))}">${escapeHtml(aiGroupSignature(group))}</td>
            <td class="ai-group-best" data-label="${escapeHtml(t('ai_col_best_offer'))}"><strong class="ai-group-best-price">$${Number(group.best_price || 0).toFixed(2)}</strong><small>${escapeHtml(best.supplier_name || best.supplier_code || '?')}</small></td>
            <td class="ai-group-alternatives" data-label="${escapeHtml(t('ai_col_alternatives'))}"><strong>${alternatives}</strong></td>
            <td class="ai-group-saving" data-label="${escapeHtml(t('ai_col_max_difference'))}"><strong>$${Number(group.max_saving || 0).toFixed(2)}</strong></td>
            <td class="ai-group-action"><button id="ai-group-toggle-${index}" class="btn-table-action" type="button" data-action="ai-toggle-group" data-index="${index}" title="${escapeHtml(t('ai_show_all_offers'))}"><i class="fa-solid fa-chevron-down"></i><span class="ai-mobile-action-label">${escapeHtml(t('ai_show_all_offers'))}</span></button></td>
        </tr>
        <tr id="ai-group-details-${index}" class="ai-group-details hidden"><td colspan="6"><div class="ai-group-offers">${details}</div></td></tr>`;
    }).join('');
}

async function loadAiSupplierGroups() {
    if (!DOM.aiGroupsBody) return;
    if (!state.aiSupplierGroups.length) {
        DOM.aiGroupsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="6" class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtml(t('ai_groups_loading'))}</td></tr>`;
    }
    try {
        renderAiSupplierGroups(await apiCall('/api/ai-supplier/groups'));
    } catch (error) {
        DOM.aiGroupsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="6" class="empty-state">${escapeHtml(aiSupplierErrorMessage(error, 'ai_groups_unavailable'))}</td></tr>`;
        console.error('AI supplier groups failed:', error);
    }
}

window.toggleAiSupplierGroup = function(index) {
    const details = $(`ai-group-details-${index}`);
    const button = $(`ai-group-toggle-${index}`);
    const row = $(`ai-group-row-${index}`);
    if (!details || !button) return;
    const opening = details.classList.contains('hidden');
    details.classList.toggle('hidden', !opening);
    if (row) row.classList.toggle('is-open', opening);
    const icon = button.querySelector('i');
    if (icon) icon.className = opening ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
    button.title = t(opening ? 'ai_hide_offers' : 'ai_show_all_offers');
    const label = button.querySelector('.ai-mobile-action-label');
    if (label) label.textContent = t(opening ? 'ai_hide_offers' : 'ai_show_all_offers');
};

function aiResultReason(result) {
    const affordable = Number(result.affordable_stock || 0);
    const parts = [
        t('ai_reason_compliant'),
        tf('ai_reason_reliability', {percent: Math.round(Number(result.reliability || 0) * 100)}),
        affordable > 0
            ? tf('ai_reason_affordable', {count: affordable})
            : t('ai_reason_unfunded'),
    ];
    return parts.join(' · ');
}

function renderAiSupplierResults(data) {
    const results = data.results || [];
    const hiddenUnfunded = Number(data.hidden_unfunded_count || 0);
    state.aiSupplierResults = results;
    state.aiSupplierResultData = data;
    DOM.aiResultsSummary.textContent = results.length
        ? tf('ai_results_summary', {count: results.length.toLocaleString(currentLocale())})
        : hiddenUnfunded > 0
            ? tf('ai_hidden_summary', {count: hiddenUnfunded.toLocaleString(currentLocale())})
            : t('ai_no_criteria');
    if (!results.length) {
        const message = t(hiddenUnfunded > 0 ? 'ai_unfunded_exists' : 'ai_no_result');
        DOM.aiResultsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="9" class="empty-state">${escapeHtml(message)}</td></tr>`;
        return;
    }
    DOM.aiResultsBody.innerHTML = results.map((result, index) => {
        const affordable = Number(result.affordable_stock || 0);
        const stockClass = affordable > 0 ? '' : 'ai-result-warning';
        const freshness = Number(result.freshness_hours || 0);
        const freshnessLabel = freshness >= 9999
            ? t('ai_sync_unknown')
            : freshness < 1
                ? t('ai_sync_recent')
                : tf('ai_sync_hours', {hours: Math.round(freshness)});
        const warrantyDays = Number(result.warranty_days || 0);
        const connectionState = result.supplier_enabled ? '' : ` · ${t('ai_connection_disabled')}`;
        return `<tr class="ai-result-row">
            <td class="ai-result-rank ${index === 0 ? 'ai-result-best' : ''}">${index === 0 ? '<i class="fa-solid fa-crown"></i> 1' : index + 1}</td>
            <td class="ai-result-product" data-label="${escapeHtml(t('ai_col_product'))}"><strong>${escapeHtml(result.name || '?')}</strong><small>${escapeHtml(aiDurationLabel(result))} · ${escapeHtml(aiDeliveryLabel(result.delivery_mode))} · ${escapeHtml(aiAccessLabel(result.access_mode))}</small></td>
            <td class="ai-result-supplier" data-label="${escapeHtml(t('ai_col_supplier'))}"><strong>${escapeHtml(result.supplier_name || result.supplier_code)}</strong><small>${escapeHtml(result.supplier_code || '')}${escapeHtml(connectionState)}</small></td>
            <td class="ai-result-price" data-label="${escapeHtml(t('ai_col_price'))}"><strong>$${Number(result.price || 0).toFixed(2)}</strong><span class="table-secondary">${escapeHtml(tf('ai_balance', {balance: Number(result.wallet_balance || 0).toFixed(2)}))}</span></td>
            <td class="ai-result-warranty" data-label="${escapeHtml(t('ai_col_warranty'))}"><strong>${escapeHtml(warrantyDays ? tf('ai_warranty_days', {days: warrantyDays}) : t('ai_no_warranty'))}</strong></td>
            <td class="ai-result-stock ${stockClass}" data-label="${escapeHtml(t('ai_col_stock'))}"><strong>${affordable}/${Number(result.remote_stock || 0)}</strong><span class="table-secondary">${escapeHtml(t('ai_stock_ratio'))}</span></td>
            <td class="ai-result-reliability" data-label="${escapeHtml(t('ai_col_reliability'))}"><strong>${Math.round(Number(result.reliability || 0) * 100)}%</strong><span class="table-secondary">${escapeHtml(freshnessLabel)}</span></td>
            <td class="ai-result-analysis" data-label="${escapeHtml(t('ai_col_analysis'))}"><strong>${Math.round(Number(result.confidence || 0) * 100)}%</strong><small>${escapeHtml(aiResultReason(result))}</small></td>
            <td class="ai-result-action"><button class="btn-table-action" type="button" data-action="ai-open-supplier" data-code="${escapeHtml(result.supplier_code || '')}" title="${escapeHtml(t('ai_open_supplier'))}"><i class="fa-solid fa-arrow-up-right-from-square"></i><span class="ai-mobile-action-label">${escapeHtml(t('ai_open_supplier'))}</span></button></td>
        </tr>`;
    }).join('');
}

function rerenderAiSupplierContent() {
    if (state.aiSupplierStatus) renderAiSupplierStatusData(state.aiSupplierStatus);
    if (state.aiSupplierGroupData) renderAiSupplierGroups(state.aiSupplierGroupData);
    if (state.aiSupplierResultData) renderAiSupplierResults(state.aiSupplierResultData);
}

async function searchAiSuppliers(event) {
    event?.preventDefault();
    const payload = {
        query: DOM.aiSupplierQuery.value.trim(),
        duration_value: DOM.aiDurationValue.value ? Number(DOM.aiDurationValue.value) : null,
        duration_unit: DOM.aiDurationUnit.value,
        min_warranty_days: Number(DOM.aiWarrantyFilter.value || 0),
        delivery_mode: DOM.aiDeliveryFilter.value,
        access_mode: DOM.aiAccessFilter.value,
        max_price: DOM.aiMaxPrice.value ? Number(DOM.aiMaxPrice.value) : null,
        include_unfunded: DOM.aiIncludeUnfunded.checked,
        limit: 30,
    };
    DOM.aiResultsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="9" class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtml(t('ai_searching'))}</td></tr>`;
    try {
        const data = await apiCall('/api/ai-supplier/search', 'POST', payload);
        renderAiSupplierResults(data);
    } catch (error) {
        const message = aiSupplierErrorMessage(error, 'ai_search_unavailable');
        DOM.aiResultsBody.innerHTML = `<tr class="ai-empty-row"><td colspan="9" class="empty-state">${escapeHtml(message)}</td></tr>`;
        showToast(message, 'error');
    }
}

window.openAiSupplier = function(supplierCode) {
    state.activeSupplierCode = String(supplierCode || 'canboso');
    state.supplierBot = null;
    switchTab('supplier-bots-tab');
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
        DOM.openTicketsContainer.innerHTML = tks.map(tk => `<div class="ticket-card glass-panel"><div class="ticket-header"><h3>Ticket #${Number(tk.id)}</h3><p><i class="fa-solid fa-user"></i> <code>${escapeHtml(tk.user_telegram_id)}</code></p></div><div class="ticket-message"><p>${escapeHtml(tk.message)}</p></div><form class="ticket-reply-form" data-submit-action="ticket-reply" data-id="${Number(tk.id)}"><div class="form-group"><input type="text" placeholder="${escapeHtml(t('reply_placeholder'))}" required></div><button type="submit" class="btn-primary btn-send-reply" title="Répondre"><i class="fa-solid fa-paper-plane"></i></button></form></div>`).join('');
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
                const refCount = u.referrals_count > 0 ? `${Number(u.referrals_count)} <button class="btn-table-action" data-action="user-referrals" data-id="${Number(u.telegram_id)}" data-stop-propagation="true" title="Voir les filleuls" style="margin-left:5px;color:#3b82f6;"><i class="fa-solid fa-users"></i></button>` : 0;
                const refEarnings = parseFloat(u.referral_earnings||0).toFixed(2);
                return `<tr class="user-row" data-action="user-purchases" data-id="${Number(u.telegram_id)}" title="Voir les achats"><td><code>${escapeHtml(u.telegram_id)}</code></td><td>${escapeHtml(u.username||'—')}</td><td>${escapeHtml(u.first_name||'—')}</td><td>${escapeHtml(u.language||'fr')}</td><td>${Number(u.total_orders||0)}</td><td>$${parseFloat(u.total_spent||0).toFixed(2)}</td><td>$${wb}</td><td>${refBy}</td><td>${refCount}</td><td>$${refEarnings}</td><td>${escapeHtml(d)}</td><td><button class="btn-table-action" data-action="user-purchases" data-id="${Number(u.telegram_id)}" data-stop-propagation="true" title="Voir les achats" style="color:#60a5fa;"><i class="fa-solid fa-bag-shopping"></i></button> <button class="btn-table-action" data-action="user-credit" data-id="${Number(u.telegram_id)}" data-stop-propagation="true" title="Créditer" style="color:#22c55e;"><i class="fa-solid fa-circle-plus"></i></button> <button class="btn-table-action" data-action="user-debit" data-id="${Number(u.telegram_id)}" data-stop-propagation="true" title="Retirer" style="color:#ef4444;"><i class="fa-solid fa-circle-minus"></i></button> ${banned?`<span class="status-badge banned">${escapeHtml(t('banned'))}</span> <button class="btn-table-action unban" data-action="user-unban" data-id="${Number(u.telegram_id)}" data-stop-propagation="true"><i class="fa-solid fa-lock-open"></i></button>`:`<button class="btn-table-action ban" data-action="user-ban" data-id="${Number(u.telegram_id)}" data-stop-propagation="true"><i class="fa-solid fa-ban"></i></button>`}</td></tr>`;
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

function userPurchaseStatus(status) {
    const labels = {
        COMPLETED:'Terminée', PENDING:'En attente', AWAITING_PAYMENT:'Paiement attendu',
        PROCESSING:'En traitement', PAID_PENDING_DELIVERY:'Livraison en attente',
        AWAITING_ACTIVATION:'Activation à traiter', AWAITING_ACTIVATION_INFO:'Identifiant attendu',
        CANCELLED:'Annulée'
    };
    return labels[status] || status || '—';
}

function userPurchasePayment(method) {
    const labels = {
        wallet:'Wallet', binance:'Binance Pay', nowpayments_bep20:'BEP20',
        trc20:'TRC20', admin:'Admin'
    };
    return labels[method] || method || '—';
}

async function loadUserPurchases() {
    const telegramId = state.userPurchasesTelegramId;
    if (!telegramId || !DOM.userPurchasesBody) return;
    const limit = state.userPurchasesPerPage || 10;
    const offset = (state.userPurchasesPage || 0) * limit;
    DOM.userPurchasesBody.innerHTML = '<tr><td colspan="8" class="empty-state">Chargement...</td></tr>';
    try {
        const data = await apiCall(`/api/users/${telegramId}/orders?limit=${limit}&offset=${offset}`);
        const user = data.user || {};
        const orders = Array.isArray(data.orders) ? data.orders : [];
        const total = Number(data.total || 0);
        const totalPages = Math.max(1, Math.ceil(total / limit));
        if (state.userPurchasesPage >= totalPages && state.userPurchasesPage > 0) {
            state.userPurchasesPage = totalPages - 1;
            return loadUserPurchases();
        }

        const username = user.username ? `@${user.username}` : 'sans username';
        DOM.userPurchasesIdentity.textContent = `${user.first_name || 'Client'} · ${username} · ID ${user.telegram_id}`;
        DOM.userPurchasesTotal.textContent = total.toLocaleString();
        DOM.userPurchasesSpent.textContent = `$${Number(user.total_spent || 0).toFixed(2)}`;
        DOM.userPurchasesWallet.textContent = `$${Number(user.wallet_balance || 0).toFixed(2)}`;
        DOM.userPurchasesJoined.textContent = user.created_at ? parseUTCDate(user.created_at).toLocaleDateString() : '—';
        state.userPurchaseOrders = orders;
        state.userPurchaseUser = user;

        DOM.userPurchasesBody.innerHTML = orders.length ? orders.map(order => {
            const product = `${order.product_emoji || '📦'} ${order.product_name || `Produit #${order.product_id}`}`.trim();
            const orderNo = escapeHtml(order.merchant_trade_no || '—');
            const date = order.created_at ? parseUTCDate(order.created_at).toLocaleString([], {dateStyle:'short', timeStyle:'short'}) : '—';
            const status = escapeHtml(String(order.status || ''));
            const detail = order.status === 'COMPLETED'
                ? `<button type="button" class="btn-table-action" data-action="user-purchase-order" data-id="${Number(order.id)}" title="Voir les articles livrés"><i class="fa-solid fa-eye"></i></button>`
                : '—';
            return `<tr>
                <td><strong>#${Number(order.id)}</strong><br><small><code>${orderNo}</code></small></td>
                <td><span class="user-purchases-product"><strong>${escapeHtml(product)}</strong><small>Produit #${Number(order.product_id || 0)}</small></span></td>
                <td>${Number(order.quantity || 1)}</td>
                <td><strong>$${Number(order.amount_usd || 0).toFixed(2)}</strong></td>
                <td>${escapeHtml(userPurchasePayment(order.payment_method))}</td>
                <td><span class="status-badge ${status.toLowerCase()}">${escapeHtml(userPurchaseStatus(order.status))}</span></td>
                <td>${escapeHtml(date)}</td><td>${detail}</td>
            </tr>`;
        }).join('') : '<tr><td colspan="8" class="empty-state">Aucun achat pour ce client.</td></tr>';

        DOM.userPurchasesPageInfo.textContent = `${state.userPurchasesPage + 1} / ${totalPages}`;
        DOM.userPurchasesPagination.classList.toggle('hidden', totalPages <= 1);
        DOM.userPurchasesPrev.disabled = state.userPurchasesPage <= 0;
        DOM.userPurchasesNext.disabled = state.userPurchasesPage >= totalPages - 1;
    } catch (error) {
        DOM.userPurchasesBody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(error.message)}</td></tr>`;
        showToast('Impossible de charger les achats de ce client.', 'error');
    }
}

window.openUserPurchases = function(telegramId) {
    state.userPurchasesTelegramId = Number(telegramId);
    state.userPurchasesPage = 0;
    DOM.userPurchasesIdentity.textContent = `ID ${telegramId}`;
    showModal(DOM.userPurchasesModal);
    loadUserPurchases();
};

window.openUserPurchaseOrderDetail = function(orderId) {
    const order = (state.userPurchaseOrders || []).find(item => Number(item.id) === Number(orderId));
    if (order) {
        const user = state.userPurchaseUser || {};
        state.orders = [
            ...state.orders.filter(item => Number(item.id) !== Number(orderId)),
            {...order, username:user.username, user_first_name:user.first_name, user_telegram_id:user.telegram_id}
        ];
    }
    hideModal(DOM.userPurchasesModal);
    openOrderDetail(Number(orderId));
};

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
                const isProductPrice = p.discount_type === 'product_price';
                const typeText = p.discount_type === 'percent'
                    ? t('percent')
                    : isProductPrice ? 'Prix produit' : t('fixed');
                const valueText = p.discount_type === 'percent'
                    ? `${Number(p.discount_value)}%`
                    : isProductPrice
                        ? `$${Number(p.discount_value).toFixed(2)} / unite`
                        : `$${Number(p.discount_value).toFixed(2)}`;
                let usesLabel = p.max_uses > 0 ? `${p.used_count}/${p.max_uses}` : `${p.used_count} (${t('unlimited')})`;
                if (p.max_uses_per_user > 0) usesLabel += ` <br><small>(${p.max_uses_per_user}/user)</small>`;
                if (p.max_qty_per_order > 0) usesLabel += ` <br><small>(Max ${p.max_qty_per_order}/cmd)</small>`;
                if (p.applicable_product_ids) usesLabel += ` <br><small>(Produits limités)</small>`;
                const active = p.is_active ? 'active-promo' : 'expired';
                return `<tr><td><strong>${escapeHtml(p.code)}</strong></td><td>${escapeHtml(typeText)}</td><td>${escapeHtml(valueText)}</td><td>${escapeHtml(usesLabel)}</td><td><span class="status-badge ${active}">${escapeHtml(p.is_active?t('active'):t('inactive'))}</span></td><td><button class="btn-table-action delete" data-action="delete-promo" data-id="${Number(p.id)}"><i class="fa-solid fa-trash-can"></i></button></td></tr>`;
            }).join('');
        } else DOM.promosTableBody.innerHTML = `<tr><td colspan="6" class="empty-state">${t('no_promos')}</td></tr>`;
    } catch(e) { console.warn('loadPromos:', e); }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  ACTIONS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

function syncPromoTypeUI() {
    const isProductPrice = $('promo-type')?.value === 'product_price';
    const valueLabel = $('promo-value-label');
    const productsHelp = $('promo-products-help');
    if (valueLabel) valueLabel.textContent = isProductPrice ? 'Prix final unitaire ($)' : 'Valeur';
    if (productsHelp) {
        productsHelp.textContent = isProductPrice
            ? 'Obligatoire : selectionnez exactement un produit.'
            : 'Optionnel pour les reductions classiques.';
    }
    if (isProductPrice) {
        const checked = Array.from(document.querySelectorAll('.promo-product-cb:checked'));
        checked.slice(1).forEach(input => { input.checked = false; });
    }
}

function enforceSinglePromoProduct(changedInput) {
    if ($('promo-type')?.value !== 'product_price' || !changedInput.checked) return;
    document.querySelectorAll('.promo-product-cb').forEach(input => {
        if (input !== changedInput) input.checked = false;
    });
}

async function handleAddPromo(e) {
    e.preventDefault();
    const discountType = $('promo-type').value;
    const selectedProducts = Array.from(document.querySelectorAll('.promo-product-cb:checked'));
    if (discountType === 'product_price' && selectedProducts.length !== 1) {
        showToast('Selectionnez exactement un produit pour ce prix promo.', 'error');
        return;
    }
    showLoading(true);
    try {
        await apiCall('/api/promos', 'POST', {
            code: $('promo-code').value.trim(),
            discount_type: discountType,
            discount_value: $('promo-value').value,
            max_uses: $('promo-max').value || 0,
            max_uses_per_user: $('promo-max-user').value || 0,
            max_qty_per_order: $('promo-max-qty').value || 0,
            applicable_product_ids: selectedProducts.map(input => input.value).join(','),
            expires_at: $('promo-expires').value || null,
        });
        hideModal(DOM.promoModal);
        DOM.addPromoForm.reset();
        await loadPromos();
        showToast('Code promo cree.', 'success');
    } catch (error) {
        showToast(error.message || 'Creation du code promo impossible.', 'error');
    } finally {
        showLoading(false);
    }
}

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
            <button type="button" class="btn-table-action delete" data-action="delete-tier" style="margin-bottom:0.3rem;"><i class="fa-solid fa-trash-can"></i></button>
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
const ORDER_TIMELINE_KEYS = {
    'order.created':'order_event_created',
    'payment.confirmed':'order_event_payment_confirmed',
    'activation.requested':'order_event_activation_requested',
    'activation.completed':'order_event_activation_completed',
    'provider_payment.created':'order_event_provider_created',
    'provider_payment.status':'order_event_provider_status',
    'provider_payment.processed':'order_event_provider_processed',
    'supplier.started':'order_event_supplier_started',
    'supplier.status':'order_event_supplier_status',
    'supplier.completed':'order_event_supplier_completed',
    'stock.reserved':'order_event_stock_reserved',
    'payment_review.action':'order_event_review_action',
};

function renderOrderTimeline(payload) {
    if (!DOM.orderTimelineList) return;
    const events = Array.isArray(payload?.events) ? payload.events : [];
    state.orderDetailTimeline = events;
    if (!events.length) {
        DOM.orderTimelineList.innerHTML = `<p class="empty-state">${escapeHtml(t('order_timeline_empty'))}</p>`;
        return;
    }
    DOM.orderTimelineList.innerHTML = events.map(event => {
        const key = ORDER_TIMELINE_KEYS[event.type];
        const label = key ? t(key) : (event.label || event.type || '—');
        const details = event.details || {};
        const detail = details.provider_status || details.status || details.action
            || (details.item_count ? `${details.item_count} item(s)` : '');
        const when = event.occurred_at
            ? parseUTCDate(event.occurred_at).toLocaleString(currentLocale())
            : '—';
        return `<div class="order-timeline-event">
            <div><strong>${escapeHtml(label)}</strong>${detail ? `<div class="order-timeline-detail">${escapeHtml(String(detail))}</div>` : ''}</div>
            <time>${escapeHtml(when)}</time>
        </div>`;
    }).join('');
}

window.openOrderDetail = async function(orderId) {
    state.orderDetailId = Number(orderId);
    state.orderDetailItems = [];
    state.orderDetailTimeline = [];
    $('order-detail-title').textContent = `Commande #${orderId}`;
    $('order-detail-info').innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Chargement...</p>';
    $('order-items-list').innerHTML = '';
    $('order-items-count').textContent = '...';
    $('btn-download-order-txt').style.display = 'none';
    if (DOM.orderTimelineList) {
        DOM.orderTimelineList.innerHTML = `<p class="empty-state">${escapeHtml(t('order_timeline_loading'))}</p>`;
    }
    showModal(DOM.orderDetailModal);

    try {
        const [data, timeline] = await Promise.all([
            apiCall(`/api/orders/${orderId}/items`),
            apiCall(`/api/orders/${orderId}/timeline`).catch(() => null),
        ]);
        const order = state.orders.find(o => o.id === orderId);
        const prod = order ? state.products.find(p => p.id === order.product_id) : null;
        let pn = prod ? `${prod.emoji || ''} ${prod.name || ''}` : (order ? `#${Number(order.product_id)}` : '?');
        if (order && !prod && order.product_name) {
            pn = `${order.product_emoji || '📦'} ${order.product_name}${order.product_is_deleted ? ' (Supprimé)' : ''}`;
        }
        const uname = order ? (order.username ? `@${order.username}` : (order.user_first_name || order.user_telegram_id)) : '?';
        const orderDate = order ? parseUTCDate(order.created_at).toLocaleString() : '?';
        
        $('order-detail-info').innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.88rem;">
                <div>👤 <strong>Client :</strong> ${escapeHtml(uname)}</div>
                <div>📦 <strong>Produit :</strong> ${escapeHtml(pn)}</div>
                <div>💵 <strong>Montant :</strong> $${order ? parseFloat(order.amount_usd).toFixed(2) : '?'}</div>
                <div>📊 <strong>Quantité :</strong> ${order ? (order.quantity || 1) : '?'}</div>
                <div>📅 <strong>Date :</strong> ${escapeHtml(orderDate)}</div>
                <div>✅ <strong>Statut :</strong> <span class="status-badge completed">${escapeHtml(data.status || '')}</span></div>
            </div>`;

        const items = data.items || [];
        state.orderDetailItems = items;
        $('order-items-count').textContent = items.length;

        if (items.length > 0) {
            const btnDownload = $('btn-download-order-txt');
            btnDownload.style.display = 'inline-block';
            $('order-items-list').innerHTML = items.map((it, i) => {
                const safeData = escapeHtml(it.account_data || '');
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
        if (timeline) renderOrderTimeline(timeline);
        else if (DOM.orderTimelineList) DOM.orderTimelineList.innerHTML = `<p class="empty-state">${escapeHtml(t('order_timeline_unavailable'))}</p>`;
    } catch(e) {
        $('order-detail-info').innerHTML = `<p style="color:var(--color-error);">Erreur: ${escapeHtml(e.message)}</p>`;
        if (DOM.orderTimelineList) DOM.orderTimelineList.innerHTML = `<p class="empty-state">${escapeHtml(t('order_timeline_unavailable'))}</p>`;
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  VIEW REMAINING STOCK MODAL
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
function normalizeStockPage(payload) {
    if (Array.isArray(payload)) {
        const available = payload.filter(item => !item.is_sold).length;
        return { items: payload, total: payload.length, all_total: payload.length, available, sold: payload.length - available };
    }
    return payload || { items: [], total: 0, all_total: 0, available: 0, sold: 0 };
}

function stockRowsMarkup(items, manageable) {
    return items.map(it => {
        const safeData = escapeHtml(it.account_data || '');
        return `<div class="stock-item-row">
            <span class="stock-item-data">${it.is_sold ? '🔴' : '🟢'} ${safeData}</span>
            <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
                <button class="btn-table-action" data-action="expand-stock" title="Voir tout" style="color:#a78bfa;"><i class="fa-solid fa-eye"></i></button>
                <span class="stock-item-status ${it.is_sold ? 'sold' : 'available'}">${it.is_sold ? t('sold') : t('available')}</span>
                ${manageable && !it.is_sold ? `<button class="btn-table-action delete" data-action="delete-stock" data-id="${Number(it.id)}" title="Supprimer"><i class="fa-solid fa-trash-can"></i></button>` : ''}
            </div>
        </div>`;
    }).join('');
}

function renderStockPage(productId, target) {
    const key = `${target}:${productId}`;
    const page = state.stockPages?.[key];
    if (!page) return;
    const manageable = target === 'manage';
    const container = manageable ? DOM.stockItemsList : $('view-stock-list');
    if (manageable) DOM.stockExistingCount.textContent = page.available;
    else $('view-stock-count').textContent = `${page.available} dispo / ${page.sold} vendus`;
    if (!page.items.length) {
        container.innerHTML = `<p class="empty-state">${manageable ? t('no_stock') : 'Aucun article en stock.'}</p>`;
        return;
    }
    const remaining = Math.max(0, Number(page.total || page.all_total || 0) - page.items.length);
    container.innerHTML = stockRowsMarkup(page.items, manageable) + (remaining > 0 ? `
        <button class="btn-secondary" style="width:100%;margin-top:12px;" data-action="load-more-stock" data-product-id="${Number(productId)}" data-target="${target === 'manage' ? 'manage' : 'view'}">
            <i class="fa-solid fa-chevron-down"></i> Afficher plus (${remaining})
        </button>` : '');
}

window.loadMoreProductStock = async function(productId, target) {
    const key = `${target}:${productId}`;
    const current = state.stockPages?.[key];
    if (!current) return;
    try {
        const next = normalizeStockPage(await apiCall(`/api/products/${productId}/stock?limit=200&offset=${current.items.length}`));
        current.items.push(...next.items);
        Object.assign(current, { total: next.total, all_total: next.all_total, available: next.available, sold: next.sold });
        renderStockPage(productId, target);
    } catch (error) {
        showToast(error.message, 'error');
    }
};

function downloadCurrentOrderTxt() {
    const items = Array.isArray(state.orderDetailItems) ? state.orderDetailItems : [];
    if (!items.length || !state.orderDetailId) return;
    const textContent = items.map(item => String(item.account_data || '')).join('\n\n');
    const blob = new Blob([textContent], {type:'text/plain'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `Commande_${state.orderDetailId}_Articles.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
}

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
        state.stockPages = state.stockPages || {};
        state.stockPages[`view:${productId}`] = normalizeStockPage(await apiCall(`/api/products/${productId}/stock?limit=200&offset=0`));
        renderStockPage(productId, 'view');
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
    if ($('edit-prod-delivery-type')) {
        const deliverySelect = $('edit-prod-delivery-type');
        deliverySelect.value = p.delivery_type || 'stock';
        deliverySelect.disabled = p.delivery_type === 'supplier_api';
        deliverySelect.title = p.delivery_type === 'supplier_api'
            ? 'Le type fournisseur API est protégé et ne peut pas être remplacé ici.'
            : '';
    }
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
    const originalProduct = state.products.find(product => Number(product.id) === Number(id));
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
        delivery_type: originalProduct?.delivery_type === 'supplier_api'
            ? 'supplier_api'
            : ($('edit-prod-delivery-type') ? $('edit-prod-delivery-type').value : 'stock'),
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
        const res = await apiCall('/api/recalculate-stats', 'POST');
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
        state.stockPages = state.stockPages || {};
        state.stockPages[`manage:${pid}`] = normalizeStockPage(await apiCall(`/api/products/${pid}/stock?limit=200&offset=0`));
        renderStockPage(pid, 'manage');
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
    reader.addEventListener('load', ev => { DOM.stockTextarea.value = ev.target.result; const n=ev.target.result.split('\n').filter(l=>l.trim()).length; DOM.stockLineCount.textContent=`${n} ${t('accounts_detected')}`; });
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
        
        let result = r;
        if (r.job_id) {
            for (let poll = 0; poll < 600 && ['queued', 'running'].includes(result.status); poll++) {
                DOM.broadcastResult.textContent = `En cours : ${Number(result.sent || 0)}/${Number(result.total || 0)} | Echecs : ${Number(result.failed || 0)}`;
                await new Promise(resolve => setTimeout(resolve, 1000));
                result = await apiCall(`/api/broadcast/${encodeURIComponent(r.job_id)}`);
            }
            if (result.status === 'failed') throw new Error(result.error || 'Le broadcast a echoue.');
            if (result.status !== 'completed') throw new Error('Le suivi du broadcast a expire. L\'envoi peut encore etre en cours.');
            DOM.broadcastResult.textContent = `${t('broadcast_sent').replace('{sent}',result.sent).replace('{total}',result.total)} | ${t('broadcast_failed').replace('{failed}',result.failed)}`;
        }

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

const tabKeys = { 'dashboard-tab':'tab_dashboard','stats-tab':'tab_stats','inventory-tab':'tab_inventory','orders-tab':'tab_orders','payment-review-tab':'payment_review_title','activations-tab':'nav_activations','resellers-tab':'nav_resellers','supplier-bots-tab':'nav_supplier_bots','ai-bot-tab':'nav_ai_bot','game-tab':'tab_game','users-tab':'tab_users','tickets-tab':'tab_tickets','broadcast-tab':'tab_broadcast','settings-tab':'tab_settings','wallet-history-tab':'nav_wallet_history','finance-tab':'tab_finance','binance-tab':'tab_binance' };
const tabContextKeys = {
    'dashboard-tab':'context_dashboard', 'stats-tab':'context_stats', 'inventory-tab':'context_inventory',
    'orders-tab':'context_orders', 'payment-review-tab':'context_payment_review', 'activations-tab':'context_activations',
    'finance-tab':'context_finance', 'wallet-history-tab':'context_wallet', 'users-tab':'context_users',
    'tickets-tab':'context_tickets', 'resellers-tab':'context_resellers', 'supplier-bots-tab':'context_suppliers',
    'ai-bot-tab':'context_ai', 'game-tab':'context_game', 'binance-tab':'context_binance',
    'broadcast-tab':'context_broadcast', 'settings-tab':'context_settings'
};

function updateCurrentTabLabels() {
    if (DOM.currentTabTitle) DOM.currentTabTitle.textContent = t(tabKeys[state.currentTab] || 'tab_dashboard');
    if (DOM.pageContext) {
        DOM.pageContext.textContent = t(tabContextKeys[state.currentTab] || 'context_dashboard');
    }
}

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
    const ac = $(tabId);
    if (!ac || !ac.classList.contains('tab-content')) return;
    if (state.currentTab === tabId && ac.classList.contains('active')) return;
    state.tabScrollPositions[state.currentTab] = window.scrollY;
    $$('.menu-item').forEach(i=>{ i.classList.remove('active'); i.removeAttribute('aria-current'); });
    $$('.tab-content').forEach(c=>c.classList.remove('active'));
    const ai = document.querySelector(`.menu-item[data-tab="${tabId}"]`);
    if(ai) { ai.classList.add('active'); ai.setAttribute('aria-current', 'page'); }
    ac.classList.add('active');
    state.currentTab = tabId;
    updateCurrentTabLabels();
    clearPageStatus();
    requestAnimationFrame(() => window.scrollTo({top:Number(state.tabScrollPositions[tabId] || 0), behavior:'auto'}));
    if (!DOM.appContainer.classList.contains('hidden')) {
        void refreshData({tabId, useCache:true, silent:Boolean(state.tabLoadedAt[tabId])});
    }
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
function renderPageStatus(type, message) {
    if (!DOM.pageStatusRegion) return;
    const icon = type === 'error' ? 'triangle-exclamation' : type === 'success' ? 'circle-check' : 'circle-info';
    DOM.pageStatusRegion.className = `page-status-region ${type}`;
    DOM.pageStatusRegion.innerHTML = `<div class="page-status-message ${type}"><i class="fa-solid fa-${icon}"></i><p>${escapeHtml(message)}</p>${type === 'error' ? `<button type="button" class="btn-secondary btn-sm" data-action="retry-tab"><i class="fa-solid fa-rotate"></i><span>${escapeHtml(t('retry'))}</span></button>` : ''}</div>`;
}

function clearPageStatus() {
    if (!DOM.pageStatusRegion) return;
    DOM.pageStatusRegion.className = 'page-status-region hidden';
    DOM.pageStatusRegion.replaceChildren();
}

function showLoading(v) {
    if (v) DOM.loadingOverlay.classList.remove('hidden'); else DOM.loadingOverlay.classList.add('hidden');
    DOM.mainContent?.setAttribute('aria-busy', String(Boolean(v)));
}
function showToast(message, type='info') {
    if (!DOM.toastRegion) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    const icon = type === 'success' ? 'circle-check' : type === 'error' ? 'triangle-exclamation' : 'circle-info';
    toast.innerHTML = `<i class="fa-solid fa-${icon}"></i><p>${escapeHtml(message)}</p><button type="button" title="${escapeHtml(t('close'))}" aria-label="${escapeHtml(t('close'))}"><i class="fa-solid fa-xmark"></i></button>`;
    toast.querySelector('button').addEventListener('click', () => toast.remove());
    DOM.toastRegion.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}
async function logout() {
    try {
        if (isSameOriginApi(state.botUrl)) await apiCall('/api/admin/session', 'DELETE');
    } catch(e) {}
    state.botUrl=''; state.apiKey='';
    localStorage.removeItem('ventebot_url'); localStorage.removeItem('ventebot_key');
    sessionStorage.removeItem('ventebot_key');
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

const RECONCILIATION_CHECK_KEYS = {
    negative_wallets:'ops_check_negative_wallets',
    stuck_paid_orders:'ops_check_stuck_paid_orders',
    unknown_supplier_outcomes:'ops_check_unknown_supplier_outcomes',
    unprofitable_supplier_orders:'ops_check_unprofitable_supplier_orders',
    completed_without_delivery:'ops_check_completed_without_delivery',
    finished_provider_payments_unresolved:'ops_check_finished_provider_payments_unresolved',
};

function renderFinancialReconciliation(report) {
    if (!DOM.financeReconcileStatus || !DOM.financeReconcileChecks) return;
    if (!report || !Array.isArray(report.checks)) {
        DOM.financeReconcileStatus.className = 'status-badge pending';
        DOM.financeReconcileStatus.textContent = '—';
        DOM.financeReconcileSummary.textContent = t('ops_reconcile_empty');
        DOM.financeReconcileUpdated.textContent = '';
        DOM.financeReconcileChecks.innerHTML = '';
        return;
    }
    const status = ['healthy', 'warning', 'critical'].includes(report.status) ? report.status : 'warning';
    const statusClass = status === 'healthy' ? 'completed' : status === 'critical' ? 'cancelled' : 'pending';
    DOM.financeReconcileStatus.className = `status-badge ${statusClass}`;
    DOM.financeReconcileStatus.textContent = t(`ops_status_${status}`);
    DOM.financeReconcileSummary.textContent = tf('ops_reconcile_summary', {
        critical:Number(report.critical_count || 0),
        warnings:Number(report.warning_count || 0),
    });
    const generatedAt = report.generated_at
        ? parseUTCDate(report.generated_at).toLocaleString(currentLocale())
        : '—';
    DOM.financeReconcileUpdated.textContent = tf('ops_reconcile_updated', {date:generatedAt});
    DOM.financeReconcileChecks.innerHTML = report.checks.map(check => {
        const severity = check.ok ? 'ok' : (check.severity === 'critical' ? 'critical' : 'warning');
        const icon = check.ok ? 'fa-circle-check' : (severity === 'critical' ? 'fa-circle-xmark' : 'fa-triangle-exclamation');
        const title = t(RECONCILIATION_CHECK_KEYS[check.key]) || check.title || check.key;
        return `<div class="ops-check-row ${severity}">
            <i class="fa-solid ${icon}"></i>
            <span>${escapeHtml(title)}</span>
            <strong>${Number(check.count || 0)}</strong>
        </div>`;
    }).join('');
}

async function loadFinancialReconciliation() {
    try {
        const data = await apiCall('/api/finance/reconciliation');
        renderFinancialReconciliation(data.available ? data.report : null);
    } catch(error) {
        console.error('Error loading financial reconciliation', error);
        renderFinancialReconciliation(null);
    }
}

async function runFinancialReconciliation() {
    const button = DOM.financeReconcileRun;
    if (button?.disabled) return;
    if (button) button.disabled = true;
    if (DOM.financeReconcileRunLabel) DOM.financeReconcileRunLabel.textContent = t('ops_reconcile_running');
    try {
        const report = await apiCall('/api/finance/reconciliation/run', 'POST');
        renderFinancialReconciliation(report);
        showToast(t('ops_reconcile_done'), 'success');
    } catch(error) {
        console.error('Financial reconciliation failed', error);
        showToast(t('ops_reconcile_failed'), 'error');
    } finally {
        if (button) button.disabled = false;
        if (DOM.financeReconcileRunLabel) DOM.financeReconcileRunLabel.textContent = t('ops_reconcile_run');
    }
}

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
    await loadFinancialReconciliation();
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
