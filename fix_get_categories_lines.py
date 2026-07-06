import codecs

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_get_categories = """async def get_categories() -> list[dict]:
    \"\"\"Retourne les catégories actives, triées par sort_order.\"\"\"
    global _CATEGORIES_CACHE
    if _CATEGORIES_CACHE is not None:
        return _CATEGORIES_CACHE
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "SELECT * FROM categories WHERE is_active = 1 AND is_deleted = 0 ORDER BY sort_order ASC, id ASC"
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute(
                "SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order ASC, id ASC"
            )
            rows = await cursor.fetchall()
        _CATEGORIES_CACHE = [dict(r) for r in rows]
        return _CATEGORIES_CACHE
    finally:
        await db.close()
"""

# Replace lines 204 to 226
lines[204:226] = [new_get_categories]

with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed lines 205-226')
