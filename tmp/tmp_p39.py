import pdfplumber

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
with pdfplumber.open(PDF) as pdf:
    text = pdf.pages[38].extract_text() or ''  # page 39, 0-indexed
    print("=== PAGINA 39 COMPLETA ===")
    for line in text.splitlines():
        print(repr(line))
