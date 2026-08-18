import sys, pdfplumber, json

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'
TARGET_PAGES = [16, 22, 23, 24, 34]  # 1-based

with pdfplumber.open(PDF) as pdf:
    total = len(pdf.pages)
    print(f"Total páginas: {total}\n")
    
    for pnum in TARGET_PAGES:
        page = pdf.pages[pnum - 1]
        text = page.extract_text() or ""
        words = page.extract_words() or []
        tables = page.extract_tables() or []
        
        print(f"{'='*60}")
        print(f"PÁGINA {pnum}")
        print(f"  Chars texto: {len(text)}")
        print(f"  Palabras:    {len(words)}")
        print(f"  Tablas:      {len(tables)}")
        
        if text:
            print(f"  --- Primeros 600 chars ---")
            print(text[:600])
        
        if tables:
            print(f"  --- Primera tabla (primeras 5 filas) ---")
            for row in tables[0][:5]:
                print(f"  {row}")
        
        if words and not text:
            print(f"  --- Primeras 10 palabras (sin texto continuo) ---")
            for w in words[:10]:
                print(f"  {w}")
        print()
