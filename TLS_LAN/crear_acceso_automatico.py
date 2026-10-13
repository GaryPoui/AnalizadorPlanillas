"""Generate a self-contained client BAT carrying only a verified PUBLIC CA."""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509


def create_script(certificate: bytes, expected_sha256: str, server_ip: str) -> bytes:
    cert = x509.load_der_x509_certificate(certificate)
    expected = "".join(expected_sha256.upper().split()).replace(":", "").replace("-", "")
    actual = hashlib.sha256(certificate).hexdigest().upper()
    constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
    now = datetime.now(timezone.utc)
    if actual != expected or not constraints.ca or constraints.path_length != 0:
        raise ValueError("CA o huella incorrecta; no se genera el instalador automatico.")
    if not cert.not_valid_before_utc <= now < cert.not_valid_after_utc:
        raise ValueError("La CA no esta vigente.")
    address = ipaddress.ip_address(server_ip)
    private_networks = [ipaddress.ip_network(s) for s in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if address.version != 4 or not any(address in network for network in private_networks):
        raise ValueError("Se requiere una IPv4 privada del servidor.")

    source = Path(__file__).resolve().parent / "cliente"
    importer = (source / "instalar-cliente.ps1").read_text(encoding="utf-8-sig")
    verifier = (source / "verificar-conexion.ps1").read_text(encoding="utf-8-sig")
    payload = base64.b64encode(certificate).decode("ascii")
    header = r'''@echo off
setlocal
rem PriceBot LAN - certificado publico incorporado; no contiene claves privadas.
rem Ejecutar normalmente, con el usuario Windows que usara PriceBot.
set "PRICEBOT_SETUP_FILE=%~f0"
set "PRICEBOT_VALIDATE_ONLY="
set "PRICEBOT_NO_BROWSER="
if /I "%~1"=="--comprobar" set "PRICEBOT_VALIDATE_ONLY=1"
if /I "%~1"=="--sin-abrir" set "PRICEBOT_NO_BROWSER=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:PRICEBOT_SETUP_FILE); $m='# PRICEBOT_POWERSHELL_START'; $i=$t.LastIndexOf($m); if($i -lt 0){exit 1}; & ([ScriptBlock]::Create($t.Substring($i+$m.Length)))"
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" echo No se completo la configuracion. Revisar el error anterior.
if not defined PRICEBOT_VALIDATE_ONLY if not defined PRICEBOT_NO_BROWSER pause
endlocal & exit /b %PRICEBOT_EXIT_CODE%
# PRICEBOT_POWERSHELL_START
'''
    body = f'''Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$expectedSha256 = "{actual}"
$serverIP = "{address}"
$certificateBase64 = "{payload}"
$validateOnly = $env:PRICEBOT_VALIDATE_ONLY -eq "1"
$temporaryCertificate = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName() + ".cer")
try {{
    [IO.File]::WriteAllBytes($temporaryCertificate, [Convert]::FromBase64String($certificateBase64))
    & {{
{importer}
    }} -CertificatePath $temporaryCertificate -ExpectedSha256 $expectedSha256 -Scope CurrentUser -ValidateOnly:$validateOnly
    if ($validateOnly) {{
        Write-Host "Comprobacion completa. No se instalo confianza ni se abrio el navegador."
    }} else {{
        & {{
{verifier}
        }} -ServerIP $serverIP
        Write-Host "ACCESO CONFIGURADO para este usuario. URL: https://${{serverIP}}:3000/" -ForegroundColor Green
        if ($env:PRICEBOT_NO_BROWSER -ne "1") {{ Start-Process "https://${{serverIP}}:3000/" }}
    }}
}} catch {{
    Write-Error $_ -ErrorAction Continue
    exit 1
}} finally {{
    if (Test-Path -LiteralPath $temporaryCertificate) {{ Remove-Item -LiteralPath $temporaryCertificate }}
}}
exit 0
'''
    return (header + body).replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-cert", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--server-ip", default="192.168.190.146")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = create_script(args.client_cert.read_bytes(), args.expected_sha256, args.server_ip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(args.output)
    print("SHA-256 del archivo:", hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
