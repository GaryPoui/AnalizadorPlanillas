import time
from pathlib import Path
import pdfplumber

pdf_path = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Listas/Lista de Precios N\u00b0 95 (2).pdf")
started = time.perf_counter()
print("open", flush=True)
with pdfplumber.open(pdf_path) as pdf:
    print(f"pages={len(pdf.pages)} after={time.perf_counter()-started:.1f}s", flush=True)
    page = pdf.pages[0]
    print("extract_text start", flush=True)
    text = page.extract_text() or ""
    print(f"extract_text done chars={len(text)} after={time.perf_counter()-started:.1f}s", flush=True)
    print("extract_tables start", flush=True)
    tables = page.extract_tables() or []
    print(f"extract_tables done tables={len(tables)} after={time.perf_counter()-started:.1f}s", flush=True)
    print("extract_words start", flush=True)
    words = page.extract_words() or []
    print(f"extract_words done words={len(words)} after={time.perf_counter()-started:.1f}s", flush=True)
