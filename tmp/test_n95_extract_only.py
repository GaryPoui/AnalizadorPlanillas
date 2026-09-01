import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")


async def run():
    print("Starting extractor", flush=True)
    data = await main.agent_extractor(PDF.read_bytes(), PDF.name, "")
    print(f"Done: pages={data['metadata']['pages']} chars={data['char_count']}", flush=True)
    print(f"PDF page blocks={len(data.get('pdf_pages', []))}", flush=True)


asyncio.run(run())
