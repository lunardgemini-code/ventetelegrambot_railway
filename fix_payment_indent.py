import codecs
import re

with codecs.open('handlers/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to fix the indentation and newlines in payment.py
# The block currently looks like:
#             conf_msg = get_confirmation_message(product, lang, order_id)
#                 footer = (
#                     f"{t('warranty_lbl', lang).format(days=warranty_days)}
# "
#                     f"{t('save_info', lang)}
# 
# "
#                     f"{conf_msg}"
#                 )

# Let's just fix it by finding "conf_msg = get_confirmation_message(product, lang, order_id)" and replacing the whole block up to ")" with a properly formatted string.
def fix_block(match):
    indent = match.group(1)
    return f"""{indent}conf_msg = get_confirmation_message(product, lang, order_id)
{indent}footer = (
{indent}    f"{{t('warranty_lbl', lang).format(days=warranty_days)}}\\n"
{indent}    f"{{t('save_info', lang)}}\\n\\n"
{indent}    f"{{conf_msg}}"
{indent})"""

pattern = re.compile(r'([ \t]+)conf_msg = get_confirmation_message\(product, lang, order_id\)\s+footer = \([\s\S]*?f"\{conf_msg\}"\s*\)')
content = pattern.sub(fix_block, content)

with codecs.open('handlers/payment.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("payment.py fixed")
