import re
content = open('handlers/payment.py', 'r', encoding='utf-8').read()
content = re.sub(r'f\"[^\"]*delivery_error.*?\\n\\n.*?Action requise.*?\"', 'f\"{t(\'payment_confirmed\', lang)}\\n\\n{t(\'delivery_error\', lang).replace(\'{order_id}\', str(order_id))}\"', content, flags=re.DOTALL)
open('handlers/payment.py', 'w', encoding='utf-8').write(content)
