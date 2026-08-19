"""
Quick test: verifica que los garbage codes esten eliminados del resultado,
usando el ultimo JSON guardado (sin llamar a la API).
"""
import json, re
from pathlib import Path

JSON = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas/n95_test_result.json")
data = json.loads(JSON.read_text(encoding="utf-8"))
rows = data.get("rows", [])

# Codigos basura conocidos del reporte anterior
GARBAGE = {"DE", "PC", "4757", "02846", "10464", "PATENTE", "INVENCI",
           "ACLARAR", "CUPLA", "6000", "V-16", "B-16", "B-09"}

found_garbage = [(r.get("Cód. Artículo",""), r.get("Precio","")) for r in rows
                 if r.get("Cód. Artículo","").upper() in GARBAGE]

double_dash = [(r.get("Cód. Artículo",""), r.get("Precio","")) for r in rows
               if "--" in r.get("Cód. Artículo","")]

print(f"Total filas en JSON: {len(rows)}")
print()
if found_garbage:
    print(f"Garbage codes presentes ({len(found_garbage)}):")
    for code, price in found_garbage:
        print(f"  {code} -> {price}")
else:
    print("OK: ningún garbage code detectado en el JSON actual")

if double_dash:
    print(f"\nCódigos con doble guión ({len(double_dash)}):")
    for code, price in double_dash:
        print(f"  {code} -> {price}")
else:
    print("OK: ningún código con doble guión")

print("\nNota: estos checks usan el JSON guardado del test anterior.")
print("Los fixes se aplican al PRÓXIMO llamado a la API (uvicorn ya recargó).")
