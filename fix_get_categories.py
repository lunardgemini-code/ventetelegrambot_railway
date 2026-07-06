import codecs
import re

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'async def get_categories\(\) -> list\[dict\]:[\s\S]*?finally:\n        await db\.close\(\)', content)
if match:
    old_text = match.group(0)
    print("Found get_categories")
    
    new_text = old_text.replace(
        "        except Exception:\n"
        "            # Fallback if is_deleted column does not exist yet\n"
        "            cursor = await db.execute(\n"
        "                \"SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id ASC\",\n"
        "                (category_id,),\n"
        "            )\n"
        "            rows = await cursor.fetchall()",
        "        except Exception:\n"
        "            # Fallback if is_deleted column does not exist yet\n"
        "            cursor = await db.execute(\n"
        "                \"SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order ASC, id ASC\"\n"
        "            )\n"
        "            rows = await cursor.fetchall()\n"
        "        global _CATEGORIES_CACHE\n"
        "        _CATEGORIES_CACHE = [dict(r) for r in rows]"
    )
    if new_text != old_text:
        content = content.replace(old_text, new_text)
        with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('FIXED GET_CATEGORIES')
    else:
        print('get_categories already fixed or pattern mismatch.')
else:
    print('get_categories not found.')
