import json
data = json.loads(open("Respuestas/n95_test_result.json", encoding="utf-8").read())
rows = data["rows"]
targets = {"BE64-12-150","TBE-07-150","CPE90-64-16-150","RSE-18-75","CAE-64-16-150"}
for r in rows:
    code = str(r.get("Cód. Artículo","")).strip().upper()
    if code in targets:
        print(f"{code:<25} precio={r.get('Precio',''):<12}  desc={str(r.get('Descripción artículo',''))[:60]}")
