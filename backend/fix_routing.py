"""Fix behavioral routing tuple in ai_service.py"""
import pathlib, re

p = pathlib.Path(__file__).parent / 'app' / 'services' / 'ai_service.py'
txt = p.read_text(encoding='utf-8')

# Fix the routing tuple: (4, 5, 6, 7) -> (3, 4, 5, 6)
count = txt.count('if turn in (4, 5, 6, 7):')
print(f'Found "if turn in (4, 5, 6, 7):" {count} times')
txt = txt.replace('if turn in (4, 5, 6, 7):', 'if turn in (3, 4, 5, 6):', 1)

# Fix the sub_category threshold: turn <= 5 -> turn <= 4 (only in this specific context)
# Pattern: right after the fix above, the next line has the sub= assignment
# We use a line-by-line replacement after the routing tuple
lines = txt.splitlines(keepends=True)
for i, line in enumerate(lines):
    if 'if turn in (3, 4, 5, 6):' in line:
        # Next line should have the sub= assignment; update threshold
        if i+1 < len(lines) and 'if turn <=' in lines[i+1]:
            lines[i+1] = lines[i+1].replace('if turn <= 5', 'if turn <= 4')
            print(f'Fixed sub_category threshold at line {i+2}')
        break

p.write_text(''.join(lines), encoding='utf-8')
print('Done.')
