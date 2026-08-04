"""
Test básico: ejecuta el orquestador sobre lista95.pdf y reporta filas y quality_score.
Uso: python tests/test_orchestrator.py
"""

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "pricebot" / "api"))
import main  # noqa: E402

pdf_path = Path(__file__).parent / "samples" / "lista95.pdf"


async def run() -> None:
    print("START_TEST", flush=True)
    try:
        print("CALL_ORCHESTRATOR", flush=True)
        result = await asyncio.wait_for(
            main.orchestrator(pdf_path.read_bytes(), pdf_path.name, ""),
            timeout=90,
        )
        print("ORCH_OK", len(result.get("rows", [])), result.get("report", {}).get("quality_score"))
    except TimeoutError:
        print("ORCH_ERR timeout waiting orchestrator")
    except Exception as exc:
        print("ORCH_ERR", str(exc))


if __name__ == "__main__":
    asyncio.run(run())
