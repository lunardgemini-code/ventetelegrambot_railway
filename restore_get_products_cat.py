import codecs

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix get_categories:
old_get_categories = """async def get_categories() -> list[dict]:
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
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()"""

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

async def get_products_by_category(category_id: int) -> list[dict]:
    \"\"\"Retourne les produits actifs d'une catégorie.\"\"\"
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 AND is_deleted = 0 ORDER BY sort_order ASC, id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()"""

if old_get_categories in content:
    content = content.replace(old_get_categories, new_get_categories)
    with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed get_categories and added get_products_by_category.")
else:
    print("Could not find old_get_categories. Attempting manual injection.")
    if 'def get_products_by_category' not in content:
        content += "\n" + new_get_categories.split("async def get_products_by_category")[1]
        with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Injected get_products_by_category at the bottom.")
