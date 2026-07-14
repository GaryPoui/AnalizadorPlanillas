import sys, json
sys.path.insert(0, r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\python-portable\Lib\site-packages')

import httpx

pdf_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'

with open(pdf_path, 'rb') as f:
    pdf_bytes = f.read()

with httpx.Client(timeout=180.0) as client:
    resp = client.post(
        'http://127.0.0.1:8000/extract',
        files={'file': ('LCT Lista de Precios 02-2026 (3).pdf', pdf_bytes, 'application/pdf')}
    )

status_code = resp.status_code
obj = resp.json()

# Save full response
with open(r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_check_codes_response.json', 'w', encoding='utf-8') as f:
    json.dump(obj, f, ensure_ascii=False, indent=2)

# --- Analysis ---
target_codes = {'2354','6030','5570','5571','2200','2201','3000','3001','6214','6215','4501','4502','4033','4032','3230','3231','4044','4500'}
price_check_codes = {'2200','4501'}

rows = obj.get('rows', [])
report = obj.get('report', {})

# Build lookup by code
code_map = {}
for row in rows:
    code = str(row.get('Cód. Artículo', '') or '').strip()
    if code in target_codes:
        code_map[code] = row

found = set(code_map.keys())
missing = target_codes - found

result = {
    'status_code': status_code,
    'total_rows': report.get('total_rows'),
    'valid_rows': report.get('valid_rows'),
    'quality_score': report.get('quality_score'),
    'extraction_method': obj.get('extraction_method'),
    'codes_found': sorted(found),
    'codes_missing': sorted(missing),
    'count_found': len(found),
    'count_missing': len(missing),
    'price_check': {}
}

for c in price_check_codes:
    if c in code_map:
        row = code_map[c]
        result['price_check'][c] = {
            'description': row.get('Descripción') or row.get('Descripcion') or row.get('descripcion') or '',
            'precio': row.get('Precio') or row.get('precio') or row.get('Precio Unitario') or row.get('precio_unitario') or 'N/A',
            'all_keys': list(row.keys())
        }
    else:
        result['price_check'][c] = 'NOT FOUND'

print(json.dumps(result, ensure_ascii=False, indent=2))
