"""
Convierte cualquier JSON de Respuestas/ (formato orquestador) a XLSX.
Costo: $0.00 — solo Python/pandas, sin llamadas a la API.

Uso:
    python tmp/json_to_xlsx.py                      # convierte todos los JSON de Respuestas/
    python tmp/json_to_xlsx.py nombre_archivo.json  # convierte uno específico
"""
import json
import sys
from pathlib import Path

import pandas as pd

RESPUESTAS = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas")
OUTPUT_DIR = RESPUESTAS

COLUMN_ORDER = [
    "Cód. Artículo",
    "Descripción artículo",
    "Precio",
    "Moneda",
    "Cód. Lista",
    "Desc. Lista",
    "Sinónimo",
]


def convert(json_path: Path) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = data.get("rows", [])
    if not rows:
        print(f"  SKIP {json_path.name}: sin filas")
        return None

    df = pd.DataFrame(rows)
    # Reorder columns: known first, then any extras
    cols = [c for c in COLUMN_ORDER if c in df.columns]
    extras = [c for c in df.columns if c not in COLUMN_ORDER]
    df = df[cols + extras]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / (json_path.stem + ".xlsx")
    df.to_excel(out, index=False, engine="openpyxl")
    return out


def main():
    targets: list[Path] = []

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = RESPUESTAS / arg if not Path(arg).is_absolute() else Path(arg)
            if not p.exists():
                print(f"No encontrado: {p}")
                continue
            targets.append(p)
    else:
        targets = sorted(RESPUESTAS.glob("*.json"))

    if not targets:
        print("No hay archivos JSON para convertir.")
        sys.exit(1)

    print(f"Convirtiendo {len(targets)} archivo(s) → {OUTPUT_DIR}/\n")
    for p in targets:
        out = convert(p)
        if out:
            data = json.loads(p.read_text(encoding="utf-8"))
            rows = len(data.get("rows", []))
            print(f"  OK  {p.name:<55} {rows:>5} filas → {out.name}")

    print("\nListo. Costo: $0.00")


if __name__ == "__main__":
    main()
