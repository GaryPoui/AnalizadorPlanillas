"""
Extractor para los 56 códigos ausentes del LCT.
Maneja el formato paired-table (dos productos por línea).
"""
import pdfplumber, re, json, pathlib

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'

def normalize_price(s):
    s = str(s).replace('$','').replace(' ','').strip()
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    try:
        return str(round(float(s), 2))
    except:
        return ''

# ── Extractor genérico de líneas con patrón CODE ... $ PRICE ─────────────────
PAIRED_RE = re.compile(
    r'(\d{4,5})\s+'        # código izq
    r'([^\$]*?)\s*'        # texto izq (lazy)
    r'\$\s*([\d\.,]+)'     # precio izq
    r'(?:\s+(\d{4,5})\s+'  # código der (opcional)
    r'([^\$]*?)\s*'
    r'\$\s*([\d\.,]+))?',  # precio der (opcional)
    re.DOTALL
)

results = []  # {code, desc, price}

def extract_paired_page(text, codes_expected=None):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # Buscar pares en la línea
        for m in PAIRED_RE.finditer(line):
            c1, d1, p1 = m.group(1), (m.group(2) or '').strip(), m.group(3)
            c2, d2, p2 = m.group(4), (m.group(5) or '').strip(), m.group(6)
            if p1 and (codes_expected is None or c1 in codes_expected):
                rows.append({'code': c1, 'desc': d1, 'price': normalize_price(p1)})
            if c2 and p2 and (codes_expected is None or c2 in codes_expected):
                rows.append({'code': c2, 'desc': d2, 'price': normalize_price(p2)})
    return rows

with pdfplumber.open(PDF) as pdf:

    # ── PÁGINA 8: 6030 (LYA6C) ───────────────────────────────────────────────
    text8 = pdf.pages[7].extract_text() or ''
    rows8 = extract_paired_page(text8, {'6030'})
    print(f"Página 8 (6030): {len(rows8)} encontradas")
    for r in rows8: print(f"  {r}")
    results.extend(rows8)

    # ── PÁGINA 12: SCA/UCA (2170-2212) ───────────────────────────────────────
    SCA_UCA = {str(c) for c in range(2170,2213)} | {'2181','2182'}
    text12 = pdf.pages[11].extract_text() or ''
    rows12 = extract_paired_page(text12, SCA_UCA)
    print(f"\nPágina 12 (SCA/UCA 2170-2212): {len(rows12)} encontradas")
    for r in rows12: print(f"  {r}")
    results.extend(rows12)

    # ── PÁGINA 17: terminales R y N (3130-3358) ───────────────────────────────
    TERM = {str(c) for c in list(range(3130,3200)) + list(range(3300,3360))}
    text17 = pdf.pages[16].extract_text() or ''
    rows17 = extract_paired_page(text17, TERM)
    # También página 18 por si desborda
    text18 = pdf.pages[17].extract_text() or ''
    rows18 = extract_paired_page(text18, TERM)
    print(f"\nPáginas 17-18 (terminales R/N): {len(rows17)+len(rows18)} encontradas")
    for r in rows17+rows18: print(f"  {r}")
    results.extend(rows17 + rows18)

    # ── PÁGINA 35: grampas G1-01/G2-01/G3-01 (4761/4764/4771) ──────────────
    GRAMPAS = {'4761','4764','4771'}
    text35 = pdf.pages[34].extract_text() or ''
    rows35 = extract_paired_page(text35, GRAMPAS)
    print(f"\nPágina 35 (grampas): {len(rows35)} encontradas")
    for r in rows35: print(f"  {r}")
    results.extend(rows35)

    # ── PÁGINAS 38-40: PKD series (5924/5935/5937/5943/5945) ─────────────────
    PKD = {'5924','5935','5937','5943','5945'}
    for pnum in [38,39,40]:
        text = pdf.pages[pnum-1].extract_text() or ''
        rows = extract_paired_page(text, PKD)
        print(f"\nPágina {pnum} (PKD): {len(rows)} encontradas")
        for r in rows: print(f"  {r}")
        results.extend(rows)

# Quitar duplicados por código (mantener primero)
seen = set()
deduped = []
for r in results:
    if r['code'] not in seen and r['price']:
        seen.add(r['code'])
        deduped.append(r)

ABSENT_CODES = set([
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "4761","4764","4771",
    "5924","5935","5937","5943","5945",
    "6030"
])
found_absent = [r for r in deduped if r['code'] in ABSENT_CODES]
print(f"\n{'='*50}")
print(f"TOTAL encontrados de los 56 ausentes: {len(found_absent)}")
missing_still = ABSENT_CODES - {r['code'] for r in found_absent}
if missing_still: print(f"Aún sin encontrar: {missing_still}")

pathlib.Path('tmp_56_extracted.json').write_text(
    json.dumps(found_absent, ensure_ascii=False, indent=2), encoding='utf-8')
print("Guardado: tmp_56_extracted.json")
