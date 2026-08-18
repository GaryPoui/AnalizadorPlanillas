"""
Busca los 56 códigos ausentes en el PDF LCT para encontrar en qué páginas están.
"""
import pdfplumber, re

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'

ABSENT = [
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "4761","4764","4771",
    "5924","5935","5937","5943","5945",
    "6030"
]

found = {}  # code -> [(page, line_excerpt)]

with pdfplumber.open(PDF) as pdf:
    for pnum, page in enumerate(pdf.pages, 1):
        text = page.extract_text() or ''
        for code in ABSENT:
            # Buscar el código como word boundary al inicio de línea o como valor aislado
            pattern = rf'\b{re.escape(code)}\b'
            if re.search(pattern, text):
                # Encontrar línea que lo contiene
                for line in text.splitlines():
                    if re.search(pattern, line):
                        excerpt = line.strip()[:80]
                        found.setdefault(code, []).append((pnum, excerpt))
                        break

# Agrupar por página
page_groups = {}
for code in ABSENT:
    if code in found:
        for pnum, excerpt in found[code]:
            page_groups.setdefault(pnum, []).append((code, excerpt))

print(f"Códigos encontrados en PDF: {len(found)}/{len(ABSENT)}")
print(f"Códigos NO encontrados: {[c for c in ABSENT if c not in found]}")
print()
for pnum in sorted(page_groups):
    codes = [c for c,_ in page_groups[pnum]]
    print(f"Página {pnum}: {codes}")
    for code, exc in page_groups[pnum][:2]:
        print(f"  [{code}] {exc}")
