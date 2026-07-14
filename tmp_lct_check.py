import urllib.request
import urllib.parse
import json
import os
import uuid

pdf_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'
url = 'http://127.0.0.1:8000/extract'

boundary = uuid.uuid4().hex
CRLF = b'\r\n'

with open(pdf_path, 'rb') as f:
    file_data = f.read()

filename = 'LCT Lista de Precios 02-2026 (3).pdf'
body = (
    ('--' + boundary).encode() + CRLF +
    f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode() + CRLF +
    b'Content-Type: application/pdf' + CRLF +
    CRLF +
    file_data + CRLF +
    ('--' + boundary + '--').encode() + CRLF
)

req = urllib.request.Request(url, data=body)
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
req.add_header('Content-Length', str(len(body)))

with urllib.request.urlopen(req, timeout=300) as resp:
    status = resp.status
    raw = resp.read().decode('utf-8')

obj = json.loads(raw)

report = obj.get('report', {})
total_rows = report.get('total_rows')
quality_score = report.get('quality_score')
rows = obj.get('rows', [])

test_codes = ['2354','6030','5570','5571','2200','2201','3000','3001','3002','6214','6215','4501','4502','4033','4032','3230','3231','4044']

extracted_codes = set()
for r in rows:
    c = r.get('Cód. Artículo') or r.get('cod_articulo') or r.get('codigo') or r.get('code') or ''
    if c:
        extracted_codes.add(str(c).strip())

present = [c for c in test_codes if c in extracted_codes]
missing = [c for c in test_codes if c not in extracted_codes]

first10 = []
for r in rows[:10]:
    c = r.get('Cód. Artículo') or r.get('cod_articulo') or r.get('codigo') or r.get('code') or ''
    first10.append(str(c).strip())

result = {
    'status_code': status,
    'total_rows': total_rows,
    'quality_score': quality_score,
    'test_codes_present': present,
    'test_codes_missing': missing,
    'present_count': len(present),
    'first_10_codes': first10
}

print(json.dumps(result, indent=2, ensure_ascii=False))

out_path = r'c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_lct_check_result.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f'\nSaved to {out_path}')
