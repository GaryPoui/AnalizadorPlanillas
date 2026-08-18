import json, pathlib
data = json.loads(pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json').read_text(encoding='utf-8'))
rows = data['rows']

print('=== HERRAMIENTAS NUEVAS ===')
for code in ['4033','4072','4315','4032','4073','4306','4076','4030']:
    matches = [r for r in rows if r.get('Cod. Articulo','') == code or r.get('Cód. Artículo','') == code]
    for r in matches:
        desc = r.get('Descripción artículo', r.get('Descripcion articulo',''))
        precio = r.get('Precio','')
        print(f'  {code}: {desc[:60]}  | ${precio}')

print()
print('=== TERMI-PLAST NUEVAS (muestra) ===')
for code in ['3000','3001','3045','3051']:
    matches = [r for r in rows if r.get('Cód. Artículo','') == code]
    for r in matches:
        desc = r.get('Descripción artículo','')
        print(f'  {code}: {desc[:60]}  | ${r.get("Precio","")}')

print()
print('=== CORRECCIONES ===')
for code in ['3032','4325','3021']:
    matches = [r for r in rows if r.get('Cód. Artículo','') == code]
    for r in matches:
        print(f'  {code}: precio={r.get("Precio","")}  desc={r.get("Descripción artículo","")[:40]}')

print(f'\nTotal filas: {len(rows)}')
