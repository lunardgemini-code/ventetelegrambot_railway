import os

filepath = 'handlers/payment.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the formatting
replacement = """async def _notify_admins_sale(context, order_id, product_id, amount):
    product = await get_product(product_id) if product_id else None
    prod_name = escape_html(product["name"]) if product else "?"
    text = (
        "🔔 <b>Nouvelle vente !</b>\\n"
        f"📦 Produit : {prod_name}\\n"
        f"💰 Montant : {format_price(amount)}\\n"
        f"🔖 Commande : #{order_id}"
    )"""

import re
content = re.sub(r'async def _notify_admins_sale\(context, order_id, product_id, amount\):.*?f"🔖 Commande : #\{order_id\}"\n    \)', replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed!")
