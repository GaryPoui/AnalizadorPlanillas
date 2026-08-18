import sys, asyncio, os
sys.path.insert(0, 'pricebot/api')
from dotenv import load_dotenv
load_dotenv('pricebot/.env')
import main as m

async def test():
    with open('Listas/LCT Lista de Precios 02-2026 (4).pdf','rb') as f:
        file_bytes = f.read()

    result = await m.orchestrator(
        file_bytes=file_bytes,
        filename="LCT Lista de Precios 02-2026 (4).pdf",
    )
    rows = result.get("rows", [])
    print(f"Total rows: {len(rows)}")

    # Count noisy entries
    noise_blacklist = {"CODIGO", "REFERENCIA", "PRECIO", "ALUMINIO", "COBRE",
                       "BRONCE", "SIN", "POR", "PVC", "IEC", "QM15", "ISO9001",
                       "IP23", "IP24"}
    noisy = [r for r in rows if str(r.get("Cód. Artículo","")).upper() in noise_blacklist]
    print(f"Noisy blacklisted rows: {len(noisy)}")

    # Count code=desc rows (word-coord fallback)
    code_eq_desc = [r for r in rows
                    if r.get("Cód. Artículo") == r.get("Descripción artículo")
                    and r.get("Cód. Artículo")]
    print(f"Code=Desc rows: {len(code_eq_desc)}")
    for r in code_eq_desc[:5]:
        print(f"  {r['Cód. Artículo']} | {r['Precio']}")

    # Check 6219 specifically
    rows_6219 = [r for r in rows if r.get("Cód. Artículo") == "6219"]
    print(f"Rows for code 6219: {len(rows_6219)}")
    for r in rows_6219:
        print(f"  desc={r['Descripción artículo']!r}  price={r['Precio']}")

asyncio.run(test())
