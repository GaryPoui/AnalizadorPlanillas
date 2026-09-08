import asyncio, sys, json
sys.path.insert(0, 'pricebot/api')
import main
from pathlib import Path

async def run():
    pdf = Path('Listas/LCT Lista de Precios 02-2026 (4).pdf')
    result = await main.orchestrator(pdf.read_bytes(), pdf.name)
    rows = result['rows']
    rep = result['report']
    print('rows emitted:', len(rows))
    print('quality_score:', rep.get('quality_score'))
    print('rows_sent_to_review:', rep.get('rows_sent_to_review'))
    print('price_recovered_from_description:', rep.get('price_recovered_from_description'))
    print('valid_rows:', rep.get('valid_rows'))
    # audit garbage still present
    garbage = [r for r in rows if ' ' in str(r.get('Cód. Artículo','')) or 'cid:' in str(r.get('Cód. Artículo','')).lower()]
    print('garbage codes remaining:', len(garbage))
    # sample review
    print('--- review sample ---')
    for rr in rep.get('review_rows', [])[:15]:
        print('  ', repr(rr.get('Cód. Artículo')), '|', repr(rr.get('Descripción artículo'))[:50])
    # save
    Path('tmp/lct_new_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

asyncio.run(run())
