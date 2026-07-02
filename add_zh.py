import re

zh_dict_str = """
    # ═══════════════════════════════════════════
    #  CHINESE
    # ═══════════════════════════════════════════
    "zh": {
        "choose_language": "🌐 选择您的语言：",
        "language_set": "✅ 语言已设为中文！",
        "welcome": (
            "🎉 <b>欢迎！</b>\\n\\n"
            "🎯 <b>快速指南：</b>\\n"
            "1. 点击 \\"🛒 购买\\"\\n"
            "2. 选择您想要的商品\\n"
            "3. 完成支付\\n"
            "4. 支付完成后，发送订单号以供验证\\n\\n"
            "🎯 <b>请选择一个选项：</b>"
        ),
        "quick_menu_enabled": "🎯 快捷菜单已在聊天栏下方启用。",
        "btn_buy": "🛒 购买",
        "btn_profile": "👤 个人资料",
        "btn_history": "📋 购买记录",
        "btn_support": "💬 客服",
        "btn_products": "🛍️ 产品",
        "btn_back": "◀️ 返回",
        "btn_cancel": "❌ 取消",
        "btn_refresh": "🔄 刷新产品",
        "btn_buy_now": "🛒 立即购买",
        "btn_pay_binance": "◇ 币安支付 (Binance Pay)",
        "btn_i_paid": "✅ 我已支付",
        "btn_new_ticket": "📝 新建工单",
        "btn_my_tickets": "📋 我的工单",
        "btn_language": "🌐 语言",
        "btn_start": "🚀 开始",
        "btn_wallet": "💰 钱包",
        "btn_referral": "👥 邀请好友",
        "wallet_title": "💰 <b>我的钱包</b>",
        "wallet_balance_lbl": "💵 余额：",
        "wallet_topup": "➕ 充值",
        "wallet_history": "📜 记录",
        "wallet_topup_title": "💰 <b>钱包充值</b>\\n\\n✏️ 发送您想要充值的美元金额：\\n(示例：5, 10.50, 25)",
        "wallet_topup_preset": "或选择预设金额：",
        "wallet_invalid_amount": "❌ 金额无效。请输入数字 (例：5, 10, 20)。",
        "wallet_credited": "✅ <b>充值成功！</b>\\n\\n💵 增加：+${amount}\\n💰 新余额：${balance}",
        "wallet_insufficient": "❌ <b>余额不足！</b>\\n\\n💰 您的余额：${balance}\\n💲 需要金额：${required}\\n\\n请先给钱包充值。",
        "wallet_paid": "✅ <b>钱包支付成功！</b>\\n\\n💲 扣除：${amount}\\n💰 剩余余额：${balance}",
        "wallet_no_transactions": "📭 暂无交易记录。",
        "wallet_tx_topup": "➕ 充值",
        "wallet_tx_purchase": "🛒 购买",
        "btn_pay_wallet": "💰 钱包支付 (${balance})",
        "categories_title": "📂 <b>分类</b>\\n\\n请选择一个分类：",
        "choose_quantity": "🔢 <b>数量</b>\\n\\n✏️ 请发送您要购买的数量：\\n📦 可用库存：{stock}",
        "invalid_quantity": "❌ <b>数量无效</b>\\n\\n请发送一个有效的正数。",
        "insufficient_stock": "❌ <b>库存不足</b>\\n\\n我们目前只有 {stock} 个库存。请选择较小的数量。",
        "quantity_lbl": "🔢 <b>数量：</b> {qty}",
        "no_categories": "📭 暂无可用分类。",
        "product_not_found": "❌ 找不到该产品。",
        "access_denied": "❌ 拒绝访问：该订单不属于您。",
        "cannot_cancel": "❌ 此订单无法取消 (状态：{status})",
        "tx_used": "❌ 此交易已使用过。",
        "max_topup": "⚠️ 最高充值金额为 $10,000。",
        "contact_support": "我已支付 / 联系客服",
        "banned_msg": "⛔ 您已被本机器人封禁。",
        "out_of_stock": "❌ <b>缺货！</b>\\n此产品目前不可用。",
        "product_detail": (
            "{emoji} <b>{name}</b>\\n"
            "💵 <b>价格：</b> {price}\\n"
            "🛡️ <b>质保：</b> {warranty} 天\\n"
            "📦 <b>库存：</b> {stock} 个\\n"
            "📊 <b>已售出：</b> {sold} 个\\n\\n"
            "❞ <b>产品描述：</b>\\n{description}"
        ),
        "new_order": "🛒 <b>新订单</b>",
        "product_lbl": "📦 <b>产品：</b>",
        "total_lbl": "💰 <b>总计：</b>",
        "ref_lbl": "🔖 <b>参考号：</b>",
        "choose_payment": "💳 <b>请选择支付方式：</b>",
        "binance_title": "◇ <b>币安支付 (Binance Pay)</b>",
        "binance_id_lbl": "◇ <b>币安 ID</b> (点击复制)：",
        "amount_lbl": "💰 <b>需转账金额：</b>",
        "pay_instructions": "📝 <b>付款说明：</b>",
        "pay_step1": "1️⃣ 通过币安支付发送准确的金额",
        "pay_step2": "2️⃣ 付款后，请在此发送 <b>订单号 (Order ID)</b> 或\\n   <b>交易参考号</b>",
        "waiting_payment": "⏳ <i>等待您的付款中…</i>",
        "verifying": "🔍 正在验证付款…",
        "payment_confirmed": "✅ <b>付款已确认！</b>",
        "your_account": "📧 <b>这是您的账号信息：</b>",
        "warranty_lbl": "🛡️ <b>质保：</b> {days} 天",
        "save_info": "📌 <b>请妥善保存此信息</b>",
        "thank_you": "感谢您的购买！🙏",
        "delivery_error": "⚠️ <b>库存不足！</b>\\n看来您支付耗时较长，库存已售罄。\\n\\n⚠️ <b>需要采取的行动：</b>请向客服提供订单号 <b>#{order_id}</b> 以进行人工发货或退款。",
        "payment_not_detected": "⏳ <b>未检测到付款</b>",
        "retry_order_id": "请核实您已完成付款，\\n然后<b>重新发送订单号重试</b>。",
        "support_hint": "💡 <i>如果问题仍然存在，请联系客服。</i>",
        "no_pending_order": "⚠️ 没有待处理的订单。请使用 /start 重新开始。",
        "check_title": "📝 <b>付款验证</b>",
        "order_lbl": "🔖 <b>订单：</b>",
        "send_order_id": "📩 请发送 <b>订单号 (Order ID)</b> 或 <b>交易参考号</b>\\n以验证您的付款。",
        "promo_prompt": "🎫 <b>使用优惠码</b>\\n\\n✏️ 请发送您的优惠码：",
        "promo_success": "✅ <b>优惠码已应用！</b>\\n\\n🎉 折扣金额：<b>{discount}</b>\\n💰 新总价：<b>{total}</b>",
        "promo_invalid": "❌ <b>优惠码无效或已过期！</b>\\n\\n请检查优惠码并重新发送，或者取消操作。",
        "promo_max_uses_reached": "❌ <b>已达使用上限！</b>\\n\\n您已经达到了该优惠码的最大使用次数限制。",
        "promo_product_invalid": "❌ <b>产品无效！</b>\\n\\n此优惠码不能用于该产品。",
        "promo_qty_limit": "❌ <b>数量限制！</b>\\n\\n此优惠码只能用于最多购买 {max_qty} 件的订单。",
        "promo_already_applied": "❌ <b>该订单已经应用过优惠码。</b>",
        "order_expired_notification": "⏳ <b>时间已过！</b>\\n您的订单 <b>#{order_id}</b> 已被自动取消，因为在 5 分钟期限内未收到付款。\\n如果您仍希望购买或已经付款，请发起新订单。",
        "order_cancelled": "❌ <b>订单已取消</b>\\n\\n您的订单已被取消。\\n返回主菜单以继续。",
        "order_timeout": "❌ <b>订单已过期</b>\\n\\n您的订单 #{id} 已过期，因为在 5 分钟内未收到付款。",
        "order_error": "⚠️ 创建订单时出错。",
        "pay_error": "⚠️ 初始化付款时出错。",
        "cancel_error": "⚠️ 取消时出错。",
        "verify_error": "⚠️ 验证错误。请重试。",
        "profile_title": "👤 <b>您的个人资料</b>",
        "id_lbl": "🆔 <b>ID：</b>",
        "name_lbl": "👤 <b>昵称：</b>",
        "joined_lbl": "📅 <b>加入时间：</b>",
        "purchases_lbl": "🛒 <b>总购买次数：</b>",
        "spent_lbl": "💰 <b>总消费：</b>",
        "history_title": "📋 <b>购买记录</b>",
        "no_orders": "📭 您还没有订单。",
        "order_detail": "📦 <b>订单 #{id}</b>",
        "status_lbl": "📊 <b>状态：</b>",
        "date_lbl": "📅 <b>日期：</b>",
        "account_lbl": "📧 <b>账号：</b>",
        "support_title": "💬 <b>客服</b>\\n\\n如需客服支持，请在 Telegram 上联系管理员：@Drbatman2",
        "describe_problem": "📝 请描述您的问题：",
        "ticket_created": "✅ 工单 #{id} 已创建！我们将尽快回复。",
        "no_tickets": "📭 暂无工单。",
        "ticket_title": "🎫 <b>工单 #{id}</b>",
        "message_lbl": "📝 <b>信息：</b>",
        "reply_lbl": "💬 <b>回复：</b>",
        "ticket_replied": "💬 <b>对您工单 #{id} 的回复</b>",
        "ticket_closed": "🔒 您的工单 #{id} 已关闭。\\n感谢您的联系！🙏",
        "s_pending": "⏳ 待处理",
        "s_completed": "✅ 已完成",
        "s_cancelled": "❌ 已取消",
        "s_awaiting": "⏳ 等待付款",
        "s_open": "🟢 开启",
        "s_replied": "💬 已回复",
        "s_closed": "🔴 已关闭",
        "notif_sale": "🔔 <b>新销售！</b>",
        "notif_low_stock": "⚠️ <b>库存不足！</b>",
        "notif_remaining": "📉 剩余：",
        "notif_manual": "🔔 <b>需要人工验证</b>",
        "notif_order_id": "📝 提交的订单号：",
        "error_generic": "⚠️ 发生错误。",
        "admin_panel": "🔧 <b>管理面板</b>\\n\\n请选择一个选项：",
        "admin_access_denied": "🚫 拒绝访问。仅限管理员。",
        "admin_categories_title": "📂 <b>分类管理</b>\\n\\n总计：{count} 个分类",
        "admin_products_title": "📦 <b>产品管理</b>",
        "admin_stock_title": "📦 <b>库存管理</b>\\n\\n请选择要添加库存的产品：",
        "admin_enter_cat_name": "📝 请输入分类名称：",
        "admin_enter_cat_emoji": "🎨 请发送该分类的 Emoji (或输入 /skip 跳过)：",
        "admin_cat_created": "✅ 分类已创建！",
        "admin_enter_prod_name": "📝 请输入产品名称：",
        "admin_enter_prod_desc": "📝 请输入产品描述 (或输入 /skip 跳过)：",
        "admin_enter_prod_price": "💰 请输入价格 (美元)：",
        "admin_enter_prod_warranty": "🔒 请输入质保天数 (或输入 /skip 设为 0)：",
        "admin_enter_prod_emoji": "🎨 请发送一个 Emoji (或输入 /skip 跳过)：",
        "admin_prod_created": "✅ 产品已创建！",
        "admin_enter_stock": "📋 请发送账号 (每行一个)：",
        "admin_stock_added": "✅ 已添加 {count} 个账号到库存！",
        "admin_stats_title": "📊 <b>统计信息 (30天)</b>",
        "admin_stats_revenue": "💰 收入：${revenue}",
        "admin_stats_orders": "📦 订单：{orders}",
        "admin_stats_completed": "✅ 已完成：{completed}",
        "admin_stats_users": "👥 用户：{users}",
        "admin_broadcast_prompt": "📢 请发送要向所有用户广播的消息：",
        "admin_broadcast_sent": "✅ 已发送给 {sent}/{total} 位用户。",
        "admin_no_pending": "✅ 没有待处理的订单。",
        "admin_no_tickets": "✅ 没有未解决的工单。",
        "admin_order_confirmed": "✅ 订单 #{id} 已确认！",
        "admin_ticket_replied": "✅ 工单 #{id} 已回复！",
        "admin_not_found": "❌ 未找到。",
        "admin_error": "⚠️ 错误。",
        "referral_title": "👥 <b>邀请好友计划</b>\\n\\n使用您的邀请链接邀请好友！每邀请 <b>20 位朋友</b>，您将免费获得一个 <b>免费链接</b>。\\n\\n如需领取奖励，请开启支持工单并联系管理员。\\n\\n🔗 <b>您的邀请链接：</b>\\n<code>{link}</code>\\n\\n📊 <b>统计信息：</b>\\n- 已邀请好友：<b>{count}</b>",
        "referral_notif": "🎁 <b>已收到邀请佣金！</b>\\n您已从您的朋友 {friend} 的购买中获得 <b>{amount}</b> 的佣金。",
        "btn_pay_bep20": "🪙 USDT 支付 (BEP20)",
        "bep20_title": "🪙 <b>USDT 支付 (BEP20)</b>",
        "bep20_address_lbl": "🪙 <b>USDT 充值地址 (BSC/BEP20)</b> (点击复制)：",
        "bep20_instructions": "📝 <b>付款说明：</b>\\n1️⃣ 将准确金额的 USDT (BEP20) 发送至上述地址。\\n2️⃣ 完成后，请在此发送 <b>交易哈希值 (Tx Hash)</b> 以供验证。",
        "bep20_waiting_payment": "⏳ <i>等待您的交易哈希值…</i>",
        "bep20_send_tx_hash": "📩 请发送 <b>交易哈希值 (Tx Hash)</b> 以验证您的付款。",
        "bep20_invalid_tx_hash": "❌ 交易哈希值无效。请发送有效的 66 字符哈希值 (以 0x 开头)。",
        "btn_pay_trc20": "🪙 USDT 支付 (TRC20)",
        "trc20_title": "🪙 <b>USDT 支付 (TRC20)</b>",
        "trc20_address_lbl": "🪙 <b>USDT 充值地址 (TRON/TRC20)</b> (点击复制)：",
        "trc20_instructions": "📝 <b>付款说明：</b>\\n1️⃣ 将准确金额的 USDT (TRC20) 发送至上述地址。\\n2️⃣ 完成后，请在此发送 <b>交易哈希值 (Tx Hash)</b> 以供验证。",
        "trc20_waiting_payment": "⏳ <i>等待您的交易哈希值…</i>",
        "trc20_send_tx_hash": "📩 请发送 <b>交易哈希值 (Tx Hash)</b> 以验证您的付款。",
        "trc20_invalid_tx_hash": "❌ 交易哈希值无效。请发送有效的 64 字符波场 (TRON) 哈希值 (不要带 0x)。",
        "tx_already_used": "❌ 此交易已用于其他订单。"
    }
}
"""

with open('utils/locales.py', 'r', encoding='utf-8') as f:
    loc_content = f.read()

# Add zh to LANGUAGES
if '"zh":' not in loc_content:
    loc_content = loc_content.replace(
        '"ar": "🇸🇦 العربية",',
        '"ar": "🇸🇦 العربية",\n    "zh": "🇨🇳 简体中文",'
    )

# Append zh_dict to TRANSLATIONS
if '"zh": {' not in loc_content:
    loc_content = re.sub(r'(\s*)\}\s*$', r',\n' + zh_dict_str + r'\n\1}', loc_content)
    with open('utils/locales.py', 'w', encoding='utf-8') as f:
        f.write(loc_content)
    print("Injected zh dictionary.")
else:
    print("zh already exists.")
