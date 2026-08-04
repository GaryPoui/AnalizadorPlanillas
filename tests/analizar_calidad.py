"""
Analiza la calidad de extracción de todos los JSON en Respuestas/
(excluyendo los que necesitan Claude API) y genera un reporte.

Uso:
    cd c:\\Users\\Pasante\\Desktop\\AnalizadorPlanillas
    python tests/analizar_calidad.py
"""

import json
import re
import unicodedata
from pathlib import Path
import pandas as pd

RESPUESTAS_DIR = Path("Respuestas")
LISTAS_DIR     = Path("Listas")
REPORT_PATH    = RESPUESTAS_DIR / "calidad_extraccion.xlsx"

# Archivos a analizar (excluir los que requieren Claude)
TARGETS = [
    "L26031 (5).json",
    "LCT Lista de Precios 02-2026 (4).json",
    "Lista de Precios N° 95 (2).json",
]

# Archivo CSV de origen para L26031 (para comparar igual que con el XLSX)
CSV_SOURCE = LISTAS_DIR / "L26031 (5).csv"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def clean_price(val) -> float | None:
    try:
        v = str(val or "").replace(",", ".").strip()
        return round(float(v), 4) if v else None
    except (ValueError, TypeError):
        return None


# ── Análisis genérico de un JSON ──────────────────────────────────────────────
def analizar_json(json_path: Path) -> dict:
    data  = json.loads(json_path.read_text(encoding="utf-8"))
    rows  = data.get("rows", [])
    total = len(rows)

    if total == 0:
        return {"total": 0, "issues": [], "column_mapping": {}, "extraction_method": data.get("extraction_method")}

    sin_codigo  = [r for r in rows if not str(r.get("Cód. Artículo") or "").strip()]
    sin_desc    = [r for r in rows if not str(r.get("Descripción artículo") or "").strip()]
    sin_precio  = [r for r in rows if not str(r.get("Precio") or "").strip()]
    sin_moneda  = [r for r in rows if not str(r.get("Moneda") or "").strip()]

    # Precios sospechosos (no numérico)
    precios_invalidos = [
        r for r in rows
        if str(r.get("Precio") or "").strip() and clean_price(r.get("Precio")) is None
    ]

    # Monedas distintas de las esperadas
    monedas_raras = [
        r for r in rows
        if str(r.get("Moneda") or "").strip() not in ("ARS", "USD", "EUR", "")
    ]

    # Duplicados exactos (mismo código + mismo precio)
    seen = {}
    duplicados = []
    for r in rows:
        key = (str(r.get("Cód. Artículo") or "").strip(),
               str(r.get("Descripción artículo") or "").strip())
        if key[0] or key[1]:
            if key in seen:
                duplicados.append(r)
            else:
                seen[key] = r

    return {
        "total":             total,
        "sin_codigo":        len(sin_codigo),
        "sin_desc":          len(sin_desc),
        "sin_precio":        len(sin_precio),
        "sin_moneda":        len(sin_moneda),
        "precios_invalidos": len(precios_invalidos),
        "monedas_raras":     len(monedas_raras),
        "duplicados":        len(duplicados),
        "column_mapping":    data.get("column_mapping", {}),
        "extraction_method": data.get("extraction_method", "?"),
        "quality_score":     data.get("report", {}).get("quality_score"),
        "rows":              rows,
        "rows_sin_codigo":   sin_codigo,
        "rows_sin_precio":   sin_precio,
        "rows_duplicados":   duplicados,
        "rows_monedas_raras": monedas_raras,
    }


# ── Comparación con CSV de origen (L26031) ────────────────────────────────────
def comparar_con_csv(json_rows: list, csv_path: Path) -> list[dict]:
    df = pd.read_csv(csv_path, dtype=str, encoding="latin-1", sep=";").fillna("")

    # Detectar columnas clave
    cols = list(df.columns)
    partid_col = next((c for c in cols if "partid" in c.lower()), None)
    desc_col   = next((c for c in cols if "descripcion" in normalize(c)), None)
    price_col  = next((c for c in cols if "unit_price" in c.lower()), None)
    ean_col    = next((c for c in cols if "codigo de barras" in normalize(c)), None)

    print(f"  CSV cols usadas → partid={partid_col}, desc={desc_col}, price={price_col}, ean={ean_col}")

    # Build lookup
    excel_by_desc = {}
    for _, row in df.iterrows():
        key = normalize(row.get(desc_col, ""))
        if key:
            excel_by_desc[key] = {
                "partid": str(row.get(partid_col, "") or "").strip(),
                "precio": clean_price(row.get(price_col, "")),
                "ean":    str(row.get(ean_col, "") or "").strip(),
                "desc":   str(row.get(desc_col, "") or "").strip(),
            }

    results = []
    matched = set()

    for jrow in json_rows:
        j_code  = str(jrow.get("Cód. Artículo") or "").strip()
        j_desc  = str(jrow.get("Descripción artículo") or "").strip()
        j_price = clean_price(jrow.get("Precio"))
        j_key   = normalize(j_desc)

        exc = excel_by_desc.get(j_key)
        if exc:
            matched.add(j_key)

        if not exc:
            estado = "SIN_MATCH_CSV"
            partid_correcto = ""
            diff_precio = ""
        else:
            partid_correcto = exc["partid"]
            ean_clean       = exc["ean"].replace(".0", "")
            j_code_clean    = j_code.replace(".0", "")

            if not j_code:
                estado = "SIN_CODIGO"
            elif j_code_clean == partid_correcto:
                estado = "OK"
            elif j_code_clean == ean_clean:
                estado = "CODIGO_ES_EAN"
            else:
                estado = "CODIGO_INCORRECTO"

            diff_precio = ""
            if exc["precio"] is not None and j_price is not None:
                if abs(exc["precio"] - j_price) > 0.01:
                    diff_precio = f"CSV={exc['precio']} | JSON={j_price}"

        results.append({
            "Estado":             estado,
            "JSON Cód. Artículo": j_code,
            "PARTID correcto":    partid_correcto,
            "JSON Descripción":   j_desc,
            "JSON Precio":        j_price or "",
            "Diff Precio":        diff_precio,
        })

    # Items en CSV que no matchearon
    for key, exc in excel_by_desc.items():
        if key not in matched:
            results.append({
                "Estado":             "FALTA_EN_JSON",
                "JSON Cód. Artículo": "",
                "PARTID correcto":    exc["partid"],
                "JSON Descripción":   exc["desc"],
                "JSON Precio":        f"CSV: {exc['precio']}",
                "Diff Precio":        "",
            })

    return results


# ── Main ──────────────────────────────────────────────────────────────────────
all_summaries = []
per_file_dfs  = {}

for fname in TARGETS:
    fpath = RESPUESTAS_DIR / fname
    if not fpath.exists():
        print(f"[SKIP] No encontrado: {fname}")
        continue

    print(f"\n{'='*60}")
    print(f"Analizando: {fname}")
    res = analizar_json(fpath)

    summary = {
        "Archivo":           fname,
        "Método extracción": res["extraction_method"],
        "Quality Score":     res["quality_score"],
        "Total filas":       res["total"],
        "Sin Cód. Artículo": res.get("sin_codigo", 0),
        "Sin Descripción":   res.get("sin_desc", 0),
        "Sin Precio":        res.get("sin_precio", 0),
        "Sin Moneda":        res.get("sin_moneda", 0),
        "Precios inválidos": res.get("precios_invalidos", 0),
        "Monedas raras":     res.get("monedas_raras", 0),
        "Duplicados":        res.get("duplicados", 0),
        "Column mapping":    str(res["column_mapping"]),
    }
    all_summaries.append(summary)

    print(f"  extraction_method: {res['extraction_method']}")
    print(f"  column_mapping:    {res['column_mapping']}")
    print(f"  total={res['total']}  sin_codigo={res.get('sin_codigo',0)}  "
          f"sin_desc={res.get('sin_desc',0)}  sin_precio={res.get('sin_precio',0)}")

    # Comparación con CSV para L26031
    if "L26031 (5)" in fname and CSV_SOURCE.exists():
        print("  → Comparando con CSV de origen...")
        cmp_rows = comparar_con_csv(res["rows"], CSV_SOURCE)
        cmp_df   = pd.DataFrame(cmp_rows)
        per_file_dfs[f"L26031_csv_cmp"] = cmp_df
        conteo = cmp_df["Estado"].value_counts()
        print("  Conteo estados:")
        for e, n in conteo.items():
            print(f"    {e:<25}: {n:>5}")
    else:
        # Hojas con filas problemáticas para PDFs
        if res.get("rows_sin_codigo"):
            per_file_dfs[f"{fname[:20]}_sin_cod"] = pd.DataFrame(res["rows_sin_codigo"])
        if res.get("rows_sin_precio"):
            per_file_dfs[f"{fname[:20]}_sin_prec"] = pd.DataFrame(res["rows_sin_precio"])
        if res.get("rows_duplicados"):
            per_file_dfs[f"{fname[:20]}_duplic"] = pd.DataFrame(res["rows_duplicados"])
        if res.get("rows_monedas_raras"):
            per_file_dfs[f"{fname[:20]}_moneda"] = pd.DataFrame(res["rows_monedas_raras"])

# ── Generar Excel ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Generando reporte: {REPORT_PATH}")

with pd.ExcelWriter(REPORT_PATH, engine="openpyxl") as writer:
    pd.DataFrame(all_summaries).to_excel(writer, sheet_name="RESUMEN_GENERAL", index=False)
    for sheet_name, df in per_file_dfs.items():
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

print(f"Reporte guardado en: {REPORT_PATH}")
