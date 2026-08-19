import json
from pathlib import Path

lines = Path("costs_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
print(f"Total entradas: {len(lines)}")
print()
total = 0.0
for line in lines:
    r = json.loads(line)
    total += r["cost_display"]
    print(f"{r['ts'][:19]}  {r['file'][:45]:<45}  rows={r['rows']:>5}  tokens={r['tokens_total']:>7,}  cost=${r['cost_display']:.4f}")
print(f"\nTotal acumulado: ${total:.4f}")
