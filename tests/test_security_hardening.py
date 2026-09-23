import asyncio
import io
import sys
import unittest
import zipfile
from pathlib import Path


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

    def test_office_zip_bomb_is_rejected(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"0" * (11 * 1024 * 1024))
        with self.assertRaises(HTTPException):
            main._validate_upload("documento.xlsx", payload.getvalue())

    def test_spreadsheet_formula_is_neutralized(self):
        self.assertEqual(main._safe_spreadsheet_value("=1+1"), "'=1+1")
        self.assertEqual(main._safe_spreadsheet_value("texto"), "texto")

    def test_api_documentation_is_disabled_by_default(self):
        self.assertIsNone(main.app.docs_url)
        self.assertIsNone(main.app.openapi_url)


if __name__ == "__main__":
    unittest.main()
