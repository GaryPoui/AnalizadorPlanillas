"""
Price Extractor API - Multi-Agent System
Orchestrates extraction of price data from various file formats
and maps them to the purchase price template format.
"""

import os
import io
import json
import base64
import asyncio
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx
import pandas as pd
import pdfplumber
import pytesseract
from docx import Document as DocxDocument
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Price Extractor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anthropic (Claude) configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")


async def claude_chat(messages: list, system: str = "") -> str:
    """Send a chat request to Anthropic Claude API and return the response text."""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 8000,
        "temperature": 0.1,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

# Template columns matching Plantilla_Precios_Compras
TEMPLATE_COLUMNS = [
    "Cód. Artículo",
    "Descripción artículo",
    "Descripción adicional artículo",
    "Sinónimo",
    "Cód. Lista",
    "Desc. Lista",
    "Moneda",
    "Unidad",
    "Precio",
    "Bonif.",
    "Fecha vigencia desde",
    "Fecha vigencia hasta",
]


# ─────────────────────────────────────────────
# AGENT 1: File Extraction Agent
# ─────────────────────────────────────────────
async def agent_extractor(file_bytes: bytes, filename: str, file_type: str) -> dict:
    """
    Extracts raw text/data from the uploaded file.
    Handles: PDF, XLS/XLSX, CSV, images (JPG, PNG).
    Returns a dict with raw_text and metadata.
    """
    ext = Path(filename).suffix.lower()
    raw_text = ""
    metadata = {"filename": filename, "type": ext, "pages": 0}

    try:
        if ext in [".pdf"]:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                metadata["pages"] = len(pdf.pages)
                pages_text = []
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    table_str = ""
                    for table in tables:
                        for row in table:
                            if row:
                                table_str += " | ".join(
                                    str(c) if c else "" for c in row
                                ) + "\n"
                    pages_text.append(f"=== PAGE {i+1} ===\n{text}\n{table_str}")
                raw_text = "\n".join(pages_text)

        elif ext in [".xlsx", ".xlsm"]:
            xl = pd.ExcelFile(io.BytesIO(file_bytes))
            sheets_text = []
            for sheet in xl.sheet_names:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet)
                sheets_text.append(f"=== SHEET: {sheet} ===\n{df.to_csv(index=False)}")
            raw_text = "\n".join(sheets_text)

        elif ext in [".xls"]:
            xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
            sheets_text = []
            for sheet in xl.sheet_names:
                df = pd.read_excel(
                    io.BytesIO(file_bytes), engine="xlrd", sheet_name=sheet
                )
                sheets_text.append(f"=== SHEET: {sheet} ===\n{df.to_csv(index=False)}")
            raw_text = "\n".join(sheets_text)

        elif ext in [".csv"]:
            # Auto-detect separator (;  ,  \t)
            sample = file_bytes[:4096].decode("utf-8", errors="replace")
            if sample.count(";") > sample.count(","):
                sep = ";"
            elif sample.count("\t") > sample.count(","):
                sep = "\t"
            else:
                sep = ","
            df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding="utf-8", errors="replace")
            raw_text = df.to_csv(index=False, sep=",")

        elif ext in [".docx", ".doc"]:
            doc = DocxDocument(io.BytesIO(file_bytes))
            parts = []
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            # Extract tables
            for i, table in enumerate(doc.tables):
                parts.append(f"=== TABLE {i+1} ===")
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    parts.append(" | ".join(cells))
            raw_text = "\n".join(parts)

        elif ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
            # Use Claude Vision for image files
            img_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
            media_type = "image/jpeg"
            if ext == ".png":
                media_type = "image/png"
            elif ext == ".webp":
                media_type = "image/webp"
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL price/product information from this image. "
                                "Include: product codes, descriptions, prices, units, "
                                "currency, discounts, validity dates, and any other "
                                "relevant data. Format as structured text preserving "
                                "all values exactly as shown."
                            ),
                        },
                    ],
                }
            ]
            raw_text = await claude_chat(messages)
            metadata["type"] = "image"

        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file type: {ext}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Extraction error: {str(e)}"
        )

    return {
        "raw_text": raw_text,
        "metadata": metadata,
        "char_count": len(raw_text),
        "extraction_method": "vision_ai" if metadata.get("type") == "image"
            else "direct_structured" if ext in [".csv", ".xlsx", ".xlsm", ".xls"]
            else "pdf_text_ai",
    }


# ─────────────────────────────────────────────
# AGENT 2: Transformation Agent
# Maps raw text → template columns
# ─────────────────────────────────────────────
async def agent_transformer(raw_data: dict, supplier_cuit: str = "") -> dict:
    """
    Uses Claude to map raw extracted text to the template columns.
    Returns a dict with 'rows' and 'column_mapping'.
    """
    system_prompt = """You are a specialized data extraction agent for price lists.
Your task: extract product/price records from raw text and map them to the template columns.

TEMPLATE COLUMNS (exact names required):
- Cód. Artículo: product/item code from the supplier
- Descripción artículo: main product description
- Descripción adicional artículo: additional description, specs, model details
- Sinónimo: alternative name or code
- Cód. Lista: price list code/number
- Desc. Lista: price list description/name
- Moneda: currency (ARS, USD, EUR)
- Unidad: unit of measure (Un, m, kg, caja, etc.)
- Precio: numeric price WITHOUT currency symbol
- Bonif.: discount percentage if any (numeric, e.g. 15 for 15%)
- Fecha vigencia desde: validity start date (DD/MM/YYYY)
- Fecha vigencia hasta: validity end date (DD/MM/YYYY)

RULES:
1. Extract EVERY product/price row found
2. Leave fields empty ("") if not available
3. Infer currency from context ($ = ARS, U$S/USD = USD)
4. Return ONLY valid JSON, no markdown, no preamble
5. For prices: use numeric values only (e.g. 1535.26 not "$1.535,26")
6. Normalize Argentine number format: 1.535,26 → 1535.26
7. Extract dates in DD/MM/YYYY format
8. If a list code/name is mentioned in header, apply it to all rows

RESPONSE FORMAT: Return a JSON object with two keys:
- "column_mapping": object mapping source column names to template column names (e.g. {"PARTID": "Cód. Artículo", "DESCRIPCION": "Descripción artículo"})
- "rows": array of product objects with template column names"""

    user_prompt = f"""Extract all product price records from this raw data:

SOURCE FILE: {raw_data['metadata']['filename']}
CHAR COUNT: {raw_data['char_count']}

RAW DATA:
{raw_data['raw_text'][:12000]}

Return JSON object with:
1. "column_mapping": mapping from source columns to template columns
2. "rows": array of objects with these exact keys: {json.dumps(TEMPLATE_COLUMNS)}

Example:
{{
  "column_mapping": {{"PARTID": "Cód. Artículo", "DESCRIPCION": "Descripción artículo", "UNIT_PRICE": "Precio", "MONEDA": "Moneda", "STOCK_UM": "Unidad"}},
  "rows": [
    {{
      "Cód. Artículo": "2002",
      "Descripción artículo": "Terminal de cobre SCC 1.5/2",
      "Descripción adicional artículo": "",
      "Sinónimo": "",
      "Cód. Lista": "",
      "Desc. Lista": "",
      "Moneda": "ARS",
      "Unidad": "Un",
      "Precio": "490.78",
      "Bonif.": "",
      "Fecha vigencia desde": "",
      "Fecha vigencia hasta": ""
    }}
  ]
}}

Return ONLY the JSON object."""

    text = await claude_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    text = text.strip()
    # Strip markdown if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        parsed = json.loads(text)
        column_mapping = {}
        rows = []

        if isinstance(parsed, dict) and "rows" in parsed:
            column_mapping = parsed.get("column_mapping", {})
            rows = parsed["rows"]
        elif isinstance(parsed, list):
            rows = parsed
        else:
            rows = [parsed]

        # Ensure all template columns exist
        for row in rows:
            for col in TEMPLATE_COLUMNS:
                if col not in row:
                    row[col] = ""
        return {"rows": rows, "column_mapping": column_mapping}
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, detail=f"Transform parse error: {str(e)}\nRaw: {text[:500]}"
        )


# ─────────────────────────────────────────────
# AGENT 3: Verification Agent
# ─────────────────────────────────────────────
async def agent_verifier(rows: list[dict], raw_data: dict) -> dict:
    """
    Validates extracted rows for quality and consistency.
    Returns validation report and cleaned rows.
    """
    issues = []
    cleaned_rows = []

    for i, row in enumerate(rows):
        row_issues = []

        # Check required fields
        if not row.get("Descripción artículo", "").strip():
            row_issues.append("Missing description")

        # Validate price
        price_str = str(row.get("Precio", "")).strip()
        if price_str:
            # Normalize: remove thousand separators, fix decimal
            price_str = price_str.replace("$", "").strip()
            price_str = price_str.replace(".", "").replace(",", ".")
            try:
                price_val = float(price_str)
                if price_val <= 0:
                    row_issues.append(f"Invalid price: {price_val}")
                else:
                    row["Precio"] = str(round(price_val, 2))
            except ValueError:
                row_issues.append(f"Non-numeric price: '{row.get('Precio')}'")
                row["Precio"] = ""
        else:
            row_issues.append("Missing price")

        # Validate currency
        currency = row.get("Moneda", "").strip().upper()
        if currency and currency not in ["ARS", "USD", "EUR", "US$", "U$S"]:
            row["Moneda"] = "ARS"  # Default
            row_issues.append(f"Normalized currency: {currency} → ARS")

        # Normalize currency aliases
        if row.get("Moneda") in ["US$", "U$S", "USD"]:
            row["Moneda"] = "USD"
        elif row.get("Moneda") == "":
            row["Moneda"] = "ARS"

        # Validate discount
        bonif = str(row.get("Bonif.", "")).strip()
        if bonif:
            try:
                bonif_val = float(bonif.replace(",", ".").replace("%", ""))
                if bonif_val < 0 or bonif_val > 100:
                    row_issues.append(f"Discount out of range: {bonif_val}")
                    row["Bonif."] = ""
                else:
                    row["Bonif."] = str(round(bonif_val, 2))
            except ValueError:
                row["Bonif."] = ""

        if row_issues:
            issues.append({"row": i + 1, "issues": row_issues})

        cleaned_rows.append(row)

    total = len(rows)
    valid = total - len([i for i in issues if any("Missing price" in x or "Missing description" in x for x in i["issues"])])

    report = {
        "total_rows": total,
        "valid_rows": valid,
        "rows_with_issues": len(issues),
        "issues": issues[:20],  # Limit to first 20 for brevity
        "quality_score": round((valid / total * 100) if total > 0 else 0, 1),
    }

    return {"rows": cleaned_rows, "report": report}


# ─────────────────────────────────────────────
# ORCHESTRATOR AGENT
# ─────────────────────────────────────────────
async def orchestrator(file_bytes: bytes, filename: str, supplier_cuit: str = "") -> dict:
    """
    Master agent that coordinates extraction, transformation, and verification.
    """
    log = []

    def log_step(step: str, status: str, detail: str = ""):
        entry = {
            "step": step,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }
        log.append(entry)
        return entry

    # Step 1: Extract
    log_step("extraction", "running", f"Processing {filename}")
    raw_data = await agent_extractor(file_bytes, filename, "")
    log_step(
        "extraction",
        "done",
        f"Extracted {raw_data['char_count']} chars from {raw_data['metadata'].get('pages', 1)} pages",
    )

    # Step 2: Transform
    log_step("transformation", "running", "Mapping data to template columns")
    transform_result = await agent_transformer(raw_data, supplier_cuit)
    rows = transform_result["rows"]
    column_mapping = transform_result["column_mapping"]
    log_step("transformation", "done", f"Extracted {len(rows)} product rows")

    # Step 3: Verify
    log_step("verification", "running", "Validating and cleaning data")
    result = await agent_verifier(rows, raw_data)
    log_step(
        "verification",
        "done",
        f"Quality: {result['report']['quality_score']}% ({result['report']['valid_rows']}/{result['report']['total_rows']} valid)",
    )

    return {
        "filename": filename,
        "rows": result["rows"],
        "report": result["report"],
        "metadata": raw_data["metadata"],
        "extraction_method": raw_data.get("extraction_method", "unknown"),
        "column_mapping": column_mapping,
        "log": log,
    }


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Price Extractor API v1.0"}


@app.post("/extract")
async def extract_file(
    file: UploadFile = File(...),
    supplier_cuit: str = "",
):
    """
    Main endpoint: upload a price list file and get structured data back.
    Accepts: PDF, XLS, XLSX, CSV, JPG, PNG
    """
    allowed_ext = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"File type not supported: {ext}")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    result = await orchestrator(file_bytes, file.filename, supplier_cuit)
    return JSONResponse(content=result)


@app.post("/extract/download")
async def extract_and_download(
    file: UploadFile = File(...),
    supplier_cuit: str = "",
    format: str = "xlsx",
):
    """
    Same as /extract but returns a file ready to import.
    format: 'xlsx' or 'xls'
    """
    allowed_ext = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"File type not supported: {ext}")

    file_bytes = await file.read()
    result = await orchestrator(file_bytes, file.filename, supplier_cuit)

    cuit_val = supplier_cuit or "30-55555555-1"
    safe_name = Path(file.filename).stem
    df = pd.DataFrame(result["rows"], columns=TEMPLATE_COLUMNS)

    output = io.BytesIO()

    if format == "xls":
        # Generate .xls (legacy format matching template exactly)
        import xlwt
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("Sheet1")

        # Row 0: CUIT
        ws.write(0, 0, cuit_val)

        # Row 1: Column headers
        for col_idx, col_name in enumerate(TEMPLATE_COLUMNS):
            ws.write(1, col_idx, col_name)

        # Row 2+: Data
        for row_idx, row in enumerate(result["rows"]):
            for col_idx, col_name in enumerate(TEMPLATE_COLUMNS):
                val = row.get(col_name, "")
                ws.write(row_idx + 2, col_idx, val)

        wb.save(output)
        output.seek(0)
        out_filename = f"precios_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
        media_type = "application/vnd.ms-excel"
    else:
        # Generate .xlsx
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            header_df = pd.DataFrame([[cuit_val] + [""] * 11])
            header_df.to_excel(writer, index=False, header=False, sheet_name="Sheet1", startrow=0)
            df.to_excel(writer, index=False, sheet_name="Sheet1", startrow=1)

        output.seek(0)
        out_filename = f"precios_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={out_filename}"},
    )


@app.post("/extract/batch")
async def extract_batch(
    files: list[UploadFile] = File(...),
    supplier_cuit: str = "",
):
    """
    Process multiple files and merge into a single result.
    """
    all_rows = []
    all_logs = []
    all_reports = []

    for file in files:
        file_bytes = await file.read()
        result = await orchestrator(file_bytes, file.filename, supplier_cuit)
        all_rows.extend(result["rows"])
        all_logs.extend(result["log"])
        all_reports.append({"file": file.filename, "report": result["report"]})

    return JSONResponse(content={
        "total_files": len(files),
        "total_rows": len(all_rows),
        "rows": all_rows,
        "reports": all_reports,
        "log": all_logs,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
