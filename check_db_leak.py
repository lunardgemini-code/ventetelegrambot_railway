import re

with open("database/models.py", "r", encoding="utf-8") as f:
    content = f.read()

functions = re.split(r'^async def ', content, flags=re.MULTILINE)
for func in functions[1:]:
    name = func.split('(')[0]
    if "get_db()" in func:
        if "finally:" not in func and "db.close()" not in func:
            print(f"Potential leak in {name}: missing finally/close")
        elif "finally:" not in func:
            print(f"Warning in {name}: db.close() used but no finally block")
