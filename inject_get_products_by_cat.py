import codecs

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

func = """
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
        await db.close()
"""

# Insert after get_categories
content = content.replace("async def get_product(product_id", func + "\nasync def get_product(product_id")

with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Injected get_products_by_category')
