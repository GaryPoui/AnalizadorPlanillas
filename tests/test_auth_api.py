import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "pricebot" / "api"
sys.path.insert(0, str(API_DIR))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from user_auth import UserStore  # noqa: E402


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.previous = {
            "USER_STORE": main.USER_STORE,
            "AUTH_REQUIRED": main.AUTH_REQUIRED,
            "SESSION_SECRET": main.SESSION_SECRET,
            "COOKIE_SECURE": main.COOKIE_SECURE,
            "API_ACCESS_KEY": main.API_ACCESS_KEY,
            "REQUIRE_HTTPS": main.REQUIRE_HTTPS,
            "LOGIN_MAX_ATTEMPTS": main.LOGIN_MAX_ATTEMPTS,
        }
        main.USER_STORE = UserStore(Path(self.temp_directory.name) / "users.db")
        main.AUTH_REQUIRED = True
        main.SESSION_SECRET = "integration-test-session-secret"
        main.COOKIE_SECURE = False
        main.API_ACCESS_KEY = ""
        main.REQUIRE_HTTPS = False
        main.LOGIN_MAX_ATTEMPTS = 5
        main._LOGIN_ATTEMPTS.clear()

        email, token = main.USER_STORE.create_pending_user(
            "persona@empresa.com", "una-clave-segura", 3600
        )
        main.USER_STORE.confirm(token)
        self.email = email

    def tearDown(self):
        for name, value in self.previous.items():
            setattr(main, name, value)
        self.temp_directory.cleanup()

    def test_confirmed_user_can_login_and_use_a_session(self):
        with TestClient(
            main.app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)
        ) as client:
            response = client.post(
                "/auth/login",
                json={"username": self.email, "password": "una-clave-segura"},
            )
            self.assertEqual(response.status_code, 200)
            me = client.get("/auth/me")
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["username"], self.email)
            self.assertTrue(me.json()["local_admin"])

    def test_wrong_password_is_rejected(self):
        with TestClient(main.app) as client:
            response = client.post(
                "/auth/login",
                json={"username": self.email, "password": "incorrecta"},
            )
            self.assertEqual(response.status_code, 401)

    def test_login_is_rate_limited(self):
        main.LOGIN_MAX_ATTEMPTS = 3
        with TestClient(
            main.app, client=("192.168.190.112", 50000)
        ) as client:
            for _ in range(3):
                response = client.post(
                    "/auth/login",
                    json={"username": self.email, "password": "incorrecta"},
                )
                self.assertEqual(response.status_code, 401)
            blocked = client.post(
                "/auth/login",
                json={"username": self.email, "password": "incorrecta"},
            )
            self.assertEqual(blocked.status_code, 429)
            self.assertIn("retry-after", blocked.headers)

    def test_extraction_is_rejected_without_a_session(self):
        with TestClient(main.app) as client:
            response = client.post("/extract")
            self.assertEqual(response.status_code, 401)

    def test_session_cookie_is_http_only_and_same_site(self):
        with TestClient(main.app) as client:
            response = client.post(
                "/auth/login",
                json={"username": self.email, "password": "una-clave-segura"},
            )
            cookie = response.headers.get("set-cookie", "").lower()
            self.assertIn("httponly", cookie)
            self.assertIn("samesite=lax", cookie)

    def test_cors_rejects_an_untrusted_web_origin(self):
        with TestClient(main.app) as client:
            response = client.options(
                "/auth/me",
                headers={
                    "Origin": "https://evil.example",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertNotEqual(
                response.headers.get("access-control-allow-origin"),
                "https://evil.example",
            )

    def test_remote_plain_http_is_rejected_when_https_is_required(self):
        main.REQUIRE_HTTPS = True
        with TestClient(
            main.app,
            base_url="http://192.168.190.146",
            client=("192.168.190.112", 50000),
        ) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 426)
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_remote_user_cannot_open_user_administration(self):
        with TestClient(
            main.app,
            base_url="http://192.168.190.146",
            client=("192.168.190.112", 50000),
        ) as client:
            login = client.post(
                "/auth/login",
                json={"username": self.email, "password": "una-clave-segura"},
            )
            self.assertEqual(login.status_code, 200)
            response = client.get("/admin/users")
            self.assertEqual(response.status_code, 403)

    def test_initial_bootstrap_is_available_only_from_loopback(self):
        main.USER_STORE = UserStore(
            Path(self.temp_directory.name) / "empty-users.db"
        )
        with TestClient(
            main.app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)
        ) as local_client:
            response = local_client.get("/auth/me")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["local_admin"])

        with TestClient(
            main.app,
            base_url="http://192.168.190.146",
            client=("192.168.190.112", 50000),
        ) as remote_client:
            response = remote_client.get("/auth/me")
            self.assertEqual(response.status_code, 401)

    def test_public_host_through_loopback_proxy_is_not_local_admin(self):
        main.USER_STORE = UserStore(
            Path(self.temp_directory.name) / "empty-proxy-users.db"
        )
        with TestClient(
            main.app,
            base_url="https://pricebot.empresa.example",
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.get("/auth/me")
            self.assertEqual(response.status_code, 401)

    def test_oversized_login_secret_is_rejected_before_hashing(self):
        with TestClient(main.app) as client:
            response = client.post(
                "/auth/login",
                json={"username": self.email, "password": "x" * 257},
            )
            self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
