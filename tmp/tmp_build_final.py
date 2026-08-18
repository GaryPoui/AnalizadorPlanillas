import pdfplumber, re, json, pathlib

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'

def norm(s):
    s = str(s).replace('$','').replace(' ','').strip()
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    try: return str(round(float(s), 2))
    except: return ''

# Check pages 38-40 for PKD codes
PKD_TARGETS = {'5924','5935','5937','5943','5945'}

pkd_results = []
with pdfplumber.open(PDF) as pdf:
    for pnum in range(35, 46):
        text = pdf.pages[pnum-1].extract_text() or ''
        for code in PKD_TARGETS:
            if code in text:
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if code in line:
                        # Context around the line
                        ctx = ' '.join(lines[max(0,i-1):i+3])
                        pm = re.search(r'\$\s*([\d\.,]+)', ctx)
                        dm = re.search(rf'{code}\s+([\w\-]+)', ctx)
                        pkd_results.append({
                            'code': code,
                            'desc': dm.group(1) if dm else code,
                            'price': norm(pm.group(1)) if pm else '',
                            'page': pnum,
                            'raw': line[:100]
                        })
                        break

print(f"PKD encontrados en paginas 35-46: {len(pkd_results)}")
for r in pkd_results:
    print(f"  Pag{r['page']} [{r['code']}]: {r['desc']} ${r['price']}")
    print(f"    raw: {r['raw']}")

# Now load existing 56 extracted and build final patch
existing_56 = json.loads(pathlib.Path('tmp_56_extracted.json').read_text(encoding='utf-8'))
existing_codes = {r['code'] for r in existing_56}

all_rows = list(existing_56)
for r in pkd_results:
    if r['code'] not in existing_codes and r['price']:
        all_rows.append({'code': r['code'], 'desc': r['desc'], 'price': r['price']})
        existing_codes.add(r['code'])

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

final = [r for r in all_rows if r['code'] in ABSENT]
seen = set()
final_dedup = []
for r in final:
    if r['code'] not in seen and r['price']:
        seen.add(r['code'])
        final_dedup.append(r)

missing = ABSENT - seen
print(f"\nTotal encontrados de 56: {len(final_dedup)}")
if missing:
    print(f"Sin datos: {missing}")

pathlib.Path('tmp_56_final.json').write_text(
    json.dumps(final_dedup, ensure_ascii=False, indent=2), encoding='utf-8')
print("Guardado tmp_56_final.json")
