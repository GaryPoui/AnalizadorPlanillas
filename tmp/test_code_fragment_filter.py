import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

exact_codes = {"PC44.44-09-6000", "BE64-12-150"}
rows = [
    {"Cód. Artículo": "PC", "Precio": "3000"},
    {"Cód. Artículo": "6000", "Precio": "3000"},
    {"Cód. Artículo": "BE64", "Precio": "440"},
    {"Cód. Artículo": "PC44.44-09-6000", "Precio": "36587.27"},
    {"Cód. Artículo": "BE64-12-150", "Precio": "49440.42"},
    {"Cód. Artículo": "2200", "Precio": "708.30"},
]

kept = [
    row for row in rows
    if not (
        (code := str(row.get("Cód. Artículo", "")).strip().upper()) not in exact_codes
        and len(code) >= 2
        and any(code in full_code and code != full_code for full_code in exact_codes)
        and (len(code) <= 4 or code.isdigit())
    )
]

codes = [row["Cód. Artículo"] for row in kept]
print(f"Kept: {codes}")
assert "PC" not in codes
assert "6000" not in codes
assert "BE64" not in codes
assert "PC44.44-09-6000" in codes
assert "BE64-12-150" in codes
assert "2200" in codes
print("PASS")
