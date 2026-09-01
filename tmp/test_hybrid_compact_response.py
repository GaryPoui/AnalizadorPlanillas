import asyncio
import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def compact_claude_chat(*args, **kwargs):
    assert '"desc"' not in kwargs["system"]
    assert "exactly" in kwargs["system"]
    return '[{"code":"BE64-12-150","price":"49440.42"}]'


async def run():
    original_chat = main.claude_chat
    main.claude_chat = compact_claude_chat
    raw_data = {
        "metadata": {"type": ".pdf"},
        "pdf_pages": ["BE64-12-150 49440,42"],
        "pdf_page_tables": {},
    }
    try:
        rows = await main._run_hybrid_pass(raw_data, "N95", "Lista N95", "ARS")
    finally:
        main.claude_chat = original_chat

    assert len(rows) == 1
    assert rows[0]["Cód. Artículo"] == "BE64-12-150"
    assert rows[0]["Precio"] == "49440.42"
    assert rows[0]["Descripción artículo"] == ""
    print("PASS: compact Claude response parsed without description")


asyncio.run(run())
