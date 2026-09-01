"""
Diagnóstico de problemas de precios en el último resultado de N°95.
Clasifica los errores por tipo y frecuencia.
"""
import json
from pathlib import Path

JSON  = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas/n95_test_result.json")
data  = json.loads(JSON.read_text(encoding="utf-8"))
rows  = data.get("rows", [])

by_code = {str(r.get("Cód. Artículo","")).strip().upper(): r for r in rows}

# Valores correctos del PDF (obtenidos del análisis externo)
# formato: (codigo, precio_correcto, precio_en_json)
CHECK = [
    # Correctos (control)
    ("BE64-12-150",     49440.42),
    ("TBE-07-150",      17814.76),
    ("CAE-64-16-150",   40219.77),
    ("GSE-64/92",       1454.55),
    ("BRO-1/2",         894.45),
    ("RSE-18-75",       3022.03),
    ("GCE",             2444.71),
    # Potencialmente erroneos
    ("CPE90-64-16-150", 23268.59),  # 23268,59 segun el PDF (la variante -64-)
    ("CPE90-92-16-150", 24979.47),  # variante -92- que podría estar mezclada
    ("CPP45-07-050",    2934.12),   # tenia doble guion y precio truncado
    ("TEP-09-450",      2617.85),
    ("TEP-09-600",      3175.54),
    ("EMP-09-050",      23356.51),
    ("TBP-07-050",      9164.52),
    ("SR-130",          5345.57),
    ("SES-050",         2461.91),
]

print(f"JSON cargado: {len(rows)} filas")
print()
print(f"{'CÓDIGO':<25} {'ESPERADO':>12} {'EXTRAÍDO':>12} {'OK?'}")
print("-"*60)

ok = fail = miss = 0
for code, expected in CHECK:
    row = by_code.get(code)
    if row is None:
        print(f"  {code:<25} {expected:>12.2f} {'AUSENTE':>12} ❌ ausente")
        miss += 1
    else:
        got = float(row.get("Precio", 0) or 0)
        match = abs(got - expected) < 0.05
        icon = "✓" if match else "❌"
        print(f"  {code:<25} {expected:>12.2f} {got:>12.2f} {icon}")
        if match: ok += 1
        else:      fail += 1

print()
print(f"Resultado: {ok} OK / {fail} precio incorrecto / {miss} ausentes")
print()

# Detectar patrones comunes de error de precio
print("=== Patrones de error detectados en TODAS las filas ===")
desc_has_price    = 0  # descripcion contiene numeros que parecen precios
truncated_price   = 0  # precio con muy pocos digitos (posible truncacion)
price_looks_round = 0  # precio terminado en .0 sin decimales reales
for r in rows:
    desc  = str(r.get("Descripción artículo",""))
    price = str(r.get("Precio",""))
    try:
        pf = float(price)
        if pf == int(pf) and pf > 100:
            price_looks_round += 1
        if len(price.replace(".","").replace("-","")) <= 3:
            truncated_price += 1
    except: pass
    import re
    if re.search(r'\d{3,},\d{2}', desc):
        desc_has_price += 1

print(f"  Descripcion contiene patron precio (xxx,xx): {desc_has_price}")
print(f"  Precio truncado (<= 3 digitos):               {truncated_price}")
print(f"  Precio sin decimales reales (ej 3000.0):      {price_looks_round}")
