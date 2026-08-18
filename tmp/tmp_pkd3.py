import pdfplumber, re

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
PKD_TARGETS = ['5924','5935','5937','5943','5945']

with pdfplumber.open(PDF) as pdf:
    for pnum in range(1, 47):
        text = pdf.pages[pnum-1].extract_text() or ''
        for c in PKD_TARGETS:
            if c in text:
                for line in text.splitlines():
                    if c in line:
                        print(f"Pag {pnum} [{c}]: {line[:120]}")
                        break
