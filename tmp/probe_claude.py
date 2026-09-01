import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def run():
    try:
        response = await main.claude_chat(
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )
        print(f"Claude respondió: {response!r}")
    except Exception as exc:
        print(f"Claude falló: {type(exc).__name__}: {exc}")
        raise


asyncio.run(run())
