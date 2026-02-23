"""One-shot fix for ai_service.py behavioral routing (run from backend/)"""
import re, pathlib

path = pathlib.Path('app/services/ai_service.py')
txt  = path.read_text(encoding='utf-8')

# Fix 1: routing tuple 4,5,6,7 -> 3,4,5,6
txt = txt.replace('if turn in (4, 5, 6, 7):', 'if turn in (3, 4, 5, 6):')

# Fix 2: sub_category threshold  <= 5  ->  <= 4
txt = re.sub(
    r'sub\s*=\s*"팀 프로젝트 / 인성"\s+if turn\s*<=\s*5',
    'sub = "팀 프로젝트 / 갈등" if turn <= 4',
    txt
)

# Fix 3: branch labels in _generate_behavioral_question: turns called as 3,4,5,6 now
# Old: if turn == 4 / elif turn == 5 / elif turn == 6 / else: turn 7
# New: if turn == 3 / elif turn == 4 / elif turn == 5 / else: turn 6
txt = txt.replace('if turn == 4:\n', 'if turn == 3:  # team project\n')
txt = txt.replace("elif turn == 5:  # follow-up on team project", "elif turn == 4:  # team follow-up")
txt = txt.replace("elif turn == 6:  # NEW — personality / cultural fit", "elif turn == 5:  # personality / culture-fit")
txt = txt.replace("else:  # turn == 7 — follow-up on personality question", "else:  # turn == 6 — personality follow-up")

path.write_text(txt, encoding='utf-8')
print("✅ Done")
