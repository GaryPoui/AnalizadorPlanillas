"""
Diagnóstico: muestra exactamente qué texto extrae pdfplumber del N°95
y qué matchea CODE_PRICE_RE para las primeras páginas con productos.
"""
import re, sys
sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import pdfplumber
from pathlib import Path

PDF = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")

CODE_TOKEN_RE  = r"(?:[A-Z][A-Z0-9]{0,7}(?:[-./][A-Z0-9]{1,10}){1,4}|[A-Z]{1,5}\d{2,6}|[A-Z]{2,8}|\d{4,5})"
PRICE_TOKEN_RE = r"(?:\$\s*)?\d{1,3}(?:\.\d{3})*[,\.]\d{2}|(?:\$\s*)?\d{2,7}[,\.]\d{2}|(?:\$\s*)?\d{4,7}"
CODE_PRICE_RE  = re.compile(rf"({CODE_TOKEN_RE})\s+({PRICE_TOKEN_RE})")

TARGETS = {"BE64-12-150","TBE-07-150","CPE90-64-16-150","CAE-64-16-150","RSE-18-75"}

with pdfplumber.open(PDF) as pdf:
    for i, page in enumerate(pdf.pages, 1):
        raw_text = (page.extract_text() or "").strip()
        # Apply Fix 1 (price reassembly)
        text = re.sub(r'(\d{1,3})\.\s+(\d{3}[,]\d{2})\b', r'\1.\2', raw_text)
        text = re.sub(r'(\d{1,3})\.\s+(\d{3})\.\s+(\d{3}[,]\d{2})\b', r'\1.\2.\3', text)

        # Check if any target codes appear on this page
        found_any = any(t in text.upper() for t in TARGETS)
        tables = page.extract_tables() or []
        if not found_any and not tables:
            continue

        print(f"\n{'='*70}")
        print(f"PÁGINA {i}  — {len(tables)} tablas, {len(raw_text)} chars")
        print(f"{'='*70}")

        # Show lines containing target-like patterns
        for line in text.splitlines():
            if any(t[:4] in line.upper() for t in TARGETS) or CODE_PRICE_RE.search(line):
                matches = CODE_PRICE_RE.findall(line)
                marker = f"  → {matches}" if matches else "  (no match)"
                print(f"  {repr(line[:100])}{marker}")

        # Show table structure for first table
        if tables:
            print(f"\n  --- Table[0] first 5 rows ---")
            for row in (tables[0] or [])[:5]:
                cells = [str(c or "").strip()[:20] for c in (row or [])]
                print(f"    {cells}")

        if i >= 4:
            print("\n(mostrando solo pág 1-4)")
            break
