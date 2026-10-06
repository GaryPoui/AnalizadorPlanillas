import asyncio
import io
import sys
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from docx import Document as DocxDocument


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))

from fastapi import HTTPException  # noqa: E402
import main  # noqa: E402


class SecurityHardeningTests(unittest.TestCase):
    def test_external_ai_requires_explicit_opt_in(self):
        previous = main.ALLOW_EXTERNAL_AI
        main.ALLOW_EXTERNAL_AI = False
        try:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(main.claude_chat([{"role": "user", "content": "test"}]))
            self.assertEqual(raised.exception.status_code, 503)
        finally:
            main.ALLOW_EXTERNAL_AI = previous

    def test_upload_name_removes_client_paths(self):
        self.assertEqual(
            main._safe_upload_name(r"C:\Users\persona\lista.pdf"), "lista.pdf"
        )

    def test_file_content_must_match_extension(self):
        with self.assertRaises(HTTPException) as raised:
            main._validate_upload("documento.pdf", b"not a pdf")
        self.assertEqual(raised.exception.status_code, 400)

    def test_docx_is_accepted_and_legacy_doc_is_not_advertised(self):
        payload = io.BytesIO()
        document = DocxDocument()
        document.add_paragraph("Código Descripción Precio")
        document.save(payload)

        self.assertEqual(main._validate_upload("lista.docx", payload.getvalue()), ".docx")
        with self.assertRaises(HTTPException) as raised:
            main._validate_upload("lista.doc", payload.getvalue())
        self.assertEqual(raised.exception.status_code, 400)

    def test_office_zip_bomb_is_rejected(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"0" * (11 * 1024 * 1024))
        with self.assertRaises(HTTPException):
            main._validate_upload("documento.xlsx", payload.getvalue())

    def test_office_archive_paths_are_validated(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", b"types")
            archive.writestr("xl/workbook.xml", b"workbook")
            archive.writestr("../escape.xml", b"bad")
        with self.assertRaises(HTTPException) as raised:
            main._validate_upload("documento.xlsx", payload.getvalue())
        self.assertEqual(raised.exception.status_code, 400)

    def test_oversized_image_dimensions_are_rejected(self):
        payload = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(payload, format="PNG")
        previous = main.MAX_IMAGE_PIXELS
        main.MAX_IMAGE_PIXELS = 5000
        try:
            with self.assertRaises(HTTPException) as raised:
                main._validate_upload("imagen.png", payload.getvalue())
            self.assertEqual(raised.exception.status_code, 413)
        finally:
            main.MAX_IMAGE_PIXELS = previous

    def test_csv_control_bytes_are_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            main._validate_upload("lista.csv", b"codigo,precio\nA1,10\x00")
        self.assertEqual(raised.exception.status_code, 400)

    def test_csv_control_bytes_after_first_megabyte_are_rejected(self):
        payload = b"codigo,precio\nA1,10\n" + (b" " * (1024 * 1024)) + b"\x01"
        with self.assertRaises(HTTPException) as raised:
            main._validate_upload("lista.csv", payload)
        self.assertEqual(raised.exception.status_code, 400)

    def test_spreadsheet_formula_is_neutralized(self):
        self.assertEqual(main._safe_spreadsheet_value("=1+1"), "'=1+1")
        self.assertEqual(main._safe_spreadsheet_value("texto"), "texto")

    def test_api_documentation_is_disabled_by_default(self):
        self.assertIsNone(main.app.docs_url)
        self.assertIsNone(main.app.openapi_url)


if __name__ == "__main__":
    unittest.main()
