import asyncio, sys, json
sys.path.insert(0, 'pricebot/api')
import os
os.environ['HYBRID_EXTRACTION'] = '0'
os.environ['ANTHROPIC_API_KEY'] = ''
import main
from pathlib import Path

_out = []
def out(*a):
    _out.append(' '.join(str(x) for x in a))

async def run():
    pdf = Path('Listas/LCT Lista de Precios 02-2026 (4).pdf')
    raw = await main.agent_extractor(pdf.read_bytes(), pdf.name, '')
    exact = main._extract_unambiguous_pdf_prices(raw)
    checks = {'2060': 8383.53, '2062': 15285.10}
    out('=== authoritative extractor (BUG-9/10) ===')
    out('total authoritative pairs:', len(exact))
    for code, want in checks.items():
        got = exact.get(code)
        ok = 'OK' if got and abs(float(got) - want) < 0.01 else 'CHECK'
        out(f'  {code}: got={got} want~{want} {ok}')
    for bad in ['CCD-16', 'CCD-25', 'T30-44']:
        out(f'  mid-line {bad} present? {bad in exact} (should be False)')
    for code in ['4569', '4570', '4571']:
        out(f'  GK {code}: {exact.get(code)}')

    result = await main.orchestrator(pdf.read_bytes(), pdf.name)
    rows = result['rows']
    codes = [str(r.get('Cód. Artículo', '')) for r in rows]
    numeric = [int(c) for c in codes if c.isdigit()]
    is_sorted = numeric == sorted(numeric)
    out('=== sorting ===')
    out('rows:', len(rows), 'numeric codes sorted:', is_sorted)
    out('first 10 codes:', codes[:10])
    rep = result['report']
    out('quality:', rep.get('quality_score'), 'review:', rep.get('rows_sent_to_review'),
        'recovered:', rep.get('price_recovered_from_description'))
    Path('tmp/lct_fixed_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    asyncio.run(run())
except Exception:
    import traceback
    _out.append('ERROR:\n' + traceback.format_exc())
Path('tmp/fixes_result.txt').write_text('\n'.join(_out), encoding='utf-8')
