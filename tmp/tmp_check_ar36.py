import json, pathlib
d = json.loads(pathlib.Path('Respuestas/LISTA AR36 (2).json').read_text(encoding='utf-8'))
rows = d['rows']
print(f'Total filas: {len(rows)}')
bad  = [r for r in rows if r.get('Cód. Artículo','') == r.get('Descripción artículo','')]
good = [r for r in rows if r.get('Cód. Artículo','') != r.get('Descripción artículo','')]
print(f'Filas code=desc (malas):   {len(bad)}')
print(f'Filas con buena desc:      {len(good)}')
print()
print('Muestra buenas:')
for r in good[:5]:
    print(f"  {r.get('Cód. Artículo',''):8} | {r.get('Descripción artículo','')[:50]:50} | ${r.get('Precio','')}")
print()
print('Muestra malas:')
for r in bad[:5]:
    print(f"  {r.get('Cód. Artículo',''):8} | {r.get('Descripción artículo','')[:50]:50} | ${r.get('Precio','')}")
