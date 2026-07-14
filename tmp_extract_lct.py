import json
from pathlib import Path

import httpx

pdf_path = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf")
summary_path = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_extract_summary.json")

if not pdf_path.exists():
    raise FileNotFoundError(str(pdf_path))

with pdf_path.open("rb") as f:
    files = {"file": (pdf_path.name, f, "application/pdf")}
    with httpx.Client(timeout=600.0) as client:
        resp = client.post("http://127.0.0.1:8000/extract", files=files)

body = resp.json()
rows = body.get("rows") or []

codes = []
for row in rows:
    if isinstance(row, dict):
        code = row.get("Cód. Artículo")
        if code:
            codes.append(str(code))
    if len(codes) >= 20:
        break

report = body.get("report") or {}
summary = {
    "status_code": resp.status_code,
    "total_rows": report.get("total_rows"),
    "valid_rows": report.get("valid_rows"),
    "quality_score": report.get("quality_score"),
    "first_20_codes": codes,
    "extraction_method": body.get("extraction_method"),
    "has_adaptive_recovery": "adaptive_recovery" in body,
}

if "ai_fallback" in body:
    summary["ai_fallback"] = body.get("ai_fallback")

summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
