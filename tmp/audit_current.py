import json, re
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

for name in ['LCT Lista de Precios 02-2026 (4)_hybrid.json', 'LCT Lista de Precios 02-2026 (4).json']:
    p = Path('Respuestas') / name
    if not p.exists():
        print(name, 'MISSING'); continue
    data = load(p)
    rows = data.get('rows', [])
    code_re = re.compile(r'^[A-Za-z][A-Za-z0-9\-/\.]{0,19}$')
    price_in_desc = re.compile(r'\$|\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}')
    garbage_code = 0
    no_desc = 0
    no_price = 0
    price_in_desc_empty_price = 0
    numeric = 0
    examples_garbage = []
    examples_pid = []
    for r in rows:
        code = str(r.get('Cód. Artículo','')).strip()
        desc = str(r.get('Descripción artículo','')).strip()
        price = str(r.get('Precio','')).strip()
        if code.isdigit():
            numeric += 1
        # garbage: code contains space, or is a pure dictionary word (no digit no dash), or long
        is_word = bool(re.match(r'^[A-Za-zÁÉÍÓÚÑñ]+$', code)) and '-' not in code
        if ' ' in code or is_word or len(code) > 15 or 'cid:' in code:
            garbage_code += 1
            if len(examples_garbage) < 15:
                examples_garbage.append((code, desc[:40]))
        if not desc:
            no_desc += 1
        if not price:
            no_price += 1
            if price_in_desc.search(desc):
                price_in_desc_empty_price += 1
                if len(examples_pid) < 15:
                    examples_pid.append((code, desc[:60]))
    print('====', name)
    print('total rows:', len(rows))
    print('numeric codes:', numeric)
    print('garbage-ish codes:', garbage_code)
    print('no desc:', no_desc)
    print('no price:', no_price)
    print('no price but price-like token in desc:', price_in_desc_empty_price)
    print('  garbage examples:')
    for c,d in examples_garbage:
        print('   ', repr(c), '|', repr(d))
    print('  price-in-desc examples:')
    for c,d in examples_pid:
        print('   ', repr(c), '|', repr(d))
    print()
