// VenteBot operational workspace: local cockpit preferences, command palette,
// contextual details, supplier comparison, and mobile navigation.
const COCKPIT_TRANSLATIONS = {
fr: {
    ops_command_open:"Ouvrir la recherche rapide",ops_command_search:"Rechercher",ops_command_title:"Palette de commandes",ops_command_placeholder:"Produit, client, commande ou action...",ops_command_results:"Résultats",ops_command_hint:"↑↓ naviguer · Entrée ouvrir",ops_command_empty:"Aucun résultat",ops_command_searching:"Recherche...",ops_command_actions:"Actions rapides",ops_command_entities:"Résultats",ops_command_cancelled:"Recherche annulée",
    ops_customize:"Personnaliser",ops_alerts:"Alertes opérationnelles",ops_underpaid:"Sous-payés",ops_pending_activations:"Activations",ops_critical_stock:"Stocks critiques",ops_supplier_attention:"Fournisseurs à vérifier",ops_known_profit:"Bénéfice fournisseur connu (30J)",ops_profit_coverage:"{count} commande(s) avec coût connu",ops_profit_coverage_empty:"Aucune commande avec coût connu",ops_activity_title:"Centre d’activité",ops_from_current_data:"Données courantes",ops_more:"Plus",ops_mobile_navigation:"Navigation rapide",
    ops_details:"Détails",ops_customize_title:"Organiser le cockpit",ops_customize_help:"Glissez les modules pour les réordonner et masquez ceux dont vous n’avez pas besoin.",ops_show_module:"Afficher",ops_reset_layout:"Réinitialiser",ops_layout_saved:"Disposition enregistrée",ops_module_alerts:"Alertes",ops_module_operations:"Priorités et activité",ops_module_today:"Aujourd’hui",ops_module_metrics:"Indicateurs",ops_module_charts:"Tendances",ops_module_stock:"Stock",ops_module_performance:"Performance du bot",
    ops_product_intelligence:"Intelligence produit",ops_view_intelligence:"Ouvrir l’intelligence produit",ops_sales_today:"Ventes aujourd’hui",ops_sales_7d:"Ventes sur 7 jours",ops_revenue_7d:"Revenus sur 7 jours",ops_known_margin:"Bénéfice connu",ops_conversion:"Conversion",ops_stock_runway:"Autonomie du stock",ops_days_left:"{days} jours estimés",ops_unknown_runway:"Données insuffisantes",ops_sales_momentum:"Momentum des ventes",ops_price_evolution:"Évolution du prix",ops_supplier_comparison:"Comparaison fournisseurs",ops_no_supplier_route:"Aucun fournisseur alternatif confirmé.",ops_recommended:"Recommandé",ops_cost:"Coût",ops_margin:"Marge",ops_wallet:"Wallet",ops_reliability:"Fiabilité",ops_freshness:"Fraîcheur",ops_affordable:"Achetable",ops_warranty:"Garantie",ops_days_short:"j",ops_sync_recent:"Récent",ops_sync_hours:"Il y a {hours} h",ops_sync_unknown:"Inconnue",ops_open_product_editor:"Modifier le produit",ops_manage_stock:"Gérer le stock",ops_open_supplier:"Ouvrir le fournisseur",ops_product_load_error:"Impossible de charger l’intelligence produit.",
    ops_order_details:"Détail de commande",ops_order_timeline:"Chronologie",ops_delivered_items:"Articles livrés",ops_no_timeline:"Aucun événement disponible.",ops_open_orders:"Voir dans les commandes",ops_download_txt:"Télécharger .txt",ops_user_details:"Fiche client",ops_user_orders:"Achats récents",ops_user_wallet:"Solde wallet",ops_user_spent:"Dépenses",ops_user_total_orders:"Commandes",ops_open_purchase_history:"Historique complet",ops_credit_wallet:"Créditer",ops_debit_wallet:"Débiter",ops_supplier_details:"Fiche fournisseur",ops_supplier_products:"Produits sélectionnés",ops_last_sync:"Dernière synchronisation",ops_connection:"Connexion",ops_open_management:"Ouvrir la gestion",ops_profit_details:"Bénéfice connu",ops_profit_explanation:"Ce bénéfice couvre uniquement les commandes fournisseur dont le coût d’achat est enregistré. Les produits issus de votre propre stock ne sont pas estimés.",ops_open_supplier_stats:"Voir les statistiques fournisseurs",
    ops_activity_underpaid:"Paiement sous-payé",ops_activity_activation:"Activation en attente",ops_activity_supplier:"Synchronisation fournisseur à vérifier",ops_activity_order:"Commande #{id}",ops_activity_empty:"Aucune activité importante pour le moment.",ops_status_active:"Actif",ops_status_inactive:"Inactif",ops_loading:"Chargement...",ops_retry:"Réessayer",ops_close:"Fermer",ops_action_add_product:"Ajouter un produit",ops_action_add_stock:"Ajouter du stock",ops_action_activation:"Ouvrir les activations",ops_action_supplier_sync:"Synchroniser un fournisseur",ops_action_promo:"Créer un code promotionnel",ops_type_product:"Produit",ops_type_user:"Client",ops_type_order:"Commande",ops_type_supplier:"Fournisseur"
},
en: {
    ops_command_open:"Open quick search",ops_command_search:"Search",ops_command_title:"Command palette",ops_command_placeholder:"Product, client, order, or action...",ops_command_results:"Results",ops_command_hint:"↑↓ navigate · Enter to open",ops_command_empty:"No results",ops_command_searching:"Searching...",ops_command_actions:"Quick actions",ops_command_entities:"Results",ops_command_cancelled:"Search cancelled",
    ops_customize:"Customize",ops_alerts:"Operational alerts",ops_underpaid:"Underpaid",ops_pending_activations:"Activations",ops_critical_stock:"Critical stock",ops_supplier_attention:"Suppliers to review",ops_known_profit:"Known supplier profit (30D)",ops_profit_coverage:"{count} order(s) with known cost",ops_profit_coverage_empty:"No order with known cost",ops_activity_title:"Activity center",ops_from_current_data:"Current data",ops_more:"More",ops_mobile_navigation:"Quick navigation",
    ops_details:"Details",ops_customize_title:"Organize cockpit",ops_customize_help:"Drag modules to reorder them and hide those you do not need.",ops_show_module:"Show",ops_reset_layout:"Reset",ops_layout_saved:"Layout saved",ops_module_alerts:"Alerts",ops_module_operations:"Priorities and activity",ops_module_today:"Today",ops_module_metrics:"Metrics",ops_module_charts:"Trends",ops_module_stock:"Stock",ops_module_performance:"Bot performance",
    ops_product_intelligence:"Product intelligence",ops_view_intelligence:"Open product intelligence",ops_sales_today:"Sales today",ops_sales_7d:"Sales over 7 days",ops_revenue_7d:"Revenue over 7 days",ops_known_margin:"Known profit",ops_conversion:"Conversion",ops_stock_runway:"Stock runway",ops_days_left:"Estimated {days} days",ops_unknown_runway:"Insufficient data",ops_sales_momentum:"Sales momentum",ops_price_evolution:"Price evolution",ops_supplier_comparison:"Supplier comparison",ops_no_supplier_route:"No confirmed supplier alternative.",ops_recommended:"Recommended",ops_cost:"Cost",ops_margin:"Margin",ops_wallet:"Wallet",ops_reliability:"Reliability",ops_freshness:"Freshness",ops_affordable:"Purchasable",ops_warranty:"Warranty",ops_days_short:"d",ops_sync_recent:"Recent",ops_sync_hours:"{hours}h ago",ops_sync_unknown:"Unknown",ops_open_product_editor:"Edit product",ops_manage_stock:"Manage stock",ops_open_supplier:"Open supplier",ops_product_load_error:"Could not load product intelligence.",
    ops_order_details:"Order details",ops_order_timeline:"Timeline",ops_delivered_items:"Delivered items",ops_no_timeline:"No event available.",ops_open_orders:"View in orders",ops_download_txt:"Download .txt",ops_user_details:"Client profile",ops_user_orders:"Recent purchases",ops_user_wallet:"Wallet balance",ops_user_spent:"Spent",ops_user_total_orders:"Orders",ops_open_purchase_history:"Full history",ops_credit_wallet:"Credit",ops_debit_wallet:"Debit",ops_supplier_details:"Supplier profile",ops_supplier_products:"Selected products",ops_last_sync:"Last sync",ops_connection:"Connection",ops_open_management:"Open management",ops_profit_details:"Known profit",ops_profit_explanation:"This profit only covers supplier orders whose purchase cost is recorded. Products delivered from your own stock are not estimated.",ops_open_supplier_stats:"View supplier statistics",
    ops_activity_underpaid:"Underpaid payment",ops_activity_activation:"Activation pending",ops_activity_supplier:"Supplier sync needs review",ops_activity_order:"Order #{id}",ops_activity_empty:"No important activity right now.",ops_status_active:"Active",ops_status_inactive:"Inactive",ops_loading:"Loading...",ops_retry:"Retry",ops_close:"Close",ops_action_add_product:"Add product",ops_action_add_stock:"Add stock",ops_action_activation:"Open activations",ops_action_supplier_sync:"Sync supplier",ops_action_promo:"Create promo code",ops_type_product:"Product",ops_type_user:"Client",ops_type_order:"Order",ops_type_supplier:"Supplier"
},
ar: {
    ops_command_open:"فتح البحث السريع",ops_command_search:"بحث",ops_command_title:"لوحة الأوامر",ops_command_placeholder:"منتج أو عميل أو طلب أو إجراء...",ops_command_results:"النتائج",ops_command_hint:"↑↓ للتنقل · Enter للفتح",ops_command_empty:"لا توجد نتائج",ops_command_searching:"جارٍ البحث...",ops_command_actions:"إجراءات سريعة",ops_command_entities:"النتائج",ops_command_cancelled:"تم إلغاء البحث",
    ops_customize:"تخصيص",ops_alerts:"تنبيهات التشغيل",ops_underpaid:"مدفوع جزئياً",ops_pending_activations:"التفعيلات",ops_critical_stock:"مخزون حرج",ops_supplier_attention:"موردون للمراجعة",ops_known_profit:"ربح المورد المعروف (30 يوماً)",ops_profit_coverage:"{count} طلب بتكلفة معروفة",ops_profit_coverage_empty:"لا توجد طلبات بتكلفة معروفة",ops_activity_title:"مركز النشاط",ops_from_current_data:"البيانات الحالية",ops_more:"المزيد",ops_mobile_navigation:"تنقل سريع",
    ops_details:"التفاصيل",ops_customize_title:"تنظيم لوحة التحكم",ops_customize_help:"اسحب الوحدات لإعادة ترتيبها وأخفِ ما لا تحتاج إليه.",ops_show_module:"إظهار",ops_reset_layout:"إعادة ضبط",ops_layout_saved:"تم حفظ التخطيط",ops_module_alerts:"التنبيهات",ops_module_operations:"الأولويات والنشاط",ops_module_today:"اليوم",ops_module_metrics:"المؤشرات",ops_module_charts:"الاتجاهات",ops_module_stock:"المخزون",ops_module_performance:"أداء البوت",
    ops_product_intelligence:"تحليل المنتج",ops_view_intelligence:"فتح تحليل المنتج",ops_sales_today:"مبيعات اليوم",ops_sales_7d:"مبيعات 7 أيام",ops_revenue_7d:"إيرادات 7 أيام",ops_known_margin:"الربح المعروف",ops_conversion:"التحويل",ops_stock_runway:"مدة كفاية المخزون",ops_days_left:"نحو {days} يوم",ops_unknown_runway:"بيانات غير كافية",ops_sales_momentum:"زخم المبيعات",ops_price_evolution:"تطور السعر",ops_supplier_comparison:"مقارنة الموردين",ops_no_supplier_route:"لا يوجد مورد بديل مؤكد.",ops_recommended:"موصى به",ops_cost:"التكلفة",ops_margin:"الهامش",ops_wallet:"المحفظة",ops_reliability:"الموثوقية",ops_freshness:"حداثة البيانات",ops_affordable:"قابل للشراء",ops_warranty:"الضمان",ops_days_short:"ي",ops_sync_recent:"حديث",ops_sync_hours:"منذ {hours} س",ops_sync_unknown:"غير معروف",ops_open_product_editor:"تعديل المنتج",ops_manage_stock:"إدارة المخزون",ops_open_supplier:"فتح المورد",ops_product_load_error:"تعذر تحميل تحليل المنتج.",
    ops_order_details:"تفاصيل الطلب",ops_order_timeline:"التسلسل الزمني",ops_delivered_items:"العناصر المسلّمة",ops_no_timeline:"لا توجد أحداث.",ops_open_orders:"عرض في الطلبات",ops_download_txt:"تنزيل .txt",ops_user_details:"ملف العميل",ops_user_orders:"المشتريات الأخيرة",ops_user_wallet:"رصيد المحفظة",ops_user_spent:"المصروف",ops_user_total_orders:"الطلبات",ops_open_purchase_history:"السجل الكامل",ops_credit_wallet:"إضافة رصيد",ops_debit_wallet:"خصم",ops_supplier_details:"ملف المورد",ops_supplier_products:"المنتجات المحددة",ops_last_sync:"آخر مزامنة",ops_connection:"الاتصال",ops_open_management:"فتح الإدارة",ops_profit_details:"الربح المعروف",ops_profit_explanation:"يشمل هذا الربح طلبات المورد التي تم تسجيل تكلفة شرائها فقط. لا يتم تقدير منتجات مخزونك الخاص.",ops_open_supplier_stats:"عرض إحصاءات الموردين",
    ops_activity_underpaid:"دفعة ناقصة",ops_activity_activation:"تفعيل معلق",ops_activity_supplier:"مزامنة المورد تحتاج مراجعة",ops_activity_order:"الطلب #{id}",ops_activity_empty:"لا يوجد نشاط مهم الآن.",ops_status_active:"نشط",ops_status_inactive:"غير نشط",ops_loading:"جارٍ التحميل...",ops_retry:"إعادة المحاولة",ops_close:"إغلاق",ops_action_add_product:"إضافة منتج",ops_action_add_stock:"إضافة مخزون",ops_action_activation:"فتح التفعيلات",ops_action_supplier_sync:"مزامنة مورد",ops_action_promo:"إنشاء رمز ترويجي",ops_type_product:"منتج",ops_type_user:"عميل",ops_type_order:"طلب",ops_type_supplier:"مورد"
},
zh: {
    ops_command_open:"打开快速搜索",ops_command_search:"搜索",ops_command_title:"命令面板",ops_command_placeholder:"产品、客户、订单或操作...",ops_command_results:"结果",ops_command_hint:"↑↓ 导航 · Enter 打开",ops_command_empty:"没有结果",ops_command_searching:"正在搜索...",ops_command_actions:"快捷操作",ops_command_entities:"结果",ops_command_cancelled:"搜索已取消",
    ops_customize:"自定义",ops_alerts:"运营警报",ops_underpaid:"少付",ops_pending_activations:"待激活",ops_critical_stock:"库存告急",ops_supplier_attention:"需检查的供应商",ops_known_profit:"已知供应商利润（30天）",ops_profit_coverage:"{count} 个已知成本订单",ops_profit_coverage_empty:"没有已知成本订单",ops_activity_title:"活动中心",ops_from_current_data:"当前数据",ops_more:"更多",ops_mobile_navigation:"快捷导航",
    ops_details:"详情",ops_customize_title:"整理控制台",ops_customize_help:"拖动模块重新排序，并隐藏不需要的模块。",ops_show_module:"显示",ops_reset_layout:"重置",ops_layout_saved:"布局已保存",ops_module_alerts:"警报",ops_module_operations:"优先事项和活动",ops_module_today:"今天",ops_module_metrics:"指标",ops_module_charts:"趋势",ops_module_stock:"库存",ops_module_performance:"机器人性能",
    ops_product_intelligence:"产品分析",ops_view_intelligence:"打开产品分析",ops_sales_today:"今日销量",ops_sales_7d:"7天销量",ops_revenue_7d:"7天收入",ops_known_margin:"已知利润",ops_conversion:"转化率",ops_stock_runway:"库存可用天数",ops_days_left:"预计 {days} 天",ops_unknown_runway:"数据不足",ops_sales_momentum:"销售趋势",ops_price_evolution:"价格变化",ops_supplier_comparison:"供应商比较",ops_no_supplier_route:"没有已确认的替代供应商。",ops_recommended:"推荐",ops_cost:"成本",ops_margin:"利润",ops_wallet:"钱包",ops_reliability:"可靠性",ops_freshness:"数据新鲜度",ops_affordable:"可购买",ops_warranty:"保修",ops_days_short:"天",ops_sync_recent:"最近",ops_sync_hours:"{hours} 小时前",ops_sync_unknown:"未知",ops_open_product_editor:"编辑产品",ops_manage_stock:"管理库存",ops_open_supplier:"打开供应商",ops_product_load_error:"无法加载产品分析。",
    ops_order_details:"订单详情",ops_order_timeline:"时间线",ops_delivered_items:"已交付项目",ops_no_timeline:"没有可用事件。",ops_open_orders:"在订单中查看",ops_download_txt:"下载 .txt",ops_user_details:"客户资料",ops_user_orders:"最近购买",ops_user_wallet:"钱包余额",ops_user_spent:"消费",ops_user_total_orders:"订单",ops_open_purchase_history:"完整记录",ops_credit_wallet:"充值",ops_debit_wallet:"扣款",ops_supplier_details:"供应商资料",ops_supplier_products:"已选产品",ops_last_sync:"上次同步",ops_connection:"连接",ops_open_management:"打开管理",ops_profit_details:"已知利润",ops_profit_explanation:"此利润仅涵盖已记录采购成本的供应商订单，不估算您自有库存的产品。",ops_open_supplier_stats:"查看供应商统计",
    ops_activity_underpaid:"少付付款",ops_activity_activation:"待处理激活",ops_activity_supplier:"供应商同步需要检查",ops_activity_order:"订单 #{id}",ops_activity_empty:"目前没有重要活动。",ops_status_active:"启用",ops_status_inactive:"停用",ops_loading:"加载中...",ops_retry:"重试",ops_close:"关闭",ops_action_add_product:"添加产品",ops_action_add_stock:"添加库存",ops_action_activation:"打开激活",ops_action_supplier_sync:"同步供应商",ops_action_promo:"创建促销码",ops_type_product:"产品",ops_type_user:"客户",ops_type_order:"订单",ops_type_supplier:"供应商"
},
vi: {
    ops_command_open:"Mở tìm kiếm nhanh",ops_command_search:"Tìm kiếm",ops_command_title:"Bảng lệnh",ops_command_placeholder:"Sản phẩm, khách hàng, đơn hàng hoặc thao tác...",ops_command_results:"Kết quả",ops_command_hint:"↑↓ di chuyển · Enter để mở",ops_command_empty:"Không có kết quả",ops_command_searching:"Đang tìm...",ops_command_actions:"Thao tác nhanh",ops_command_entities:"Kết quả",ops_command_cancelled:"Đã hủy tìm kiếm",
    ops_customize:"Tùy chỉnh",ops_alerts:"Cảnh báo vận hành",ops_underpaid:"Thiếu tiền",ops_pending_activations:"Kích hoạt",ops_critical_stock:"Tồn kho nguy cấp",ops_supplier_attention:"Nhà cung cấp cần kiểm tra",ops_known_profit:"Lợi nhuận nhà cung cấp đã biết (30 ngày)",ops_profit_coverage:"{count} đơn có chi phí đã biết",ops_profit_coverage_empty:"Không có đơn với chi phí đã biết",ops_activity_title:"Trung tâm hoạt động",ops_from_current_data:"Dữ liệu hiện tại",ops_more:"Thêm",ops_mobile_navigation:"Điều hướng nhanh",
    ops_details:"Chi tiết",ops_customize_title:"Sắp xếp bảng điều khiển",ops_customize_help:"Kéo các mô-đun để sắp xếp và ẩn những phần không cần thiết.",ops_show_module:"Hiển thị",ops_reset_layout:"Đặt lại",ops_layout_saved:"Đã lưu bố cục",ops_module_alerts:"Cảnh báo",ops_module_operations:"Ưu tiên và hoạt động",ops_module_today:"Hôm nay",ops_module_metrics:"Chỉ số",ops_module_charts:"Xu hướng",ops_module_stock:"Tồn kho",ops_module_performance:"Hiệu suất bot",
    ops_product_intelligence:"Phân tích sản phẩm",ops_view_intelligence:"Mở phân tích sản phẩm",ops_sales_today:"Bán hôm nay",ops_sales_7d:"Bán trong 7 ngày",ops_revenue_7d:"Doanh thu 7 ngày",ops_known_margin:"Lợi nhuận đã biết",ops_conversion:"Chuyển đổi",ops_stock_runway:"Số ngày tồn kho",ops_days_left:"Ước tính {days} ngày",ops_unknown_runway:"Chưa đủ dữ liệu",ops_sales_momentum:"Đà bán hàng",ops_price_evolution:"Biến động giá",ops_supplier_comparison:"So sánh nhà cung cấp",ops_no_supplier_route:"Không có nhà cung cấp thay thế đã xác nhận.",ops_recommended:"Đề xuất",ops_cost:"Chi phí",ops_margin:"Biên lợi nhuận",ops_wallet:"Ví",ops_reliability:"Độ tin cậy",ops_freshness:"Độ mới",ops_affordable:"Có thể mua",ops_warranty:"Bảo hành",ops_days_short:"ngày",ops_sync_recent:"Gần đây",ops_sync_hours:"{hours} giờ trước",ops_sync_unknown:"Không rõ",ops_open_product_editor:"Sửa sản phẩm",ops_manage_stock:"Quản lý tồn kho",ops_open_supplier:"Mở nhà cung cấp",ops_product_load_error:"Không thể tải phân tích sản phẩm.",
    ops_order_details:"Chi tiết đơn hàng",ops_order_timeline:"Dòng thời gian",ops_delivered_items:"Mục đã giao",ops_no_timeline:"Không có sự kiện.",ops_open_orders:"Xem trong đơn hàng",ops_download_txt:"Tải .txt",ops_user_details:"Hồ sơ khách hàng",ops_user_orders:"Mua gần đây",ops_user_wallet:"Số dư ví",ops_user_spent:"Đã chi",ops_user_total_orders:"Đơn hàng",ops_open_purchase_history:"Lịch sử đầy đủ",ops_credit_wallet:"Cộng tiền",ops_debit_wallet:"Trừ tiền",ops_supplier_details:"Hồ sơ nhà cung cấp",ops_supplier_products:"Sản phẩm đã chọn",ops_last_sync:"Đồng bộ gần nhất",ops_connection:"Kết nối",ops_open_management:"Mở quản lý",ops_profit_details:"Lợi nhuận đã biết",ops_profit_explanation:"Lợi nhuận này chỉ bao gồm đơn nhà cung cấp có chi phí mua đã được ghi nhận. Sản phẩm từ kho riêng không được ước tính.",ops_open_supplier_stats:"Xem thống kê nhà cung cấp",
    ops_activity_underpaid:"Thanh toán thiếu",ops_activity_activation:"Kích hoạt đang chờ",ops_activity_supplier:"Cần kiểm tra đồng bộ nhà cung cấp",ops_activity_order:"Đơn #{id}",ops_activity_empty:"Hiện không có hoạt động quan trọng.",ops_status_active:"Hoạt động",ops_status_inactive:"Không hoạt động",ops_loading:"Đang tải...",ops_retry:"Thử lại",ops_close:"Đóng",ops_action_add_product:"Thêm sản phẩm",ops_action_add_stock:"Thêm tồn kho",ops_action_activation:"Mở kích hoạt",ops_action_supplier_sync:"Đồng bộ nhà cung cấp",ops_action_promo:"Tạo mã khuyến mãi",ops_type_product:"Sản phẩm",ops_type_user:"Khách hàng",ops_type_order:"Đơn hàng",ops_type_supplier:"Nhà cung cấp"
},
ru: {
    ops_command_open:"Открыть быстрый поиск",ops_command_search:"Поиск",ops_command_title:"Палитра команд",ops_command_placeholder:"Товар, клиент, заказ или действие...",ops_command_results:"Результаты",ops_command_hint:"↑↓ навигация · Enter открыть",ops_command_empty:"Нет результатов",ops_command_searching:"Поиск...",ops_command_actions:"Быстрые действия",ops_command_entities:"Результаты",ops_command_cancelled:"Поиск отменён",
    ops_customize:"Настроить",ops_alerts:"Операционные оповещения",ops_underpaid:"Недоплата",ops_pending_activations:"Активации",ops_critical_stock:"Критический запас",ops_supplier_attention:"Поставщики для проверки",ops_known_profit:"Известная прибыль поставщика (30 дн.)",ops_profit_coverage:"{count} заказ(ов) с известной стоимостью",ops_profit_coverage_empty:"Нет заказов с известной стоимостью",ops_activity_title:"Центр активности",ops_from_current_data:"Текущие данные",ops_more:"Ещё",ops_mobile_navigation:"Быстрая навигация",
    ops_details:"Подробности",ops_customize_title:"Настроить панель",ops_customize_help:"Перетаскивайте модули и скрывайте ненужные.",ops_show_module:"Показать",ops_reset_layout:"Сбросить",ops_layout_saved:"Макет сохранён",ops_module_alerts:"Оповещения",ops_module_operations:"Приоритеты и активность",ops_module_today:"Сегодня",ops_module_metrics:"Показатели",ops_module_charts:"Тенденции",ops_module_stock:"Запас",ops_module_performance:"Производительность бота",
    ops_product_intelligence:"Аналитика товара",ops_view_intelligence:"Открыть аналитику товара",ops_sales_today:"Продажи сегодня",ops_sales_7d:"Продажи за 7 дней",ops_revenue_7d:"Выручка за 7 дней",ops_known_margin:"Известная прибыль",ops_conversion:"Конверсия",ops_stock_runway:"Запас в днях",ops_days_left:"Примерно {days} дн.",ops_unknown_runway:"Недостаточно данных",ops_sales_momentum:"Динамика продаж",ops_price_evolution:"Динамика цены",ops_supplier_comparison:"Сравнение поставщиков",ops_no_supplier_route:"Нет подтверждённого альтернативного поставщика.",ops_recommended:"Рекомендуется",ops_cost:"Стоимость",ops_margin:"Маржа",ops_wallet:"Кошелёк",ops_reliability:"Надёжность",ops_freshness:"Актуальность",ops_affordable:"Доступно",ops_warranty:"Гарантия",ops_days_short:"д",ops_sync_recent:"Недавно",ops_sync_hours:"{hours} ч назад",ops_sync_unknown:"Неизвестно",ops_open_product_editor:"Изменить товар",ops_manage_stock:"Управлять запасом",ops_open_supplier:"Открыть поставщика",ops_product_load_error:"Не удалось загрузить аналитику товара.",
    ops_order_details:"Детали заказа",ops_order_timeline:"Хронология",ops_delivered_items:"Доставленные позиции",ops_no_timeline:"Событий нет.",ops_open_orders:"Открыть в заказах",ops_download_txt:"Скачать .txt",ops_user_details:"Профиль клиента",ops_user_orders:"Недавние покупки",ops_user_wallet:"Баланс кошелька",ops_user_spent:"Потрачено",ops_user_total_orders:"Заказы",ops_open_purchase_history:"Полная история",ops_credit_wallet:"Пополнить",ops_debit_wallet:"Списать",ops_supplier_details:"Профиль поставщика",ops_supplier_products:"Выбранные товары",ops_last_sync:"Последняя синхронизация",ops_connection:"Подключение",ops_open_management:"Открыть управление",ops_profit_details:"Известная прибыль",ops_profit_explanation:"Прибыль учитывает только заказы поставщиков с записанной закупочной стоимостью. Товары из собственного запаса не оцениваются.",ops_open_supplier_stats:"Статистика поставщиков",
    ops_activity_underpaid:"Недоплаченный платёж",ops_activity_activation:"Ожидает активации",ops_activity_supplier:"Нужно проверить синхронизацию поставщика",ops_activity_order:"Заказ #{id}",ops_activity_empty:"Сейчас нет важных событий.",ops_status_active:"Активен",ops_status_inactive:"Неактивен",ops_loading:"Загрузка...",ops_retry:"Повторить",ops_close:"Закрыть",ops_action_add_product:"Добавить товар",ops_action_add_stock:"Добавить запас",ops_action_activation:"Открыть активации",ops_action_supplier_sync:"Синхронизировать поставщика",ops_action_promo:"Создать промокод",ops_type_product:"Товар",ops_type_user:"Клиент",ops_type_order:"Заказ",ops_type_supplier:"Поставщик"
}
};
Object.entries(COCKPIT_TRANSLATIONS).forEach(([language, strings]) => {
    Object.assign(LANG[language], strings);
});

(() => {
    const LAYOUT_KEY = 'ventebot_cockpit_layout_v1';
    const HIDDEN_KEY = 'ventebot_cockpit_hidden_v1';
    const DEFAULT_LAYOUT = ['alerts', 'operations', 'today', 'metrics', 'charts', 'stock', 'performance'];
    const MODULE_KEYS = Object.freeze({
        alerts:'ops_module_alerts',
        operations:'ops_module_operations',
        today:'ops_module_today',
        metrics:'ops_module_metrics',
        charts:'ops_module_charts',
        stock:'ops_module_stock',
        performance:'ops_module_performance',
    });
    const ops = {
        overview:null,
        stats:null,
        paymentReview:null,
        suppliers:[],
        supplierLoadedAt:0,
        commandItems:[],
        commandIndex:0,
        commandTimer:null,
        commandController:null,
        drawerController:null,
        drawerReturnFocus:null,
        insightCache:new Map(),
        searchCache:new Map(),
        currentProductInsights:null,
        showUnavailableSuppliers:true,
        legacyOpenOrder:null,
        legacyOpenUser:null,
        customizeSortable:null,
    };
    const els = {};

    function safeNumber(value) {
        const number = Number(value);
        return Number.isFinite(number) ? number : 0;
    }

    function safeEntityId(value) {
        const number = Number(value);
        return Number.isSafeInteger(number) && number > 0 ? number : null;
    }

    function money(value, digits=2) {
        return `$${safeNumber(value).toFixed(digits)}`;
    }

    function localDate(value, options={dateStyle:'short', timeStyle:'short'}) {
        if (!value) return '—';
        const date = parseUTCDate(value);
        return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(currentLocale(), options);
    }

    function readJson(key, fallback) {
        try {
            const value = JSON.parse(localStorage.getItem(key) || '');
            return value ?? fallback;
        } catch (_) {
            return fallback;
        }
    }

    function validLayout() {
        const stored = readJson(LAYOUT_KEY, []);
        const unique = stored.filter((key, index) => MODULE_KEYS[key] && stored.indexOf(key) === index);
        return [...unique, ...DEFAULT_LAYOUT.filter(key => !unique.includes(key))];
    }

    function hiddenModules() {
        const stored = readJson(HIDDEN_KEY, []);
        return new Set(Array.isArray(stored) ? stored.filter(key => MODULE_KEYS[key]) : []);
    }

    function applyCockpitLayout() {
        const layout = validLayout();
        const hidden = hiddenModules();
        layout.forEach((key, index) => {
            const module = document.querySelector(`[data-cockpit-module="${key}"]`);
            if (!module) return;
            module.style.order = String(index + 2);
            module.classList.toggle('ops-module-hidden', hidden.has(key));
        });
    }

    function saveCockpitLayout(layout, hidden) {
        localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
        localStorage.setItem(HIDDEN_KEY, JSON.stringify([...hidden]));
        applyCockpitLayout();
        showToast(t('ops_layout_saved'), 'success');
    }

    function drawerLoading() {
        return `<div class="ops-drawer-loading" aria-busy="true">
            <div class="ops-skeleton-block"></div><div class="ops-skeleton-block short"></div>
            <div class="ops-skeleton-grid"><span></span><span></span><span></span><span></span></div>
        </div>`;
    }

    function setDrawer({eyebrow='', title='', body='', actions=''}) {
        els.drawerEyebrow.textContent = eyebrow;
        els.drawerTitle.textContent = title || t('ops_details');
        els.drawerBody.innerHTML = body;
        els.drawerActions.innerHTML = actions;
    }

    function openDrawer(config) {
        ops.drawerReturnFocus = document.activeElement;
        setDrawer(config);
        els.drawer.classList.remove('hidden');
        els.drawerBackdrop.classList.remove('hidden');
        els.drawerBackdrop.setAttribute('aria-hidden', 'false');
        document.body.classList.add('ops-drawer-open');
        requestAnimationFrame(() => els.drawerClose.focus());
    }

    function closeDrawer() {
        ops.drawerController?.abort();
        ops.drawerController = null;
        ops.customizeSortable?.destroy?.();
        ops.customizeSortable = null;
        els.drawer.classList.add('hidden');
        els.drawerBackdrop.classList.add('hidden');
        els.drawerBackdrop.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('ops-drawer-open');
        ops.drawerReturnFocus?.focus?.();
        ops.drawerReturnFocus = null;
    }

    function sparkline(values, className='') {
        const data = (values || []).map(safeNumber);
        if (!data.length) return '';
        const width = 320;
        const height = 92;
        const min = Math.min(...data);
        const max = Math.max(...data);
        const span = Math.max(1, max - min);
        const points = data.map((value, index) => {
            const x = data.length === 1 ? width / 2 : (index / (data.length - 1)) * width;
            const y = height - 8 - ((value - min) / span) * (height - 16);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(' ');
        return `<svg class="ops-sparkline ${className}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(t('ops_sales_momentum'))}">
            <polyline points="${points}"></polyline>
        </svg>`;
    }

    function freshnessLabel(hours) {
        const value = safeNumber(hours);
        if (value >= 9999) return t('ops_sync_unknown');
        if (value < 1) return t('ops_sync_recent');
        return tf('ops_sync_hours', {hours:Math.round(value)});
    }

    function supplierComparisonMarkup(candidates) {
        if (!candidates?.length) {
            return `<p class="empty-state">${escapeHtml(t('ops_no_supplier_route'))}</p>`;
        }
        const visibleCandidates = ops.showUnavailableSuppliers
            ? candidates
            : candidates.filter(candidate => (
                candidate.provider_enabled
                && safeNumber(candidate.affordable_stock) > 0
                && safeNumber(candidate.cost) > 0
            ));
        const toolbar = `<label class="ops-comparison-filter">
            <input type="checkbox" data-ops-filter="supplier-unavailable" ${ops.showUnavailableSuppliers ? 'checked' : ''}>
            <span>${escapeHtml(t('ai_show_unfunded'))}</span>
        </label>`;
        if (!visibleCandidates.length) {
            return `${toolbar}<p class="empty-state">${escapeHtml(t('ops_no_supplier_route'))}</p>`;
        }
        return `${toolbar}<div class="ops-comparison-list">${visibleCandidates.map(candidate => {
            const recommended = Boolean(candidate.recommended);
            const available = safeNumber(candidate.affordable_stock);
            return `<article class="ops-comparison-row ${recommended ? 'recommended' : ''}">
                <div class="ops-comparison-rank">${recommended ? '<i class="fa-solid fa-crown"></i>' : '<i class="fa-solid fa-server"></i>'}</div>
                <div class="ops-comparison-name">
                    <strong>${escapeHtml(candidate.supplier_name || candidate.supplier_code || '?')}</strong>
                    <small>${escapeHtml(candidate.name || candidate.external_product_id || '')}</small>
                    ${recommended ? `<span class="status-badge success">${escapeHtml(t('ops_recommended'))}</span>` : ''}
                    ${recommended ? `<small class="ops-recommendation-reason">${escapeHtml(t('ai_reason_compliant'))} · ${escapeHtml(tf('ai_reason_affordable', {count:available}))}</small>` : ''}
                </div>
                <dl>
                    <div><dt>${escapeHtml(t('ops_cost'))}</dt><dd>${money(candidate.cost)}</dd></div>
                    <div><dt>${escapeHtml(t('ops_margin'))}</dt><dd class="${safeNumber(candidate.margin) >= 0 ? 'positive' : 'negative'}">${money(candidate.margin)}</dd></div>
                    <div><dt>${escapeHtml(t('ops_affordable'))}</dt><dd>${available}/${safeNumber(candidate.remote_stock)}</dd></div>
                    <div><dt>${escapeHtml(t('ops_reliability'))}</dt><dd>${Math.round(safeNumber(candidate.reliability) * 100)}%</dd></div>
                </dl>
                <div class="ops-comparison-meta">
                    <span><i class="fa-solid fa-wallet"></i> ${money(candidate.wallet_balance)}</span>
                    <span><i class="fa-solid fa-shield"></i> ${safeNumber(candidate.warranty_days)} ${escapeHtml(t('ops_days_short'))}</span>
                    <span><i class="fa-solid fa-truck-fast"></i> ${escapeHtml(aiDeliveryLabel(candidate.delivery_mode))}</span>
                    <span><i class="fa-solid fa-clock"></i> ${escapeHtml(freshnessLabel(candidate.freshness_hours))}</span>
                </div>
                <button type="button" class="btn-icon" data-ops-action="supplier" data-code="${escapeHtml(candidate.supplier_code || '')}" title="${escapeHtml(t('ops_open_supplier'))}" aria-label="${escapeHtml(t('ops_open_supplier'))}"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
            </article>`;
        }).join('')}</div>`;
    }

    function renderProductInsights(data) {
        ops.currentProductInsights = data;
        const product = data.product || {};
        const sales = data.sales || {};
        const conversion = data.conversion || {};
        const stock = data.stock || {};
        const economics = data.economics || {};
        const priceValues = (data.price_history || []).map(item => item.new_price);
        const runway = stock.days_left === null || stock.days_left === undefined
            ? t('ops_unknown_runway')
            : tf('ops_days_left', {days:safeNumber(stock.days_left).toFixed(stock.days_left < 10 ? 1 : 0)});
        const body = `
            <section class="ops-product-hero">
                <span class="ops-product-emoji">${escapeHtml(product.emoji || '📦')}</span>
                <div><h3>${escapeHtml(product.name || `#${product.id}`)}</h3><p>${money(product.price_usd)} · ${safeNumber(product.warranty_days)} ${escapeHtml(t('days'))}</p></div>
                <span class="status-badge ${product.is_active ? 'success' : 'neutral'}">${escapeHtml(t(product.is_active ? 'ops_status_active' : 'ops_status_inactive'))}</span>
            </section>
            <section class="ops-insight-grid">
                <div><span>${escapeHtml(t('ops_sales_today'))}</span><strong>${safeNumber(sales.today)}</strong></div>
                <div><span>${escapeHtml(t('ops_sales_7d'))}</span><strong>${safeNumber(sales.sales_7d)}</strong></div>
                <div><span>${escapeHtml(t('ops_revenue_7d'))}</span><strong>${money(sales.revenue_7d)}</strong></div>
                <div><span>${escapeHtml(t('ops_known_margin'))}</span><strong>${money(economics.known_profit_30d)}</strong></div>
                <div><span>${escapeHtml(t('ops_conversion'))}</span><strong>${(safeNumber(conversion.overall_rate) * 100).toFixed(1)}%</strong></div>
                <div><span>${escapeHtml(t('ops_stock_runway'))}</span><strong>${escapeHtml(runway)}</strong></div>
            </section>
            <section class="ops-chart-band">
                <div><h4>${escapeHtml(t('ops_sales_momentum'))}</h4>${sparkline((sales.quantity_series || []).slice(-14), 'sales')}</div>
                <div><h4>${escapeHtml(t('ops_price_evolution'))}</h4>${priceValues.length ? sparkline(priceValues, 'price') : `<p class="empty-state">${escapeHtml(t('data_unavailable'))}</p>`}</div>
            </section>
            <section class="ops-funnel-compact">
                <h4>${escapeHtml(t('ops_conversion'))}</h4>
                <div><span><i class="fa-solid fa-eye"></i>${safeNumber(conversion.views)}</span><i class="fa-solid fa-chevron-right"></i><span><i class="fa-solid fa-cart-shopping"></i>${safeNumber(conversion.buy_clicks)}</span><i class="fa-solid fa-chevron-right"></i><span><i class="fa-solid fa-file-invoice-dollar"></i>${safeNumber(conversion.payments_created)}</span><i class="fa-solid fa-chevron-right"></i><span><i class="fa-solid fa-circle-check"></i>${safeNumber(conversion.payments_completed)}</span></div>
            </section>
            <section class="ops-comparison-section"><h4>${escapeHtml(t('ops_supplier_comparison'))}</h4>${supplierComparisonMarkup(data.supplier_comparison || [])}</section>`;
        setDrawer({
            eyebrow:t('ops_product_intelligence'),
            title:product.name || `#${product.id}`,
            body,
            actions:`<button type="button" class="btn-secondary" data-ops-action="edit-product" data-id="${safeNumber(product.id)}"><i class="fa-solid fa-pen"></i><span>${escapeHtml(t('ops_open_product_editor'))}</span></button>
                ${product.delivery_type === 'supplier_api' && data.recommended_supplier
                    ? `<button type="button" class="btn-primary" data-ops-action="supplier-best" data-code="${escapeHtml(data.recommended_supplier?.supplier_code || '')}"><i class="fa-solid fa-server"></i><span>${escapeHtml(t('ops_open_supplier'))}</span></button>`
                    : product.delivery_type === 'supplier_api'
                        ? `<button type="button" class="btn-primary" data-ops-tab="supplier-bots-tab"><i class="fa-solid fa-server"></i><span>${escapeHtml(t('ops_open_supplier'))}</span></button>`
                    : `<button type="button" class="btn-primary" data-ops-action="stock" data-id="${safeNumber(product.id)}"><i class="fa-solid fa-box-open"></i><span>${escapeHtml(t('ops_manage_stock'))}</span></button>`}`,
        });
    }

    async function openProductDrawer(productId, force=false) {
        const id = safeEntityId(productId);
        if (!id) return;
        const product = state.products.find(item => safeNumber(item.id) === id);
        openDrawer({
            eyebrow:t('ops_product_intelligence'),
            title:product?.name || `#${id}`,
            body:drawerLoading(),
        });
        const cached = ops.insightCache.get(id);
        if (!force && cached && Date.now() - cached.time < 60000) {
            renderProductInsights(cached.data);
            return;
        }
        ops.drawerController?.abort();
        ops.drawerController = new AbortController();
        try {
            const data = await apiCall(`/api/products/${id}/insights`, {
                signal:ops.drawerController.signal,
                timeoutMs:30000,
            });
            ops.insightCache.set(id, {time:Date.now(), data});
            renderProductInsights(data);
        } catch (error) {
            if (error.message === 'REQUEST_CANCELLED') return;
            setDrawer({
                eyebrow:t('ops_product_intelligence'),
                title:product?.name || `#${id}`,
                body:`<div class="ops-error-state"><i class="fa-solid fa-triangle-exclamation"></i><p>${escapeHtml(t('ops_product_load_error'))}</p><button type="button" class="btn-secondary" data-ops-action="retry-product" data-id="${id}">${escapeHtml(t('ops_retry'))}</button></div>`,
            });
        }
    }

    const TIMELINE_LABELS = {
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

    function orderTimelineMarkup(events) {
        if (!events?.length) return `<p class="empty-state">${escapeHtml(t('ops_no_timeline'))}</p>`;
        return `<div class="ops-timeline">${events.map(event => {
            const details = event.details || {};
            const label = TIMELINE_LABELS[event.type] ? t(TIMELINE_LABELS[event.type]) : (event.label || event.type || '—');
            const detail = details.provider_status || details.status || details.action || '';
            return `<article><span></span><div><strong>${escapeHtml(label)}</strong>${detail ? `<small>${escapeHtml(detail)}</small>` : ''}</div><time>${escapeHtml(localDate(event.occurred_at))}</time></article>`;
        }).join('')}</div>`;
    }

    async function openOrderDrawer(orderId, summary={}) {
        const id = safeEntityId(orderId);
        if (!id) return;
        const order = state.orders.find(item => safeNumber(item.id) === id) || summary || {};
        openDrawer({eyebrow:t('ops_order_details'), title:`#${id}`, body:drawerLoading()});
        ops.drawerController?.abort();
        ops.drawerController = new AbortController();
        try {
            const [itemsData, timeline] = await Promise.all([
                apiCall(`/api/orders/${id}/items`, {signal:ops.drawerController.signal, timeoutMs:30000}),
                apiCall(`/api/orders/${id}/timeline`, {signal:ops.drawerController.signal, timeoutMs:30000}).catch(error => {
                    if (error.message === 'REQUEST_CANCELLED') throw error;
                    return {events:[]};
                }),
            ]);
            const product = order.product_name || state.products.find(item => safeNumber(item.id) === safeNumber(order.product_id))?.name || order.subtitle || '—';
            const customer = order.username ? `@${order.username}` : (order.user_first_name || order.user_telegram_id || '—');
            const items = itemsData.items || [];
            state.orderDetailItems = items;
            state.orderDetailId = id;
            setDrawer({
                eyebrow:t('ops_order_details'),
                title:`#${id}`,
                body:`<section class="ops-order-summary">
                        <div><span>${escapeHtml(t('th_product'))}</span><strong>${escapeHtml(product)}</strong></div>
                        <div><span>${escapeHtml(t('th_client'))}</span><strong>${escapeHtml(customer)}</strong></div>
                        <div><span>${escapeHtml(t('th_amount'))}</span><strong>${money(order.amount_usd ?? order.amount)}</strong></div>
                        <div><span>${escapeHtml(t('th_status'))}</span><strong>${escapeHtml(itemsData.status || order.status || '—')}</strong></div>
                    </section>
                    <section class="ops-timeline-section"><h4>${escapeHtml(t('ops_order_timeline'))}</h4>${orderTimelineMarkup(timeline.events || [])}</section>
                    <section class="ops-delivery-section"><h4>${escapeHtml(t('ops_delivered_items'))} <span>${items.length}</span></h4>
                        ${items.length ? `<div>${items.map(item => `<code>${escapeHtml(item.account_data || '')}</code>`).join('')}</div>` : `<p class="empty-state">${escapeHtml(t('no_stock'))}</p>`}
                    </section>`,
                actions:`<button type="button" class="btn-secondary" data-ops-tab="orders-tab"><i class="fa-solid fa-receipt"></i><span>${escapeHtml(t('ops_open_orders'))}</span></button>
                    ${items.length ? `<button type="button" class="btn-primary" data-ops-action="download-order"><i class="fa-solid fa-download"></i><span>${escapeHtml(t('ops_download_txt'))}</span></button>` : ''}`,
            });
        } catch (error) {
            if (error.message === 'REQUEST_CANCELLED') return;
            setDrawer({
                eyebrow:t('ops_order_details'),
                title:`#${id}`,
                body:`<div class="ops-error-state"><i class="fa-solid fa-triangle-exclamation"></i><p>${escapeHtml(error.message)}</p></div>`,
                actions:`<button type="button" class="btn-secondary" data-ops-tab="orders-tab">${escapeHtml(t('ops_open_orders'))}</button>`,
            });
        }
    }

    function userOrdersMarkup(orders) {
        if (!orders?.length) return `<p class="empty-state">${escapeHtml(t('no_orders'))}</p>`;
        return `<div class="ops-user-orders">${orders.map(order => `<button type="button" data-ops-open="order" data-id="${safeNumber(order.id)}">
            <span><strong>#${safeNumber(order.id)} · ${escapeHtml(order.product_name || `#${order.product_id}`)}</strong><small>${escapeHtml(localDate(order.created_at))}</small></span>
            <span><strong>${money(order.amount_usd)}</strong><small>${escapeHtml(order.status || '')}</small></span>
        </button>`).join('')}</div>`;
    }

    async function openUserDrawer(telegramId, summary={}) {
        const id = safeEntityId(telegramId);
        if (!id) return;
        const loaded = state.users.find(item => safeNumber(item.telegram_id) === id) || summary || {};
        openDrawer({eyebrow:t('ops_user_details'), title:loaded.title || loaded.first_name || `ID ${id}`, body:drawerLoading()});
        ops.drawerController?.abort();
        ops.drawerController = new AbortController();
        try {
            const data = await apiCall(`/api/users/${id}/orders?limit=6&offset=0`, {
                signal:ops.drawerController.signal,
                timeoutMs:30000,
            });
            const user = data.user || loaded;
            const name = user.username ? `@${user.username}` : (user.first_name || `ID ${id}`);
            setDrawer({
                eyebrow:t('ops_user_details'),
                title:name,
                body:`<section class="ops-client-identity"><i class="fa-solid fa-user"></i><div><h3>${escapeHtml(name)}</h3><p><code>${id}</code> · ${escapeHtml(user.language || '—')}</p></div></section>
                    <section class="ops-insight-grid ops-client-metrics">
                        <div><span>${escapeHtml(t('ops_user_total_orders'))}</span><strong>${safeNumber(data.total ?? user.total_orders)}</strong></div>
                        <div><span>${escapeHtml(t('ops_user_spent'))}</span><strong>${money(user.total_spent)}</strong></div>
                        <div><span>${escapeHtml(t('ops_user_wallet'))}</span><strong>${money(user.wallet_balance ?? loaded.amount)}</strong></div>
                    </section>
                    <section><h4>${escapeHtml(t('ops_user_orders'))}</h4>${userOrdersMarkup(data.orders || [])}</section>`,
                actions:`<button type="button" class="btn-secondary" data-ops-action="user-history" data-id="${id}"><i class="fa-solid fa-bag-shopping"></i><span>${escapeHtml(t('ops_open_purchase_history'))}</span></button>
                    <button type="button" class="btn-secondary" data-ops-action="user-credit" data-id="${id}"><i class="fa-solid fa-circle-plus"></i><span>${escapeHtml(t('ops_credit_wallet'))}</span></button>
                    <button type="button" class="btn-secondary danger-quiet" data-ops-action="user-debit" data-id="${id}"><i class="fa-solid fa-circle-minus"></i><span>${escapeHtml(t('ops_debit_wallet'))}</span></button>`,
            });
        } catch (error) {
            if (error.message === 'REQUEST_CANCELLED') return;
            setDrawer({eyebrow:t('ops_user_details'), title:`ID ${id}`, body:`<div class="ops-error-state"><p>${escapeHtml(error.message)}</p></div>`});
        }
    }

    function openSupplierDrawer(code) {
        const supplier = ops.suppliers.find(item => item.code === code)
            || state.supplierBots.find(item => item.code === code)
            || {code, name:code};
        const status = supplier.configured && supplier.enabled ? t('ops_status_active') : t('ops_status_inactive');
        openDrawer({
            eyebrow:t('ops_supplier_details'),
            title:supplier.name || supplier.code,
            body:`<section class="ops-client-identity supplier"><i class="fa-solid fa-server"></i><div><h3>${escapeHtml(supplier.name || supplier.code)}</h3><p>${escapeHtml(supplier.code || '')}</p></div><span class="status-badge ${supplier.configured && supplier.enabled ? 'success' : 'warning'}">${escapeHtml(status)}</span></section>
                <section class="ops-insight-grid">
                    <div><span>${escapeHtml(t('ops_supplier_products'))}</span><strong>${safeNumber(supplier.selected_count)}</strong></div>
                    <div><span>${escapeHtml(t('th_product'))}</span><strong>${safeNumber(supplier.products_count)}</strong></div>
                    <div><span>${escapeHtml(t('ops_last_sync'))}</span><strong>${escapeHtml(supplier.last_sync ? localDate(supplier.last_sync) : '—')}</strong></div>
                </section>`,
            actions:`<button type="button" class="btn-primary" data-ops-action="supplier" data-code="${escapeHtml(supplier.code || '')}"><i class="fa-solid fa-arrow-up-right-from-square"></i><span>${escapeHtml(t('ops_open_management'))}</span></button>`,
        });
    }

    function openProfitDrawer() {
        const economics = ops.overview?.economics || {};
        openDrawer({
            eyebrow:t('ops_profit_details'),
            title:money(economics.known_profit_30d),
            body:`<section class="ops-profit-explanation"><i class="fa-solid fa-circle-info"></i><p>${escapeHtml(t('ops_profit_explanation'))}</p></section>
                <section class="ops-insight-grid"><div><span>${escapeHtml(t('ops_known_profit'))}</span><strong>${money(economics.known_profit_30d)}</strong></div><div><span>${escapeHtml(t('ops_profit_coverage'))}</span><strong>${safeNumber(economics.known_profit_orders_30d)}</strong></div></section>`,
            actions:`<button type="button" class="btn-primary" data-ops-tab="supplier-bots-tab"><i class="fa-solid fa-chart-line"></i><span>${escapeHtml(t('ops_open_supplier_stats'))}</span></button>`,
        });
    }

    function renderCustomizeDrawer() {
        const layout = validLayout();
        const hidden = hiddenModules();
        openDrawer({
            eyebrow:t('ops_customize'),
            title:t('ops_customize_title'),
            body:`<p class="ops-drawer-help">${escapeHtml(t('ops_customize_help'))}</p>
                <div id="ops-module-sorter" class="ops-module-sorter">${layout.map(key => `<div data-module="${key}">
                    <i class="fa-solid fa-grip-vertical" aria-hidden="true"></i>
                    <strong>${escapeHtml(t(MODULE_KEYS[key]))}</strong>
                    <label><input type="checkbox" data-ops-module-toggle="${key}" ${hidden.has(key) ? '' : 'checked'}><span>${escapeHtml(t('ops_show_module'))}</span></label>
                </div>`).join('')}</div>`,
            actions:`<button type="button" class="btn-secondary" data-ops-action="reset-layout"><i class="fa-solid fa-rotate-left"></i><span>${escapeHtml(t('ops_reset_layout'))}</span></button>
                <button type="button" class="btn-primary" data-ops-action="save-layout"><i class="fa-solid fa-floppy-disk"></i><span>${escapeHtml(t('btn_save'))}</span></button>`,
        });
        const sorter = document.getElementById('ops-module-sorter');
        if (window.Sortable && sorter) {
            ops.customizeSortable = new Sortable(sorter, {handle:'.fa-grip-vertical', animation:140});
        }
    }

    function currentCustomizeValues() {
        const rows = [...document.querySelectorAll('#ops-module-sorter [data-module]')];
        const layout = rows.map(row => row.dataset.module).filter(key => MODULE_KEYS[key]);
        const hidden = new Set(rows.filter(row => !row.querySelector('input')?.checked).map(row => row.dataset.module));
        return {layout, hidden};
    }

    function updateCockpitSignals() {
        const overview = ops.overview || {};
        const actions = overview.actions || {};
        const payment = ops.paymentReview || state.paymentReviewSummary || {};
        const stock = ops.stats?.stock_summary || state.lastStats?.stock_summary || [];
        const criticalStock = stock.filter(item => item.delivery_type !== 'activation' && ['out', 'soon'].includes(item.stock_risk)).length;
        const supplierIssues = ops.suppliers.filter(supplier => {
            if (!supplier.configured || !supplier.enabled) return false;
            if (!supplier.last_sync) return true;
            return Date.now() - parseUTCDate(supplier.last_sync).getTime() > 6 * 60 * 60 * 1000;
        }).length;
        document.getElementById('ops-underpaid-count').textContent = safeNumber(payment.underpaid);
        document.getElementById('ops-activation-count').textContent = safeNumber(actions.pending_activations);
        document.getElementById('ops-stock-count').textContent = criticalStock;
        document.getElementById('ops-supplier-count').textContent = supplierIssues;
        const economics = overview.economics || {};
        document.getElementById('ops-known-profit').textContent = money(economics.known_profit_30d);
        document.getElementById('ops-known-profit-coverage').textContent = safeNumber(economics.known_profit_orders_30d)
            ? tf('ops_profit_coverage', {count:safeNumber(economics.known_profit_orders_30d)})
            : t('ops_profit_coverage_empty');
    }

    function activityItems() {
        const result = [];
        const seen = new Set();
        const overview = ops.overview || state.dashboardOverview || {};
        const actions = overview.actions || {};
        const stock = ops.stats?.stock_summary || state.lastStats?.stock_summary || [];
        (state.paymentReviewItems || []).filter(item => item.category === 'underpaid' && !item.resolved).slice(0, 4).forEach(item => {
            const key = `payment:${item.payment_id}`;
            if (seen.has(key)) return;
            seen.add(key);
            result.push({
                key,
                icon:'circle-exclamation',
                tone:'coral',
                title:t('ops_activity_underpaid'),
                detail:`${item.product_name || item.payment_id} · ${safeNumber(item.actually_paid).toFixed(4)} USDT`,
                date:item.updated_at || item.created_at,
                tab:'payment-review-tab',
            });
        });
        (ops.overview?.recent_orders || []).forEach(order => {
            const key = `order:${order.id}`;
            if (seen.has(key)) return;
            seen.add(key);
            result.push({
                key,
                icon:order.status === 'COMPLETED' ? 'circle-check' : 'receipt',
                tone:order.status === 'COMPLETED' ? 'mint' : 'cobalt',
                title:tf('ops_activity_order', {id:order.id}),
                detail:`${order.product_name || `#${order.product_id}`} · ${money(order.amount_usd)}`,
                date:order.created_at,
                order,
            });
        });
        if (safeNumber(actions.pending_activations) > 0) {
            result.push({
                key:'activation:pending',
                icon:'bolt',
                tone:'cobalt',
                title:t('ops_activity_activation'),
                detail:String(safeNumber(actions.pending_activations)),
                date:'',
                tab:'activations-tab',
            });
        }
        const criticalStock = stock.filter(item => item.delivery_type !== 'activation' && ['out', 'soon'].includes(item.stock_risk));
        if (criticalStock.length) {
            result.push({
                key:'stock:critical',
                icon:'box-open',
                tone:'amber',
                title:t('ops_critical_stock'),
                detail:criticalStock.slice(0, 3).map(item => item.name || `#${item.product_id}`).join(', '),
                date:'',
                tab:'inventory-tab',
            });
        }
        ops.suppliers.filter(supplier => supplier.configured && supplier.enabled && (!supplier.last_sync || Date.now() - parseUTCDate(supplier.last_sync).getTime() > 6 * 60 * 60 * 1000)).slice(0, 2).forEach(supplier => {
            const key = `supplier:${supplier.code}`;
            if (seen.has(key)) return;
            seen.add(key);
            result.push({key, icon:'server', tone:'amber', title:t('ops_activity_supplier'), detail:supplier.name || supplier.code, date:supplier.last_sync, supplier});
        });
        return result.sort((a, b) => {
            const at = a.date ? parseUTCDate(a.date).getTime() : 0;
            const bt = b.date ? parseUTCDate(b.date).getTime() : 0;
            return bt - at;
        }).slice(0, 10);
    }

    function renderActivityCenter() {
        if (!DOM.recentOrdersList) return;
        const items = activityItems();
        DOM.recentOrdersList.innerHTML = items.length ? items.map(item => {
            const action = item.order
                ? `data-ops-open="order" data-id="${safeNumber(item.order.id)}"`
                : item.supplier
                    ? `data-ops-open="supplier" data-code="${escapeHtml(item.supplier.code)}"`
                    : `data-ops-tab="${escapeHtml(item.tab || 'dashboard-tab')}"`;
            return `<button type="button" class="ops-activity-item" ${action}>
                <span class="ops-activity-icon ${item.tone}"><i class="fa-solid fa-${item.icon}"></i></span>
                <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.detail)}</small></span>
                <time>${escapeHtml(item.date ? localDate(item.date) : '')}</time>
                <i class="fa-solid fa-chevron-right"></i>
            </button>`;
        }).join('') : `<p class="empty-state">${escapeHtml(t('ops_activity_empty'))}</p>`;
    }

    async function ensureSupplierSummaries(force=false) {
        if (document.hidden || (!force && Date.now() - ops.supplierLoadedAt < 120000)) return;
        try {
            const data = await apiCall('/api/supplier-bots');
            ops.suppliers = data.providers || [];
            ops.supplierLoadedAt = Date.now();
            state.supplierBots = ops.suppliers;
            updateCockpitSignals();
            renderActivityCenter();
        } catch (error) {
            console.warn('Supplier summaries unavailable for cockpit:', error);
        }
    }

    const QUICK_ACTIONS = [
        {id:'add-product', icon:'plus', label:'ops_action_add_product', keywords:'product produit'},
        {id:'add-stock', icon:'boxes-stacked', label:'ops_action_add_stock', keywords:'stock inventory'},
        {id:'activations', icon:'bolt', label:'ops_action_activation', keywords:'activation'},
        {id:'supplier-sync', icon:'arrows-rotate', label:'ops_action_supplier_sync', keywords:'supplier fournisseur api sync'},
        {id:'promo', icon:'ticket', label:'ops_action_promo', keywords:'promo code discount'},
    ];

    function executeQuickAction(id) {
        closeCommandPalette();
        if (id === 'add-product') {
            switchTab('inventory-tab');
            setTimeout(() => document.getElementById('btn-add-product')?.click(), 80);
        } else if (id === 'add-stock') {
            switchTab('inventory-tab');
        } else if (id === 'activations') {
            switchTab('activations-tab');
        } else if (id === 'supplier-sync') {
            switchTab('supplier-bots-tab');
            setTimeout(() => document.getElementById('btn-supplier-sync')?.focus(), 120);
        } else if (id === 'promo') {
            switchTab('inventory-tab');
            setTimeout(() => {
                document.querySelector('[data-subtab="promos-sub"]')?.click();
                document.getElementById('btn-add-promo')?.click();
            }, 100);
        }
    }

    function commandTypeLabel(type) {
        return t({product:'ops_type_product', user:'ops_type_user', order:'ops_type_order', supplier:'ops_type_supplier'}[type] || 'ops_details');
    }

    function renderCommandResults(items, sectionLabel='ops_command_actions') {
        ops.commandItems = items;
        ops.commandIndex = Math.min(ops.commandIndex, Math.max(0, items.length - 1));
        if (!items.length) {
            els.commandResults.innerHTML = `<p class="ops-command-empty">${escapeHtml(t('ops_command_empty'))}</p>`;
            return;
        }
        els.commandResults.innerHTML = `<p class="ops-command-section">${escapeHtml(t(sectionLabel))}</p>${items.map((item, index) => `<button type="button" role="option" aria-selected="${index === ops.commandIndex}" class="${index === ops.commandIndex ? 'active' : ''}" data-command-index="${index}">
            <span class="ops-command-icon"><i class="fa-solid fa-${item.icon || 'arrow-right'}"></i></span>
            <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.subtitle || commandTypeLabel(item.entity_type))}</small></span>
            ${item.status ? `<span class="status-badge neutral">${escapeHtml(item.status)}</span>` : '<i class="fa-solid fa-arrow-right"></i>'}
        </button>`).join('')}`;
    }

    function defaultCommandItems() {
        return QUICK_ACTIONS.map(action => ({
            kind:'action',
            id:action.id,
            icon:action.icon,
            title:t(action.label),
            subtitle:t('ops_command_actions'),
            search:`${t(action.label)} ${action.keywords}`.toLowerCase(),
        }));
    }

    function openCommandPalette() {
        ops.drawerReturnFocus = document.activeElement;
        els.command.classList.remove('hidden');
        document.body.classList.add('ops-command-open');
        els.commandInput.value = '';
        els.commandStatus.textContent = '';
        renderCommandResults(defaultCommandItems());
        requestAnimationFrame(() => els.commandInput.focus());
    }

    function closeCommandPalette() {
        ops.commandController?.abort();
        ops.commandController = null;
        clearTimeout(ops.commandTimer);
        els.command.classList.add('hidden');
        document.body.classList.remove('ops-command-open');
        ops.drawerReturnFocus?.focus?.();
        ops.drawerReturnFocus = null;
    }

    async function runCommandSearch(query) {
        const normalized = query.trim();
        if (!normalized) {
            els.commandStatus.textContent = '';
            renderCommandResults(defaultCommandItems());
            return;
        }
        const matchingActions = defaultCommandItems().filter(item => item.search.includes(normalized.toLowerCase()));
        const supplierMatches = ops.suppliers.filter(item => `${item.name} ${item.code}`.toLowerCase().includes(normalized.toLowerCase())).slice(0, 4).map(item => ({
            kind:'entity', entity_type:'supplier', entity_id:item.code, icon:'server',
            title:item.name || item.code, subtitle:commandTypeLabel('supplier'),
        }));
        ops.commandController?.abort();
        ops.commandController = new AbortController();
        els.commandStatus.textContent = t('ops_command_searching');
        try {
            let remote = ops.searchCache.get(normalized.toLowerCase());
            if (!remote || Date.now() - remote.time > 30000) {
                const data = await apiCall(`/api/dashboard/search?q=${encodeURIComponent(normalized)}&limit=14`, {
                    signal:ops.commandController.signal,
                    timeoutMs:15000,
                });
                remote = {time:Date.now(), results:data.results || []};
                ops.searchCache.set(normalized.toLowerCase(), remote);
            }
            const entities = remote.results.map(result => ({
                ...result,
                kind:'entity',
                icon:{product:'box-open', user:'user', order:'receipt'}[result.entity_type] || 'arrow-right',
            }));
            els.commandStatus.textContent = `${entities.length + supplierMatches.length}`;
            renderCommandResults([...matchingActions, ...supplierMatches, ...entities], 'ops_command_entities');
        } catch (error) {
            if (error.message === 'REQUEST_CANCELLED') return;
            els.commandStatus.textContent = '';
            renderCommandResults([...matchingActions, ...supplierMatches]);
        }
    }

    function executeCommandItem(item) {
        if (!item) return;
        if (item.kind === 'action') return executeQuickAction(item.id);
        closeCommandPalette();
        if (item.entity_type === 'product') openProductDrawer(item.entity_id);
        else if (item.entity_type === 'user') openUserDrawer(item.entity_id, item);
        else if (item.entity_type === 'order') openOrderDrawer(item.entity_id, item);
        else if (item.entity_type === 'supplier') openSupplierDrawer(item.entity_id);
    }

    function updateCommandSelection(nextIndex) {
        if (!ops.commandItems.length) return;
        ops.commandIndex = (nextIndex + ops.commandItems.length) % ops.commandItems.length;
        const buttons = [...els.commandResults.querySelectorAll('[data-command-index]')];
        buttons.forEach((button, index) => {
            button.classList.toggle('active', index === ops.commandIndex);
            button.setAttribute('aria-selected', String(index === ops.commandIndex));
        });
        buttons[ops.commandIndex]?.scrollIntoView({block:'nearest'});
    }

    function activateMobileTab(tabId) {
        document.querySelectorAll('#ops-mobile-nav [data-ops-tab]').forEach(button => {
            button.classList.toggle('active', button.dataset.opsTab === tabId);
        });
    }

    function handleOpsClick(event) {
        const tabButton = event.target.closest('[data-ops-tab]');
        if (tabButton) {
            event.preventDefault();
            closeDrawer();
            switchTab(tabButton.dataset.opsTab);
            return;
        }
        const open = event.target.closest('[data-ops-open]');
        if (open) {
            event.preventDefault();
            event.stopPropagation();
            const type = open.dataset.opsOpen;
            if (type === 'product') openProductDrawer(open.dataset.id);
            else if (type === 'order') openOrderDrawer(open.dataset.id);
            else if (type === 'supplier') openSupplierDrawer(open.dataset.code);
            else if (type === 'profit') openProfitDrawer();
            return;
        }
        const action = event.target.closest('[data-ops-action]');
        if (!action) return;
        event.preventDefault();
        const id = safeEntityId(action.dataset.id);
        const code = action.dataset.code || '';
        switch (action.dataset.opsAction) {
            case 'save-layout': {
                const values = currentCustomizeValues();
                saveCockpitLayout(values.layout, values.hidden);
                closeDrawer();
                break;
            }
            case 'reset-layout':
                localStorage.removeItem(LAYOUT_KEY);
                localStorage.removeItem(HIDDEN_KEY);
                applyCockpitLayout();
                renderCustomizeDrawer();
                break;
            case 'retry-product': if (id) openProductDrawer(id, true); break;
            case 'edit-product': if (id) { closeDrawer(); openEditProduct(id); } break;
            case 'stock': if (id) { closeDrawer(); openStockModal(id); } break;
            case 'supplier':
            case 'supplier-best':
                closeDrawer();
                switchTab('supplier-bots-tab');
                if (code) setTimeout(() => selectSupplierBot(code), 80);
                break;
            case 'download-order': downloadCurrentOrderTxt(); break;
            case 'user-history':
                if (id && ops.legacyOpenUser) { closeDrawer(); ops.legacyOpenUser(id); }
                break;
            case 'user-credit': if (id) { closeDrawer(); creditWallet(id); } break;
            case 'user-debit': if (id) { closeDrawer(); debitWallet(id); } break;
            default: break;
        }
    }

    function trapDrawerFocus(event) {
        if (event.key !== 'Tab' || els.drawer.classList.contains('hidden')) return;
        const focusable = [...els.drawer.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href]')];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function setupEvents() {
        document.addEventListener('click', handleOpsClick, true);
        els.commandTrigger.addEventListener('click', openCommandPalette);
        els.command.addEventListener('click', event => {
            if (event.target === els.command) closeCommandPalette();
            const result = event.target.closest('[data-command-index]');
            if (result) executeCommandItem(ops.commandItems[Number(result.dataset.commandIndex)]);
        });
        els.commandInput.addEventListener('input', () => {
            clearTimeout(ops.commandTimer);
            ops.commandTimer = setTimeout(() => runCommandSearch(els.commandInput.value), 260);
        });
        els.commandInput.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown') { event.preventDefault(); updateCommandSelection(ops.commandIndex + 1); }
            else if (event.key === 'ArrowUp') { event.preventDefault(); updateCommandSelection(ops.commandIndex - 1); }
            else if (event.key === 'Enter') { event.preventDefault(); executeCommandItem(ops.commandItems[ops.commandIndex]); }
        });
        document.addEventListener('change', event => {
            const filter = event.target.closest('[data-ops-filter="supplier-unavailable"]');
            if (!filter) return;
            ops.showUnavailableSuppliers = Boolean(filter.checked);
            if (ops.currentProductInsights) renderProductInsights(ops.currentProductInsights);
        });
        els.drawerClose.addEventListener('click', closeDrawer);
        els.drawerBackdrop.addEventListener('click', closeDrawer);
        els.customize.addEventListener('click', renderCustomizeDrawer);
        document.getElementById('ops-mobile-more').addEventListener('click', () => document.getElementById('mobile-menu-btn')?.click());
        document.addEventListener('keydown', event => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                if (els.command.classList.contains('hidden')) openCommandPalette(); else closeCommandPalette();
            } else if (event.key === 'Escape') {
                if (!els.command.classList.contains('hidden')) closeCommandPalette();
                else if (!els.drawer.classList.contains('hidden')) closeDrawer();
            }
            trapDrawerFocus(event);
        });
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && state.currentTab === 'dashboard-tab') ensureSupplierSummaries();
        });
        document.addEventListener('ventebot:data', event => {
            const {type, payload} = event.detail || {};
            if (type === 'overview') {
                ops.overview = payload;
                updateCockpitSignals();
                renderActivityCenter();
                ensureSupplierSummaries();
            } else if (type === 'stats') {
                ops.stats = payload;
                updateCockpitSignals();
            } else if (type === 'payment-review') {
                ops.paymentReview = payload.summary || {};
                updateCockpitSignals();
                renderActivityCenter();
            } else if (type === 'tab') {
                activateMobileTab(payload.tabId);
                ops.commandController?.abort();
            } else if (type === 'language') {
                updateCockpitSignals();
                renderActivityCenter();
                if (!els.drawer.classList.contains('hidden')) closeDrawer();
            }
        });
    }

    function initialize() {
        Object.assign(els, {
            commandTrigger:document.getElementById('btn-command-palette'),
            command:document.getElementById('command-palette'),
            commandInput:document.getElementById('ops-command-input'),
            commandResults:document.getElementById('ops-command-results'),
            commandStatus:document.getElementById('ops-command-status'),
            drawer:document.getElementById('ops-context-drawer'),
            drawerBackdrop:document.getElementById('ops-drawer-backdrop'),
            drawerClose:document.getElementById('ops-drawer-close'),
            drawerEyebrow:document.getElementById('ops-drawer-eyebrow'),
            drawerTitle:document.getElementById('ops-drawer-title'),
            drawerBody:document.getElementById('ops-drawer-body'),
            drawerActions:document.getElementById('ops-drawer-actions'),
            customize:document.getElementById('btn-customize-cockpit'),
        });
        if (!els.commandTrigger || !els.drawer) return;
        applyCockpitLayout();
        ops.legacyOpenOrder = window.openOrderDetail;
        ops.legacyOpenUser = window.openUserPurchases;
        window.openOrderDetail = openOrderDrawer;
        window.openUserPurchases = openUserDrawer;
        setupEvents();
        activateMobileTab(state.currentTab);
        updateCockpitSignals();
    }

    document.addEventListener('DOMContentLoaded', initialize);
    window.VenteOps = {
        openProduct:openProductDrawer,
        openOrder:openOrderDrawer,
        openUser:openUserDrawer,
        openSupplier:openSupplierDrawer,
        openCommand:openCommandPalette,
    };
})();
