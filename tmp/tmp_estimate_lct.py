import pdfplumber

with pdfplumber.open("Listas/LCT Lista de Precios 02-2026 (4).pdf") as pdf:
    pages = len(pdf.pages)
    total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)

tokens_in = total_chars // 4
overhead = pages * 500
total_in = tokens_in + overhead
out_est = pages * 300
cost_haiku = (total_in / 1e6 * 0.80) + (out_est / 1e6 * 4.0)
cost_display = (total_in / 1e6 * 3.0) + (out_est / 1e6 * 15.0)

print(f"Paginas: {pages}")
print(f"Chars texto: {total_chars:,}")
print(f"Tokens input estimados (texto + overhead): {total_in:,}")
print(f"Tokens output estimados: {out_est:,}")
print(f"Costo real Haiku ($0.80/$4 por M): USD {cost_haiku:.4f}")
print(f"Costo mostrado (Sonnet $3/$15 por M): USD {cost_display:.4f}")
