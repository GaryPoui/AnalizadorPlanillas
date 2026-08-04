"""
Comparación completa entre el Excel original L26031 y el JSON extraído.
Genera un reporte Excel con todas las diferencias encontradas.

Uso:
    cd c:\\Users\\Pasante\\Desktop\\AnalizadorPlanillas
    python tests/comparar_l26031.py
"""

import json
import unicodedata
import re
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
EXCEL_PATH  = Path("Listas/L26031 (1) (5).xlsx")
JSON_PATH   = Path("Respuestas/L26031 (1) (5).json")
REPORT_PATH = Path("Respuestas/L26031_comparacion.xlsx")

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin tildes, sin espacios extra."""
    text = unicodedata.normalize("NFKD", str(text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_price(val) -> float | None:
    """Convierte un valor de precio a float, o None si no es parseable."""
    try:
        v = str(val or "").replace(",", ".").strip()
        if not v:
            return None
        return round(float(v), 4)
    except (ValueError, TypeError):
        return None


# ── Leer Excel ────────────────────────────────────────────────────────────────
print("Leyendo Excel...")
df = pd.read_excel(EXCEL_PATH, sheet_name=0, header=0, dtype=str)
df = df.fillna("")

# Columnas relevantes del Excel
COL_PARTID  = "PARTID"
COL_DESC    = "DESCRIPCION"
COL_FAMILY  = "FAMILIA"
COL_BRAND   = "MARCA"
COL_PRICE   = "UNIT_PRICE"
COL_CURR    = "MONEDA"
COL_UNIT    = "STOCK_UM"
COL_EAN     = "CODIGO DE BARRAS"

print(f"  Excel: {len(df)} filas | columnas: {list(df.columns)}")

# Construir lookup por descripción normalizada
excel_by_desc: dict[str, list[dict]] = {}
for _, row in df.iterrows():
    key = normalize(row.get(COL_DESC, ""))
    if not key:
        continue
    entry = {
        "partid":      str(row.get(COL_PARTID, "")).strip(),
        "descripcion": str(row.get(COL_DESC, "")).strip(),
        "familia":     str(row.get(COL_FAMILY, "")).strip(),
        "marca":       str(row.get(COL_BRAND, "")).strip(),
        "precio":      clean_price(row.get(COL_PRICE, "")),
        "moneda":      str(row.get(COL_CURR, "")).strip(),
        "unidad":      str(row.get(COL_UNIT, "")).strip(),
        "ean":         str(row.get(COL_EAN, "")).strip(),
    }
    excel_by_desc.setdefault(key, []).append(entry)

# Lookup por PARTID
excel_by_partid = {
    str(row.get(COL_PARTID, "")).strip(): row
    for _, row in df.iterrows()
    if str(row.get(COL_PARTID, "")).strip()
}

print(f"  Productos únicos por descripción: {len(excel_by_desc)}")
print(f"  Productos con PARTID: {len(excel_by_partid)}")

# ── Leer JSON ─────────────────────────────────────────────────────────────────
print("Leyendo JSON extraído...")
data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
json_rows = data.get("rows", [])
column_mapping = data.get("column_mapping", {})

print(f"  JSON: {len(json_rows)} filas")
print(f"  column_mapping: {column_mapping}")
print(f"  extraction_method: {data.get('extraction_method')}")

# ── Análisis ──────────────────────────────────────────────────────────────────
print("\nAnalizando diferencias...")

results = []

# Para cada fila del JSON, buscar su equivalente en el Excel por descripción
matched_excel_descs = set()

for jrow in json_rows:
    j_code  = str(jrow.get("Cód. Artículo", "") or "").strip()
    j_desc  = str(jrow.get("Descripción artículo", "") or "").strip()
    j_price = clean_price(jrow.get("Precio", ""))
    j_curr  = str(jrow.get("Moneda", "") or "").strip()
    j_unit  = str(jrow.get("Unidad", "") or "").strip()
    j_key   = normalize(j_desc)

    excel_matches = excel_by_desc.get(j_key, [])
    excel         = excel_matches[0] if excel_matches else None

    if not excel:
        # Intento secundario: el código del JSON es un EAN → buscar por EAN en Excel
        if j_code:
            ean_clean = j_code.replace(".0", "").strip()
            for _, erow in df.iterrows():
                if str(erow.get(COL_EAN, "")).strip() == ean_clean:
                    excel = {
                        "partid":      str(erow.get(COL_PARTID, "")).strip(),
                        "descripcion": str(erow.get(COL_DESC, "")).strip(),
                        "familia":     str(erow.get(COL_FAMILY, "")).strip(),
                        "marca":       str(erow.get(COL_BRAND, "")).strip(),
                        "precio":      clean_price(erow.get(COL_PRICE, "")),
                        "moneda":      str(erow.get(COL_CURR, "")).strip(),
                        "unidad":      str(erow.get(COL_UNIT, "")).strip(),
                        "ean":         str(erow.get(COL_EAN, "")).strip(),
                    }
                    break

    # Determinar estado
    if not excel:
        estado = "SIN_MATCH_EXCEL"
        partid_correcto = ""
        diff_precio     = ""
        diff_moneda     = ""
    else:
        matched_excel_descs.add(normalize(excel["descripcion"]))
        partid_correcto = excel["partid"]
        excel_price     = excel["precio"]

        if not j_code:
            estado = "SIN_CODIGO"
        elif j_code.replace(".0", "") == excel.get("ean", "").replace(".0", ""):
            estado = "CODIGO_ES_EAN"           # código correcto pero es EAN, no PARTID
        elif j_code == partid_correcto:
            estado = "OK"
        else:
            estado = "CODIGO_INCORRECTO"

        diff_precio = ""
        if excel_price is not None and j_price is not None:
            if abs(excel_price - j_price) > 0.01:
                diff_precio = f"Excel={excel_price} | JSON={j_price}"

        diff_moneda = ""
        if excel and j_curr and excel["moneda"] and excel["moneda"] != j_curr:
            diff_moneda = f"Excel={excel['moneda']} | JSON={j_curr}"

    results.append({
        "Estado":               estado,
        "JSON Cód. Artículo":   j_code,
        "PARTID correcto":      partid_correcto,
        "JSON Descripción":     j_desc,
        "JSON Precio":          j_price or "",
        "JSON Moneda":          j_curr,
        "JSON Unidad":          j_unit,
        "Diff Precio":          diff_precio,
        "Diff Moneda":          diff_moneda,
    })

# Productos del Excel que no aparecen en el JSON
for key, entries in excel_by_desc.items():
    if key in matched_excel_descs:
        continue
    for excel in entries:
        results.append({
            "Estado":             "FALTA_EN_JSON",
            "JSON Cód. Artículo": "",
            "PARTID correcto":    excel["partid"],
            "JSON Descripción":   excel["descripcion"],
            "JSON Precio":        "",
            "JSON Moneda":        excel["moneda"],
            "JSON Unidad":        excel["unidad"],
            "Diff Precio":        f"Precio Excel: {excel['precio']}",
            "Diff Moneda":        "",
        })

# ── Resumen ───────────────────────────────────────────────────────────────────
df_result = pd.DataFrame(results)
conteo = df_result["Estado"].value_counts()

print("\n=== RESUMEN ===")
for estado, n in conteo.items():
    print(f"  {estado:<25}: {n:>5}")
print(f"  {'TOTAL':<25}: {len(df_result):>5}")

# ── Guardar reporte Excel ─────────────────────────────────────────────────────
print(f"\nGenerando reporte Excel: {REPORT_PATH}")

# Orden de hojas
order = ["OK", "SIN_CODIGO", "CODIGO_ES_EAN", "CODIGO_INCORRECTO",
         "SIN_MATCH_EXCEL", "FALTA_EN_JSON"]

with pd.ExcelWriter(REPORT_PATH, engine="openpyxl") as writer:
    # Hoja resumen
    resumen_df = pd.DataFrame(conteo).reset_index()
    resumen_df.columns = ["Estado", "Cantidad"]
    resumen_df["Descripción"] = resumen_df["Estado"].map({
        "OK":                 "Código y datos correctos",
        "SIN_CODIGO":         "Producto sin código (EAN vacío, tiene PARTID)",
        "CODIGO_ES_EAN":      "Código es EAN (barcode), no PARTID interno",
        "CODIGO_INCORRECTO":  "Código presente pero no coincide con PARTID ni EAN",
        "SIN_MATCH_EXCEL":    "Fila en JSON sin equivalente en Excel",
        "FALTA_EN_JSON":      "Producto en Excel que no está en el JSON",
    })
    resumen_df.to_excel(writer, sheet_name="RESUMEN", index=False)

    # Una hoja por estado
    for estado in order:
        subset = df_result[df_result["Estado"] == estado]
        if not subset.empty:
            subset.to_excel(writer, sheet_name=estado[:31], index=False)

    # Hoja completa
    df_result.to_excel(writer, sheet_name="TODOS", index=False)

print(f"Reporte guardado: {REPORT_PATH}")
