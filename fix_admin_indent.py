import codecs
import re

with codecs.open('handlers/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken f-string from the previous replacement
def fix_admin_block(match):
    indent = match.group(1)
    return f"""{indent}f"{{t('save_info', user_lang)}}\\n\\n"\n{indent}f"{{get_confirmation_message(product, user_lang, order_id)}}","""

pattern = re.compile(r'([ \t]+)f"\{t\(\'save_info\', user_lang\)\}[\s\S]*?f"\{get_confirmation_message\(product, user_lang, order_id\)\}",')
content = pattern.sub(fix_admin_block, content)

with codecs.open('handlers/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("admin.py fixed")
