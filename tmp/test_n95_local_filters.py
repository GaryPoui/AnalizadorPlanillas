import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
GARBAGE = {"DE", "PC", "4757", "02846", "10464", "PATENTE", "INVENCI", "ACLARAR", "CUPLA", "6000", "V-16"}


async def run():
    main.HYBRID_EXTRACTION = False
    raw_data = await main.agent_extractor(PDF.read_bytes(), PDF.name, "")
    result = await main.agent_transformer(raw_data)
    rows = result["rows"]

    garbage = [row for row in rows if str(row.get("Cód. Artículo", "")).upper() in GARBAGE]
    double_dash = [row for row in rows if "--" in str(row.get("Cód. Artículo", ""))]
    desc_pairs = [
        row for row in rows
        if main.CODE_PRICE_RE.search(str(row.get("Descripción artículo", "")))
    ]

    print(f"Filas locales: {len(rows)}")
    print(f"Garbage codes: {len(garbage)}")
    print(f"Códigos con doble guión: {len(double_dash)}")
    print(f"Descripciones con otro código+precio: {len(desc_pairs)}")

    for code in ("CPP45-07-050", "TEP-09-450", "TEP-09-600"):
        matches = [row for row in rows if str(row.get("Cód. Artículo", "")).upper() == code]
        values = [row.get("Precio") for row in matches]
        print(f"{code}: {values or 'ausente'}")


asyncio.run(run())
