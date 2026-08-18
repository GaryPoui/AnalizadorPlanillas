import json, pathlib

# Cargar JSON actual del LCT
current = json.loads(pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json').read_text(encoding='utf-8'))
current_codes = {r.get('Cód. Artículo','').strip() for r in current['rows']}

# Cargar los extraídos
extracted = json.loads(pathlib.Path('tmp_lct_missing_extracted.json').read_text(encoding='utf-8'))

new_rows = []
already = []
for r in extracted:
    code = r['code']
    if code in current_codes:
        already.append(code)
    else:
        new_rows.append(r)

print(f"Extraídos total:     {len(extracted)}")
print(f"Ya en JSON actual:   {len(already)}")
print(f"Genuinamente nuevos: {len(new_rows)}")
print()

tools = [r for r in new_rows if r['page'] != 16]
termi = [r for r in new_rows if r['page'] == 16]
print(f"  Herramientas nuevas: {len(tools)}")
print(f"  Termi-Plast nuevas:  {len(termi)}")
print()

if already:
    print(f"Códigos ya presentes: {sorted(already)[:20]}")

print("\n=== TODOS LOS NUEVOS ===")
for r in new_rows:
    desc = r.get('desc','') or r.get('model','')
    print(f"  [{r['page']}] {r['code']:8} | {r.get('model',''):12} | {desc[:45]:45} | ${r['price']}")
