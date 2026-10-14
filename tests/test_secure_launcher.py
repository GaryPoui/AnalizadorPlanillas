"""Launcher preflight only: no services, trust stores or machine settings changed."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell required')
class SecureLauncherTests(unittest.TestCase):
    def check(self, config, expected):
        result = subprocess.run([
            'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT / 'TLS_LAN' / 'iniciar-seguro.ps1'),
            '-ConfigPath', str(config), '-ValidateOnly',
        ], capture_output=True, text=True, errors='replace', timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return ' '.join((result.stdout + result.stderr).split())

    def test_missing_installation_explains_required_server_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.check(Path(directory) / 'missing.json', 1)
            self.assertIn('SOLO en la PC servidor', output)

    def test_configured_server_preflight_and_unsafe_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            config = path / 'config.json'
            environment = {
                'PRICEBOT_REQUIRE_HTTPS': '1', 'PRICEBOT_COOKIE_SECURE': '1',
                'PRICEBOT_AUTH_REQUIRED': '1',
                'PRICEBOT_TLS_CERTFILE': str(ROOT / 'TLS_LAN' / 'LEEME.md'),
                'PRICEBOT_TLS_KEYFILE': str(ROOT / 'TLS_LAN' / 'LEEME.md'),
                'PRICEBOT_PUBLIC_URL': 'https://192.168.190.146:3000',
            }
            # Preflight checks only file presence, not certificate contents.
            data = {'project_path': str(ROOT), 'environment': environment}
            config.write_text(json.dumps(data), encoding='utf-8')
            self.assertIn('No se iniciaron servicios', self.check(config, 0))
            for name in ('PRICEBOT_REQUIRE_HTTPS', 'PRICEBOT_COOKIE_SECURE', 'PRICEBOT_AUTH_REQUIRED'):
                environment[name] = '0'
                config.write_text(json.dumps(data), encoding='utf-8')
                self.check(config, 1)
                environment[name] = '1'
            environment['PRICEBOT_PUBLIC_URL'] = 'http://192.168.190.146:3000'
            config.write_text(json.dumps(data), encoding='utf-8')
            self.assertIn('No se iniciara por HTTP', self.check(config, 1))
            environment['PRICEBOT_PUBLIC_URL'] = 'https://192.168.190.146:3000'
            environment['PRICEBOT_TLS_KEYFILE'] = str(path / 'missing.key')
            config.write_text(json.dumps(data), encoding='utf-8')
            self.assertIn('PRICEBOT_TLS_KEYFILE', self.check(config, 1))
            data['project_path'] = str(path / 'missing-repo')
            config.write_text(json.dumps(data), encoding='utf-8')
            self.assertIn('ruta guardada', self.check(config, 1))
