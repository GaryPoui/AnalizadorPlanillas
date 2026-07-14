import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path("pricebot/api").resolve()))
import main  # noqa: E402

# Optional API key via CLI arg to avoid shell env quirks.
if len(sys.argv) > 1 and sys.argv[1].strip():
    os.environ["ANTHROPIC_API_KEY"] = sys.argv[1].strip()

# Default pricing assumptions (USD per 1M tokens) for Claude Sonnet tier.
# Adjust with env vars INPUT_RATE_PER_M / OUTPUT_RATE_PER_M if needed.
INPUT_RATE_PER_M = float(os.getenv("INPUT_RATE_PER_M", "3.0"))
OUTPUT_RATE_PER_M = float(os.getenv("OUTPUT_RATE_PER_M", "15.0"))

usage_totals = {
    "input_tokens": 0,
    "output_tokens": 0,
    "calls": 0,
}


async def tracked_claude_chat(messages: list, system: str = "", max_tokens: int = 8000) -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": main.CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    in_t = int(usage.get("input_tokens", 0) or 0)
    out_t = int(usage.get("output_tokens", 0) or 0)

    usage_totals["input_tokens"] += in_t
    usage_totals["output_tokens"] += out_t
    usage_totals["calls"] += 1

    content_blocks = data.get("content", [])
    texts = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("text"):
            texts.append(block["text"])

    if texts:
        return "\n".join(texts)

    raise RuntimeError(f"No text in Anthropic response: {json.dumps(data)[:600]}")


async def run() -> None:
    print("STEP start", flush=True)
    pdf = Path("Lista de Precios N° 95 (2).pdf")
    if not pdf.exists():
        raise FileNotFoundError(pdf)

    main.claude_chat = tracked_claude_chat
    print(f"STEP orchestrator model={main.CLAUDE_MODEL}", flush=True)

    result = await asyncio.wait_for(
        main.orchestrator(pdf.read_bytes(), pdf.name, ""),
        timeout=240,
    )
    print("STEP orchestrator_done", flush=True)

    input_tokens = usage_totals["input_tokens"]
    output_tokens = usage_totals["output_tokens"]
    total_tokens = input_tokens + output_tokens

    input_cost = input_tokens / 1_000_000 * INPUT_RATE_PER_M
    output_cost = output_tokens / 1_000_000 * OUTPUT_RATE_PER_M
    total_cost = input_cost + output_cost

    summary = {
        "model": main.CLAUDE_MODEL,
        "rows": len(result.get("rows", [])),
        "quality_score": result.get("report", {}).get("quality_score"),
        "api_calls": usage_totals["calls"],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "rates_usd_per_million": {
            "input": INPUT_RATE_PER_M,
            "output": OUTPUT_RATE_PER_M,
        },
    }

    Path("orchestrator_usage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("STEP summary_written", flush=True)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
