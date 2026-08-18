import sys, os
sys.path.insert(0, 'pricebot/api')
from dotenv import load_dotenv
load_dotenv('pricebot/.env')
import json, pathlib

# --- Check structured files directly ---
import pandas as pd

# L26031 xlsx
df_xlsx = pd.read_excel('Listas/L26031 (1) (5).xlsx', sheet_name=None)
print("=== L26031 xlsx ===")
for sheet, df in df_xlsx.items():
    print(f"  Sheet '{sheet}': {len(df)} rows x {len(df.columns)} cols")
    print(f"  Columns: {list(df.columns)[:8]}")

# L26031 csv
df_csv = pd.read_csv('Listas/L26031 (5).csv', sep=';', encoding='latin-1', on_bad_lines='skip')
print(f"\n=== L26031 csv ===")
print(f"  Rows: {len(df_csv)}  Cols: {len(df_csv.columns)}")
print(f"  Columns: {list(df_csv.columns)[:8]}")

# LP MICROCONTROL xls
try:
    df_xls = pd.read_excel('Listas/LP MICROCONTROL 2026-02 (3).xls', sheet_name=None, header=None)
    print(f"\n=== LP MICROCONTROL xls ===")
    for sheet, df in df_xls.items():
        print(f"  Sheet '{sheet}': {len(df)} rows x {len(df.columns)} cols (raw, no header)")
except Exception as e:
    print(f"  Error: {e}")

# Compare extracted vs source
print("\n=== COMPARISON: Extracted vs Source ===")
resp_lct = json.loads(pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json').read_text(encoding='utf-8'))
resp_n95 = json.loads(pathlib.Path('Respuestas/Lista de Precios N\u00b0 95 (2).json').read_text(encoding='utf-8'))
resp_lc1 = json.loads(pathlib.Path('Respuestas/L26031 (1) (5).json').read_text(encoding='utf-8'))
resp_lp  = json.loads(pathlib.Path('Respuestas/LP MICROCONTROL 2026-02 (3).json').read_text(encoding='utf-8'))

print(f"  L26031 xlsx extracted: {len(resp_lc1['rows'])} rows")
print(f"  LP MICROCONTROL extracted: {len(resp_lp['rows'])} rows")
print(f"  LCT PDF extracted: {len(resp_lct['rows'])} rows (46 pages)")
print(f"  N°95 PDF extracted: {len(resp_n95['rows'])} rows")

# Sample LP MICROCONTROL rows
print("\n=== LP MICROCONTROL sample rows ===")
for r in resp_lp['rows'][:5]:
    print(f"  {r.get('Cód. Artículo','')} | {r.get('Descripción artículo','')[:50]} | {r.get('Precio','')}")
