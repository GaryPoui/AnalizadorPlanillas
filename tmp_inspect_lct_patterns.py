from pathlib import Path
import io
import re
import pdfplumber
from markitdown import MarkItDown

pdf = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf")

md = ""
try:
    md = (MarkItDown().convert(io.BytesIO(pdf.read_bytes())).markdown or "")
except Exception as e:
    md = f"<md error {e}>"

pp_blocks = []
with pdfplumber.open(io.BytesIO(pdf.read_bytes())) as p:
    for i, page in enumerate(p.pages[:8], 1):
        txt = page.extract_text() or ""
        pp_blocks.append(f"=== PAGE {i} ===\n{txt}")
pp = "\n\n".join(pp_blocks)

text = (md[:120000] + "\n" + pp)
lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

code_pat = re.compile(r"\b(?:[A-Z]{1,6}-?\d{2,}|\d{4,6})\b")
price_pat = re.compile(r"\$?\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})|\$?\s*\d{4,7}")

hits = []
for ln in lines:
    if code_pat.search(ln) and price_pat.search(ln):
        hits.append(ln)

out = Path(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_lct_pattern_lines.txt")
out.write_text("\n".join(hits[:200]), encoding="utf-8")
print(f"LINES_WITH_CODE_PRICE={len(hits)}")
print("WROTE", out)
