"""
Llama al endpoint /extract via HTTP con lct_02_2026.pdf, verifica códigos conocidos
y valida precios de artículos específicos. Requiere que la API esté corriendo en localhost:8000.
Uso: python tests/check_codes.py
"""

import json
import sys
from pathlib import Path

import httpx

PDF_PATH = Path(__file__).parent / "samples" / "lct_02_2026.pdf"
OUTPUT_PATH = Path(__file__).parent / "outputs" / "check_codes_response.json"

TARGET_CODES = {
    "2354", "6030", "5570", "5571", "2200", "2201", "3000", "3001",
    "6214", "6215", "4501", "4502", "4033", "4032", "3230", "3231", "4044", "4500",
}
PRICE_CHECK_CODES = {"2200", "4501"}

with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()

with httpx.Client(timeout=180.0) as client:
    resp = client.post(
        "http://127.0.0.1:8000/extract",
        files={"file": (PDF_PATH.name, pdf_bytes, "application/pdf")},
    )

status_code = resp.status_code
obj = resp.json()

OUTPUT_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

rows = obj.get("rows", [])
report = obj.get("report", {})

code_map = {}
for row in rows:
    code = str(row.get("Cód. Artículo", "") or "").strip()
    if code in TARGET_CODES:
        code_map[code] = row

found = set(code_map.keys())
missing = TARGET_CODES - found

result = {
    "status_code": status_code,
    "total_rows": report.get("total_rows"),
    "valid_rows": report.get("valid_rows"),
    "quality_score": report.get("quality_score"),
    "extraction_method": obj.get("extraction_method"),
    "codes_found": sorted(found),
    "codes_missing": sorted(missing),
    "count_found": len(found),
    "count_missing": len(missing),
    "price_check": {},
}

for c in PRICE_CHECK_CODES:
    if c in code_map:
        row = code_map[c]
        result["price_check"][c] = {
            "description": (
                row.get("Descripción") or row.get("Descripcion")
                or row.get("descripcion") or ""
            ),
            "precio": (
                row.get("Precio") or row.get("precio")
                or row.get("Precio Unitario") or row.get("precio_unitario") or "N/A"
            ),
            "all_keys": list(row.keys()),
        }
    else:
        result["price_check"][c] = "NOT FOUND"

print(json.dumps(result, ensure_ascii=False, indent=2))
