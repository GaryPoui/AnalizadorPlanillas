import asyncio
import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main


async def run():
    rows = [
        {"Cód. Artículo": "TBE-07-150", "Descripción artículo": "Correct product", "Precio": "17814.76", "Moneda": "ARS", "Bonif.": ""},
        {"Cód. Artículo": "PC", "Descripción artículo": "Fragment", "Precio": "3000", "Moneda": "ARS", "Bonif.": ""},
        {"Cód. Artículo": "ABC-10", "Descripción artículo": "BE64-12-150 49440,42", "Precio": "1250", "Moneda": "ARS", "Bonif.": ""},
        {"Cód. Artículo": "DUP-10", "Descripción artículo": "First", "Precio": "100", "Moneda": "ARS", "Bonif.": ""},
        {"Cód. Artículo": "DUP-10", "Descripción artículo": "Second", "Precio": "200", "Moneda": "ARS", "Bonif.": ""},
    ]
    result = await main.agent_verifier(rows, {"metadata": {"type": ".pdf"}})
    report = result["report"]
    print(f"Rows with issues: {report['rows_with_issues']}")
    print(f"Suspicious rows: {report['suspicious_rows']}")
    print(f"Conflicting codes: {report['conflicting_price_codes']}")
    for item in report["issues"]:
        print(f"Row {item['row']}: {item['issues']}")
    assert "DUP-10" in report["conflicting_price_codes"]
    assert report["suspicious_rows"] >= 3
    assert any("Invalid product code" in issue for item in report["issues"] for issue in item["issues"])
    print("PASS")


asyncio.run(run())
