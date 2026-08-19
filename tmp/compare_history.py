"""
Compara todas las versiones históricas de un archivo extraído.
Muestra evolución de filas, costo, método y puntaje de calidad.

Uso:
    python tmp/compare_history.py                          # todos los archivos
    python tmp/compare_history.py "Lista de Precios N"     # filtro por nombre
"""
import json
import sys
from pathlib import Path

HISTORY_DIR = Path("c:/Users/Pasante/Desktop/AnalizadorPlanillas/Respuestas/history")


def load_versions(pattern: str = "") -> dict[str, list[dict]]:
    if not HISTORY_DIR.exists():
        print(f"No existe la carpeta {HISTORY_DIR}")
        return {}
    files: dict[str, list[dict]] = {}
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = data.get("filename", f.stem)
        if pattern and pattern.lower() not in name.lower():
            continue
        files.setdefault(name, []).append({
            "ts":     data.get("ts", "?"),
            "rows":   len(data.get("rows", [])),
            "method": data.get("extraction_method", "?"),
            "score":  data.get("report", {}).get("quality_score", "?"),
            "cost":   data.get("usage", {}).get("cost_display", 0),
            "tokens": data.get("usage", {}).get("tokens_total", 0),
            "file":   f.name,
        })
    return files


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    versions = load_versions(pattern)

    if not versions:
        print("Sin historial guardado aún.")
        return

    for name, runs in versions.items():
        print(f"\n{'='*70}")
        print(f"Archivo: {name}")
        print(f"{'='*70}")
        print(f"{'#':<4} {'Fecha/Hora':<20} {'Filas':>6} {'Score':>6} {'Tokens':>8} {'Costo':>8}  Método")
        print("-" * 70)

        prev_rows = None
        for i, r in enumerate(runs, 1):
            delta = ""
            if prev_rows is not None:
                diff = r["rows"] - prev_rows
                delta = f"({'+'if diff>=0 else ''}{diff})"
            print(
                f"{i:<4} {r['ts'][:19]:<20} {r['rows']:>6} {delta:>8} "
                f"{str(r['score']):>6} {r['tokens']:>8,} ${r['cost']:>7.4f}  {r['method']}"
            )
            prev_rows = r["rows"]

        if len(runs) >= 2:
            first, last = runs[0], runs[-1]
            row_change = last["rows"] - first["rows"]
            print(f"\n  Evolución: {first['rows']} → {last['rows']} filas "
                  f"({'+'if row_change>=0 else ''}{row_change})")
            total_cost = sum(r["cost"] for r in runs)
            print(f"  Costo total sesión: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
