import re
import os

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

def replacer(match):
    full_match = match.group(0)
    path = match.group(2)
    # Skip b2b, webhook, health, dashboard
    if path.startswith('/api/b2b/') or path == '/webhook' or path == '/health' or path.startswith('/dashboard'):
        return full_match
    if 'include_in_schema=False' in full_match:
        return full_match
    
    if full_match.endswith(')'):
        return full_match[:-1] + ', include_in_schema=False)'
    return full_match

pattern = re.compile(r'@api\.(get|post|put|delete)\(\"([^\"]+)\"[^\)]*\)')
new_content = pattern.sub(replacer, content)

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Updated bot.py successfully')
