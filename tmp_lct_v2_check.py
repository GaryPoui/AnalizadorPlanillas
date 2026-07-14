import httpx, json
from pathlib import Path

pdf = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf")
with pdf.open("rb") as f:
    resp = httpx.post(
        "http://127.0.0.1:8000/extract",
        files={"file": (pdf.name, f, "application/pdf")},
        timeout=300,
    )
d = resp.json()
rows = d.get("rows", [])
codes = {row.get("Cód. Artículo", "").strip() for row in rows}
test = ["2200", "2201", "3000", "3001", "4501", "4502", "4033", "4032", "4044", "6030", "5570"]
hits = {c: c in codes for c in test}
result = {
    "total_rows": d.get("report", {}).get("total_rows"),
    "quality": d.get("report", {}).get("quality_score"),
    "hits": hits,
    "present": [c for c in test if c in codes],
    "missing": [c for c in test if c not in codes],
}
out = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_lct_v2_check.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
