import pdfplumber, re, json, pathlib

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
PKD_CODES = {'5924','5935','5937','5943','5945'}

def norm(s):
    s = str(s).replace('$','').replace(' ','').strip()
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    try: return str(round(float(s), 2))
    except: return ''

results = []
with pdfplumber.open(PDF) as pdf:
    for pnum in range(1, 47):
        text = pdf.pages[pnum-1].extract_text() or ''
        for code in PKD_CODES:
            if code in text:
                for line in text.splitlines():
                    if code in line:
                        m = re.search(rf'{code}\s+(\S+)\s+(.+?)\$\s*([\d\.,]+)', line)
                        if m:
                            results.append({
                                'code': code,
                                'desc': f"{m.group(1)} {m.group(2).strip()}",
                                'price': norm(m.group(3)),
                                'page': pnum,
                                'line': line[:100]
                            })
                            break
                        else:
                            # Solo tenemos el código, buscar precio en siguiente línea
                            lines = text.splitlines()
                            for i, l in enumerate(lines):
                                if code in l:
                                    # Buscar precio en este y siguiente bloque
                                    block = ' '.join(lines[i:i+3])
                                    pm = re.search(r'\$\s*([\d\.,]+)', block)
                                    dm = re.search(rf'{code}\s+([\w\-]+)', block)
                                    if pm:
                                        results.append({
                                            'code': code,
                                            'desc': dm.group(1) if dm else code,
                                            'price': norm(pm.group(1)),
                                            'page': pnum,
                                            'line': l[:100]
                                        })
                                    break

seen = set()
for r in results:
    if r['code'] not in seen and r['price']:
        seen.add(r['code'])
        print(f"  [{r['page']}] {r['code']} | {r['desc'][:50]} | ${r['price']}")
        print(f"       line: {r['line']}")

missing = PKD_CODES - seen
print(f"\nEncontrados: {len(seen)}/5  Faltantes: {missing}")
