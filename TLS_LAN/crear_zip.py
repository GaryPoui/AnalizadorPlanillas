"""Build a source-only distribution: certificates and secrets are never included."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SOURCES = (
    "INSTALAR-SERVIDOR.bat", "instalar-servidor.ps1", "generar_certificados.py",
    "requirements-tls.txt", "INICIAR-PRICEBOT-SEGURO.bat", "iniciar-seguro.ps1",
    "LEEME.md", "cliente/INSTALAR-CLIENTE.bat", "cliente/INSTALAR-SOLO-USUARIO.bat", "cliente/instalar-cliente.ps1",
    "cliente/verificar-conexion.ps1", "cliente/LEEME.md",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-cert", type=Path, help="Certificado publico DER de la CA; solo va al ZIP cliente")
    parser.add_argument("--expected-sha256", default="", help="Huella de la CA verificada por TI")
    args = parser.parse_args()
    if bool(args.client_cert) != bool(args.expected_sha256):
        parser.error("--client-cert y --expected-sha256 deben usarse juntos")
    source = Path(__file__).resolve().parent
    root = source.parent
    output = root / "dist" / "PriceBot_TLS_LAN.zip"
    output.parent.mkdir(exist_ok=True)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "files_sha256": {},
        "contains_private_keys": False,
    }
    contents = {}
    for relative in SOURCES:
        file = source / relative
        if file.is_symlink() or not file.is_file():
            raise SystemExit(f"Archivo ausente o enlace no permitido: {relative}")
        data = file.read_bytes()
        if any(header in data for header in (
            b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN RSA PRIVATE KEY-----",
            b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
        )):
            raise SystemExit(f"Se detecto material privado en {relative}; ZIP rechazado.")
        # cmd.exe receives portable CRLF, even on checkouts with LF line endings.
        if relative.endswith(".bat"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        contents[relative] = data
        manifest["files_sha256"][relative] = hashlib.sha256(data).hexdigest()
    temporary = output.with_suffix(".zip.new")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, data in contents.items():
            archive.writestr(f"PriceBot_TLS_LAN/{relative}", data)
        archive.writestr("PriceBot_TLS_LAN/CONTENIDO.json", json.dumps(manifest, indent=2))
    temporary.replace(output)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(SOURCES) + 1
        assert not any(name.endswith((".pem", ".key", ".pfx", ".p12", ".cer")) for name in archive.namelist())
    print(output)
    print("SHA-256:", hashlib.sha256(output.read_bytes()).hexdigest())

    client_contents = {relative.removeprefix("cliente/"): data for relative, data in contents.items() if relative.startswith("cliente/")}
    public_ca_sha256 = None
    if args.client_cert:
        from cryptography import x509
        data = args.client_cert.read_bytes()
        cert = x509.load_der_x509_certificate(data)
        expected = args.expected_sha256.replace(":", "").replace("-", "").replace(" ", "").upper()
        public_ca_sha256 = hashlib.sha256(data).hexdigest().upper()
        constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        now = datetime.now(timezone.utc)
        if public_ca_sha256 != expected or not constraints.ca or constraints.path_length != 0:
            raise SystemExit("CA o huella incorrecta. No se creara el ZIP cliente.")
        if not cert.not_valid_before_utc <= now < cert.not_valid_after_utc:
            raise SystemExit("La CA esta fuera de vigencia.")
        client_contents["PriceBot-CA.cer"] = data
    else:
        client_contents["COPIAR-CERTIFICADO-PUBLICO.txt"] = (
            "Antes de instalar, copiar PriceBot-CA.cer desde el paquete Clientes-PriceBot.zip "
            "del servidor a esta carpeta. Nunca copiar archivos .pem ni claves privadas.\r\n"
        ).encode("utf-8")
    client_manifest = {
        "commit": manifest["commit"], "contains_private_keys": False,
        "public_ca_sha256": public_ca_sha256,
        "files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in client_contents.items()},
    }
    client_output = output.parent / "Clientes-PriceBot-SinAdmin.zip"
    client_temp = client_output.with_suffix(".zip.new")
    with zipfile.ZipFile(client_temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in client_contents.items():
            archive.writestr(name, data)
        archive.writestr("CONTENIDO.json", json.dumps(client_manifest, indent=2))
    client_temp.replace(client_output)
    with zipfile.ZipFile(client_output) as archive:
        assert archive.testzip() is None
        assert not any(name.endswith((".pem", ".key", ".pfx", ".p12")) for name in archive.namelist())
    print(client_output)
    print("SHA-256:", hashlib.sha256(client_output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
