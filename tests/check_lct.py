"""
Llama al endpoint /extract via HTTP con lct_02_2026.pdf y valida que los códigos
conocidos estén presentes en la respuesta. Requiere que la API esté corriendo en localhost:8000.
Uso: python tests/check_lct.py
"""

import json
import urllib.request
import urllib.parse
import uuid
from pathlib import Path

PDF_PATH = Path(__file__).parent / "samples" / "lct_02_2026.pdf"
URL = "http://127.0.0.1:8000/extract"
OUTPUT_PATH = Path(__file__).parent / "outputs" / "lct_check_result.json"

# Códigos que deben estar presentes en la extracción de la lista LCT
EXPECTED_CODES = [
    "2354", "6030", "5570", "5571", "2200", "2201",
    "3000", "3001", "3002", "6214", "6215",
    "4501", "4502", "4033", "4032", "3230", "3231", "4044",
]

boundary = uuid.uuid4().hex
CRLF = b"\r\n"

with open(PDF_PATH, "rb") as f:
    file_data = f.read()

filename = PDF_PATH.name
body = (
    ("--" + boundary).encode() + CRLF
    + f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode() + CRLF
    + b"Content-Type: application/pdf" + CRLF
    + CRLF
    + file_data + CRLF
    + ("--" + boundary + "--").encode() + CRLF
)

req = urllib.request.Request(URL, data=body)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
req.add_header("Content-Length", str(len(body)))

with urllib.request.urlopen(req, timeout=300) as resp:
    status = resp.status
    raw = resp.read().decode("utf-8")

obj = json.loads(raw)
report = obj.get("report", {})
rows = obj.get("rows", [])

extracted_codes = set()
for r in rows:
    c = r.get("Cód. Artículo") or r.get("cod_articulo") or r.get("codigo") or r.get("code") or ""
    if c:
        extracted_codes.add(str(c).strip())

present = [c for c in EXPECTED_CODES if c in extracted_codes]
missing = [c for c in EXPECTED_CODES if c not in extracted_codes]
first10 = [
    str(r.get("Cód. Artículo") or r.get("cod_articulo") or "").strip()
    for r in rows[:10]
]

result = {
    "status_code": status,
    "total_rows": report.get("total_rows"),
    "quality_score": report.get("quality_score"),
    "test_codes_present": present,
    "test_codes_missing": missing,
    "present_count": len(present),
    "first_10_codes": first10,
}

print(json.dumps(result, indent=2, ensure_ascii=False))
OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved to {OUTPUT_PATH}")
