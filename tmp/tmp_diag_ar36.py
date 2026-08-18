import sys, io, asyncio, os
sys.path.insert(0, 'pricebot/api')
from dotenv import load_dotenv
load_dotenv('pricebot/.env')
import main as m

with open('Listas/LISTA AR36 (2).pdf','rb') as f:
    file_bytes = f.read()

sync_result = m._extract_pdf_sync(file_bytes)
print('pages:', sync_result.get('pages'))
print('md_chars:', sync_result.get('md_chars'))
print('plumber_chars:', sync_result.get('plumber_chars'))
print('extraction_method:', sync_result.get('extraction_method'))
print('pdf_word_rows count:', len(sync_result.get('pdf_word_rows',[])))
print('word_rows[0:3]:', sync_result.get('pdf_word_rows',[])[:3])
print('pdf_raw_tables count:', len(sync_result.get('pdf_raw_tables',[])))
raw = sync_result.get('raw_text','')
print('raw_text len:', len(raw))
print('--- FIRST 3000 chars of raw_text ---')
print(raw[:3000])
print()
print('--- LINES 100-200 ---')
lines = raw.splitlines()
print('\n'.join(lines[100:200]))
