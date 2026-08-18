import pdfplumber, re

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
TARGETS = ['5935','5937','5943']

with pdfplumber.open(PDF) as pdf:
    for pnum in range(1, 47):
        text = pdf.pages[pnum-1].extract_text() or ''
        for code in TARGETS:
            if code in text:
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if code in line:
                        # Show context
                        ctx = lines[max(0,i-1):i+4]
                        print(f"\nPag {pnum} [{code}]:")
                        for l in ctx:
                            print(f"  {repr(l[:120])}")
                        break
