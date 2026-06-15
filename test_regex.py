import re

def test_split(val_str):
    parts = re.split(r'[/;,]|\s+y\s+|\s+-\s+', val_str)
    valid_parts = []
    for part in parts:
        cleaned = ''.join(filter(str.isdigit, part))
        if 7 <= len(cleaned) <= 15 and part.replace('+','').replace('-','').replace(' ','').strip().isdigit():
            valid_parts.append((part.strip(), cleaned))
    return valid_parts

print(test_split('12345678 / 87654321'))
print(test_split('123-456-7890'))
print(test_split('12345678 - 87654321'))
print(test_split('+56912345678, 56987654321'))
print(test_split('Tel: 12345678'))
