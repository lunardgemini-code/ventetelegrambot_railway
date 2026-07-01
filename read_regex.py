with open('bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'app.add_handler(MessageHandler(filters.Regex' in line:
        print(repr(line))
