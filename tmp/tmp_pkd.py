import pdfplumber
PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
PKD_CODES = ['5924','5935','5937','5943','5945']
with pdfplumber.open(PDF) as pdf:
    for pnum in [38,39,40]:
        text = pdf.pages[pnum-1].extract_text() or ''
        print(f'=== PAG {pnum} ===')
        for line in text.splitlines():
            if any(c in line for c in PKD_CODES):
                print(f'  {line[:120]}')
