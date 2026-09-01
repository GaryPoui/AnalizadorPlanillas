import time
from pathlib import Path
import pdfplumber

pdf_path = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
with pdfplumber.open(pdf_path) as pdf:
    for index in (5, 6):
        page = pdf.pages[index]
        started = time.perf_counter()
        text = page.extract_text() or ""
        tables = page.extract_tables() or []
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False) or []
        print(f"page={index + 1} seconds={time.perf_counter()-started:.2f} chars={len(text)} tables={len(tables)} words={len(words)}", flush=True)
