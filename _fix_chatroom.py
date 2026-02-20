path = r'c:\big20\AI_Interview_System_V2\frontend\src\components\ChatRoom.jsx'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep only up to and including line 739 (index 738)
# The component closes at line 739 with `}`
keep = lines[:739]

# Make sure file ends with a single newline
if keep and not keep[-1].endswith('\n'):
    keep[-1] += '\n'

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(keep)

print(f"Done. File now has {len(keep)} lines.")
print(f"Last 3 lines: {[l.rstrip() for l in keep[-3:]]}")
