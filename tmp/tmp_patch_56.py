"""Aplica el patch de 56 (+ correcciones) al JSON del LCT."""
import json, pathlib, copy

RESP = pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json')
data = json.loads(RESP.read_text(encoding='utf-8'))
rows = data['rows']
current_codes = {r.get('Cód. Artículo','').strip() for r in rows}

EMPTY = {
    "Cód. Artículo": "", "Descripción artículo": "", "Descripción adicional artículo": "",
    "Sinónimo": "", "Cód. Lista": "01-2026.", "Desc. Lista": "Lista 01-2026.",
    "Moneda": "ARS", "Unidad": "Un", "Precio": "",
    "Bonif.": "", "Fecha vigencia desde": "", "Fecha vigencia hasta": ""
}

# Cargar los 53 extraídos
extracted = json.loads(pathlib.Path('tmp_56_final.json').read_text(encoding='utf-8'))

# Agregar los 3 PKD faltantes manualmente
manual_3 = [
    {'code': '5935', 'desc': 'PKD-16C 25-95 mm2 25-95 mm2 Cobre 1', 'price': '14393.3'},
    {'code': '5937', 'desc': 'PKD-16CE 25-95 mm2 25-95 mm2 Cobre 1 Estano', 'price': '14804.97'},
    {'code': '5943', 'desc': 'PKD-16DCE 25-95 mm2 25-95 mm2 Cobre 2 Estano', 'price': '29455.79'},
]
extracted.extend(manual_3)

# Convertir a formato template
new_rows = []
for r in extracted:
    code = r['code']
    if code in current_codes:
        continue
    row = copy.copy(EMPTY)
    row['Cód. Artículo'] = code
    row['Descripción artículo'] = r.get('desc', code)
    row['Precio'] = r.get('price', '')
    new_rows.append(row)
    current_codes.add(code)

print(f"Filas nuevas a agregar: {len(new_rows)}")

# Verificar que los 56 estén todos cubiertos
ABSENT_56 = {
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "4761","4764","4771",
    "5924","5935","5937","5943","5945",
    "6030"
}
added_codes = {r['Cód. Artículo'] for r in new_rows}
still_missing = ABSENT_56 - added_codes - (ABSENT_56 & (current_codes - added_codes))
# also check what was already in json
in_json = ABSENT_56 & ({r.get('Cód. Artículo','') for r in data['rows']} - {r['Cód. Artículo'] for r in new_rows})
print(f"De los 56: {len(added_codes)} agregados, {len(in_json)} ya estaban, {len(still_missing)} sin datos")
if still_missing:
    print(f"  Sin datos: {still_missing}")

# Aplicar
data['rows'].extend(new_rows)
data['report']['total_rows'] = len(data['rows'])
data['report']['valid_rows'] = len(data['rows'])

RESP.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\nLCT actualizado: {len(data['rows'])} filas totales")
print(f"  (era 988 → +{len(new_rows)} nuevas)")
