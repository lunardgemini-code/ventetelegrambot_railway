import os

filepath = 'handlers/payment.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the mangled separator
lines = content.split('\n')
for i, line in enumerate(lines):
    if "â” â” â” â” â” â” " in line or "ǽ" in line:
        # Just replace any line that looks like the corrupted separator
        if 't(\'amount_lbl\'' in lines[i-1]:
            lines[i] = '            "━━━━━━━━━━━━━━━━━━━━\\n"'

with open(filepath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Replaced!")
