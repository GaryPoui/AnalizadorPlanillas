"""Run the current hybrid extractor against any PDF.

Usage:
  python tmp/run_pdf_hybrid.py "Listas/archivo.pdf"
  python tmp/run_pdf_hybrid.py "archivo.pdf" --output "Respuestas/archivo.json"

The API key is read by pricebot/api/main.py from pricebot/.env.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))
import main  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Extraccion hibrida generica de cualquier PDF")
    parser.add_argument("pdf", type=Path, help="Ruta al PDF a procesar")
    parser.add_argument("--output", type=Path, help="Ruta del JSON de salida")
    return parser.parse_args()


async def run(pdf_path: Path, output_path: Path | None) -> int:
    pdf_path = pdf_path if pdf_path.is_absolute() else REPO_ROOT / pdf_path
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        print(f"PDF no encontrado o invalido: {pdf_path}", file=sys.stderr)
        return 2

    print(f"Archivo: {pdf_path.name}")
    print(f"Modo: híbrido PDF, concurrencia={main.HYBRID_CONCURRENCY}, timeout total={main.HYBRID_TOTAL_TIMEOUT_SEC:.0f}s")
    print("Procesando...")

    result = await main.orchestrator(pdf_path.read_bytes(), pdf_path.name)
    output_path = output_path or (REPO_ROOT / "Respuestas" / f"{pdf_path.stem}_hybrid.json")
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    usage = result.get("usage", {})
    warnings = [
        item.get("detail", "")
        for item in result.get("log", [])
        if item.get("step") == "hybrid" and item.get("status") == "warning"
    ]
    report = result.get("report", {})
    print(f"Filas: {len(result.get('rows', []))}")
    print(f"Calidad: {report.get('quality_score', '?')}%")
    print(f"Tokens: {usage.get('tokens_total', 0):,}")
    print(f"Costo display: ${usage.get('cost_display', 0):.4f}")
    print(f"Costo real Haiku: ${usage.get('cost_real', 0):.4f}")
    print(f"Advertencias híbridas: {len(warnings)}")
    for warning in warnings[:20]:
        print(f"  - {warning}")
    print(f"JSON guardado: {output_path}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(args.pdf, args.output)))
