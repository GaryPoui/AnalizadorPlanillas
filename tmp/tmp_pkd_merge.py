import pdfplumber, re, json, pathlib

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'

def norm(s):
    s = str(s).replace('$','').replace(' ','').strip()
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    try:
        return str(round(float(s), 2))
    except:
        return ''

# Páginas PKD y sus datos (extraídos manualmente de las líneas del PDF)
PKD_DATA = []
PKD_CODES = {'5924','5935','5937','5943','5945'}
with pdfplumber.open(PDF) as pdf:
    for pnum in [38, 39, 40]:
        text = pdf.pages[pnum-1].extract_text() or ''
        for line in text.splitlines():
            m = re.search(r'(\d{4,5})\s+(PKD-\S+)\s+(.+?)\$\s*([\d\.,]+)', line)
            if m and m.group(1) in PKD_CODES:
                PKD_DATA.append({
                    'code': m.group(1),
                    'desc': f"{m.group(2)} {m.group(3).strip()}",
                    'price': norm(m.group(4))
                })
            # Try alternate: just code + $ price on same line
            elif any(c in line for c in PKD_CODES):
                # Extract all code+price pairs
                pairs = re.findall(r'(\d{4,5})\s+([A-Z][\w-]+)\s+[^$]*\$\s*([\d\.,]+)', line)
                for c, model, price in pairs:
                    if c in PKD_CODES:
                        PKD_DATA.append({'code': c, 'desc': model, 'price': norm(price)})

print("PKD encontrados:")
for r in PKD_DATA:
    print(f"  {r}")

# Cargar los ya extraídos
existing = json.loads(pathlib.Path('tmp_56_extracted.json').read_text(encoding='utf-8'))
existing_codes = {r['code'] for r in existing}

to_add_all = existing + [r for r in PKD_DATA if r['code'] not in existing_codes and r['price']]

# Filtrar solo los 56 ausentes
ABSENT = {
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "4761","4764","4771",
    "5924","5935","5937","5943","5945",
    "6030"
}

final = [r for r in to_add_all if r['code'] in ABSENT]
# dedup
seen = set()
final_dedup = []
for r in final:
    if r['code'] not in seen and r['price']:
        seen.add(r['code'])
        final_dedup.append(r)

still_missing = ABSENT - seen
print(f"\nTotal de 56 encontrados: {len(final_dedup)}")
if still_missing:
    print(f"Aún sin precio: {still_missing}")

pathlib.Path('tmp_56_final.json').write_text(
    json.dumps(final_dedup, ensure_ascii=False, indent=2), encoding='utf-8')
print("Guardado: tmp_56_final.json")
