# AnalizadorPlanillas — PriceBot

Sistema multi-agente que recibe archivos de listas de precios de proveedores y los convierte automáticamente al formato de importación **Plantilla_Precios_Compras** (12 columnas estandarizadas).

---

## Arquitectura

```
Archivo (PDF / XLS / XLSX / CSV / imagen)
          │
    ┌─────▼──────────────┐
    │   EXTRACTOR        │  PDF → MarkItDown + pdfplumber (fallback)
    │                    │  XLS/XLSX/CSV → pandas
    │                    │  Imágenes → Claude Vision
    └─────┬──────────────┘
          │ raw_text
    ┌─────▼──────────────┐
    │   TRANSFORMER      │  Intenta mapear localmente (pandas/regex)
    │                    │  Si falla → Claude claude-sonnet-4-6
    │                    │  raw_text → rows[] (12 columnas)
    └─────┬──────────────┘
          │ rows[]
    ┌─────▼──────────────┐
    │   VERIFIER         │  Valida precios, normaliza monedas
    │                    │  Calcula quality_score (0–100)
    └─────┬──────────────┘
          │
    ┌─────▼──────────────┐
    │   OUTPUT           │  JSON response  /  XLSX descarga
    └────────────────────┘
```

> **Principio de extracción**: para Excel y CSV siempre se intenta extraer localmente con pandas primero. Claude solo es llamado cuando el mapeo automático no es suficiente. Esto reduce el consumo de tokens al mínimo necesario.

---

## Columnas del Template

| # | Columna | Descripción |
|---|---------|-------------|
| 1 | Cód. Artículo | Código del artículo del proveedor |
| 2 | Descripción artículo | Descripción principal |
| 3 | Descripción adicional artículo | Especificaciones técnicas, modelo |
| 4 | Sinónimo | Código alternativo |
| 5 | Cód. Lista | Código de la lista de precios |
| 6 | Desc. Lista | Nombre/descripción de la lista |
| 7 | Moneda | ARS, USD, EUR |
| 8 | Unidad | Un, m, kg, caja, etc. |
| 9 | Precio | Valor numérico sin símbolo |
| 10 | Bonif. | Porcentaje de descuento |
| 11 | Fecha vigencia desde | DD/MM/YYYY |
| 12 | Fecha vigencia hasta | DD/MM/YYYY |

---

## Setup

### Requisitos
- Python 3.11+
- pip

### 1. Configurar API Key

```bash
# Copiar el ejemplo y completar con tu clave
cp pricebot/.env.example pricebot/.env
# Editar pricebot/.env y agregar tu ANTHROPIC_API_KEY
```

### 2. Instalar dependencias

```bash
pip install -r pricebot/api/requirements.txt
```

### 3. Levantar el servidor

```bash
cd pricebot/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El frontend estático está en `pricebot/frontend/` — abrirlo con Live Server o cualquier servidor HTTP.

### Docker (alternativa)

```bash
cp pricebot/.env.example pricebot/.env   # completar la API key
docker compose -f pricebot/docker-compose.yml up --build
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/extract` | Extrae datos → JSON con rows + report |
| `POST` | `/extract/download` | Extrae datos → descarga XLSX |
| `POST` | `/extract/batch` | Múltiples archivos → JSON batch |

### Ejemplo básico

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@lista.pdf"
```

### Respuesta típica

```json
{
  "filename": "lista.pdf",
  "rows": [ { "Cód. Artículo": "2200", "Precio": "15000", "..." : "..." } ],
  "report": {
    "total_rows": 1601,
    "valid_rows": 1601,
    "quality_score": 100.0
  },
  "extraction_method": "pdf_dual",
  "metadata": { "pages": 42 }
}
```

---

## Formatos Soportados

| Formato | Método de extracción |
|---------|---------------------|
| `.pdf` | MarkItDown (principal) + pdfplumber (fallback) |
| `.xlsx` / `.xlsm` | pandas + openpyxl; Claude si el mapeo local falla |
| `.xls` | pandas + xlrd; Claude si el mapeo local falla |
| `.csv` | pandas; Claude si el mapeo local falla |
| `.jpg` / `.png` / `.webp` | Claude Vision (multimodal) |

---

## Tests

Los scripts de prueba están en `tests/`. Todos requieren la API corriendo en `localhost:8000`
(excepto `run_with_usage.py` y `test_orchestrator.py` que importan `main.py` directamente).

| Script | Descripción |
|--------|-------------|
| `tests/run_with_usage.py` | Ejecuta orquestador sobre `lista95.pdf`, mide tokens y costo real. Guarda `outputs/orchestrator_usage_summary.json` |
| `tests/test_orchestrator.py` | Smoke test: ejecuta orquestador y verifica que devuelva filas |
| `tests/check_lct.py` | Envía `lct_02_2026.pdf` a la API y valida que los códigos conocidos estén presentes |
| `tests/check_codes.py` | Igual que el anterior pero además verifica precios de artículos específicos |
| `tests/call_extract_http.ps1` | Test HTTP via PowerShell con `lista95.pdf`, guarda métricas básicas |
| `tests/call_extract_summary.ps1` | Test HTTP via PowerShell con `lct_02_2026.pdf`, muestra resumen completo |

### PDFs de prueba

| Archivo | Descripción |
|---------|-------------|
| `tests/samples/lista95.pdf` | Lista N° 95 — 1601 artículos, quality_score 100% |
| `tests/samples/lct_02_2026.pdf` | Lista proveedor LCT (febrero 2026) |

### Outputs de referencia

| Archivo | Descripción |
|---------|-------------|
| `tests/outputs/salida_lista95.json` | Extracción completa de lista95 (resultado de referencia) |
| `tests/outputs/orchestrator_usage_summary.json` | Último resumen de uso de tokens y costo |

---

## Historial de avances y costos (2026-08-04 / 05)

### Sesión 1 — 2026-08-04 · Setup y organización

- Reorganización completa del proyecto: eliminados ~45 archivos `tmp_*`, creadas carpetas `tests/`, `Listas/`, `Respuestas/`
- Documentados los primeros bugs del sistema
- Primer batch test **sin Claude** (sin API key):

| Archivo | Filas | Quality | Tiempo |
|---------|------:|--------:|-------:|
| L26031 xlsx | 2558 | 99.8% | 0.8s |
| L26031 csv | 2558 | 99.8% | 0.1s |
| LCT 02-2026 pdf | 981 | 100% | 101.5s |
| Lista N°95 pdf | 606 | 100%* | 26.5s |
| LP MICROCONTROL xls | 1093 | 0% | 1.1s |
| LISTA AR36 pdf | 0 | 0% | 41.5s |

> \* quality_score=100% nominal, pero 606/1601 filas con 85% de descripciones malformadas.

**Costo: $0.00** — 0 llamadas a Claude.

---

### Sesión 2 — 2026-08-05 · Primera prueba con Claude (con bugs activos)

- Configurada API key en `pricebot/.env` (con BOM bug que impedía que Python la leyera)
- Detectado y corregido el BOM de PowerShell (`Set-Content -Encoding UTF8` agrega BOM, `load_dotenv` falla silenciosamente)
- Primer batch test **con Claude** y `AI_COMPLEMENT_ALL_CHUNKS=True` (default activo):

| Archivo | Filas | Tokens | Costo | Tiempo | Problema |
|---------|------:|-------:|------:|-------:|---------|
| L26031 xlsx | 2558 | 0 | $0.0000 | 0.8s | Local puro |
| L26031 csv | 2558 | 0 | $0.0000 | 0.1s | Local puro |
| LCT 02-2026 pdf | **0** | 103.299 | **$0.5492** | 300s | Timeout BUG-7 |
| LISTA AR36 pdf | 0 | 1.602 | $0.0074 | 42.9s | PDF escaneado |
| Lista N°95 pdf | **0** | 65.426 | **$0.5468** | 300s | Timeout BUG-7 |
| LP MICROCONTROL xls | 1093 | 0 | $0.0000 | 0.2s | Local BUG-1 |
| **TOTAL** | | **170.327** | **$1.1034** | | |

**Resultado: $1.10 gastados, 0 filas útiles de PDFs con Claude.**

---

### Sesión 3 — 2026-08-05 · Fixes y batch test final

**Fixes aplicados en `pricebot/api/main.py`:**

| Bug | Descripción | Fix |
|-----|-------------|-----|
| BUG-7 | `AI_COMPLEMENT_ALL_CHUNKS=True` enviaba TODOS los chunks a Claude | Default → `"0"` |
| BUG-7b | `strict_numeric_profile` filtraba local_rows a 0, disparando AI en todos los chunks del LCT | Skip AI cuando seed ≥ `PDF_MIN_EXPECTED_ROWS` |
| BUG-5 | `pick_column()` mapeaba `CODIGO DE BARRAS` como código en lugar de `PARTID` | Prioridad: `partid` primero; excluir columnas con `"barras"`/`"ean"` |
| BUG-5+ | `CODIGO DE BARRAS` y `EAN` no iban a ningún campo útil | Mapeados a `Sinónimo` |
| BUG-1 | Excel/XLS sin headers retornaba 1093 filas vacías en lugar de usar Claude | Fallback a text/Claude si no mapea `Cód. Artículo` ni `Precio` |
| BUG-6 | PDFs con múltiples columnas por página extraían solo la primera | `_detect_table_column_roles` retorna `extra_pairs`; segundo loop de extracción |

**Batch test final post-fixes:**

| Archivo | Formato | KB | Filas | Quality | Tokens | Costo USD | Tiempo | Claude |
|---------|---------|---:|------:|--------:|-------:|----------:|-------:|--------|
| L26031 (xlsx) | .xlsx | 186 | 2558 | 99.8% | 0 | $0.0000 | 0.8s | No (local) |
| L26031 (csv) | .csv | 288 | 2558 | 99.8% | 0 | $0.0000 | 0.1s | No (local) |
| LCT 02-2026 (pdf) | .pdf | 3713 | 981 | 100% | 0 | $0.0000 | 82.0s | No (heurístico) |
| LISTA AR36 (pdf) | .pdf | 1762 | 0 | 0% | 1.602 | $0.0074 | 48.0s | Sí (PDF escaneado) |
| Lista N°95 (pdf) | .pdf | 1344 | 620 | 100% | 0 | $0.0000 | 23.9s | No (tabla) |
| LP MICROCONTROL (xls) | .xls | 6134 | 60 | — | 0 | $0.0000 | 0.2s | No (heurístico texto) |
| **TOTAL** | | | **6779** | | **1.602** | **$0.0074** | | |

**Reducción de costo: 99.3%** — de $1.10 a $0.0074 por el batch completo.

### Comparación consolidada: antes vs después

| Archivo | Filas antes | Filas después | Costo antes | Costo después | Mejora principal |
|---------|------------:|--------------:|------------:|--------------:|-----------------|
| L26031 xlsx | 2558 (EAN) | **2558 (PARTID)** | $0.00 | $0.00 | Código correcto |
| LCT pdf | 0 (timeout) | **981** | $0.55 | $0.00 | BUG-7 + BUG-7b |
| Lista N°95 pdf | 606 (desc malform.) | **620** | $0.55 | $0.00 | BUG-6 (parcial) |
| LP MICROCONTROL | 1093 (vacíos) | **60 (reales)** | $0.00 | $0.00 | BUG-1 |
| LISTA AR36 | 0 | 0 | $0.01 | $0.01 | Sin cambio (OCR pendiente) |

### Sesión 4 — 2026-08-05 · Cambio de modelo a Haiku + comparación final

**Objetivo**: reducir costos cambiando de `claude-sonnet-4-6` a `claude-haiku-4-5`.

**Hallazgo durante el cambio**: Los model IDs de Anthropic siguen un formato estricto. Se probaron varios nombres y solo dos funcionaron con la API key actual:

| Model ID | Status |
|----------|--------|
| `claude-haiku-3-5` | ❌ 404 (nombre incorrecto) |
| `claude-3-5-haiku-20241022` | ❌ 404 (no disponible en este tier) |
| `claude-3-haiku-20240307` | ❌ 404 (no disponible en este tier) |
| `claude-sonnet-4-6` | ✅ 200 |
| `claude-haiku-4-5` | ✅ 200 |

**Conclusión**: con esta API key solo están disponibles los modelos Claude 4.x (`claude-sonnet-4-6` y `claude-haiku-4-5`). Los modelos 3.x no están habilitados.

---

**Comparación: `claude-sonnet-4-6` vs `claude-haiku-4-5`** (post-fixes, 2026-08-05)

| Archivo | Filas Sonnet | Filas Haiku | Tokens Sonnet | Tokens Haiku | Costo Sonnet* | Costo Haiku* |
|---------|------------:|------------:|--------------:|-------------:|-------------:|-------------:|
| L26031 xlsx | 2558 | 2558 | 0 | 0 | $0.0000 | $0.0000 |
| L26031 csv | 2558 | 2558 | 0 | 0 | $0.0000 | $0.0000 |
| LCT 02-2026 pdf | 981 | 981 | 0 | 0 | $0.0000 | $0.0000 |
| LISTA AR36 pdf | 0 | 0 | 1.602 | 1.669 | $0.0074 | $0.0084 |
| Lista N°95 pdf | 620 | 620 | 0 | 0 | $0.0000 | $0.0000 |
| LP MICROCONTROL xls | 60 | 60 | 0 | 0 | $0.0000 | $0.0000 |
| **TOTAL** | **6777** | **6777** | **1.602** | **1.669** | **$0.0074** | **$0.0084** |

> \* Costos estimados usando tarifas de Sonnet ($3/$15 por M tokens). Con las tarifas reales de Haiku el costo real de Haiku sería **significativamente menor**.

**Diferencias observadas:**
- **Filas extraídas**: idénticas en todos los archivos — Haiku produce los mismos resultados que Sonnet para esta tarea
- **Tokens**: AR36 usó 67 tokens más con Haiku (1669 vs 1602) — diferencia insignificante en tokenización
- **Archivos que usan Claude**: solo LISTA AR36 (PDF escaneado). El resto se procesa localmente sin ninguna llamada a la API

**Modelo activo**: `claude-haiku-4-5` — más económico, misma calidad de extracción para este caso de uso.

---

| Prioridad | Bug/Feature | Estado |
|-----------|------------|--------|
| ✅ Resuelto | LISTA AR36: PDF escaneado — OCR Tesseract | BUG-2 cerrado |
| Alta | Lista N°95: 620/1601 filas (38%) — mejorar heurísticas | ~1000 filas extra sin costo |
| Alta | LP MICROCONTROL: 60/1000+ filas — Claude con headers inferidos | +940 filas, costo bajo |
| Media | Tracking tokens/costo en endpoint `/extract` | Observabilidad producción |
| Baja | asyncio.to_thread() para extracción síncrona de PDFs | BUG-4 |

---

### Sesión 8 — 2026-08-18 · Batch test Sesión 8 + patch LCT páginas faltantes

#### Contexto
Sesión enfocada en dos tareas:
1. **Patch del LCT** (Paso 2): extracción directa de las páginas con layout transpuesto que el extractor normal no procesa
2. **Batch test completo** con la versión actual del extractor para actualizar todos los JSONs

#### Extracción páginas faltantes del LCT (sin archivo externo)

El PDF tiene texto vectorial en las páginas problemáticas, pero en formato transpuesto (cada columna = un producto con 4 filas: CÓDIGO / MODELO / DESCRIPCIÓN / PRECIO). Se escribió `tmp_extract_missing.py` con un parser específico.

| Páginas | Contenido | Productos extraídos |
|---------|-----------|-------------------:|
| 16 | Terminales Preaislados Termi-Plast (A2–A22, B18–B30, C1–C18) | +48 |
| 22 | Herramientas: LY-10, LY-16, LY-35, HX-50/150/240, LY-120 | +7 |
| 23 | Herramientas: LY-03C/35C/04WF/16WF/35WF/95WF/150WF, ES-10WF, LY-03B/05H/518G | +11 |
| 24 | Herramientas: LY-468/5684A/B, LY-5D/7/700, WS-16, LY-6/25-3/4/9, PG-5, LY-332 | +13 |
| 34 | Herramientas HM: HM-1/2/3/5/C | +5 |
| — | LY-16C (4073) agregado manualmente (no extraído por layout) | +1 |
| **Total** | | **+85** |

Correcciones de precio aplicadas:
- `3021` (B3): desc=`3022`, precio=`$3020` → desc=`B3`, precio=`$228.68`
- `3032` (B17): precio=`$3033` → `$161.02`
- `4325` (DPH-8): precio=`$972.95` → `$24972.95`

**LCT resultante**: 903 (extractor) + 85 (patch) = **988 filas**

#### Batch test — versión actual del extractor (2026-08-18)

| Archivo | Filas | Quality | Tokens | Costo | Tiempo | Notas |
|---------|------:|--------:|-------:|------:|-------:|-------|
| L26031 xlsx | 2558 | 99.8% | 0 | $0.00 | 0.9s | ✅ Estable |
| L26031 csv | 2558 | 99.8% | 0 | $0.00 | 0.3s | ✅ Estable |
| **LCT PDF** | **988** | 100% | 0 | $0.00 | 113s | ✅ 903 extractor + 85 patch manual |
| LISTA AR36 PDF | 109 | — | 19.685 | $0.2216 | 134.5s | ⚠️ OCR deficiente: 30/109 code=desc, 79 con artefactos OCR |
| Lista N°95 PDF | 620 | 100% | 0 | $0.00 | 28s | ✅ Estable |
| LP MICROCONTROL xls | 60 | — | 0 | $0.00 | 0.3s | ✅ Estable |
| **TOTAL** | | | **19.685** | **$0.2216** | | |

#### AR36 — análisis de calidad (extracción OCR)
De 109 filas extraídas:
- **30 malas**: patrón code=desc=precio (ej: código=`2473`, desc=`2473`, precio=`$2473.0`)
- **79 "buenas"** pero con artefactos OCR: emails, CBU bancarios, texto cortado

El problema es inherente al PDF escaneado. No es resoluble mejorando el extractor sin una fuente de datos limpia. **Excluido de análisis de calidad.**

---

### Sesión 7 — 2026-08-11 · BUG-8 fix completo + limpieza de filas basura (auditoría Sonnet)

#### Batch test final (modelo `claude-haiku-4-5`)

| Archivo | Filas | Quality | Tokens | Costo | Tiempo | Método |
|---------|------:|--------:|-------:|------:|-------:|--------|
| L26031 xlsx | 2558 | 99.8% | 0 | $0.00 | 1.3s | direct_structured |
| L26031 csv | 2558 | 99.8% | 0 | $0.00 | 0.1s | direct_structured |
| LCT 02-2026 pdf | **903** | 100% | 0 | $0.00 | 109s | pdf_dual |
| LISTA AR36 pdf | ~97–115 | — | 21.143 | $0.2434 | 138s | pdf_ocr |
| Lista N°95 pdf | **620** | 100% | 0 | $0.00 | 31s | pdf_dual |
| LP MICROCONTROL xls | 60 | — | 0 | $0.00 | 0.2s | direct_structured |
| **TOTAL** | | | **21.143** | **$0.2434** | | |

#### Progresión LCT (limpieza acumulada)

| Etapa | Filas | Cambio | Motivo |
|-------|------:|-------:|--------|
| Sesión 6 (post BUG-3) | 1065 | base | +84 filas word-coord |
| BUG-8 fix (blacklist + `$` filter) | 923 | −142 | CODIGO/Aluminio/Bronce/PVC bloqueados |
| Ghost cleanup R2/R3 (Sesión 7) | **903** | −20 | HT-240U/CO-12CB/etc. eliminados |

#### Cambios en código (commits `506d82b` y `69b931f`)

**`_CODE_BLACKLIST` ampliada** (`main.py` línea ~180):
- Se agregaron nombres de modelos de herramientas LCT: `PH-6`, `HT-240U`, `HT-240C`, `HM-12CB`, `CO-12CB`, `CO-400`, `CO-630`, `CO-IP`, `HH-IP`, `HEC-240`, `HEC-400`, `MHEC-240`, `MHEC-240S`
- Labels de normas/specs: `IEC-6`, `APTAS`, `LY-468`
- Estas palabras nunca pueden ser códigos de producto válidos

**Nueva función `_is_pdf_ghost()`** en `agent_transformer()` post-dedup (PDF-only):
- **R1**: código duplicado + `$` en descripción → precio fragmentado del word-coord
- **R2**: código duplicado + `desc == código` → fallback sin descripción real, existe versión mejor
- **R3**: código alfanumérico que aparece como primera palabra de una fila con código numérico → nombre de modelo capturado como código primario

#### Auditoría externa del LCT (Sonnet 4.5, 2026-08-11)

Se hizo una comparación manual del JSON vs el PDF LCT. Hallazgos principales:

**Gaps sistemáticos (pendientes — Paso 2):**
- Páginas 22-24 y 34 — herramientas manuales: ~37 productos completamente ausentes (LY-10, LY-16, HX-50, WS-16, etc.)
- Página 16 — Termi-Plast: ~34 productos faltantes (A2–A22, B17–B30, C1–C18)
- UCA aluminio (códigos 2200–2212): 13 productos ausentes

**Errores de precio puntuales (pendientes — Paso 2):**
- `4325` (DPH-8): precio truncado $972,95 en lugar de $24.972,95
- `3032` (B17): precio mezclado con código vecino
- `3021` (B3): duplicado con datos basura

**Resuelto en esta sesión:**
- ~30 filas basura eliminadas (HT-240U, CO-12CB, MHEC-240, PKR-20, PRA-1500 duplicados, etc.)
- Código `6219` corregido: ahora tiene 1 sola fila con precio `37447.55` (antes: 2 filas, una con precio fragmentado `47.55`)

#### Pendiente — Paso 2 (requiere archivo de correcciones de Sonnet)

| Tipo | Cantidad | Acción |
|------|--------:|--------|
| Productos faltantes (páginas 16, 22-24, 34) | ~127 | Patch manual |
| Errores de precio | 3 | Corrección puntual |
| Filas basura restantes (QM15, ISO9001, etc.) | ~14 | Patch manual |

---

### Sesión 6 — 2026-08-11 · Resultados post BUG-3/BUG-4 + hallazgo de ruido en word-coords

**Batch test ejecutado con todos los fixes aplicados (BUG-1/2/3/4/5/6/7):**

| Archivo | Filas | Quality | Tokens | Costo | Tiempo |
|---------|------:|--------:|-------:|------:|-------:|
| L26031 xlsx | 2558 | 99.8% | 0 | $0.00 | 0.8s |
| L26031 csv | 2558 | 99.8% | 0 | $0.00 | 0.1s |
| LCT 02-2026 pdf | **1065** | 100% | 0 | $0.00 | ~85s |
| LISTA AR36 pdf | 117 | — | ~21K | ~$0.24 | ~132s |
| Lista N°95 pdf | 623 | 100% | 0 | $0.00 | ~24s |
| LP MICROCONTROL xls | 60 | — | 0 | $0.00 | 0.2s |

**LCT pasó de 981 → 1065 filas** (+84) gracias a `_extract_rows_from_word_coords` (BUG-3 fix).
**asyncio.to_thread** (BUG-4) permite que el timeout funcione correctamente.

---

### Nuevo problema detectado — BUG-8 · Ruido en extracción por coordenadas (word-coords)

**Síntoma**: La función `_extract_rows_from_word_coords` introduce filas con datos incorrectos en el LCT JSON:

```json
{ "Cód. Artículo": "6219", "Descripción artículo": "185 185 $ 3 7 4", "Precio": "47.55" }
{ "Cód. Artículo": "CODIGO", "Descripción artículo": "CODIGO", "Precio": "3009.0" }
{ "Cód. Artículo": "Aluminio", "Descripción artículo": "99,5% 120 120 $ 2 1 0", "Precio": "35.22" }
```

**Causa**: El algoritmo de bounding boxes toma como "código" cualquier palabra que pase `_is_valid_product_code()`. En páginas con layouts complejos (multi-columna, tablas con encabezados tipográficos, materiales en celda) extrae:
- Palabras de encabezado: `CODIGO`, `PRECIO`, `REFERENCIA`
- Descriptores de material: `Aluminio`, `Bronce`, `Cobre`, `PVC`
- Duplicados de códigos reales con precio fragmentado (ej. `6219` con precio `47.55` en lugar de `37447.55`)

**Impacto**: Quality score reporta 100% (verificador no detecta estos errores), pero los datos son incorrectos para las ~84 filas extras. El sistema deduplica por `(código, precio)` — como el precio es diferente, los duplicados malos coexisten con los buenos.

**Solución propuesta**:
1. Filtrar códigos que sean solo palabras genéricas del dominio (`CODIGO`, `PRECIO`, `Aluminio`, etc.)
2. Validar que el precio extraído sea consistente con el rango de precios del PDF (para LCT todos los precios >100 ARS)
3. Usar umbral de confianza: solo aceptar filas word-coord donde código Y precio estén en la misma "zona" del PDF sin saltar entre columnas

---

**Problema**: LISTA AR36 era un PDF escaneado. MarkItDown y pdfplumber solo leen texto vectorial, extrayendo ~2306 chars de encabezados y 0 datos de productos.

**Implementación en `pricebot/api/main.py`**:
- Nueva función `_try_ocr(file_bytes, num_pages)` — convierte páginas PDF a imagen (200 DPI) via pdfplumber y las procesa con pytesseract (idiomas `spa+eng`)
- Activación automática cuando `len(raw_text) / páginas < 1500 chars/pág`
- `extraction_method = "pdf_ocr"` en la respuesta cuando se usa OCR
- Variable de entorno `TESSERACT_CMD` para configurar la ruta del binario en Windows

**Dependencias adicionales**:
```powershell
winget install UB-Mannheim.TesseractOCR           # Tesseract OCR v5.4+
# Luego descargar spa.traineddata a la carpeta tessdata/
# Agregar al .env: TESSERACT_CMD=C:\Users\...\Tesseract-OCR\tesseract.exe
```

**Resultado**:

| Métrica | Sin OCR | Con OCR |
|---------|--------:|--------:|
| Filas | 0 | **112** |
| Tokens | 1.669 | 20.343 |
| Costo est.* | $0.0084 | $0.2314 |
| Tiempo | 48s | 130s |

> \* Tarifas Sonnet como referencia. El costo real con Haiku sería ~75% menor.

El alto consumo de tokens (20K) se debe al ruido del OCR — Tesseract introduce caracteres especiales que Claude debe filtrar para encontrar los patrones de precio.

---
| Media | Tracking de costos por extracción en el endpoint `/extract` | Observabilidad en producción |
| Baja | BUG-4: `asyncio.to_thread()` para extracción síncrona de PDFs | Timeouts reales |

---

Modelo: `claude-sonnet-4-6` | Fixes aplicados: BUG-1, BUG-5, BUG-6, BUG-7

| Archivo | Formato | Filas | Tokens | Costo USD | Tiempo | Estado |
|---------|---------|------:|-------:|----------:|-------:|--------|
| L26031 (xlsx) | .xlsx | 2558 | 0 | $0.0000 | 0.8s | ✅ Código = PARTID (BUG-5 fixed) |
| L26031 (csv) | .csv | 2558 | 0 | $0.0000 | 0.1s | ✅ Igual |
| LCT 02-2026 | .pdf | 981 | **0** | **$0.0000** | 82s | ✅ Sin Claude (BUG-7 fixed) |
| LISTA AR36 | .pdf | 0 | 1.602 | $0.0074 | 48s | ❌ PDF escaneado — requiere OCR |
| Lista N°95 | .pdf | **620** | 0 | $0.0000 | 24s | ⬆️ +14 filas (BUG-6 partial fix) |
| LP MICROCONTROL | .xls | **60** | 0 | $0.0000 | 0.2s | ⬆️ 60 filas reales (BUG-1 fixed) |
| **TOTAL** | | | **1.602** | **$0.0074** | | |

> **Costo total: $0.0074** — vs $1.10 antes de los fixes (reducción del 99.3%)

---

## Fixes aplicados en `pricebot/api/main.py` (2026-08-05)

| Bug | Fix | Archivo / línea |
|-----|-----|----------------|
| BUG-7 | `AI_COMPLEMENT_ALL_CHUNKS` default `"1"` → `"0"` | línea 167 |
| BUG-7b | Saltar AI cuando `strict_numeric_profile=True` y seed ≥ `PDF_MIN_EXPECTED_ROWS` | `agent_transformer()` |
| BUG-5 | `pick_column` prioriza `partid` y excluye columnas con `"barras"`/`"ean"` | `transform_structured_rows()` |
| BUG-5+ | `CODIGO DE BARRAS` y `EAN` se mapean al campo `Sinónimo` | `transform_structured_rows()` |
| BUG-1 | Fallback a text/Claude cuando el mapeo de columnas no encuentra `Cód. Artículo` ni `Precio` | `agent_transformer()` |
| BUG-6 | `_detect_table_column_roles()` retorna pares extra; `extract_rows_from_pdf_tables()` extrae múltiples productos por fila | ambas funciones |

---

Modelo: `claude-sonnet-4-6` | Tarifas: input $3/M · output $15/M tokens

| Archivo | Formato | Filas | Tokens | Costo USD | Tiempo | Notas |
|---------|---------|------:|-------:|----------:|-------:|-------|
| L26031 (xlsx) | .xlsx | 2558 | 0 | $0.0000 | 0.8s | Local puro (pandas). BUG-5 activo |
| L26031 (csv) | .csv | 2558 | 0 | $0.0000 | 0.1s | Local puro (pandas). BUG-5 activo |
| LCT 02-2026 | .pdf | **0** | 103.299 | **$0.5492** | 300s ⚠️ | Timeout. El heurístico ya daba 981 filas correctas sin Claude |
| LISTA AR36 | .pdf | 0 | 1.602 | $0.0074 | 42.9s | PDF escaneado — Claude tampoco puede leerlo sin Vision |
| Lista N°95 | .pdf | **0** | 65.426 | **$0.5468** | 300s ⚠️ | Timeout. El heurístico daba 606 filas |
| LP MICROCONTROL | .xls | 1093 | 0 | $0.0000 | 0.2s | Local puro. BUG-1 activo (quality=0%) |
| **TOTAL** | | **5709** | **170.327** | **$1.1034** | ~650s | |

> ⚠️ **Problema crítico identificado**: Los PDFs grandes (LCT 3.7MB, Lista N°95 1.3MB) con `AI_COMPLEMENT_ALL_CHUNKS=True` envían TODOS los chunks a Claude, consumen todos los tokens en 300s y devuelven 0 filas por el timeout de asyncio (que no puede interrumpir el código síncrono).

---

## Resultados del Batch Test — Sin Claude (2026-08-04)

Todos los archivos procesados localmente sin API key. Referencia de comparación.

| Archivo | Formato | Filas | Quality | Estado | Tiempo |
|---------|---------|------:|--------:|--------|-------:|
| L26031 (xlsx) | .xlsx | 2558 | 99.8% | ❌ BUG-5: código = EAN, no PARTID | 0.8s |
| L26031 (csv) | .csv | 2558 | 99.8% | ❌ BUG-5: mismo problema | 0.1s |
| LCT 02-2026 | .pdf | 981 | 100.0% | ✅ Extracción correcta sin Claude | 101.5s |
| Lista N°95 | .pdf | 606 | 100.0% | ❌ BUG-3 + BUG-6: 38% recall + 85% desc malformadas | 26.5s |
| LP MICROCONTROL | .xls | 1093 | 0.0% | ❌ BUG-1: sin headers (pendiente Claude) | 1.1s |
| LISTA AR36 | .pdf | 0 | 0.0% | ❌ BUG-2: PDF escaneado (pendiente Claude) | 41.5s |

---

## Nuevo Bug identificado en tests con Claude

### BUG-7 · `AI_COMPLEMENT_ALL_CHUNKS=True` causa timeouts en PDFs grandes + 0 filas devueltas
**Síntoma**: LCT (3.7MB) y Lista N°95 (1.3MB) consumen 103K y 65K tokens respectivamente, alcanzan el timeout de 300s en el test, y devuelven 0 filas — peor que sin Claude.

**Causa raíz**: El flag `AI_COMPLEMENT_ALL_CHUNKS=True` (default) fuerza que TODOS los chunks del PDF sean enviados a Claude aunque el heurístico ya extrajo bien los datos. Para PDFs grandes (muchos chunks × ~5s/llamada API = >300s), el tiempo total supera el timeout. Además, el timeout de asyncio no puede cortar las llamadas en curso (BUG-4), lo que resulta en el orquestador devolviendo las filas acumuladas hasta el corte — que en el test llegan vacías.

**Costo desperdiciado**: $0.55 en LCT y $0.55 en Lista N°95 para obtener 0 filas.

**Solución**: Para PDFs donde el heurístico ya extrajo ≥N filas por chunk (número configurable), no enviar esos chunks a Claude. Reservar Claude solo para chunks débiles, o desactivar `AI_COMPLEMENT_ALL_CHUNKS` por defecto y sólo activarlo con env var explícita.

---

| Archivo | Formato | Filas | Quality | Estado | Tiempo |
|---------|---------|------:|--------:|--------|-------:|
| L26031 (xlsx) | .xlsx | 2558 | 99.8% | ❌ BUG-5: código = EAN, no PARTID | 0.8s |
| L26031 (csv) | .csv | 2558 | 99.8% | ❌ BUG-5: mismo problema | 0.1s |
| LCT 02-2026 | .pdf | 981 | 100.0% | ✅ Extracción correcta | 101.5s |
| Lista N°95 | .pdf | 606 | 100.0% | ❌ BUG-3 + BUG-6: 38% recall + 85% descripciones malformadas | 26.5s |
| LP MICROCONTROL | .xls | 1093 | 0.0% | ❌ BUG-1: sin headers (pendiente Claude) | 1.1s |
| LISTA AR36 | .pdf | 0 | 0.0% | ❌ BUG-2: PDF escaneado (pendiente Claude) | 41.5s |
| Plantilla | .xls | 1 | 0.0% | — Plantilla vacía (esperado) | 0.0s |

---

## Análisis de calidad por archivo (sin Claude)

### L26031 (xlsx y csv) — BUG-5 confirmado
**column_mapping**: `CODIGO DE BARRAS → Cód. Artículo` (incorrecto, debería ser `PARTID`)

| Estado | XLSX | CSV |
|--------|-----:|----:|
| Sin código (EAN vacío, tiene PARTID) | 1.400 | 1.224 |
| Código es EAN/barcode (no PARTID) | 757 | 629 |
| Código incorrecto (EAN con discrepancia float) | 397 | 156 |
| Sin match en origen | 4 | 549 * |
| Falta en JSON | 0 | 542 * |
| **OK (PARTID correcto)** | **0** | **0** |

> \* La diferencia en CSV vs XLSX se debe a que el CSV usa codificación latin-1 con separador `;`. Las discrepancias de normalización de texto entre latin-1 y el JSON (UTF-8) causan falsos "no matches". El problema de fondo es idéntico: BUG-5.

**Reporte detallado**: `Respuestas/L26031_comparacion.xlsx`

---

### LCT 02-2026 (pdf) — ✅ Sin problemas
**column_mapping**: `numeric_profile_code → Cód. Artículo`, `pdf_table_code → Cód. Artículo`

| Métrica | Valor |
|---------|------:|
| Total filas | 981 |
| Sin código | 0 |
| Sin descripción | 0 |
| Sin precio | 0 |
| Sin unidad | 0 |
| Precios no-numéricos | 0 |
| Monedas | ARS: 981 |

Extracción limpia. Los códigos son numéricos (ej. 2002, 2003) y los precios son válidos. La extracción heurística funciona correctamente para este formato de PDF.

---

### Lista N°95 (pdf) — BUG-3 + BUG-6
**column_mapping**: `pdf_table_code → Cód. Artículo`, `pdf_table_price → Precio`

| Métrica | Valor |
|---------|------:|
| Total filas extraídas | 606 de 1601 (38% recall) |
| Sin código | 0 |
| Sin descripción | 0 |
| Sin precio | 0 |
| Descripciones con números sospechosos (BUG-6) | **514 (84.8%)** |
| Descripciones muy largas >80 chars (múltiples productos) | 26 |

**BUG-6 — Desalineación de columnas en extracción heurística de PDF**:

La heurística de extracción de tablas PDF (`pdf_table_extraction`) mezcla datos de columnas adyacentes para este PDF. El precio de una fila termina en el campo descripción de la siguiente. Ejemplos:

```
cod='BE64-12-300'  desc='53486,87 BE92-12-300'  precio='486.87'
cod='TBE-07-150'   desc='17814,76'               precio='814.76'
```

El "53486" es el precio de un producto anterior que se concatenó con la descripción del siguiente. Esto hace que el 84.8% de las filas extraídas tengan datos incorrectos, sumado al 62% de filas directamente faltantes (BUG-3). **Lista N°95 requiere Claude para producir datos utilizables.**

---

## Problemas Conocidos y Plan de Solución

### BUG-1 · Excel/XLS sin fila de encabezados (LP MICROCONTROL)
**Síntoma**: 1093 filas extraídas con `quality_score: 0` — todas vacías excepto `{'Moneda': 'ARS'}`.

**Causa raíz**: El archivo `.xls` no tiene encabezados en fila 0. Pandas lo lee como `Unnamed: 0 … Unnamed: 6`. La función `transform_structured_rows()` en `main.py` intenta matchear columnas por nombre (busca "codigo", "precio", etc.) y no encuentra ninguna coincidencia. El sistema reporta éxito pero la data es inútil.

**Estructura real del archivo** (sin headers):
```
| DM 112 L | Tipo "L", uso interior, rosca 1½" | c/u u$s | 12.9 | 4 unid. |
```

**Solución propuesta**: Cuando `transform_structured_rows()` no logra mapear las columnas de `Cód. Artículo` ni `Precio` (ambas quedan `None`), el resultado tiene `quality_score = 0`. En ese caso el sistema debería caer al path de Claude: enviar el raw CSV del Excel al transformer para que identifique las columnas semánticamente.

**Regla de detección**: `if pick_column(cols, ["codigo","cod","sku"]) is None and pick_column(cols, ["precio","price","valor"]) is None → fallback a Claude`.

---

### BUG-2 · PDF escaneado (LISTA AR36)
**Síntoma**: 0 filas extraídas. El PDF tiene 2 páginas pero solo 1948 chars extraídos (texto de bordes/metadata).

**Causa raíz**: El PDF es una imagen escaneada. MarkItDown y pdfplumber extraen solo texto seleccionable — en un PDF de imagen, no hay texto. Las heurísticas no encuentran ningún patrón de artículo porque no hay texto que analizar.

**Solución propuesta**: Cuando `len(raw_text) < UMBRAL` (ej. < 500 chars por página), intentar OCR con `pytesseract` (ya está en `requirements.txt`). Si OCR produce texto suficiente, continuar el pipeline normal. Si no, escalar a Claude Vision enviando las páginas como imágenes.

---

### BUG-3 · Recall reducido en PDFs sin Claude (Lista N°95: 38%)
**Síntoma**: Sin Claude, Lista N°95 extrae 606 de 1601 filas reales (38% recall). Quality = 100% (las que extrae son válidas, pero faltan 995).

**Causa raíz**: Las heurísticas locales (`heuristic_extract_rows`, `heuristic_extract_rows_blockwise`) solo capturan patrones explícitos. Para PDFs con layouts complejos (múltiples columnas, sub-secciones, variaciones de formato), muchos productos no caen en ningún patrón reconocido.

**Nota**: Con Claude, el mismo PDF llega a 1601 filas (100% recall). Claude es actualmente necesario para alta fidelidad en PDFs.

---

### BUG-6 · Desalineación de columnas en extracción heurística de PDF (Lista N°95)
**Síntoma**: 514/606 filas (84.8%) tienen el precio de la fila anterior concatenado en el campo descripción.

```
cod='BE64-12-300'  desc='53486,87 BE92-12-300'  precio='486.87'
cod='TBE-07-150'   desc='17814,76'               precio='814.76'
```

**Causa raíz**: La extracción de tablas PDF (`extract_rows_from_pdf_tables` / heurística) no maneja correctamente el layout de este PDF. Las celdas de precio y descripción de filas adyacentes se solapan en el texto extraído.

**Impacto combinado con BUG-3**: Solo 606/1601 filas extraídas (38% recall), y de esas 606, el 84.8% tiene datos incorrectos. Lista N°95 no es utilizable sin Claude.

**Solución propuesta**: Mejorar `extract_rows_from_pdf_tables()` para detectar y cortar correctamente los límites de columna usando coordenadas de bounding boxes de pdfplumber (en lugar de solo texto plano). Con coordenadas, el precio de una fila no puede "derramarse" en la descripción de la siguiente.

---

### BUG-5 · Prioridad incorrecta en `pick_column()` — código mapeado a EAN en vez de PARTID (L26031)
**Síntoma**: 0 productos con código correcto (PARTID). 1400 sin código, 757 con EAN/barcode como código.

**Causa raíz**: En `transform_structured_rows()`, `pick_column()` evalúa patrones en orden. El patrón `"codigo"` aparece antes que `"partid"`, por lo que `CODIGO DE BARRAS` (que contiene la subcadena "codigo") es elegida como columna de código antes de evaluar `PARTID`.

```python
# Actual — INCORRECTO:
code_col = pick_column(columns, ["codigo", "cod", "partid", "sku", ...])
# "CODIGO DE BARRAS" matchea "codigo" → wins. PARTID nunca se evalúa.

# Fix:
code_col = pick_column(columns, ["partid", "cod articulo", "cod. articulo", "sku", "item", "articulo", "codigo", "ean"])
```

**Impacto verificado** (comparación L26031 Excel vs JSON):

| Estado | Cantidad |
|--------|--------:|
| `SIN_CODIGO` — EAN vacío, tiene PARTID | 1.400 |
| `CODIGO_ES_EAN` — código es barcode, no PARTID | 757 |
| `CODIGO_INCORRECTO` — EAN con discrepancia por float | 397 |
| `SIN_MATCH_EXCEL` — fila JSON sin par en Excel | 4 |
| **OK** | **0** |

**Reporte**: `Respuestas/L26031_comparacion.xlsx` (hojas por estado, comparación fila a fila).

**Solución adicional**: Mover `"ean"` y `"codigo de barras"` al campo `Sinónimo` del template (es información complementaria, no el código primario).

---
**Síntoma**: `asyncio.wait_for(orchestrator(...), timeout=300)` no interrumpe la extracción si se cuelga. LCT PDF tardó 101s; si hubiese colgado, el timeout no habría funcionado.

**Causa raíz**: `agent_extractor` contiene código síncrono bloqueante (MarkItDown + pdfplumber). `asyncio.wait_for` solo puede cancelar en puntos `await` — no puede interrumpir un bucle síncrono de Python.

**Solución propuesta**: Ejecutar la extracción en un thread separado con `asyncio.to_thread()` y cancelar el future si supera el timeout. O usar `concurrent.futures.ProcessPoolExecutor` con timeout real de proceso.

---

## Roadmap

- [x] ~~**BUG-1**~~ — Fallback a Claude cuando `transform_structured_rows` no mapea código ni precio. ✅ Resuelto Sesión 3
- [x] ~~**BUG-2**~~ — OCR con pytesseract para PDFs escaneados. ✅ Resuelto Sesión 5
- [ ] **BUG-3** — Recall LCT: ~127 productos faltantes en páginas 16, 22-24, 34. Requiere patch manual (Paso 2).
- [x] ~~**BUG-4**~~ — `asyncio.to_thread()` para extracción síncrona de PDFs. ✅ Resuelto Sesión 6
- [x] ~~**BUG-5**~~ — Prioridad en `pick_column()`: `partid` antes que `codigo de barras`. ✅ Resuelto Sesión 3
- [x] ~~**BUG-6**~~ — Bounding boxes / multi-columna PDF. ✅ Resuelto Sesión 3 (parcial), Sesión 6
- [x] ~~**BUG-7**~~ — `AI_COMPLEMENT_ALL_CHUNKS` causa timeouts. ✅ Resuelto Sesión 3
- [x] ~~**BUG-8**~~ — Word-coord noise (CODIGO/Aluminio/precios fragmentados). ✅ Resuelto Sesión 7
- [ ] **PASO-2** — Patch LCT: aplicar correcciones de auditoría Sonnet (~127 faltantes + 3 precios + ~14 basura).
- [ ] **FEAT** — Tracking de tokens/costo en endpoint `/extract`.
- [ ] **FEAT** — LP MICROCONTROL: extracción completa (actualmente 60/~100 productos).

---

## Notas Técnicas

- La API usa el SDK de Anthropic vía **httpx directo** (no el paquete `anthropic` de Python).
- Modelo configurado: `claude-sonnet-4-6` (sobreescribible con la variable `CLAUDE_MODEL` en `.env`).
- `claude_chat` en `main.py` actualmente **no retorna ni guarda el uso de tokens**. El tracking manual solo existe en `tests/run_with_usage.py`.
- Tarifas de referencia para estimaciones de costo: input $3/M tokens, output $15/M tokens.
- `ai_enabled = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())` — si no hay key, Claude no se llama en ningún path del Transformer.
- Para Excel/CSV, el código siempre usa `transform_structured_rows()` (local) y **nunca llama a Claude**, incluso con key configurada, salvo que se implemente el fallback de BUG-1.
