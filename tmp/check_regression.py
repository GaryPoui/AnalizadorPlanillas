import json, sys
sys.path.insert(0, 'pricebot/api')
import main
from pathlib import Path

data = json.loads(Path('Respuestas/LCT Lista de Precios 02-2026 (4)_hybrid.json').read_text(encoding='utf-8'))
rows = data.get('rows', [])
quarantined = []
for r in rows:
    code = str(r.get('Cód. Artículo',''))
    if main._looks_like_garbage_code(code, set()):
        quarantined.append((code, str(r.get('Descripción artículo',''))[:50], r.get('Precio','')))
print('hybrid rows:', len(rows))
print('would be quarantined:', len(quarantined))
for c,d,p in quarantined:
    print('  ', repr(c), '|', repr(d), '| precio=', p)
