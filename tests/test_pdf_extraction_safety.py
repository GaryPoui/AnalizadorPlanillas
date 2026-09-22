import sys
import unittest
import asyncio
from pathlib import Path


API_DIR = Path(__file__).resolve().parents[1] / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))

import main  # noqa: E402


class PdfExtractionSafetyTests(unittest.TestCase):
    def test_decimal_amount_cannot_be_split_into_code_and_price(self):
        rows = main.heuristic_extract_rows(
            "BP50-05-300 31163,97 TBP-05-300 28104,33"
        )
        pairs = {(row["Cód. Artículo"], row["Precio"]) for row in rows}

        self.assertIn(("BP50-05-300", "31163.97"), pairs)
        self.assertIn(("TBP-05-300", "28104.33"), pairs)
        self.assertNotIn(("3116", "3.97"), pairs)
        self.assertNotIn(("2810", "4.33"), pairs)

    def test_dimensions_are_not_integer_price_pairs(self):
        rows = main.heuristic_extract_rows(
            "PC 44 x 44 x 3000/6000 mm ventilado"
        )
        self.assertEqual(rows, [])

    def test_parallel_pdf_pairs_keep_their_own_prices(self):
        raw_data = {
            "pdf_pages": [
                "BE64-12-150 49440,42 BE92-12-150 58155,88 "
                "BP50-05-050 13145,05 TBP-05-050 8545,11"
            ]
        }
        prices = main._extract_unambiguous_pdf_prices(raw_data)

        self.assertEqual(prices["BE64-12-150"], "49440.42")
        self.assertEqual(prices["BE92-12-150"], "58155.88")
        self.assertEqual(prices["BP50-05-050"], "13145.05")
        self.assertEqual(prices["TBP-05-050"], "8545.11")

    def test_native_text_wins_over_conflicting_reconstructed_table(self):
        raw_data = {
            "pdf_pages": [
                "BP50-05-300 31163,97 TBP-05-300 28104,33\n"
                "BP50-05-300 | 28671,24 | TBP-05-300 | 23015,29"
            ]
        }
        prices = main._extract_unambiguous_pdf_prices(raw_data)

        self.assertEqual(prices["BP50-05-300"], "31163.97")
        self.assertEqual(prices["TBP-05-300"], "28104.33")

    def test_explicit_no_price_codes_are_source_backed(self):
        raw_data = {
            "pdf_pages": [
                "PC44.44-16-3000 Pedir precio PC44.44V-16-3000 Pedir precio\n"
                "TIR-3/8 | Pedir precio"
            ]
        }
        self.assertEqual(
            main._extract_explicit_no_price_codes(raw_data),
            {"PC44.44-16-3000", "PC44.44V-16-3000", "TIR-3/8"},
        )

    def test_no_price_markers_do_not_promote_prices_or_prose_to_codes(self):
        raw_data = {
            "pdf_pages": [
                "GCE 2444,71\n"
                "Por bulonería, tuercas y arandelas. Pedir precio"
            ]
        }
        self.assertEqual(main._extract_explicit_no_price_codes(raw_data), set())

    def test_contiguous_mixed_alphanumeric_codes_are_supported(self):
        rows = main.heuristic_extract_rows(
            "RCP450h300 12125,70 TRCP450a300 7010,50 CP45PC44 3939,45"
        )
        pairs = {(row["Cód. Artículo"], row["Precio"]) for row in rows}
        self.assertEqual(
            pairs,
            {
                ("RCP450H300", "12125.70"),
                ("TRCP450A300", "7010.50"),
                ("CP45PC44", "3939.45"),
            },
        )

    def test_code_only_recovery_ignores_price_fragments(self):
        rows = main._extract_code_only_rows(
            "RCP450h300 12125,70 TRCP450a300 7010,50"
        )
        self.assertEqual(rows, [])

    def test_spaced_decimal_separator_is_still_a_price(self):
        rows = main.heuristic_extract_rows("SG-50 1766 ,84")
        self.assertEqual(
            [(row["Cód. Artículo"], row["Precio"]) for row in rows],
            [("SG-50", "1766.84")],
        )

    def test_numeric_code_only_recovery_can_be_disabled_for_mixed_layouts(self):
        rows = main._extract_code_only_rows(
            "Largo 3000 mm", allow_numeric=False
        )
        self.assertEqual(rows, [])

    def test_source_confirmed_alpha_sku_is_not_garbage(self):
        self.assertFalse(main._looks_like_garbage_code("GCE", {"GCE"}))
        self.assertTrue(main._looks_like_garbage_code("MATERIAL", {"GCE"}))

    def test_normalized_code_price_duplicates_keep_richer_row(self):
        sparse = main._empty_template_row()
        sparse.update({"Cód. Artículo": "CPP45-07-050", "Precio": "2934.12"})
        rich = dict(sparse)
        rich["Descripción artículo"] = "Curva plana a 45°"

        result = main._dedupe_rows_by_key([sparse, rich])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Descripción artículo"], "Curva plana a 45°")

    def test_pdf_verifier_quarantines_unbacked_price_less_noise(self):
        rows = [main._empty_template_row(), main._empty_template_row()]
        rows[0].update({"Cód. Artículo": "AR104640", "Descripción artículo": "PATENTE"})
        rows[1].update({"Cód. Artículo": "TIR-3/8", "Descripción artículo": "Pedir precio"})
        raw_data = {
            "metadata": {"type": ".pdf"},
            "raw_text": "TIR-3/8 Pedir precio",
            "pdf_pages": ["TIR-3/8 Pedir precio"],
        }

        result = asyncio.run(main.agent_verifier(rows, raw_data))

        self.assertEqual(
            [row["Cód. Artículo"] for row in result["rows"]],
            ["TIR-3/8"],
        )


if __name__ == "__main__":
    unittest.main()
