"""
Test rapido: envia N95 PDF a la API y muestra resultados + spot-checks.
"""
import httpx, json
from pathlib import Path

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
OUT = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas/n95_test_result.json")

# Spot-checks: (code, expected_price)
CHECKS = [
    ("BE64-12-150",     49440.42),
    ("BE64-12-300",     53486.87),
    ("TBE-07-150",      17814.76),
    ("TBE-07-300",      30240.50),
    ("CPE90-64-16-150", 24979.47),
    ("CAE-64-16-150",   40219.77),
    ("GSE-64/92",       1454.55),
    ("GCE",             2444.71),
    ("RSE-18-75",       3022.03),
    ("BRO-1/2",         894.45),
]

with open(str(PDF), "rb") as f:
    resp = httpx.post("http://localhost:8000/extract", files={"file": f}, timeout=600)

data = resp.json()
rows = data.get("rows", [])
usage = data.get("usage", {})

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# Build lookup by code
by_code = {str(r.get("Cód. Artículo","")).strip().upper(): r for r in rows}

print(f"Total filas: {len(rows)}")
print(f"Método:      {data.get('extraction_method','?')}")
print(f"Tokens:      {usage.get('tokens_total',0):,}  costo display: ${usage.get('cost_display',0):.4f}")
print()
print(f"{'CÓDIGO':<25} {'ESPERADO':>12} {'EXTRAÍDO':>12} {'OK?'}")
print("-" * 60)
ok = fail = missing = 0
for code, expected in CHECKS:
    row = by_code.get(code.upper())
    if row is None:
        print(f"  {code:<25} {expected:>12.2f} {'AUSENTE':>12} ❌")
        missing += 1
    else:
        got = float(row.get("Precio", 0) or 0)
        match = abs(got - expected) < 0.02
        icon = "✓" if match else "❌"
        print(f"  {code:<25} {expected:>12.2f} {got:>12.2f} {icon}")
        if match:
            ok += 1
        else:
            fail += 1

print()
print(f"Spot-checks: {ok} OK / {fail} precio incorrecto / {missing} ausentes  (de {len(CHECKS)} total)")
print(f"\nResultado guardado en: {OUT.name}")
