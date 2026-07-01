"""
Price Extractor API - Multi-Agent System
Orchestrates extraction of price data from various file formats
and maps them to the purchase price template format.
"""

import os
import io
import json
import base64
import re
import asyncio
import tempfile
import unicodedata
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx
import pandas as pd
import pdfplumber
import pytesseract
from dotenv import load_dotenv
from docx import Document as DocxDocument
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Price Extractor API", version="1.0.0")

# Load local env files for non-Docker runs.
API_DIR = Path(__file__).resolve().parent
load_dotenv(API_DIR / ".env", override=True)
load_dotenv(API_DIR.parent / ".env", override=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anthropic (Claude) configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


async def claude_chat(messages: list, system: str = "", max_tokens: int = 8000) -> str:
    """Send a chat request to Anthropic Claude API and return the response text."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "ANTHROPIC_API_KEY is not configured. "
                "Set it in your environment or .env file."
            ),
        )

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:600] if e.response is not None else str(e)
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic API error ({e.response.status_code}): {detail}",
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic connection error: {str(e)}",
            )

        data = resp.json()
        content_blocks = data.get("content", [])
        texts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("text"):
                texts.append(block["text"])

        if texts:
            return "\n".join(texts)

        raise HTTPException(
            status_code=502,
            detail=(
                "Anthropic response did not include text content. "
                f"Raw: {json.dumps(data)[:600]}"
            ),
        )

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
    structured_rows = []
    metadata = {"filename": filename, "type": ext, "pages": 0}

    def normalize_df_to_records(df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        local_df = df.copy().fillna("")
        local_df.columns = [str(c).strip() for c in local_df.columns]
        records = local_df.to_dict(orient="records")
        normalized = []
        for rec in records:
            row = {str(k).strip(): str(v).strip() if v is not None else "" for k, v in rec.items()}
            normalized.append(row)
        return normalized

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
                structured_rows.extend(normalize_df_to_records(df))
                sheets_text.append(f"=== SHEET: {sheet} ===\n{df.to_csv(index=False)}")
            raw_text = "\n".join(sheets_text)

        elif ext in [".xls"]:
            xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
            sheets_text = []
            for sheet in xl.sheet_names:
                df = pd.read_excel(
                    io.BytesIO(file_bytes), engine="xlrd", sheet_name=sheet
                )
                structured_rows.extend(normalize_df_to_records(df))
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
            csv_text = file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(csv_text), sep=sep)
            structured_rows.extend(normalize_df_to_records(df))
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
        "structured_rows": structured_rows,
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
1. Extract EVERY product/price row found in the provided chunk.
2. Leave fields empty ("") if not available.
3. Infer currency from context ($ = ARS, U$S/USD = USD).
4. Return ONLY valid JSON, no markdown, no preamble.
5. For prices: use numeric values only (e.g. 1535.26 not "$1.535,26").
6. Normalize Argentine number format: 1.535,26 → 1535.26.
7. Extract dates in DD/MM/YYYY format.
8. If a list code/name is mentioned in header, apply it to all rows.

RESPONSE FORMAT: Return a JSON object with two keys:
- "column_mapping": object mapping source column names to template column names.
- "rows": array of product objects with template column names."""

    def normalize_key(text: str) -> str:
        text = unicodedata.normalize("NFKD", str(text).lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    def normalize_json_text(raw_text: str) -> str:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) > 1:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]

        return cleaned.strip()

    def extract_balanced_object(src: str, open_idx: int) -> tuple[str, int]:
        depth = 0
        in_string = False
        escaped = False
        i = open_idx
        while i < len(src):
            ch = src[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return src[open_idx:i + 1], i
            i += 1
        return "", -1

    def salvage_rows_from_malformed_json(raw_text: str) -> tuple[dict, list[dict]]:
        column_mapping = {}
        rows = []

        cm_key = '"column_mapping"'
        cm_pos = raw_text.find(cm_key)
        if cm_pos != -1:
            cm_open = raw_text.find("{", cm_pos)
            if cm_open != -1:
                cm_obj, _ = extract_balanced_object(raw_text, cm_open)
                if cm_obj:
                    try:
                        parsed_cm = json.loads(cm_obj)
                        if isinstance(parsed_cm, dict):
                            column_mapping = parsed_cm
                    except json.JSONDecodeError:
                        column_mapping = {}

        rows_key = '"rows"'
        rows_pos = raw_text.find(rows_key)
        if rows_pos == -1:
            return column_mapping, rows

        arr_start = raw_text.find("[", rows_pos)
        if arr_start == -1:
            return column_mapping, rows

        i = arr_start + 1
        while i < len(raw_text):
            ch = raw_text[i]
            if ch == "]":
                break
            if ch != "{":
                i += 1
                continue

            obj_text, obj_end = extract_balanced_object(raw_text, i)
            if not obj_text or obj_end == -1:
                break

            try:
                row = json.loads(obj_text)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                pass

            i = obj_end + 1

        return column_mapping, rows

    def normalize_rows(rows: list[dict]) -> list[dict]:
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            for col in TEMPLATE_COLUMNS:
                if col not in row:
                    row[col] = ""
            normalized.append(row)
        return normalized

    def parse_transform_response(raw_text: str) -> tuple[dict, list[dict]]:
        parsed = json.loads(raw_text)
        column_mapping = {}
        rows = []

        if isinstance(parsed, dict) and "rows" in parsed:
            column_mapping = parsed.get("column_mapping", {})
            rows = parsed["rows"]
        elif isinstance(parsed, list):
            rows = parsed
        else:
            rows = [parsed]

        if not isinstance(column_mapping, dict):
            column_mapping = {}

        return column_mapping, normalize_rows(rows)

    def pick_column(columns: list[str], patterns: list[str]) -> Optional[str]:
        normalized = {c: normalize_key(c) for c in columns}
        for pat in patterns:
            for col, key in normalized.items():
                if pat in key:
                    return col
        return None

    def transform_structured_rows(structured_rows: list[dict]) -> dict:
        if not structured_rows:
            return {"rows": [], "column_mapping": {}}

        columns = list(structured_rows[0].keys())
        code_col = pick_column(columns, ["codigo", "cod", "partid", "sku", "item", "articulo", "ean"])
        desc_col = pick_column(columns, ["descripcion", "producto", "detalle", "articulo", "nombre"])
        add_col = pick_column(columns, ["adicional", "familia", "rubro", "linea", "modelo", "detalle2"])
        syn_col = pick_column(columns, ["sinonimo", "marca", "alias"])
        list_col = pick_column(columns, ["cod lista", "lista", "list code"])
        list_desc_col = pick_column(columns, ["desc lista", "lista desc", "list name"])
        currency_col = pick_column(columns, ["moneda", "currency", "divisa"])
        unit_col = pick_column(columns, ["unidad", "um", "u m", "stock um", "presentacion", "medida"])
        price_col = pick_column(columns, ["precio", "unit price", "price", "valor", "importe", "neto"])
        bonif_col = pick_column(columns, ["bonif", "descuento", "dto"])
        from_col = pick_column(columns, ["vigencia desde", "fecha desde", "inicio", "desde"])
        to_col = pick_column(columns, ["vigencia hasta", "fecha hasta", "hasta", "fin"])

        selected = {
            code_col: "Cód. Artículo",
            desc_col: "Descripción artículo",
            add_col: "Descripción adicional artículo",
            syn_col: "Sinónimo",
            list_col: "Cód. Lista",
            list_desc_col: "Desc. Lista",
            currency_col: "Moneda",
            unit_col: "Unidad",
            price_col: "Precio",
            bonif_col: "Bonif.",
            from_col: "Fecha vigencia desde",
            to_col: "Fecha vigencia hasta",
        }
        column_mapping = {src: dst for src, dst in selected.items() if src}

        def get_value(row: dict, col: Optional[str]) -> str:
            if not col:
                return ""
            return str(row.get(col, "") or "").strip()

        out_rows = []
        for row in structured_rows:
            mapped = {
                "Cód. Artículo": get_value(row, code_col),
                "Descripción artículo": get_value(row, desc_col),
                "Descripción adicional artículo": get_value(row, add_col),
                "Sinónimo": get_value(row, syn_col),
                "Cód. Lista": get_value(row, list_col),
                "Desc. Lista": get_value(row, list_desc_col),
                "Moneda": get_value(row, currency_col) or "ARS",
                "Unidad": get_value(row, unit_col),
                "Precio": get_value(row, price_col),
                "Bonif.": get_value(row, bonif_col),
                "Fecha vigencia desde": get_value(row, from_col),
                "Fecha vigencia hasta": get_value(row, to_col),
            }
            if any(v for v in mapped.values()):
                out_rows.append(mapped)

        return {"rows": normalize_rows(out_rows), "column_mapping": column_mapping}

    async def transform_chunk(chunk_text: str) -> tuple[dict, list[dict]]:
        user_prompt = f"""Extract all product price records from this raw data chunk.

SOURCE FILE: {raw_data['metadata']['filename']}
CHUNK CHAR COUNT: {len(chunk_text)}

RAW DATA CHUNK:
{chunk_text}

Return JSON object with:
1. "column_mapping": mapping from source columns to template columns
2. "rows": array of objects with these exact keys: {json.dumps(TEMPLATE_COLUMNS)}

Return ONLY the JSON object."""

        text = await claude_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            max_tokens=12000,
        )

        text = normalize_json_text(text)

        try:
            return parse_transform_response(text)
        except json.JSONDecodeError as e:
            repair_prompt = f"""Fix this malformed JSON and return ONLY valid JSON.

Rules:
- Keep the same schema with keys: column_mapping, rows.
- If truncated, keep only complete row objects and close the JSON properly.
- Escape all quotes/newlines correctly.
- No markdown, no comments, no extra text.

MALFORMED JSON:
{text[:50000]}"""

            repaired_text = await claude_chat(
                messages=[{"role": "user", "content": repair_prompt}],
                system="You are a JSON repair assistant. Return valid JSON only.",
                max_tokens=12000,
            )
            repaired_text = normalize_json_text(repaired_text)

            try:
                return parse_transform_response(repaired_text)
            except json.JSONDecodeError:
                salvaged_mapping, salvaged_rows = salvage_rows_from_malformed_json(text)
                salvaged_rows = normalize_rows(salvaged_rows)
                if salvaged_rows:
                    return salvaged_mapping, salvaged_rows
                raise HTTPException(
                    status_code=500,
                    detail=f"Transform parse error: {str(e)}\nRaw: {text[:500]}",
                )

    structured_rows = raw_data.get("structured_rows") or []
    if structured_rows and raw_data.get("metadata", {}).get("type") in {".csv", ".xlsx", ".xls", ".xlsm"}:
        return transform_structured_rows(structured_rows)

    raw_text = raw_data.get("raw_text", "")
    if not raw_text.strip():
        return {"rows": [], "column_mapping": {}}

    chunks = []
    max_chunk_chars = 9000
    if "=== PAGE" in raw_text:
        pages = re.split(r"(?=^=== PAGE\s+\d+\s+===)", raw_text, flags=re.MULTILINE)
        current = ""
        for page in pages:
            if not page.strip():
                continue
            if len(current) + len(page) > max_chunk_chars and current:
                chunks.append(current)
                current = page
            else:
                current += page
        if current.strip():
            chunks.append(current)
    else:
        for i in range(0, len(raw_text), max_chunk_chars):
            chunk = raw_text[i:i + max_chunk_chars]
            if chunk.strip():
                chunks.append(chunk)

    all_rows = []
    merged_mapping = {}
    for chunk in chunks:
        chunk_mapping, chunk_rows = await transform_chunk(chunk)
        merged_mapping.update(chunk_mapping)
        all_rows.extend(chunk_rows)

    deduped = []
    seen = set()
    for row in all_rows:
        key = (
            str(row.get("Cód. Artículo", "")).strip().lower(),
            str(row.get("Descripción artículo", "")).strip().lower(),
            str(row.get("Precio", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return {"rows": normalize_rows(deduped), "column_mapping": merged_mapping}


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
            # Normalize price for both AR and EN number formats.
            price_str = price_str.replace("$", "").replace(" ", "").strip()
            if "," in price_str and "." in price_str:
                if price_str.rfind(",") > price_str.rfind("."):
                    # 1.535,26 -> 1535.26
                    price_str = price_str.replace(".", "").replace(",", ".")
                else:
                    # 1,535.26 -> 1535.26
                    price_str = price_str.replace(",", "")
            elif "," in price_str:
                # 1535,26 -> 1535.26
                price_str = price_str.replace(",", ".")
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

    def sanitize_xls_value(value):
        # BIFF8 (.xls) max cell text length is 32767 characters.
        if value is None:
            return ""
        text = str(value)
        if len(text) > 32767:
            text = text[:32767]
        return text

    if format == "xls":
        # Generate .xls (legacy format matching template exactly)
        import xlwt
        try:
            wb = xlwt.Workbook(encoding="utf-8")
            ws = wb.add_sheet("Sheet1")

            # Row 0: CUIT
            ws.write(0, 0, sanitize_xls_value(cuit_val))

            # Row 1: Column headers
            for col_idx, col_name in enumerate(TEMPLATE_COLUMNS):
                ws.write(1, col_idx, sanitize_xls_value(col_name))

            # Row 2+: Data
            for row_idx, row in enumerate(result["rows"]):
                for col_idx, col_name in enumerate(TEMPLATE_COLUMNS):
                    val = sanitize_xls_value(row.get(col_name, ""))
                    ws.write(row_idx + 2, col_idx, val)

            wb.save(output)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"XLS generation error: {str(e)}",
            )

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
