import urllib.request, json, sys

OUT = open(r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_quick_check_out.txt", "w")

def log(msg):
    OUT.write(msg + "\n")
    OUT.flush()

pdf_path = r"c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf"
url = "http://127.0.0.1:8000/extract"

boundary = "----boundary12345"
with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

log(f"PDF size: {len(pdf_bytes)} bytes")

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="LCT Lista de Precios 02-2026 (3).pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(url, data=body)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        status = resp.status
        raw = resp.read().decode()
        data = json.loads(raw)
except Exception as e:
    log(f"ERROR: {e}")
    OUT.close()
    sys.exit(1)

log(f"status: {status}")
log(f"total_rows: {data.get('report', {}).get('total_rows', 'N/A')}")
log(f"quality_score: {data.get('report', {}).get('quality_score', 'N/A')}")

rows = data.get("rows", [])
for code in ["2200", "3000", "4501", "4033"]:
    found = any(str(r.get("Cód. Artículo", "")).strip() == code for r in rows)
    log(f"code {code}: {'FOUND' if found else 'NOT FOUND'}")

OUT.close()
