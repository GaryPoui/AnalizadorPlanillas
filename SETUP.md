# SETUP — AnalizadorPlanillas API

## Inicio rapido (un solo comando)

**Opcion A — doble clic o desde cmd/bat:**
```
start.bat
```

**Opcion B — desde PowerShell:**
```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File "start.ps1"
```

El script levanta el backend, espera que arranque y abre el frontend en el navegador.
- Backend: http://localhost:8000
- Docs API: http://localhost:8000/docs
- Frontend: `pricebot/frontend/index.html` (se abre automaticamente)

---

## Que es

API REST construida con FastAPI que recibe archivos de listas de precios de proveedores
(PDF, XLS, XLSX, CSV) y los convierte al formato estándar de 12 columnas
**Plantilla_Precios_Compras**, usando un sistema híbrido de extracción heurística + Claude.

---

## Requisitos

| Requisito | Versión | Notas |
|-----------|---------|-------|
| Python | 3.11+ | Testeado en 3.14.5 |
| Anthropic API Key | — | Cuenta con acceso a `claude-haiku-4-5` |
| Tesseract OCR | 5.4+ | Solo para PDFs escaneados (AR36-style) |

### Ruta Python en este entorno

```
C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

---

## Instalación de dependencias

```bash
C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install -r pricebot/api/requirements.txt
```

Dependencias clave: `fastapi`, `uvicorn`, `httpx`, `pandas`, `pdfplumber`, `markitdown`,
`openpyxl`, `xlrd`, `pytesseract`, `python-multipart`.

### Tesseract OCR (solo si se necesita PDF escaneado)

```
winget install UB-Mannheim.TesseractOCR
```

Descargar `spa.traineddata` y copiarlo a la carpeta `tessdata/` de Tesseract.

---

## Configuración — archivo .env

Crear o editar `pricebot/.env` (UTF-8 SIN BOM — importante):

```env
ANTHROPIC_API_KEY=sk-ant-api03-...          # obligatorio
CLAUDE_MODEL=claude-haiku-4-5               # modelo activo

TESSERACT_CMD=C:\Users\...\Tesseract-OCR\tesseract.exe  # opcional, para OCR

# Sistema híbrido (default: activo)
HYBRID_EXTRACTION=1                         # aplica solo a PDF e imágenes; 0 para desactivar
HYBRID_MAX_TOKENS=3500                       # salida compacta: solo código + precio
HYBRID_XLS_CHUNK_CHARS=25000
CLAUDE_TIMEOUT_SEC=20                       # timeout estricto por página/chunk
PDF_USE_MARKITDOWN=0                        # 1 solo si se necesita ese conversor; pdfplumber es default

# Tracking de costos
COST_LOG_PATH=costs_log.jsonl               # ruta del log (default: raíz del proyecto)
INPUT_RATE_PER_M=3.0                        # USD/M tokens — tasa display
OUTPUT_RATE_PER_M=15.0
REAL_INPUT_RATE_PER_M=0.80                  # USD/M tokens — tasa real Haiku
REAL_OUTPUT_RATE_PER_M=4.0
```

**ADVERTENCIA**: PowerShell `Set-Content -Encoding UTF8` agrega BOM y rompe `load_dotenv`.
Usar en su lugar:
```powershell
[System.IO.File]::WriteAllText("pricebot\.env", $content, [System.Text.UTF8Encoding]::new($false))
```

---

## Cómo levantar la API

```bash
C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --app-dir "c:\Users\Pasante\Desktop\AnalizadorPlanillas\pricebot\api"
```

La API queda disponible en: **http://localhost:8000**

Documentación interactiva Swagger: **http://localhost:8000/docs**

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/extract` | Extrae datos → JSON con rows + report + usage |
| `POST` | `/extract/download` | Extrae datos → descarga XLSX |

### Ejemplo con curl

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@Listas/LCT Lista de Precios 02-2026 (4).pdf"
```

### Ejemplo con Python

```python
import httpx

with open("Listas/LCT Lista de Precios 02-2026 (4).pdf", "rb") as f:
    resp = httpx.post("http://localhost:8000/extract", files={"file": f})
    data = resp.json()

print(f"Filas: {len(data['rows'])}")
print(f"Costo: ${data['usage']['cost_display']} display / ${data['usage']['cost_real']} real")
```

---

## Estructura de la respuesta

```json
{
  "filename": "LCT Lista de Precios 02-2026 (4).pdf",
  "rows": [
    {
      "Cód. Artículo": "2170",
      "Descripción artículo": "SCA 10 10 5/16",
      "Precio": "896.85",
      "Moneda": "ARS",
      "Cód. Lista": "LCT",
      "Desc. Lista": "LCT Lista de Precios 02-2026"
    }
  ],
  "report": {
    "total_rows": 1052,
    "valid_rows": 1052,
    "quality_score": 100.0
  },
  "usage": {
    "tokens_in": 60788,
    "tokens_out": 57706,
    "tokens_total": 118494,
    "calls": 46,
    "cost_display": 1.048,
    "cost_real": 0.28
  },
  "extraction_method": "hybrid_pdf_dual",
  "metadata": { "pages": 46 }
}
```

---

## Cómo funciona — flujo de extracción

```
Archivo recibido
      │
      ├─ PDF ──► pdfplumber (tablas + texto por página) + MarkItDown
      │          + word-coordinate extraction (BUG-3 fix)
      │          + OCR Tesseract si < 1500 chars/pág (PDFs escaneados)
      │
      ├─ XLS/XLSX/CSV ──► pandas (detección automática de columnas)
      │
      └─ Imagen ──► Claude Vision
      │
      ▼
 Heurístico (regex, perfiles numéricos, tablas estructuradas)
      │
      ▼
 Paso híbrido Claude (por página / por chunk)  ← NUEVO default
      │  • max_tokens = 6000 por llamada
      │  • Salvamento de JSON truncado
      │  • Merge: heurístico como base, Claude agrega nuevos y enriquece desc
      │
      ▼
 Deduplicación + filtro ghost rows (BUG-8)
      │
      ▼
 Verificación (quality_score, normalización de precios)
      │
      ▼
 Respuesta JSON + log de costos (costs_log.jsonl)
```

---

## Log de costos automático

Cada extracción genera una línea en `costs_log.jsonl`:

```json
{"ts":"2026-08-19T10:30:00","file":"LCT.pdf","rows":1052,"method":"hybrid_pdf_dual","tokens_in":60788,"tokens_out":57706,"tokens_total":118494,"calls":46,"cost_display":1.048,"cost_real":0.28,"model":"claude-haiku-4-5"}
```

Para ver el resumen de costos acumulados:

```python
import json
from pathlib import Path

total = 0.0
for line in Path("costs_log.jsonl").read_text().splitlines():
    r = json.loads(line)
    total += r["cost_display"]
    print(f"{r['ts']}  {r['file']:<40}  rows={r['rows']:>5}  ${r['cost_display']:.4f}")
print(f"\nTotal acumulado: ${total:.4f}")
```

---

## Costos de referencia

| Tipo de archivo | Costo display aprox. | Costo real (Haiku) |
|----------------|---------------------|-------------------|
| Excel/CSV | $0.00 | $0.00 |
| PDF pequeño (<10 pág) | $0.15–$0.35 | $0.04–$0.09 |
| PDF mediano (10–20 pág) | $0.35–$0.70 | $0.09–$0.18 |
| PDF grande (>20 pág) | $0.70–$1.50 | $0.18–$0.40 |
| PDF escaneado (OCR) | $0.20–$0.30 | $0.05–$0.08 |

Para desactivar el modo híbrido y no gastar tokens: `HYBRID_EXTRACTION=0` en `.env`.

---

## Validar una extracción PDF

El siguiente comando no usa Claude ni genera costo. Recupera pares `código → precio`
inequívocos del texto PDF y los compara con un JSON extraído:

```bash
python tmp/validate_pdf_json.py "Listas/archivo.pdf" "Respuestas/resultado.json"
```

El reporte muestra pares correctos, faltantes, precios diferentes y la precisión verificable.

---

## Compactar un PDF antes del modo híbrido

La API compacta cada página automáticamente antes de enviar texto a Claude: conserva
líneas que contienen pares `código + precio` y deja el texto completo como fallback
si no hay pares detectables. Para inspeccionar o guardar esa entrada con cualquier PDF:

```bash
python tmp/compact_pdf_for_hybrid.py "Listas/archivo.pdf" --output "tmp/archivo_compacto.txt"
```

El script no llama a Claude, no altera el PDF ni genera costo.

El paso híbrido solicita a Claude solo objetos `{"code":"...","price":"..."}`.
Las descripciones se conservan desde la extracción local; esto reduce tokens de salida,
tiempo de respuesta y riesgo de timeouts.

XLS, XLSX y CSV no usan el paso híbrido ni el transformador Claude: se procesan
localmente para mantener costo $0.00. Las imágenes usan Vision y luego el complemento
híbrido; los PDFs usan extracción local más el complemento híbrido.

---

## Tests batch

Correr extracción sobre todos los archivos de `Listas/` (sin AR36):

```bash
C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe tests/batch_test_listas.py
```

Resultados guardados en `Respuestas/` (JSON) y `tests/outputs/batch_test_results.json`.
