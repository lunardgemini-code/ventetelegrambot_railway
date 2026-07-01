import re

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make standard emojis optional in Regex handlers to fix buttons with custom emojis
content = content.replace(r'r"^(🛍️ Produits|🛒 Products|🛒 المنتجات)$"', r'r"^(?:🛍️ |🛒 )?(Produits|Products|المنتجات)$"')
content = content.replace(r'r"^(🎧 Support|🎧 الدعم)$"', r'r"^(?:🎧 )?(Support|الدعم)$"')
content = content.replace(r'r"^(🚀 Commencer|🚀 Start|🚀 ابدأ)$"', r'r"^(?:🚀 )?(Commencer|Start|ابدأ)$"')
content = content.replace(r'r"^(🌐 Langue|🌐 Language|🌐 اللغة)$"', r'r"^(?:🌐 )?(Langue|Language|اللغة)$"')

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
