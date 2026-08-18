import sys, re
sys.path.insert(0, 'pricebot/api')
from dotenv import load_dotenv
load_dotenv('pricebot/.env')
import main as m

with open('Listas/LISTA AR36 (2).pdf','rb') as f:
    file_bytes = f.read()

sync_result = m._extract_pdf_sync(file_bytes)
raw = sync_result.get('raw_text','')

hits = 0
for ln in raw.splitlines()[:2500]:
    if m.NUMERIC_ITEM_PROFILE_RE.search(ln or ''):
        hits += 1

print('NUMERIC_ITEM_PROFILE_RE hits:', hits, '-> strict_numeric_profile:', hits >= 20)
print()
print('Sample matches:')
count = 0
for ln in raw.splitlines():
    if m.NUMERIC_ITEM_PROFILE_RE.search(ln or ''):
        print(repr(ln[:120]))
        count += 1
        if count >= 10:
            break
