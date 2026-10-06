import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))

import main  # noqa: E402


class CostAlertTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.previous = {
            "COST_LOG_PATH": main.COST_LOG_PATH,
            "_ALERT_STATE_PATH": main._ALERT_STATE_PATH,
            "_AI_MONTHLY_BUDGET_USD": main._AI_MONTHLY_BUDGET_USD,
            "_AI_BUDGET_ALERT_PERCENT": main._AI_BUDGET_ALERT_PERCENT,
            "SMTP_HOST": main.SMTP_HOST,
            "SMTP_PORT": main.SMTP_PORT,
            "SMTP_USERNAME": main.SMTP_USERNAME,
            "SMTP_PASSWORD": main.SMTP_PASSWORD,
            "SMTP_FROM": main.SMTP_FROM,
            "ALERT_EMAIL": main.ALERT_EMAIL,
        }
        main.COST_LOG_PATH = Path(self.temp_directory.name) / "costs.jsonl"
        main._ALERT_STATE_PATH = Path(self.temp_directory.name) / "alerts.json"
        main._AI_MONTHLY_BUDGET_USD = 1.0
        main._AI_BUDGET_ALERT_PERCENT = 80.0
        main.SMTP_HOST = "smtp.gmail.com"
        main.SMTP_PORT = 587
        main.SMTP_USERNAME = "compras@dynamicenergy.com.ar"
        main.SMTP_PASSWORD = "test-app-password"
        main.SMTP_FROM = "compras@dynamicenergy.com.ar"
        main.ALERT_EMAIL = "compras@dynamicenergy.com.ar"

    def tearDown(self):
        for name, value in self.previous.items():
            setattr(main, name, value)
        self.temp_directory.cleanup()

    def test_monthly_budget_threshold_sends_one_alert(self):
        month = main.datetime.now().strftime("%Y-%m")
        main.COST_LOG_PATH.write_text(
            json.dumps({"ts": f"{month}-01T10:00:00", "cost_real": 0.81}) + "\n",
            encoding="utf-8",
        )
        with patch("main.send_admin_notification_email") as send_email:
            asyncio.run(main._maybe_send_budget_alert())
            asyncio.run(main._maybe_send_budget_alert())

        send_email.assert_called_once()
        self.assertEqual(
            send_email.call_args.kwargs["recipient"], "compras@dynamicenergy.com.ar"
        )
        self.assertIn(
            "no representa el saldo prepago real", send_email.call_args.kwargs["body"]
        )

    def test_budget_alert_is_disabled_when_budget_is_zero(self):
        main._AI_MONTHLY_BUDGET_USD = 0
        with patch("main.send_admin_notification_email") as send_email:
            asyncio.run(main._maybe_send_budget_alert())
        send_email.assert_not_called()

    def test_credit_exhaustion_error_is_detected_without_false_positives(self):
        self.assertTrue(main._is_credit_exhaustion_error(402, "Payment required"))
        self.assertTrue(
            main._is_credit_exhaustion_error(400, "Your credit balance is too low")
        )
        self.assertFalse(main._is_credit_exhaustion_error(400, "Invalid request"))


if __name__ == "__main__":
    unittest.main()