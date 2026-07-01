import re
import time

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'import time' not in content:
    content = content.replace('import os', 'import os\nimport time')

cache_code = '''
# Simple cache for stats endpoints to avoid hammering the database
_stats_cache = {}
_stats_cache_ttl = 60  # Cache for 60 seconds

'''

if '_stats_cache' not in content:
    content = content.replace('app = FastAPI(title="DZ Products API")', 'app = FastAPI(title="DZ Products API")\n' + cache_code)

def replace_stats_api(c):
    start = c.find('async def api_get_stats():')
    if start == -1: return c
    
    inject = '''    current_time = time.time()
    if "stats" in _stats_cache and current_time - _stats_cache["stats"]["time"] < _stats_cache_ttl:
        return _stats_cache["stats"]["data"]
'''
    if 'current_time = time.time()' not in c[start:start+500]:
        c = c.replace('async def api_get_stats():\n    from database.models', 'async def api_get_stats():\n' + inject + '\n    from database.models')
        c = c.replace('        return {\n            "total_users":', '        response_data = {\n            "total_users":')
        c = c.replace('            "returning_users": returning_users,\n        }', '            "returning_users": returning_users,\n        }\n        _stats_cache["stats"] = {"time": current_time, "data": response_data}\n        return response_data')
    return c

def replace_products_stats_api(c):
    start = c.find('async def api_get_products_stats():')
    if start == -1: return c
    
    inject = '''    current_time = time.time()
    if "products_stats" in _stats_cache and current_time - _stats_cache["products_stats"]["time"] < _stats_cache_ttl:
        return _stats_cache["products_stats"]["data"]
'''
    if 'current_time = time.time()' not in c[start:start+500]:
        c = c.replace('async def api_get_products_stats():\n    from database.models', 'async def api_get_products_stats():\n' + inject + '\n    from database.models')
        c = c.replace('        data = await get_products_sales_stats()\n        return data', '        data = await get_products_sales_stats()\n        _stats_cache["products_stats"] = {"time": current_time, "data": data}\n        return data')
    return c

content = replace_stats_api(content)
content = replace_products_stats_api(content)

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
