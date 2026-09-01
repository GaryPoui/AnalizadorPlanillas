import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
OUTPUT = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas/n95_test_result.json")
CHECKS = {
    "BE64-12-150": 49440.42,
    "TBE-07-150": 17814.76,
    "CPE90-64-16-150": 23268.59,
    "CPE90-92-16-150": 24979.47,
    "CPP45-07-050": 2934.12,
    "TEP-09-450": 2617.85,
    "TEP-09-600": 3175.54,
}


async def run():
    result = await main.orchestrator(PDF.read_bytes(), PDF.name)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    by_code = {str(row.get("Cód. Artículo", "")).upper(): row for row in result["rows"]}
    correct = 0
    for code, expected in CHECKS.items():
        actual = float(by_code.get(code, {}).get("Precio", 0) or 0)
        ok = abs(actual - expected) < 0.01
        correct += ok
        print(f"{'OK' if ok else 'FAIL'} {code}: {actual:.2f} expected {expected:.2f}")
    print(f"Rows: {len(result['rows'])}")
    print(f"Checks: {correct}/{len(CHECKS)}")
    print(f"Usage: {result['usage']}")
    print(f"Hybrid warnings: {[entry['detail'] for entry in result['log'] if entry['step'] == 'hybrid']}")


asyncio.run(run())
