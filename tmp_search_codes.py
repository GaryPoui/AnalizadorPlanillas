import pdfplumber, re, sys

pdf_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'
codes = ['2200', '3000', '3001', '6030', '4033', '4032', '4501', '4044']
out_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_search_out.txt'

all_lines = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ''
        all_lines.extend(text.splitlines())

output_lines = []
def emit(s):
    output_lines.append(s)

pattern = re.compile(r'\b(' + '|'.join(codes) + r')\b')

results = []
for i, line in enumerate(all_lines):
    if pattern.search(line):
        results.append(i)

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
        print(f'{marker} [{j}] {all_lines[j]}')
        printed += 1
    print('---')
    if printed >= 40:
        break

if not results:
    print(f'No lines matched codes {codes}')
    print(f'Total lines extracted: {len(all_lines)}')
    # show a small sample to confirm extraction worked
    for l in all_lines[:5]:
        print('SAMPLE:', l)
