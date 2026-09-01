import asyncio
import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def must_not_call_claude(*args, **kwargs):
    raise AssertionError("Claude must not be called for CSV/XLS/XLSX")


async def run():
    original_chat = main.claude_chat
    original_hybrid = main.HYBRID_EXTRACTION
    main.claude_chat = must_not_call_claude
    main.HYBRID_EXTRACTION = True
    raw_data = {
        "metadata": {"type": ".csv", "filename": "products.csv"},
        "structured_rows": [],
        "raw_text": "BE64-12-150 49440,42\nTBE-07-150 17814,76",
    }
    try:
        result = await main.agent_transformer(raw_data)
    finally:
        main.claude_chat = original_chat
        main.HYBRID_EXTRACTION = original_hybrid

    assert len(result["rows"]) == 2
    print("PASS: CSV extracted locally without Claude")


asyncio.run(run())
