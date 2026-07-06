import codecs

with codecs.open('utils/locales.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper = '''
def get_confirmation_message(product: dict | None, lang: str, order_id: str | int = "") -> str:
    """Gets the custom confirmation message for a product, falling back to the default thank_you."""
    if not product:
        return t("thank_you", lang)

    col = f"confirmation_message_{lang}" if lang in ["fr", "ar", "zh"] else "confirmation_message"
    msg = product.get(col, "")
    
    if not msg:
        msg = product.get("confirmation_message", "")
        
    if msg:
        product_name = product.get("name", "")
        return msg.replace("{product}", str(product_name)).replace("{order_id}", str(order_id))
        
    return t("thank_you", lang)
'''

if 'get_confirmation_message' not in content:
    content += helper

with codecs.open('utils/locales.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Added get_confirmation_message to utils/locales.py')
