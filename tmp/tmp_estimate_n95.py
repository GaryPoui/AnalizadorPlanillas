import pdfplumber, sys
from pathlib import Path

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas") / "Lista de Precios N\u00b0 95 (2).pdf"
OUT = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/tmp/n95_estimate.txt")

with pdfplumber.open(PDF) as pdf:
    pages = len(pdf.pages)
    total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)

tokens_in_text = total_chars // 4
prompt_overhead = pages * 200
total_in = tokens_in_text + prompt_overhead
out_est = total_in

cost_haiku = (total_in / 1e6 * 0.80) + (out_est / 1e6 * 4.0)
cost_display = (total_in / 1e6 * 3.0) + (out_est / 1e6 * 15.0)

lines = [
    f"Paginas: {pages}",
    f"Chars texto: {total_chars:,}",
    f"Tokens in estimados: {total_in:,}",
    f"Tokens out estimados (paridad LCT): {out_est:,}",
    f"Costo real Haiku: USD {cost_haiku:.4f}",
    f"Costo display Sonnet: USD {cost_display:.4f}",
]
OUT.write_text("\n".join(lines), encoding="utf-8")
sys.stdout.write("\n".join(lines) + "\n")
sys.stdout.flush()
