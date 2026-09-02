import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/LCT Lista de Precios 02-2026 (4).pdf")
CHECKS = {"2181": "19840.44", "2200": "708.30", "6030": "2997.01"}


async def run():
    original_hybrid = main.HYBRID_EXTRACTION
    original_markitdown = main.PDF_USE_MARKITDOWN
    main.HYBRID_EXTRACTION = False
    main.PDF_USE_MARKITDOWN = False
    try:
        raw_data = await main.agent_extractor(PDF.read_bytes(), PDF.name, "")
        transformed = await main.agent_transformer(raw_data)
    finally:
        main.HYBRID_EXTRACTION = original_hybrid
        main.PDF_USE_MARKITDOWN = original_markitdown

    by_code = {str(row.get("Cód. Artículo", "")).upper(): row for row in transformed["rows"]}
    print(f"Rows: {len(transformed['rows'])}")
    for code, expected in CHECKS.items():
        actual = by_code.get(code, {}).get("Precio", "")
        print(f"{code}: {actual} expected {expected}")
        assert actual == expected
    print("PASS")


asyncio.run(run())
