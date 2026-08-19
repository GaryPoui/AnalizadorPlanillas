"""
Unit test: verifica que _is_valid_product_code y _NOISE_LINE_RE
rechacen correctamente los garbage codes y líneas ruido.
"""
import sys, re
sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")

import importlib
main = importlib.import_module("main")

should_reject = [
    "DE", "PC", "4757",  # blacklist / year-like
    "02846",             # 5 digits but non-numeric start
    "PATENTE", "INVENCI", "ACLARAR", "CUPLA",  # blacklist words
    "6000",              # year range? no — but PC already blacklisted
    "V-16",              # starts with V, only 4 chars with dash — might pass...
    "CPP45--07-050",     # double dash (tested via normalization)
]
should_accept = [
    "BE64-12-150", "TBE-07-150", "CPE90-64-16-150", "GCE", "DU",
    "PC44.44-09-3000", "RSE-18-75", "BRO-1/2", "2200", "1234",
]

noise_lines = [
    "\uf028 +54 11 4757 0430 / 0035 / 4552",
    "6 DE MAYO DE 2026 1",
    "P atente M U A R 028465-B",
]
clean_lines = [
    "BE64-12-150 49440,42 BE92-12-150 58155,88",
    "TBE-07-150 17814,76",
    "GCE 2444,71",
]

print("=== _is_valid_product_code ===")
all_ok = True
for code in should_reject:
    ok = not main._is_valid_product_code(code)
    print(f"  {'OK' if ok else 'FAIL'} reject {code!r}")
    if not ok: all_ok = False

for code in should_accept:
    ok = main._is_valid_product_code(code)
    print(f"  {'OK' if ok else 'FAIL'} accept {code!r}")
    if not ok: all_ok = False

print()
print("=== _NOISE_LINE_RE ===")
for line in noise_lines:
    match = bool(main._NOISE_LINE_RE.search(line))
    print(f"  {'OK' if match else 'FAIL'} blocked: {line[:50]!r}")
    if not match: all_ok = False

for line in clean_lines:
    match = bool(main._NOISE_LINE_RE.search(line))
    print(f"  {'OK' if not match else 'FAIL'} passed: {line[:50]!r}")
    if match: all_ok = False

print()
print("=== Double-dash normalization ===")
code = "CPP45--07-050"
normalized = re.sub(r'-{2,}', '-', code)
ok = normalized == "CPP45-07-050"
print(f"  {'OK' if ok else 'FAIL'} {code!r} -> {normalized!r}")
if not ok: all_ok = False

print()
print("ALL PASS" if all_ok else "SOME FAILED")
