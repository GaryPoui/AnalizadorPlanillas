import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


API_DIR = Path(__file__).resolve().parents[1] / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))

from user_auth import (  # noqa: E402
    UserStore,
    build_confirmation_url,
    send_confirmation_email,
)


class UserAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.store = UserStore(Path(self.temp_directory.name) / "users.db")

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_user_requires_confirmation_before_login(self):
        email, token = self.store.create_pending_user(
            " Persona@Empresa.COM ", "una-clave-segura", 3600
        )

        self.assertEqual(email, "persona@empresa.com")
        self.assertIsNone(self.store.authenticate(email, "una-clave-segura"))
        self.assertEqual(self.store.confirm(token), email)
        self.assertIsNone(self.store.authenticate(email, "incorrecta"))
        self.assertEqual(
            self.store.authenticate(email, "una-clave-segura"), email
        )

        with self.assertRaisesRegex(ValueError, "ya fue usado"):
            self.store.confirm(token)

    def test_user_can_be_disabled_and_reenabled(self):
        email, token = self.store.create_pending_user(
            "persona@empresa.com", "una-clave-segura", 3600
        )
        self.store.confirm(token)

        self.store.set_enabled(email, False)
        self.assertFalse(self.store.is_active(email))
        self.assertIsNone(self.store.authenticate(email, "una-clave-segura"))

        self.store.set_enabled(email, True)
        self.assertTrue(self.store.is_active(email))
        self.assertTrue(self.store.has_active_users())

    def test_expired_confirmation_is_rejected(self):
        _, token = self.store.create_pending_user(
            "persona@empresa.com", "una-clave-segura", -1
        )
        with self.assertRaisesRegex(ValueError, "venció"):
            self.store.confirm(token)

    def test_invalid_email_and_short_password_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "correo válida"):
            self.store.create_pending_user(
                "correo-invalido", "una-clave-segura", 3600
            )
        with self.assertRaisesRegex(ValueError, "10 caracteres"):
            self.store.create_pending_user("persona@empresa.com", "corta", 3600)

    def test_confirmation_url_uses_frontend_query_parameter(self):
        self.assertEqual(
            build_confirmation_url("http://192.168.190.146:3000/", "abc_123"),
            "http://192.168.190.146:3000/?confirm=abc_123",
        )

    @patch("user_auth.smtplib.SMTP")
    def test_confirmation_email_uses_starttls_and_authentication(self, smtp_class):
        smtp = smtp_class.return_value.__enter__.return_value
        send_confirmation_email(
            recipient="persona@empresa.com",
            confirmation_url="http://192.168.190.146:3000/?confirm=token",
            smtp_host="smtp.empresa.com",
            smtp_port=587,
            smtp_username="pricebot@empresa.com",
            smtp_password="app-password",
            smtp_from="pricebot@empresa.com",
            smtp_starttls=True,
            smtp_ssl=False,
        )

        smtp_class.assert_called_once_with("smtp.empresa.com", 587, timeout=20)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("pricebot@empresa.com", "app-password")
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
