import codecs
import re

with codecs.open('handlers/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import
if 'get_confirmation_message' not in content:
    content = content.replace('from utils.locales import t', 'from utils.locales import t, get_confirmation_message')

# 2. Replace t('thank_you', user_lang) in the message
# In admin.py, it looks like:
#                     f"{t('save_info', user_lang)}\n\n"
#                     f"{t('thank_you', user_lang)}",
# We replace it with:
#                     f"{t('save_info', user_lang)}\n\n"
#                     f"{get_confirmation_message(product, user_lang, order_id)}",

old_pattern = re.compile(r'f"\{t\(\'save_info\', user_lang\)\}\\n\\n"\s*f"\{t\(\'thank_you\', user_lang\)\}",')
new_repl = r'''f"{t('save_info', user_lang)}\n\n"
                    f"{get_confirmation_message(product, user_lang, order_id)}",'''

content = old_pattern.sub(new_repl, content)

with codecs.open('handlers/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('admin.py updated.')
