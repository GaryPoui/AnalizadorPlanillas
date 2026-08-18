"""
Batch test: procesa todos los archivos de Listas/ con el orquestador,
mide tokens y costo por extracción, guarda resultados en outputs/.

Uso:
    cd c:\\Users\\Pasante\\Desktop\\AnalizadorPlanillas
    python tests/batch_test_listas.py [ANTHROPIC_API_KEY]

Requiere que pricebot/.env tenga ANTHROPIC_API_KEY, o pasarla como argumento.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT     = Path(__file__).parent.parent
LISTAS_DIR    = REPO_ROOT / "Listas"
OUTPUT_FILE   = Path(__file__).parent / "outputs" / "batch_test_results.json"
RESPUESTAS_DIR = REPO_ROOT / "Respuestas"

sys.path.insert(0, str(REPO_ROOT / "pricebot" / "api"))
import main  # noqa: E402
import httpx  # noqa: E402

# ── API Key ───────────────────────────────────────────────────────────────────
if len(sys.argv) > 1 and sys.argv[1].strip():
    os.environ["ANTHROPIC_API_KEY"] = sys.argv[1].strip()

# ── Tarifas (USD / 1M tokens) ─────────────────────────────────────────────────
INPUT_RATE  = float(os.getenv("INPUT_RATE_PER_M",  "3.0"))
OUTPUT_RATE = float(os.getenv("OUTPUT_RATE_PER_M", "15.0"))

# ── Token tracker por archivo ─────────────────────────────────────────────────
_current_usage: dict = {}


def _reset_usage() -> None:
    _current_usage.clear()
    _current_usage.update({"input_tokens": 0, "output_tokens": 0, "calls": 0})


async def _tracked_claude_chat(messages: list, system: str = "", max_tokens: int = 8000) -> str:
    """Reemplaza main.claude_chat para interceptar el uso de tokens."""
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada.")

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict = {"model": main.CLAUDE_MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    usage = data.get("usage", {})
    _current_usage["input_tokens"]  += int(usage.get("input_tokens", 0)  or 0)
    _current_usage["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
    _current_usage["calls"]         += 1

    texts = [b["text"] for b in data.get("content", []) if isinstance(b, dict) and b.get("text")]
    if texts:
        return "\n".join(texts)
    raise RuntimeError(f"Sin texto en respuesta Anthropic: {json.dumps(data)[:400]}")


# ── Lógica principal ──────────────────────────────────────────────────────────
async def test_file(path: Path) -> dict:
    """Procesa un archivo y retorna métricas."""
    _reset_usage()
    main.claude_chat = _tracked_claude_chat  # monkey-patch

    t0 = time.perf_counter()
    error = None
    result = {}

    try:
        result = await asyncio.wait_for(
            main.orchestrator(path.read_bytes(), path.name, ""),
            timeout=300,
        )
    except Exception as exc:
        error = str(exc)

    elapsed = round(time.perf_counter() - t0, 1)

    in_t  = _current_usage["input_tokens"]
    out_t = _current_usage["output_tokens"]
    in_cost  = in_t  / 1_000_000 * INPUT_RATE
    out_cost = out_t / 1_000_000 * OUTPUT_RATE

    entry = {
        "file":              path.name,
        "format":            path.suffix.lower(),
        "size_kb":           round(path.stat().st_size / 1024, 1),
        "elapsed_sec":       elapsed,
        "rows":              len(result.get("rows", [])) if result else 0,
        "quality_score":     result.get("report", {}).get("quality_score") if result else None,
        "extraction_method": result.get("extraction_method", "unknown") if result else "error",
        "claude_calls":      _current_usage["calls"],
        "input_tokens":      in_t,
        "output_tokens":     out_t,
        "total_tokens":      in_t + out_t,
        "input_cost_usd":    round(in_cost,  6),
        "output_cost_usd":   round(out_cost, 6),
        "total_cost_usd":    round(in_cost + out_cost, 6),
        "error":             error,
    }

    # Guardar respuesta completa en Respuestas/
    if result:
        RESPUESTAS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", path.stem)
        resp_file = RESPUESTAS_DIR / f"{safe_name}.json"
        resp_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    status = "ERROR" if error else "OK"
    print(
        f"  [{status}] {path.name[:50]:<50}  "
        f"rows={entry['rows']:>5}  "
        f"tokens={entry['total_tokens']:>7}  "
        f"cost=${entry['total_cost_usd']:.4f}  "
        f"({elapsed}s)",
        flush=True,
    )
    return entry


async def run() -> None:
    files = sorted(LISTAS_DIR.glob("*"))
    files = [f for f in files if f.is_file()]

    # Files to skip (variable OCR quality, used only for specific OCR tests)
    SKIP_FILES = set(os.getenv("SKIP_FILES", "LISTA AR36").split(","))
    files = [f for f in files if not any(skip.strip() in f.name for skip in SKIP_FILES if skip.strip())]

    if not files:
        print(f"No se encontraron archivos en {LISTAS_DIR}")
        sys.exit(1)

    print(f"PriceBot Batch Test — modelo: {main.CLAUDE_MODEL}")
    print(f"Tarifas: input=${INPUT_RATE}/M  output=${OUTPUT_RATE}/M")
    if SKIP_FILES:
        print(f"Omitidos (SKIP_FILES): {', '.join(s for s in SKIP_FILES if s.strip())}")
    print(f"Procesando {len(files)} archivo(s) desde {LISTAS_DIR.name}/\n")

    results = []
    for f in files:
        print(f"→ {f.name}", flush=True)
        entry = await test_file(f)
        results.append(entry)
        print()

    # ── Totales ───────────────────────────────────────────────────────────────
    total_tokens = sum(r["total_tokens"] for r in results)
    total_cost   = sum(r["total_cost_usd"] for r in results)
    ok_count     = sum(1 for r in results if not r["error"])

    summary = {
        "model":         main.CLAUDE_MODEL,
        "files_tested":  len(results),
        "files_ok":      ok_count,
        "files_error":   len(results) - ok_count,
        "total_tokens":  total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "rates_usd_per_million": {"input": INPUT_RATE, "output": OUTPUT_RATE},
        "results":       results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("─" * 75)
    print(f"  Archivos procesados : {len(results)}  (OK={ok_count}  Error={len(results)-ok_count})")
    print(f"  Tokens totales      : {total_tokens:,}")
    print(f"  Costo total estimado: ${total_cost:.4f} USD")
    print(f"\n  Resultados guardados en: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(run())
