import codecs

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the add_product definition, and inject the missing get_* functions right before it.
# Wait, let's see what is currently in models.py right before add_product
import re

start_idx = content.find('async def add_product(')

missing_content = """            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_product(product_id: int) -> dict | None:
    \"\"\"Récupère un produit par son identifiant.\"\"\"
    if product_id in _PRODUCT_BY_ID_CACHE:
        return _PRODUCT_BY_ID_CACHE[product_id]
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        res = dict(row) if row else None
        if res is not None:
            _PRODUCT_BY_ID_CACHE[product_id] = res
        return res
    finally:
        await db.close()


async def get_all_products() -> list[dict]:
    \"\"\"Retourne la liste de tous les produits (actifs et inactifs, non supprimés).\"\"\"
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    db = await get_db()
    try:
        try:
            cursor = await db.execute("SELECT * FROM products WHERE is_deleted = 0 ORDER BY category_id, sort_order ASC, id ASC")
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute("SELECT * FROM products ORDER BY category_id, id")
            rows = await cursor.fetchall()
        _PRODUCTS_CACHE = [dict(r) for r in rows]
        return _PRODUCTS_CACHE
    finally:
        await db.close()


"""

if "def get_product(" not in content:
    # It seems the previous replace_file_content completely deleted the functions.
    # Let's find "async def add_product" and insert them before.
    idx = content.find("async def add_product(")
    if idx != -1:
        # Before we insert, let's make sure we aren't inserting inside an existing function.
        # It's likely that the fallback query was also mangled. Let's find the fallback query.
        fallback_idx = content.find("            # Fallback if is_deleted column does not exist yet")
        if fallback_idx != -1:
            # We replace from fallback_idx to idx with our missing content
            content = content[:fallback_idx] + missing_content + content[idx:]
        else:
            print("Fallback comment not found. Inserting before add_product.")
            content = content[:idx] + missing_content + content[idx:]

# Ensure ALLOWED_PRODUCT_COLUMNS has confirmation_message fields
if "confirmation_message" not in content and "ALLOWED_PRODUCT_COLUMNS = " in content:
    content = content.replace(
        'ALLOWED_PRODUCT_COLUMNS = {"category_id", "name", "description", "description_fr", "description_ar", "description_zh", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "price_usd", "warranty_days", "emoji", "custom_emoji_id", "image_url", "is_active", "binance_account_id", "delivery_type"}',
        'ALLOWED_PRODUCT_COLUMNS = {"category_id", "name", "description", "description_fr", "description_ar", "description_zh", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "confirmation_message", "confirmation_message_fr", "confirmation_message_ar", "confirmation_message_zh", "price_usd", "warranty_days", "emoji", "custom_emoji_id", "image_url", "is_active", "binance_account_id", "delivery_type"}'
    )

with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("models.py repaired.")
