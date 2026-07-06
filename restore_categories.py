import codecs

with codecs.open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

missing_funcs = """
async def get_category(category_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

async def add_category(
    name: str,
    emoji: str = "📂",
    description: str = "",
) -> int:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO categories (name, emoji, description) VALUES (?, ?, ?)",
            (name, emoji, description),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()

async def update_category(category_id: int, **kwargs) -> None:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    allowed = {"name", "emoji", "description", "sort_order", "is_active", "is_deleted"}
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    if not safe_kwargs:
        return
    columns = ", ".join(f"{k} = ?" for k in safe_kwargs)
    values = list(safe_kwargs.values()) + [category_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE categories SET {columns} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()

async def delete_category(category_id: int) -> None:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    db = await get_db()
    try:
        await db.execute("UPDATE categories SET is_deleted = 1 WHERE id = ?", (category_id,))
        await db.commit()
    finally:
        await db.close()

"""

if 'def add_category(' not in content:
    # Insert right before get_product
    content = content.replace("async def get_product(", missing_funcs + "\nasync def get_product(")
    with codecs.open('database/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected missing category functions!")
else:
    print("add_category already exists")
