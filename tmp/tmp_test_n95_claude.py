"""
Extracción híbrida Lista N°95: heurística existente + Claude por página.
Costo estimado: ~$0.025 USD (Haiku real) / ~$0.095 USD (tasas display Sonnet)
"""
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
import pdfplumber
from dotenv import load_dotenv

REPO_ROOT      = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas")
PDF_PATH       = REPO_ROOT / "Listas" / "Lista de Precios N\u00b0 95 (2).pdf"
HEURISTIC_JSON = REPO_ROOT / "Respuestas" / "Lista de Precios N\u00b0 95 (2).json"
OUTPUT_JSON    = REPO_ROOT / "Respuestas" / "Lista de Precios N\u00b0 95 (2)_hybrid.json"

load_dotenv(REPO_ROOT / "pricebot" / ".env", encoding="utf-8-sig")
API_KEY      = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

INPUT_RATE  = float(os.getenv("INPUT_RATE_PER_M",  "3.0"))
OUTPUT_RATE = float(os.getenv("OUTPUT_RATE_PER_M", "15.0"))

SYSTEM_PROMPT = (
    "You extract product entries from Argentine electrical supply price list pages.\n"
    "Return ONLY a JSON array. Each object must have:\n"
    '  "code": product code (4-5 digit number, or alphanumeric e.g. SCA-10, UCA-16)\n'
    '  "desc": product description including model name and specifications\n'
    '  "price": unit price as a plain decimal number (no currency symbols, no spaces)\n'
    "\n"
    "Rules:\n"
    "- Extract ALL products, including from BOTH columns when a page has two side-by-side columns\n"
    "- For paired rows (two products on the same line), produce two separate objects\n"
    "- Skip page headers, section/category titles, and subtotal rows\n"
    "- If price is written with spaces (e.g. '1 234,56'), join them: 1234.56\n"
    "- Return [] if the page contains no product rows"
)

_total_in  = 0
_total_out = 0


async def _call_claude(client: httpx.AsyncClient, page_num: int, text: str) -> list[dict]:
    global _total_in, _total_out
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 6000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Page {page_num}:\n{text}"}],
    }
    resp = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    _total_in  += int(usage.get("input_tokens",  0) or 0)
    _total_out += int(usage.get("output_tokens", 0) or 0)

    stop_reason = data.get("stop_reason", "")
    raw = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text").strip()
    if raw.startswith("```"):
        raw = raw[raw.find("\n") + 1:]
        raw = re.sub(r"```\s*$", "", raw).strip()
    try:
        rows = json.loads(raw)
        return rows if isinstance(rows, list) else []
    except Exception:
        if stop_reason == "max_tokens" and "[" in raw:
            last_close = raw.rfind("}")
            if last_close > 0:
                try:
                    rows = json.loads(raw[:last_close + 1] + "]")
                    if isinstance(rows, list):
                        return rows
                except Exception:
                    pass
        return []


def _norm_price(val) -> str:
    if val is None:
        return ""
    s = re.sub(r"[^\d.,]", "", str(val)).replace(",", ".").replace(" ", "")
    try:
        return str(round(float(s), 2))
    except Exception:
        return ""


def _is_valid_code(code: str) -> bool:
    return bool(re.match(r"^(\d{4,5}|[A-Z][A-Z0-9\-/]{1,15})$", code.upper()))


async def main() -> None:
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY no configurada en pricebot/.env", flush=True)
        sys.exit(1)

    print(f"=== Extracción híbrida N\u00b095  (modelo: {CLAUDE_MODEL}) ===", flush=True)
    print(f"PDF: {PDF_PATH.name}", flush=True)
    print(f"Costo estimado: ~$0.025 USD (Haiku real) / ~$0.095 USD (display)", flush=True)
    print(flush=True)

    heuristic_rows: list[dict] = []
    base_data: dict = {}
    if HEURISTIC_JSON.exists():
        base_data = json.loads(HEURISTIC_JSON.read_text(encoding="utf-8"))
        heuristic_rows = base_data.get("rows", [])
    print(f"Base heurística cargada: {len(heuristic_rows)} filas", flush=True)

    with pdfplumber.open(PDF_PATH) as pdf:
        pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
    print(f"Páginas PDF: {len(pages)}", flush=True)
    print(f"Enviando cada página a Claude...\n", flush=True)

    t0 = time.perf_counter()
    claude_raw: list[dict] = []

    async with httpx.AsyncClient() as client:
        for page_num, text in pages:
            if not text.strip():
                print(f"  Pág {page_num:3d}: vacía, skip", flush=True)
                continue
            rows = await _call_claude(client, page_num, text)
            claude_raw.extend(rows)
            print(
                f"  Pág {page_num:3d}: {len(rows):3d} filas  "
                f"[acum {_total_in:,}in / {_total_out:,}out tokens]",
                flush=True,
            )

    elapsed = round(time.perf_counter() - t0, 1)
    cost_in  = _total_in  / 1e6 * INPUT_RATE
    cost_out = _total_out / 1e6 * OUTPUT_RATE
    total_cost = cost_in + cost_out

    print(f"\n--- Claude listo en {elapsed}s ---", flush=True)
    print(f"Tokens input: {_total_in:,}  output: {_total_out:,}  total: {_total_in + _total_out:,}", flush=True)
    print(f"Gasto: ${total_cost:.4f} USD (tasas display ${INPUT_RATE}/${OUTPUT_RATE} por M)", flush=True)
    print(flush=True)

    LIST_CODE = "N95"
    LIST_DESC = "Lista de Precios N\u00b0 95"
    claude_normalized: list[dict] = []
    for r in claude_raw:
        code  = str(r.get("code",  "")).strip().upper()
        desc  = str(r.get("desc",  "")).strip()
        price = _norm_price(r.get("price"))
        if not _is_valid_code(code) or not price:
            continue
        claude_normalized.append({
            "Cód. Artículo":        code,
            "Descripción artículo": desc,
            "Precio":               price,
            "Cód. Lista":           LIST_CODE,
            "Desc. Lista":          LIST_DESC,
            "Moneda":               "ARS",
            "Sinónimo":             "",
        })

    print(f"Filas Claude válidas (code + precio): {len(claude_normalized)}", flush=True)

    merged: dict[str, dict] = {}
    for row in heuristic_rows:
        code = str(row.get("Cód. Artículo", "")).strip().upper()
        if code:
            merged[code] = row

    new_from_claude = 0
    enriched        = 0
    for row in claude_normalized:
        code = row["Cód. Artículo"]
        if code not in merged:
            merged[code] = row
            new_from_claude += 1
        else:
            existing = str(merged[code].get("Descripción artículo", "")).strip()
            incoming = row["Descripción artículo"]
            if len(incoming) > len(existing):
                merged[code]["Descripción artículo"] = incoming
                enriched += 1

    final_rows = list(merged.values())

    print(flush=True)
    print(f"Filas heurística:              {len(heuristic_rows):>5}", flush=True)
    print(f"Nuevas aportadas por Claude:   {new_from_claude:>5}", flush=True)
    print(f"Descripciones enriquecidas:    {enriched:>5}", flush=True)
    print(f"TOTAL final merged:            {len(final_rows):>5}", flush=True)

    output = dict(base_data)
    output["rows"]              = final_rows
    output["extraction_method"] = "hybrid_heuristic_claude"
    output["claude_tokens"]     = {
        "input":    _total_in,
        "output":   _total_out,
        "cost_usd": round(total_cost, 6),
    }
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en: {OUTPUT_JSON.name}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
