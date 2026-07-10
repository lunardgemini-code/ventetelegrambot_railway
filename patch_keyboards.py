# -*- coding: utf-8 -*-
import io

file_path = r'N:\geminiopus\ventetelegrambot_railway\utils\keyboards.py'
with io.open(file_path, 'a', encoding='utf-8') as f:
    f.write('\n\ndef referral_dashboard_keyboard(lang: str) -> InlineKeyboardMarkup:\n    \"\"\"Keyboard for the referral dashboard.\"\"\"\n    from utils.locales import t\n    btn_text = {\"fr\": \"👥 Voir mes filleuls\", \"en\": \"👥 View my referrals\", \"ar\": \"👥 عرض الإحالات الخاصة بي\"}.get(lang, \"👥 Voir mes filleuls\")\n    buttons = [\n        [InlineKeyboardButton(btn_text, callback_data=\"view_referrals_list\")],\n        [make_button(\"btn_back\", lang, callback_data=\"back_main\")]\n    ]\n    return InlineKeyboardMarkup(buttons)\n')
print('Appended referral_dashboard_keyboard')
