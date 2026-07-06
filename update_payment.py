import codecs

with codecs.open('handlers/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import
if 'get_confirmation_message' not in content:
    content = content.replace('from utils.locales import t', 'from utils.locales import t, get_confirmation_message')

# 2. Replace instances in payment.py
old_footer = '''                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\\n"
                    f"{t('save_info', lang)}\\n\\n"
                    f"{t('thank_you', lang)}"
                )'''

new_footer = '''                conf_msg = get_confirmation_message(product, lang, order_id)
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\\n"
                    f"{t('save_info', lang)}\\n\\n"
                    f"{conf_msg}"
                )'''
                
content = content.replace(old_footer, new_footer)

# Also there's one with `footer = (` that might be indented differently or not assigned right there. Let's check lines 674, 882, 1323, 1603 in the original.
# Wait, I already replaced the exact string `old_footer`. If it matches, great. If not, we can use regex.
import re

old_footer_pattern = re.compile(r'footer = \(\s*f"\{t\(\'warranty_lbl\', lang\)\.format\(days=warranty_days\)\}\\n"\s*f"\{t\(\'save_info\', lang\)\}\\n\\n"\s*f"\{t\(\'thank_you\', lang\)\}"\s*\)')

new_footer_repl = r'''conf_msg = get_confirmation_message(product, lang, order_id)
                footer = (
                    f"{t('warranty_lbl', lang).format(days=warranty_days)}\n"
                    f"{t('save_info', lang)}\n\n"
                    f"{conf_msg}"
                )'''

content = old_footer_pattern.sub(new_footer_repl, content)

with codecs.open('handlers/payment.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('payment.py updated.')
