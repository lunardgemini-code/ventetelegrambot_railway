import codecs, sys
sys.stdout.reconfigure(encoding='utf-8')

with codecs.open('bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1709, min(len(lines), 1785)):
    print(f"{i+1}: {lines[i].rstrip()}")
