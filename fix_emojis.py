import os
import re

filepath = 'handlers/payment.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace using regex to catch the corrupted bytes
content = re.sub(r'".*Nouvelle vente !\\n"', '"🔔 <b>Nouvelle vente !</b>\\n"', content)
content = re.sub(r'f".*Produit : \{prod_name\}\\n"', 'f"📦 Produit : {prod_name}\\n"', content)
content = re.sub(r'f".*Montant : \{format_price\(amount\)\}\\n"', 'f"💰 Montant : {format_price(amount)}\\n"', content)
content = re.sub(r'f".*Commande : #\{order_id\}"', 'f"🔖 Commande : #{order_id}"', content)

content = re.sub(r'f".*<b>Wallet Purchase!</b>\\n"', 'f"💰 <b>Wallet Purchase!</b>\\n"', content)
content = re.sub(r'f".*\{escape_html\(update\.effective_user\.first_name\)\}\\n"', 'f"👤 {escape_html(update.effective_user.first_name)}\\n"', content)
content = re.sub(r'f".*\{pname\} x\{order\.get\(\'quantity\', 1\)\}\\n"', 'f"📦 {pname} x{order.get(\'quantity\', 1)}\\n"', content)
content = re.sub(r'f".*\{format_price\(amount\)\}"', 'f"💰 {format_price(amount)}"', content)

content = re.sub(r'f".*<b>BEP20 Sale!</b>\\n"', 'f"💸 <b>BEP20 Sale!</b>\\n"', content)
content = re.sub(r'f".*\{pname\} x\{db_order\.get\(\'quantity\', 1\)\}\\n"', 'f"📦 {pname} x{db_order.get(\'quantity\', 1)}\\n"', content)
content = re.sub(r'f".*\{format_price\(expected_amount\)\}"', 'f"💰 {format_price(expected_amount)}"', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Regex replace done!")
