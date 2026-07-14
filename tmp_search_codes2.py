import pdfplumber, re

pdf_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'
codes = ['2200', '3000', '3001', '6030', '4033', '4032', '4501', '4044']
out_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_search_out.txt'

all_lines = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ''
        all_lines.extend(text.splitlines())

pattern = re.compile(r'\b(' + '|'.join(codes) + r')\b')

results = []
for i, line in enumerate(all_lines):
    if pattern.search(line):
        results.append(i)

out = []
printed = 0
seen = set()
for idx in results:
    if idx in seen:
        continue
    start = max(0, idx - 2)
    end = min(len(all_lines), idx + 3)
    seen.update(range(start, end))
    for j in range(start, end):
        marker = '>>>' if j == idx else '   '
        out.append(f'{marker} [{j}] {all_lines[j]}')
        printed += 1
    out.append('---')
    if printed >= 40:
        break

if not results:
    out.append(f'No matches found for codes: {codes}')
    out.append(f'Total lines extracted: {len(all_lines)}')
    for l in all_lines[:5]:
        out.append(f'SAMPLE: {l}')

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
