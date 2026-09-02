import asyncio
import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def slow_hybrid(*args, **kwargs):
    await asyncio.sleep(1)
    return []


async def run():
    original_pass = main._run_hybrid_pass
    original_timeout = main.HYBRID_TOTAL_TIMEOUT_SEC
    main._run_hybrid_pass = slow_hybrid
    main.HYBRID_TOTAL_TIMEOUT_SEC = 0.05
    raw_data = {
        "metadata": {"type": ".pdf"},
        "raw_text": "1000 TBE 100,00",
        "pdf_pages": [],
        "pdf_page_tables": {},
    }
    try:
        result = await main.agent_transformer(raw_data)
    finally:
        main._run_hybrid_pass = original_pass
        main.HYBRID_TOTAL_TIMEOUT_SEC = original_timeout

    assert result["rows"]
    assert any("local rows retained" in error for error in raw_data.get("hybrid_errors", []))
    print("PASS: total hybrid timeout returns without blocking")


asyncio.run(run())
