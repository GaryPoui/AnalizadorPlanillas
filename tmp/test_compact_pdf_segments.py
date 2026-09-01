import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")


async def run():
    raw_data = await main.agent_extractor(PDF.read_bytes(), PDF.name, "")
    full_chars = sum(len(page) for page in raw_data["pdf_pages"])
    compact_pages = [main._compact_pdf_segment(page) for page in raw_data["pdf_pages"]]
    compact_chars = sum(len(page) for page in compact_pages)
    full_prices = main._extract_unambiguous_pdf_prices(raw_data)
    compact_data = {"pdf_pages": compact_pages}
    compact_prices = main._extract_unambiguous_pdf_prices(compact_data)
    print(f"Full chars: {full_chars}")
    print(f"Compact chars: {compact_chars}")
    print(f"Reduction: {(1 - compact_chars / full_chars) * 100:.1f}%")
    print(f"Exact pairs full: {len(full_prices)}")
    print(f"Exact pairs compact: {len(compact_prices)}")
    assert full_prices == compact_prices
    assert compact_chars < full_chars
    print("PASS")


asyncio.run(run())
