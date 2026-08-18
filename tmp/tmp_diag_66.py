"""
Diagnóstico: de los 66 códigos reportados por Sonnet,
cuáles están en el JSON (posiblemente corruptos) vs cuáles faltan.
"""
import json, pathlib

MISSING_66 = [
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3165","3173","3178","3179","3185","3186","3191",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "3346","3351","3357",
    "4761","4764","4771",
    "5924","5935","5937","5943","5945",
    "6030"
]

data = json.loads(pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json').read_text(encoding='utf-8'))
rows = data['rows']
code_to_rows = {}
for r in rows:
    c = r.get('Cód. Artículo','').strip()
    code_to_rows.setdefault(c, []).append(r)

in_json   = []
not_in_json = []

for code in MISSING_66:
    if code in code_to_rows:
        in_json.append(code)
    else:
        not_in_json.append(code)

print(f"Total reportados: {len(MISSING_66)}")
print(f"Presentes en JSON (posiblemente corruptos): {len(in_json)}")
print(f"Ausentes del JSON (realmente faltantes):    {len(not_in_json)}")
print()

print("=== PRESENTES (necesitan corrección) ===")
for code in in_json:
    for r in code_to_rows[code]:
        desc = r.get('Descripción artículo','')
        print(f"  {code}: desc='{desc[:70]}' | precio={r.get('Precio','')}")

print()
print("=== AUSENTES (necesitan ser agregados) ===")
print(not_in_json)
