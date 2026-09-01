"""
Validacion PDF -> JSON sin API.
Compara los pares codigo-precio inequívocos del texto PDF contra una extracción JSON.

Uso:
  python tmp/validate_pdf_json.py "Listas/archivo.pdf" "Respuestas/resultado.json"
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


def normalize_price(value) -> float | None:
    try:
        return float(main._normalize_price_token(str(value)))
    except (TypeError, ValueError):
        return None


async def run(pdf_path: Path, json_path: Path) -> int:
    raw_data = await main.agent_extractor(pdf_path.read_bytes(), pdf_path.name, "")
    expected = main._extract_unambiguous_pdf_prices(raw_data)
    result = json.loads(json_path.read_text(encoding="utf-8"))

    actual: dict[str, list[float]] = {}
    for row in result.get("rows", []):
        code = str(row.get("Cód. Artículo", "")).strip().upper()
        price = normalize_price(row.get("Precio", ""))
        if code and price is not None:
            actual.setdefault(code, []).append(price)

    correct: list[str] = []
    missing: list[str] = []
    incorrect: list[tuple[str, float, list[float]]] = []
    for code, expected_text in expected.items():
        expected_price = normalize_price(expected_text)
        values = actual.get(code, [])
        if not values:
            missing.append(code)
        elif any(abs(value - expected_price) < 0.01 for value in values):
            correct.append(code)
        else:
            incorrect.append((code, expected_price, values))

    compared = len(expected)
    print(f"PDF: {pdf_path.name}")
    print(f"JSON: {json_path.name}")
    print(f"Pares PDF inequívocos: {compared}")
    print(f"Correctos: {len(correct)}")
    print(f"Faltantes: {len(missing)}")
    print(f"Precio diferente: {len(incorrect)}")
    print(f"Precision verificable: {(len(correct) / compared * 100) if compared else 0:.1f}%")

    if missing:
        print("\nFaltantes:")
        print(", ".join(sorted(missing)[:30]))
    if incorrect:
        print("\nPrecios diferentes:")
        for code, expected_price, values in incorrect[:30]:
            print(f"  {code}: PDF={expected_price:.2f}; JSON={values}")

    return 0 if not missing and not incorrect else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python tmp/validate_pdf_json.py <archivo.pdf> <resultado.json>")
    raise SystemExit(asyncio.run(run(Path(sys.argv[1]), Path(sys.argv[2]))))
