# SETUP — AnalizadorPlanillas API

## Primera instalacion despues de clonar

Ejecutar con doble clic o desde una terminal:

```bat
instalar.bat
```

El instalador detecta Python 3.11+, crea `.venv`, actualiza `pip`, instala todas
las librerias de `pricebot/api/requirements.txt` y crea `pricebot/.env` desde el
ejemplo cuando no existe. Luego hay que completar las claves y usuarios en ese
archivo.

## Inicio rapido

**Opcion A — doble clic o desde cmd/bat:**
```
start.bat
```

**Opcion B — desde PowerShell:**
```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File "C:\Users\Pasante\Desktop\AnalizadorPlanillas\start.ps1"
```

El script levanta el backend, espera que arranque y abre el frontend en el navegador.
- Backend: http://localhost:8000
- Docs API: http://localhost:8000/docs
- Frontend: http://127.0.0.1:3000 (se abre automaticamente)

El backend queda limitado a `127.0.0.1`; no acepta conexiones desde otros equipos de la red.
El frontend solo se sirve localmente y CORS permite únicamente los orígenes locales configurados.

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
| Anthropic API Key | — | Cuenta con acceso a `claude-sonnet-4-5` |
| Tesseract OCR | 5.4+ | Solo para PDFs escaneados (AR36-style) |

### Python utilizado por el proyecto

```
.venv\Scripts\python.exe
```

---

## Instalación de dependencias

```bat
instalar.bat
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
PRICEBOT_ALLOW_EXTERNAL_AI=0                # 1 solo con autorización para enviar datos a Anthropic
ANTHROPIC_API_KEY=                          # completar solo si se autorizó IA externa
CLAUDE_MODEL=claude-sonnet-4-5               # modelo activo
PRICEBOT_API_KEY=                            # recomendado: clave larga para proteger la API
PRICEBOT_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000,https://192.168.190.146:3000
PRICEBOT_REQUIRE_HTTPS=1                    # bloquea HTTP remoto; localhost sigue disponible
PRICEBOT_ENABLE_API_DOCS=0                  # Swagger/OpenAPI desactivados en producción
SAVE_HISTORY=0                               # no persistir filas completas por defecto
PRICEBOT_LOG_FILENAMES=0                    # no registrar nombres confidenciales
TRANSFORM_CACHE_MAX_ITEMS=0                 # no retener resultados entre solicitudes

TESSERACT_CMD=C:\Users\...\Tesseract-OCR\tesseract.exe  # opcional, para OCR

# Sistema híbrido (default: activo)
HYBRID_EXTRACTION=1                         # aplica solo a PDF e imágenes; 0 para desactivar
HYBRID_MAX_TOKENS=3500                       # salida compacta: solo código + precio
HYBRID_XLS_CHUNK_CHARS=25000
CLAUDE_TIMEOUT_SEC=90                       # timeout estricto por página/chunk
HYBRID_CONCURRENCY=3                        # páginas/chunks simultáneos
HYBRID_TOTAL_TIMEOUT_SEC=120                # límite total del complemento por archivo
HYBRID_TOTAL_TIMEOUT_SEC=120                # límite total; conserva filas locales si vence
PDF_USE_MARKITDOWN=0                        # 1 solo si se necesita ese conversor; pdfplumber es default

# Acceso privado (recomendado si el servidor es accesible desde otras PCs)
PRICEBOT_AUTH_REQUIRED=1
PRICEBOT_SESSION_SECRET=generar-una-clave-aleatoria-larga
PRICEBOT_COOKIE_SECURE=1                    # 1 si se usa HTTPS; 0 solo para HTTP local
PRICEBOT_LOGIN_MAX_ATTEMPTS=5
PRICEBOT_LOGIN_WINDOW_SEC=900
PRICEBOT_USERS=usuario$SAL$HASH,otro$SAL$HASH

# Límites contra agotamiento de memoria y archivos comprimidos maliciosos
PRICEBOT_MAX_UPLOAD_MB=50
PRICEBOT_MAX_BATCH_FILES=10
PRICEBOT_MAX_BATCH_MB=100
PRICEBOT_MAX_ARCHIVE_UNCOMPRESSED_MB=200
PRICEBOT_MAX_PDF_PAGES=300

# Tracking de costos
COST_LOG_PATH=costs_log.jsonl               # ruta del log (default: raíz del proyecto)
INPUT_RATE_PER_M=3.0                        # USD/M tokens — tasa display
OUTPUT_RATE_PER_M=15.0
REAL_INPUT_RATE_PER_M=0.80                  # USD/M tokens — tasa real Haiku
REAL_OUTPUT_RATE_PER_M=4.0
```

### Usuarios autorizados y seguridad de red

No guardes contraseñas en `PRICEBOT_USERS`. Generá un registro por usuario desde
la carpeta `pricebot/api`:

```powershell
python create_password_hash.py nombre_usuario
```

Copiá la línea impresa en `PRICEBOT_USERS`. Para agregar varios usuarios,
separá los registros con comas. Generá también un valor aleatorio largo para
`PRICEBOT_SESSION_SECRET`; nunca lo publiques en Git ni lo pongas en el
frontend.

La aplicación rechaza la extracción, las descargas y la documentación API si
no existe una sesión válida. El endpoint `/health` queda disponible para
monitoreo. Además, en el router/firewall del servidor permití únicamente los
puertos necesarios y no expongas directamente el puerto 8000 a Internet;
preferí un proxy HTTPS (Nginx/Caddy) o acceso solo desde la LAN/VPN.

#### Alta y confirmación de usuarios por correo

La pestaña **Usuarios** aparece únicamente al abrir el frontend desde
`http://127.0.0.1:3000` o `http://localhost:3000` en la computadora servidor.
La API también valida que la conexión administrativa provenga de loopback, por
lo que ocultar o mostrar la pestaña no es la medida de seguridad principal.

Configurá en `pricebot/.env`:

```env
PRICEBOT_AUTH_REQUIRED=1
PRICEBOT_SESSION_SECRET=una-clave-aleatoria-larga
PRICEBOT_COOKIE_SECURE=1
PRICEBOT_REQUIRE_HTTPS=1
PRICEBOT_PUBLIC_URL=https://192.168.190.146:3000
PRICEBOT_CONFIRMATION_TTL_SEC=86400

PRICEBOT_SMTP_HOST=smtp.proveedor.com
PRICEBOT_SMTP_PORT=587
PRICEBOT_SMTP_USERNAME=cuenta@empresa.com
PRICEBOT_SMTP_PASSWORD=clave-o-password-de-aplicacion
PRICEBOT_SMTP_FROM=cuenta@empresa.com
PRICEBOT_SMTP_STARTTLS=1
PRICEBOT_SMTP_SSL=0
```

Abrí la aplicación desde localhost en el servidor. Si todavía no existe ningún
usuario activo, se habilita automáticamente un modo de alta inicial que solo
responde por loopback. Si ya existen usuarios, iniciá sesión primero. Abrí la
pestaña **Usuarios** y cargá correo y contraseña inicial. La contraseña se
guarda con `scrypt`, el token de confirmación se guarda como hash y vence a las
24 horas por defecto. Hasta confirmar el enlace recibido, el usuario no puede
iniciar sesión. Desde la misma pantalla se puede reenviar la confirmación o
deshabilitar un acceso.

`PRICEBOT_PUBLIC_URL` debe apuntar a una dirección alcanzable por el receptor.
Una IP privada funciona solo dentro de la misma LAN o VPN. Para acceso por
Internet usá dominio, HTTPS y VPN/proxy; no publiques directamente el puerto
8000. El backend rechaza HTTP remoto por defecto.

Para aplicar permisos NTFS y restringir el firewall a `192.168.190.0/24`, abrí
PowerShell como administrador en el servidor y ejecutá:

```powershell
.\hardening.ps1
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
  --host 127.0.0.1 \
    --port 8000 \
    --app-dir "c:\Users\Pasante\Desktop\AnalizadorPlanillas\pricebot\api"
```

La API queda disponible en: **http://localhost:8000**

Swagger y OpenAPI están desactivados por defecto. Solo en una sesión local de
diagnóstico se pueden habilitar con `PRICEBOT_ENABLE_API_DOCS=1`.

La IA externa está desactivada por defecto. Al establecer
`PRICEBOT_ALLOW_EXTERNAL_AI=1`, los segmentos de PDF y las imágenes se envían a
Anthropic mediante HTTPS. Hacelo únicamente con autorización formal para esos
datos. Si los datos no pueden salir de la máquina, mantené el valor en `0` y usá
extracción local. Para un servidor compartido por varias personas, usar el acceso por
usuarios (`PRICEBOT_AUTH_REQUIRED=1`) y no colocar secretos en el frontend. `PRICEBOT_API_KEY`
queda disponible como compatibilidad adicional para clientes internos, pero no reemplaza el login.

### Servidor accesible desde otras computadoras

Por defecto `start.ps1` escucha únicamente en la propia PC y la API bloquea
HTTP remoto. Para compartirlo en la red necesitás un certificado cuya SAN
incluya la IP o el nombre usado por los clientes, y que esos clientes confíen
en su autoridad emisora:

```powershell
$env:PRICEBOT_BIND_HOST="0.0.0.0"
$env:PRICEBOT_TLS_CERTFILE="C:\ruta\pricebot-cert.pem"
$env:PRICEBOT_TLS_KEYFILE="C:\ruta\pricebot-key.pem"
.\start.ps1
```

Configurá además `PRICEBOT_ALLOWED_ORIGINS` y `PRICEBOT_PUBLIC_URL` con la URL
HTTPS final. En el firewall de Windows permití los puertos 3000 y 8000 solo en
el perfil **Privado** y para la subred necesaria. `hardening.ps1` configura el
rango `192.168.190.0/24`. Para acceso fuera de la LAN, usá una VPN o un proxy
HTTPS con autenticación.

Para un diagnóstico temporal sin documentos reales se puede establecer
`PRICEBOT_REQUIRE_HTTPS=0`; no lo uses en operación ni con credenciales reales.

Regla de extracción: todo código de producto válido detectado genera una fila, aunque no tenga
precio. En ese caso `Precio` queda vacío y `estado_precio` toma el valor `a completar`; la fila
no se descarta ni se considera inválida por esa ausencia.

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
    "quality_score": 100.0,
    "price_recovered_from_description": 0,
    "rows_sent_to_review": 2,
    "review_rows": [
      { "Cód. Artículo": "PHILLIPS", "Descripción artículo": "PHILLIPS", "Precio": "", "motivo": "código no válido (encabezado/texto/ruido)" }
    ]
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

Notas sobre el `report` (validación genérica, aplica a todos los formatos):
- `total_rows`: filas efectivamente emitidas (ya excluye las enviadas a revisión).
- `rows_sent_to_review` + `review_rows`: filas cuyo `Cód. Artículo` no es un código válido
  (encabezados, texto descriptivo, glyphs OCR). No se emiten como productos pero se listan
  para inspección manual; no se descartan en silencio.
- `price_recovered_from_description`: cantidad de filas donde el precio estaba dentro de
  `Descripción artículo` (columnas desalineadas) y se movió al campo `Precio`.
- Las filas se devuelven **ordenadas por código** (numéricos primero en orden ascendente,
  luego alfanuméricos).

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
 Saneamiento genérico (todos los formatos)
      │  • Códigos basura (encabezados, texto, glyphs OCR) → lista de revisión
      │  • Precio embebido en Descripción → se recupera al campo Precio
      │  • Pares código→precio inequívocos (código al inicio de línea, precio con
      │    decimales) rellenan solo precios vacíos o fragmentados (no sobreescriben)
      │
      ▼
 Verificación (quality_score, normalización de precios) + orden por código
      │
      ▼
 Respuesta JSON + log de costos (costs_log.jsonl)
```

---

## Log de costos automático

Cada extracción genera una línea en `costs_log.jsonl`:

```json
{"ts":"2026-08-19T10:30:00","file":null,"file_type":".pdf","rows":1052,"method":"pdf_dual","tokens_in":0,"tokens_out":0,"tokens_total":0,"calls":0,"cost_display":0.0,"cost_real":0.0,"model":"claude-haiku-4-5"}
```

Para ver el resumen de costos acumulados:

```python
import json
from pathlib import Path

total = 0.0
for line in Path("costs_log.jsonl").read_text().splitlines():
    r = json.loads(line)
    total += r["cost_display"]
    print(f"{r['ts']}  {r['file_type']:<8}  rows={r['rows']:>5}  ${r['cost_display']:.4f}")
print(f"\nTotal acumulado: ${total:.4f}")
```

---

## Costos de referencia

| Tipo de archivo | Costo display aprox. | Costo configurado aprox. |
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

## Ejecutar el híbrido con cualquier PDF

El comando recomendado no está ligado a ningún proveedor:

```bash
python tmp/run_pdf_hybrid.py "Listas/archivo.pdf"
```

También permite indicar el JSON de salida:

```bash
python tmp/run_pdf_hybrid.py "ruta/archivo.pdf" --output "Respuestas/resultado.json"
```

El ejecutor informa filas, calidad, tokens, costos y advertencias por página. Los scripts
con nombres de proveedores que permanecen en `tmp/` son pruebas históricas; la API y este
comando usan la implementación genérica.

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

La respuesta incluye `hybrid_status`: `completed`, `partial`, `timeout` o `disabled`.
Ante un timeout o error de Claude, la API conserva y devuelve las filas locales y agrega
el detalle en `hybrid_errors`; una falla externa no bloquea todo el procesamiento.
El frontend espera hasta 300 segundos; el complemento híbrido está limitado a 120 segundos
y después devuelve el resultado local disponible.

Las correcciones de códigos fragmentados, precios truncados y columnas paralelas son
reglas estructurales del extractor: no contienen códigos ni precios específicos de LCT.
Por eso se aplican también a cualquier PDF futuro con layouts equivalentes.

XLS, XLSX y CSV no usan el paso híbrido ni el transformador Claude: se procesan
localmente para mantener costo $0.00. Las imágenes usan Vision y luego el complemento
híbrido; los PDFs usan extracción local más el complemento híbrido.

Si Claude no responde antes de `HYBRID_TOTAL_TIMEOUT_SEC`, la API devuelve la extracción
local disponible y agrega una advertencia al `log`; no devuelve cero filas ni deja pendiente
la solicitud indefinidamente.

---

## Tests batch

Correr extracción sobre todos los archivos de `Listas/` (sin AR36):

```bash
C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe tests/batch_test_listas.py
```

Resultados guardados en `Respuestas/` (JSON) y `tests/outputs/batch_test_results.json`.
