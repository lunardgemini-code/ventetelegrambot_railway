import asyncio
from bot import api_reorder_products
from database.db import get_db, init_db

async def test():
    await init_db()
    data = {"orders": [{"id": 1, "sort_order": 2}]}
    try:
        res = await api_reorder_products(data)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
