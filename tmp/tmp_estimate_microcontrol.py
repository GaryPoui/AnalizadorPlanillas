import xlrd, json, sys
from pathlib import Path

XLS = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/LP MICROCONTROL 2026-02 (3).xls")
OUT = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/tmp/microcontrol_estimate.txt")

wb = xlrd.open_workbook(str(XLS))
lines = []
for sheet in wb.sheets():
    for row in range(sheet.nrows):
        cells = [str(sheet.cell_value(row, c)).strip() for c in range(sheet.ncols)]
        lines.append("\t".join(cells))

text = "\n".join(lines)
chars = len(text)
tokens_in = chars // 4 + 300   # +300 system prompt overhead
tokens_out = 3000               # estimated output for ~100 products

cost_display = (tokens_in / 1e6 * 3.0) + (tokens_out / 1e6 * 15.0)
cost_haiku   = (tokens_in / 1e6 * 0.80) + (tokens_out / 1e6 * 4.0)

result = [
    f"Hojas: {wb.nsheets}",
    f"Filas totales: {sum(s.nrows for s in wb.sheets())}",
    f"Chars texto: {chars:,}",
    f"Tokens input estimados: {tokens_in:,}",
    f"Tokens output estimados: {tokens_out:,}",
    f"Costo real Haiku: USD {cost_haiku:.4f}",
    f"Costo display Sonnet: USD {cost_display:.4f}",
]
OUT.write_text("\n".join(result), encoding="utf-8")
sys.stdout.write("\n".join(result) + "\n")
sys.stdout.flush()
