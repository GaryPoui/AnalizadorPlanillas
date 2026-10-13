"""Build a source-only distribution: certificates and secrets are never included."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SOURCES = (
    "INSTALAR-SERVIDOR.bat", "instalar-servidor.ps1", "generar_certificados.py",
    "requirements-tls.txt", "INICIAR-PRICEBOT-SEGURO.bat", "iniciar-seguro.ps1",
    "LEEME.md", "cliente/INSTALAR-CLIENTE.bat", "cliente/instalar-cliente.ps1",
    "cliente/verificar-conexion.ps1", "cliente/LEEME.md",
)


def main() -> None:
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


if __name__ == "__main__":
    main()
