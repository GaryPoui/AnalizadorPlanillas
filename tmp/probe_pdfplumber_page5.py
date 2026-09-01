import time
from pathlib import Path
import pdfplumber

pdf_path = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[4]
    started = time.perf_counter()
    print("page5 extract_text start", flush=True)
    text = page.extract_text() or ""
    print(f"page5 extract_text done chars={len(text)} seconds={time.perf_counter()-started:.2f}", flush=True)
    print("page5 extract_tables start", flush=True)
    tables = page.extract_tables() or []
    print(f"page5 extract_tables done tables={len(tables)} seconds={time.perf_counter()-started:.2f}", flush=True)
    print("page5 extract_words start", flush=True)
    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False) or []
    print(f"page5 extract_words done words={len(words)} seconds={time.perf_counter()-started:.2f}", flush=True)
