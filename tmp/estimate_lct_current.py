import re
import pdfplumber
from pathlib import Path

pdf = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/LCT Lista de Precios 02-2026 (4).pdf")
code = r"(?:[A-Z][A-Z0-9]{0,7}(?:[-./][A-Z0-9]{1,10}){1,4}|[A-Z]{1,5}\d{2,6}|[A-Z]{2,8}|\d{4,5})"
price = r"(?:\$\s*)?\d{1,3}(?:\.\d{3})*[,\.]\d{2}|(?:\$\s*)?\d{2,7}[,\.]\d{2}|(?:\$\s*)?\d{4,7}"
pair = re.compile(rf"({code})\s+({price})")
full = compact = pairs = 0
with pdfplumber.open(pdf) as doc:
    pages = len(doc.pages)
    for page in doc.pages:
        text = page.extract_text() or ""
        full += len(text)
        selected = []
        for line in text.splitlines():
            line = re.sub(r"-{2,}", "-", line).replace("|", " ")
            if pair.search(line):
                selected.append(line.strip())
                pairs += len(pair.findall(line))
        compact += len("\n".join(selected))
in_tokens = round(compact / 4) + pages * 250
out_tokens = pairs * 18
print(f"Pages: {pages}")
print(f"Original chars: {full:,}")
print(f"Compact chars: {compact:,}")
print(f"Pairs: {pairs:,}")
print(f"Estimated input: {in_tokens:,}")
print(f"Estimated output: {out_tokens:,}")
print(f"Estimated display: ${(in_tokens/1e6*3)+(out_tokens/1e6*15):.4f}")
print(f"Estimated Haiku: ${(in_tokens/1e6*.8)+(out_tokens/1e6*4):.4f}")
