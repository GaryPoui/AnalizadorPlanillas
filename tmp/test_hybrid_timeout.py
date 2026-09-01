import asyncio
import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def slow_claude_chat(*args, **kwargs):
    await asyncio.sleep(2)
    return "[]"


async def run():
    original_chat = main.claude_chat
    original_timeout = main.CLAUDE_TIMEOUT_SEC
    print(f"Module: {main.__file__}")
    print(f"Timeout before test: {original_timeout}")
    main.claude_chat = slow_claude_chat
    main.CLAUDE_TIMEOUT_SEC = 0.1
    raw_data = {
        "metadata": {"type": ".pdf"},
        "pdf_pages": ["=== PAGE 1 ===\nTBE-07-150 17814,76"],
        "pdf_page_tables": {},
    }
    try:
        print(f"Fixture pages: {raw_data['pdf_pages']}")
        rows = await main._run_hybrid_pass(raw_data, "", "", "ARS")
    finally:
        main.claude_chat = original_chat
        main.CLAUDE_TIMEOUT_SEC = original_timeout

    print(f"Rows: {len(rows)}")
    print(f"Errors: {raw_data.get('hybrid_errors', [])}")
    assert not rows
    assert raw_data.get("hybrid_errors")
    print("PASS: a timed out page produces a warning and does not block extraction")


asyncio.run(run())
