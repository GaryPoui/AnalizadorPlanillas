"""Prepare any PDF for the hybrid Claude pass without calling the API.

Usage:
  python tmp/compact_pdf_for_hybrid.py "Listas/archivo.pdf"
  python tmp/compact_pdf_for_hybrid.py "Listas/archivo.pdf" --output tmp/archivo_compacto.txt
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


def parse_args() -> tuple[Path, Path | None]:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python tmp/compact_pdf_for_hybrid.py <archivo.pdf> [--output archivo.txt]")

    pdf_path = Path(sys.argv[1])
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise SystemExit(f"PDF no encontrado o inválido: {pdf_path}")

    output_path = None
    if len(sys.argv) == 4 and sys.argv[2] == "--output":
        output_path = Path(sys.argv[3])
    elif len(sys.argv) > 2:
        raise SystemExit("Uso: python tmp/compact_pdf_for_hybrid.py <archivo.pdf> [--output archivo.txt]")
    return pdf_path, output_path


async def run(pdf_path: Path, output_path: Path | None) -> None:
    raw_data = await main.agent_extractor(pdf_path.read_bytes(), pdf_path.name, "")
    output_pages: list[str] = []
    original_chars = 0
    compact_chars = 0

    for page_number, page_text in enumerate(raw_data.get("pdf_pages", []), 1):
        compact = main._compact_pdf_segment(page_text)
        original_chars += len(page_text)
        compact_chars += len(compact)
        pairs = main.CODE_PRICE_RE.findall(compact)
        print(f"Página {page_number}: {len(page_text):,} -> {len(compact):,} chars; {len(pairs)} pares código-precio")
        if compact:
            output_pages.append(f"=== PAGE {page_number} ===\n{compact}")

    reduction = 100 * (1 - compact_chars / original_chars) if original_chars else 0
    print(f"\nPDF: {pdf_path.name}")
    print(f"Páginas: {len(raw_data.get('pdf_pages', []))}")
    print(f"Texto original: {original_chars:,} chars")
    print(f"Texto compacto: {compact_chars:,} chars ({reduction:.1f}% reducido)")
    print("Costo API: $0.00")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n\n".join(output_pages), encoding="utf-8")
        print(f"Salida guardada: {output_path}")


if __name__ == "__main__":
    asyncio.run(run(*parse_args()))
