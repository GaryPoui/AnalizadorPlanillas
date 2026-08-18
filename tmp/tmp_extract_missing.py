"""
Extractor para páginas del LCT con layout transpuesto:
- Herramientas (pags 22,23,24,34): cada columna = un producto
  CÓDIGO / MODELO / DESCRIPCION / PRECIO UNITARIO
- Termi-Plast (pág 16): filas horizontales de códigos + precios
"""
import sys, re, pdfplumber, json

PDF = 'Listas/LCT Lista de Precios 02-2026 (4).pdf'

def normalize_price(raw):
    """'$ 136.261,14' → '136261.14'"""
    s = raw.replace('$','').replace(' ','').strip()
    # Argentina format: 1.234.567,89
    if ',' in s and '.' in s:
        s = s.replace('.','').replace(',','.')
    elif ',' in s:
        s = s.replace(',','.')
    try:
        return str(round(float(s), 2))
    except:
        return s

def extract_tool_pages(pdf, page_nums):
    """Pages 22,23,24,34: columnas verticales de 4 filas = 1 producto."""
    rows = []
    price_re = re.compile(r'\$')
    code_re = re.compile(r'^\d{4,5}$')
    
    for pnum in page_nums:
        page = pdf.pages[pnum - 1]
        tables = page.extract_tables() or []
        
        for tbl in tables:
            # Cada fila de la tabla es una lista [valor] — aplanar
            cells = []
            for row in tbl:
                if isinstance(row, list):
                    val = ' '.join(str(c or '').strip() for c in row if str(c or '').strip())
                else:
                    val = str(row or '').strip()
                if val:
                    cells.append(val)
            
            if len(cells) < 2:
                continue
            
            code = None
            model = None
            desc_parts = []
            price = None
            
            for cell in cells:
                cell_clean = cell.replace('\n', ' ').strip()
                if code_re.match(cell_clean) and code is None:
                    code = cell_clean
                elif (cell_clean.startswith('$') or price_re.search(cell_clean)) and re.search(r'\d{4,}', cell_clean):
                    price = normalize_price(cell_clean)
                elif code and model is None and not price:
                    model = cell_clean
                elif code and model and not price:
                    desc_parts.append(cell_clean)
            
            if code and price:
                rows.append({
                    'code': code,
                    'model': model or '',
                    'desc': ' '.join(desc_parts).replace('\n', ' ').strip(),
                    'price': price,
                    'page': pnum
                })
    return rows

def extract_termi_plast(pdf, pnum=16):
    """Página 16: filas horizontales. Códigos en fila 1, precios en fila 6."""
    page = pdf.pages[pnum - 1]
    text = page.extract_text() or ''
    
    rows = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Encontrar grupos: línea de códigos seguida eventualmente de línea de precios
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detectar línea de códigos (>= 3 números de 4 dígitos)
        codes = re.findall(r'\b(\d{4})\b', line)
        if len(codes) >= 3:
            # Buscar línea de modelos (siguiente línea con letras-números)
            models = []
            prices = []
            if i + 1 < len(lines):
                models = re.findall(r'\b([A-Z]\d+[A-Z0-9]*|[A-Z]{1,2}\d+)\b', lines[i+1])
            # Buscar línea de precios (contiene $)
            for j in range(i+1, min(i+8, len(lines))):
                if '$' in lines[j]:
                    prices = re.findall(r'\$\s*([\d\.,]+)', lines[j])
                    prices = [normalize_price('$'+p) for p in prices]
                    break
            
            # Emparejar códigos con precios (mismo índice)
            for k, code in enumerate(codes):
                model = models[k] if k < len(models) else ''
                price = prices[k] if k < len(prices) else ''
                if price:
                    rows.append({
                        'code': code,
                        'model': model,
                        'desc': f'Terminal Termi-Plast {model}'.strip(),
                        'price': price,
                        'page': pnum
                    })
        i += 1
    return rows

# ---- Correr extracción ----
with pdfplumber.open(PDF) as pdf:
    tool_rows = extract_tool_pages(pdf, [22, 23, 24, 34])
    termi_rows = extract_termi_plast(pdf, 16)

all_rows = termi_rows + tool_rows

print(f"Termi-Plast (pág 16):  {len(termi_rows)} productos")
print(f"Herramientas (22-24,34): {len(tool_rows)} productos")
print(f"TOTAL nuevos: {len(all_rows)}\n")

print("=== MUESTRA HERRAMIENTAS ===")
for r in tool_rows[:12]:
    print(f"  [{r['page']}] {r['code']} | {r['model']} | {r['desc'][:50]} | ${r['price']}")

print("\n=== MUESTRA TERMI-PLAST ===")
for r in termi_rows[:12]:
    print(f"  [{r['page']}] {r['code']} | {r['model']} | ${r['price']}")

# Guardar como JSON de referencia
with open('tmp_lct_missing_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(all_rows, f, ensure_ascii=False, indent=2)
print("\nGuardado en tmp_lct_missing_extracted.json")
