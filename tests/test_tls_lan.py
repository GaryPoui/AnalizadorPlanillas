"""TLS kit tests: ephemeral keys and isolated listeners, no Windows trust changes."""
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TLS_LAN"))
from generar_certificados import generate
from crear_acceso_automatico import create_script


class LanCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name)
        cls.password = b"temporary-CA-passphrase-for-tests"
        cls.metadata = generate(cls.path, "192.168.190.146", "192.168.190.0/24", cls.password)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_private_ca_key_is_encrypted_and_leaf_is_scoped_to_server_auth(self):
        key = (self.path / "ca" / "ca-key-encrypted.pem").read_bytes()
        with self.assertRaises(TypeError):
            serialization.load_pem_private_key(key, password=None)
        with self.assertRaises(ValueError):
            serialization.load_pem_private_key(key, password=b"wrong-password")
        root = x509.load_pem_x509_certificate((self.path / "ca" / "ca-cert.pem").read_bytes())
        leaf = x509.load_pem_x509_certificate((self.path / "server-cert.pem").read_bytes())
        leaf.verify_directly_issued_by(root)
        self.assertEqual(root.extensions.get_extension_for_class(x509.BasicConstraints).value.path_length, 0)
        self.assertFalse(leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        eku = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        self.assertEqual(list(eku), [ExtendedKeyUsageOID.SERVER_AUTH])
        san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        self.assertEqual(set(san.get_values_for_type(x509.IPAddress)), {
            ipaddress.ip_address("192.168.190.146"), ipaddress.ip_address("127.0.0.1"), ipaddress.ip_address("::1"),
        })
        self.assertEqual(san.get_values_for_type(x509.DNSName), ["localhost"])

    def test_renewal_preserves_ca_and_wrong_password_preserves_existing_leaf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            first = generate(path, "192.168.190.146", "192.168.190.0/24", self.password)
            original = (path / "server-cert.pem").read_bytes()
            with self.assertRaises(ValueError):
                generate(path, "192.168.190.146", "192.168.190.0/24", b"incorrect-but-long-password")
            self.assertEqual(original, (path / "server-cert.pem").read_bytes())
            second = generate(path, "192.168.190.146", "192.168.190.0/24", self.password)
            self.assertEqual(first["ca_sha256"], second["ca_sha256"])
            self.assertNotEqual(original, (path / "server-cert.pem").read_bytes())

    def test_public_or_mismatched_networks_are_rejected_before_writing(self):
        for ip, subnet in [("8.8.8.8", "8.8.8.0/24"), ("192.168.190.146", "0.0.0.0/0"),
                           ("192.168.190.146", "192.168.1.0/24")]:
            with self.subTest(ip=ip), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "must-not-exist"
                with self.assertRaises(ValueError):
                    generate(path, ip, subnet, self.password)
                self.assertFalse(path.exists())

    def test_automatic_client_generator_rejects_wrong_ca_pin_and_public_ip(self):
        certificate = (self.path / "PriceBot-CA.cer").read_bytes()
        with self.assertRaises(ValueError):
            create_script(certificate, "0" * 64, "192.168.190.146")
        with self.assertRaises(ValueError):
            create_script(certificate, self.metadata["ca_sha256"], "8.8.8.8")

    @unittest.skipUnless(os.name == "nt", "Windows CMD and PowerShell only")
    def test_one_file_client_checks_embedded_certificate_without_manual_input(self):
        data = create_script((self.path / "PriceBot-CA.cer").read_bytes(), self.metadata["ca_sha256"], "192.168.190.146")
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "CONFIGURAR-PRICEBOT-LAN.bat"
            for expected_status in (0, 1):
                payload = data if expected_status == 0 else data.replace(
                    f'$expectedSha256 = "{self.metadata["ca_sha256"]}"'.encode(),
                    b'$expectedSha256 = "' + b"0" * 64 + b'"',
                )
                script.write_bytes(payload)
                result = subprocess.run(["cmd.exe", "/d", "/c", str(script), "--comprobar"],
                                        capture_output=True, text=True, errors="replace", timeout=20)
                self.assertEqual(result.returncode, expected_status, result.stdout + result.stderr)
                if expected_status == 0:
                    self.assertIn("Cert:\\CurrentUser\\Root", result.stdout)
                    self.assertIn("No se instalo confianza", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell only")
    def test_client_preflight_accepts_only_the_expected_fingerprint_without_importing(self):
        script = str(ROOT / "TLS_LAN" / "cliente" / "instalar-cliente.ps1")
        for scope in ("CurrentUser", "LocalMachine"):
            for fingerprint, expected_status in [(self.metadata["ca_sha256"], 0), ("0" * 64, 1)]:
                with self.subTest(scope=scope, fingerprint_matches=expected_status == 0):
                    result = subprocess.run([
                        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script,
                        "-CertificatePath", str(self.path / "PriceBot-CA.cer"),
                        "-ExpectedSha256", fingerprint, "-Scope", scope, "-ValidateOnly",
                    ], capture_output=True, text=True, errors="replace")
                    self.assertEqual(result.returncode, expected_status, result.stdout + result.stderr)
                    if expected_status == 0:
                        self.assertIn(f"Cert:\\{scope}\\Root", result.stdout)

    def test_real_frontend_and_api_https_reject_untrusted_certificates_and_plain_http(self):
        processes = []
        context = ssl.create_default_context(cafile=str(self.path / "ca" / "ca-cert.pem"))
        ports = []
        with tempfile.TemporaryDirectory() as data_directory:
            env = os.environ.copy()
            env.update({
                "PRICEBOT_USERS_DB": str(Path(data_directory) / "users.db"),
                "PRICEBOT_AUTH_REQUIRED": "1", "PRICEBOT_REQUIRE_HTTPS": "1",
                "PRICEBOT_COOKIE_SECURE": "1", "PRICEBOT_ALLOW_EXTERNAL_AI": "0",
                "PRICEBOT_SESSION_SECRET": "temporary-smoke-session-secret-never-for-production",
                "PRICEBOT_API_KEY": "", "ANTHROPIC_API_KEY": "", "SAVE_HISTORY": "0",
                "PRICEBOT_SMTP_HOST": "", "PRICEBOT_SMTP_PASSWORD": "",
                "PRICEBOT_CSP_CONNECT_SRC": "'self' https://127.0.0.1:8000 https://192.168.190.146:8000",
            })
            try:
                for mode in ("frontend", "api"):
                    with socket.socket() as listener:
                        listener.bind(("127.0.0.1", 0))
                        port = listener.getsockname()[1]
                    ports.append(port)
                    if mode == "frontend":
                        command = [sys.executable, str(ROOT / "pricebot" / "frontend_server.py"), "--bind", "127.0.0.1", "--port", str(port)]
                    else:
                        command = [sys.executable, "-m", "uvicorn", "main:app", "--app-dir", str(ROOT / "pricebot" / "api"), "--host", "127.0.0.1", "--port", str(port)]
                    command += ["--ssl-certfile", str(self.path / "server-cert.pem"), "--ssl-keyfile", str(self.path / "server-key.pem")]
                    process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    processes.append(process)
                    url = f"https://127.0.0.1:{port}" + ("/health" if mode == "api" else "/")
                    deadline = time.monotonic() + 35
                    while True:
                        try:
                            with urlopen(url, context=context, timeout=2) as response:
                                self.assertEqual(response.status, 200)
                                if mode == "api":
                                    self.assertEqual(json.load(response)["status"], "ok")
                                else:
                                    self.assertIn("https://127.0.0.1:8000", response.headers["Content-Security-Policy"])
                            break
                        except (URLError, OSError):
                            if process.poll() is not None or time.monotonic() > deadline:
                                self.fail(f"{mode} did not start on HTTPS")
                            time.sleep(0.2)
                    with self.assertRaises((URLError, OSError)):
                        urlopen(url, context=ssl.create_default_context(), timeout=3)
                    with self.assertRaises((URLError, OSError)):
                        urlopen(url.replace("https://", "http://"), timeout=3)
                    # Trusted issuer does not authorize an unrelated hostname.
                    with socket.create_connection(("127.0.0.1", port), timeout=3) as stream:
                        with self.assertRaises(ssl.SSLCertVerificationError):
                            context.wrap_socket(stream, server_hostname="unrelated.example")
            finally:
                for process in processes:
                    process.terminate()
                for process in processes:
                    process.wait(timeout=15)


if __name__ == "__main__":
    unittest.main()
