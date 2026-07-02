import re
from add_zh import zh_dict_str

with open('utils/locales.py', 'r', encoding='utf-8') as f:
    text = f.read()

if '"zh": {' not in text:
    text = text.replace('    },\n}\n', '    },\n' + zh_dict_str + '\n}\n')
    with open('utils/locales.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done!")
