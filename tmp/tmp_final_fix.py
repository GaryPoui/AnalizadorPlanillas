"""Limpieza quirúrgica de los 2 códigos con problemas residuales."""
import json, pathlib

RESP_PATH = pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json')
data = json.loads(RESP_PATH.read_text(encoding='utf-8'))
rows = data['rows']

fixes = 0

# --- 3021 (B3): ghost desc="3022", price=3020.0 → reemplazar por precio real ---
new_rows = []
has_real_3021 = False
for r in rows:
    if r.get('Cód. Artículo','') == '3021':
        try:
            p = float(r.get('Precio','0'))
        except:
            p = 0
        desc = r.get('Descripción artículo','')
        if p > 1000 or desc in ('3022',''):
            # Es el ghost: reemplazar con datos correctos
            r['Descripción artículo'] = 'B3'
            r['Precio'] = '228.68'
            fixes += 1
            print(f"3021 corregido: desc=B3  precio=228.68 (era desc={desc}, precio={p})")
    new_rows.append(r)
rows = new_rows

# --- 4325 (DPH-8): eliminar la fila ghost con desc="8", mantener la buena ---
rows_4325 = [r for r in rows if r.get('Cód. Artículo','') == '4325']
if len(rows_4325) > 1:
    # Mantener solo la que tiene desc más larga (la real)
    best = max(rows_4325, key=lambda r: len(r.get('Descripción artículo','')))
    removed = [r for r in rows_4325 if r is not best]
    rows = [r for r in rows if r.get('Cód. Artículo','') != '4325'] + [best]
    fixes += len(removed)
    print(f"4325: mantenida desc='{best['Descripción artículo'][:50]}' precio={best['Precio']}")
    for r in removed:
        print(f"  → eliminada ghost: desc='{r['Descripción artículo']}' precio={r['Precio']}")
elif rows_4325:
    r = rows_4325[0]
    if r.get('Descripción artículo','') == '8':
        r['Descripción artículo'] = 'DPH-8 PH3x150mm'
        fixes += 1
        print(f"4325: descripción mejorada a 'DPH-8 PH3x150mm'")

data['rows'] = rows
data['report']['total_rows'] = len(rows)
data['report']['valid_rows'] = len(rows)

RESP_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n✅ {fixes} correcciones aplicadas. Total filas: {len(rows)}")
