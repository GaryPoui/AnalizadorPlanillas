import sys
sys.path.insert(0, r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\python-portable\Lib\site-packages')
import pdfplumber, re

pdf_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'
codes = ['4500', '4501', '2200']
pattern = re.compile(r'\b(' + '|'.join(codes) + r')\b')
lines = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ''
        lines.extend(text.splitlines())

found_any = False
for i, l in enumerate(lines):
    if pattern.search(l):
        start = max(0, i - 1)
        end = min(len(lines), i + 2)
        for j in range(start, end):
            print(f'[{j}] {lines[j]}')
        print('---')
        found_any = True

if not found_any:
    print(f'No matches found. Total lines: {len(lines)}')
print('DONE')
