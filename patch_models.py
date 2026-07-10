# -*- coding: utf-8 -*-
import io
import re

file_path = r'N:\geminiopus\ventetelegrambot_railway\database\models.py'
with io.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the corrupted banner if it exists
content = re.sub(r'# ǽ.*?\"', '# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', content, flags=re.DOTALL)

if 'async def get_referred_users_count' in content:
    lines = content.split('\n')
    idx = -1
    for i, line in enumerate(lines):
        if line.startswith('async def get_referred_users_count'):
            idx = i
            break
    if idx != -1:
        end_idx = idx
        while not lines[end_idx].strip() == 'await db.close()':
            end_idx += 1
        
        new_func = '\n\nasync def get_referred_users_list(telegram_id: int) -> list[dict]:\n    \"\"\"Retourne la liste des utilisateurs parraines.\"\"\"\n    db = await get_db()\n    try:\n        cursor = await db.execute(\n            \"SELECT telegram_id, username, first_name, created_at, referral_commission_paid FROM users WHERE referred_by = ? ORDER BY created_at DESC LIMIT 50\", (telegram_id,)\n        )\n        rows = await cursor.fetchall()\n        return [dict(row) for row in rows]\n    finally:\n        await db.close()\n'
        
        if 'def get_referred_users_list' not in content:
            lines.insert(end_idx + 1, new_func)
            content = '\n'.join(lines)
            with io.open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print('Successfully patched database/models.py')
        else:
            print('Function already exists.')
else:
    print('Could not find get_referred_users_count')
