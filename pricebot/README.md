# PriceBot — Sistema Multi-Agente de Extracción de Listas de Precios

Extrae datos de listas de precios (PDF, XLS, XLSX, CSV, imágenes) y los mapea
automáticamente al formato de la **Plantilla_Precios_Compras**.

---

## Arquitectura Multi-Agente

```
┌─────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                        │
│          Coordina el flujo y reporta estado             │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────▼──────────┐
    │   AGENT EXTRACTOR  │
    │  PDF → pdfplumber  │
    │  XLS/XLSX → pandas │
    │  CSV → pandas      │
    │  IMG → Claude Vision│
    └────────┬──────────┘
             │  raw_text
    ┌────────▼──────────────┐
    │  AGENT TRANSFORMER    │
    │  Claude claude-sonnet-4-20250514     │
    │  raw_text → JSON rows │
    │  Mapea a 12 columnas  │
    └────────┬──────────────┘
             │  rows[]
    ┌────────▼──────────────┐
    │   AGENT VERIFIER      │
    │  Valida precios       │
    │  Normaliza monedas    │
    │  Calcula quality score│
    └────────┬──────────────┘
             │
    ┌────────▼──────────────┐
    │       OUTPUT          │
    │  JSON response        │
    │  XLSX (Plantilla fmt) │
    └───────────────────────┘
```

---

## Columnas del Template

| Columna | Descripción |
|---------|-------------|
| Cód. Artículo | Código del artículo del proveedor |
| Descripción artículo | Descripción principal |
| Descripción adicional artículo | Especificaciones técnicas, modelo |
| Sinónimo | Código alternativo o sinónimo |
| Cód. Lista | Código de la lista de precios |
| Desc. Lista | Nombre/descripción de la lista |
| Moneda | ARS, USD, EUR |
| Unidad | Un, m, kg, caja, etc. |
| Precio | Valor numérico sin símbolo |
| Bonif. | Porcentaje de descuento |
| Fecha vigencia desde | DD/MM/YYYY |
| Fecha vigencia hasta | DD/MM/YYYY |

---

## Uso de la API

### Extraer → JSON
```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@LCT_Lista_Precios.pdf" \
  -F "supplier_cuit=30-12345678-1"
```

### Extraer → XLSX (formato Plantilla)
```bash
curl -X POST http://localhost:8000/extract/download \
  -F "file=@lista.xlsx" \
  -o precios_extraidos.xlsx
```

### Batch (múltiples archivos)
```bash
curl -X POST http://localhost:8000/extract/batch \
  -F "files=@lista1.pdf" \
  -F "files=@lista2.xlsx" \
  -F "files=@foto_lista.jpg"
```

---

## Formatos Soportados

| Formato | Método de extracción |
|---------|---------------------|
| `.pdf` | pdfplumber (texto + tablas) |
| `.xlsx` / `.xlsm` | pandas + openpyxl |
| `.xls` | pandas + xlrd |
| `.csv` | pandas |
| `.jpg` / `.png` / `.webp` | Claude Vision (multimodal) |

---

## Respuesta Ejemplo

```json
{
  "filename": "LCT_Lista.pdf",
  "rows": [
    {
      "Cód. Artículo": "2002",
      "Descripción artículo": "Terminal de cobre SCC 1.5/2",
      "Descripción adicional artículo": "Sección 1.5mm² - ø 5/32 pulgadas - Cant. 500",
      "Sinónimo": "SCC1.5/2",
      "Cód. Lista": "LCT-01-2026",
      "Desc. Lista": "Lista LCT Enero 2026",
      "Moneda": "ARS",
      "Unidad": "Un",
      "Precio": "490.78",
      "Bonif.": "",
      "Fecha vigencia desde": "",
      "Fecha vigencia hasta": ""
    }
  ],
  "report": {
    "total_rows": 48,
    "valid_rows": 46,
    "rows_with_issues": 2,
    "quality_score": 95.8
  },
  "log": [
    {"step": "extraction", "status": "done", "detail": "Extracted 45230 chars from 44 pages"},
    {"step": "transformation", "status": "done", "detail": "Extracted 48 product rows"},
    {"step": "verification", "status": "done", "detail": "Quality: 95.8% (46/48 valid)"}
  ]
}
```

---

## Notas Técnicas

- El **Transformer** usa `claude-sonnet-4-20250514` con contexto de hasta 12.000 chars por chunk
- Los PDFs con tablas se benefician especialmente de pdfplumber (extrae estructura tabular)
- Las imágenes usan Claude Vision directamente (no OCR local)
- El Verifier normaliza formatos argentinos: `$1.535,26` → `1535.26`
- El XLSX de salida respeta exactamente el formato de `Plantilla_Precios_Compras`
