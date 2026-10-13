"""Private LAN PKI. Run on the server; never distribute CA/server private keys."""
from __future__ import annotations

import argparse
import getpass
import ipaddress
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _write_private(path: Path, contents: bytes, *, exclusive: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(contents)


def generate(directory: Path, server_ip: str, subnet: str, password: bytes) -> dict:
    address = ipaddress.ip_address(server_ip)
    network = ipaddress.ip_network(subnet, strict=True)
    private_networks = [ipaddress.ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if address.version != 4 or not any(address in value for value in private_networks):
        raise ValueError("La IP del servidor debe ser una IPv4 privada de la LAN.")
    if network.version != 4 or not any(network.subnet_of(value) for value in private_networks):
        raise ValueError("La subred autorizada debe estar dentro de una red IPv4 privada.")
    if address not in network:
        raise ValueError("La IP del servidor no pertenece a la subred autorizada.")
    if len(password) < 16:
        raise ValueError("La frase de la CA debe tener al menos 16 caracteres.")

    directory.mkdir(parents=True, exist_ok=True)
    ca_dir = directory / "ca"
    ca_dir.mkdir(exist_ok=True)
    ca_file = ca_dir / "ca-cert.pem"
    key_file = ca_dir / "ca-key-encrypted.pem"
    now = datetime.now(timezone.utc)
    if ca_file.exists() != key_file.exists():
        raise ValueError("CA incompleta. No se reemplazara: revisar los archivos existentes.")
    if ca_file.exists():
        root = x509.load_pem_x509_certificate(ca_file.read_bytes())
        ca_key = serialization.load_pem_private_key(key_file.read_bytes(), password)
        if not isinstance(ca_key, rsa.RSAPrivateKey):
            raise ValueError("La clave de la CA no es RSA.")
        if root.public_key().public_numbers() != ca_key.public_key().public_numbers():
            raise ValueError("La clave no corresponde al certificado de la CA.")
        if not root.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("El certificado existente no es una CA.")
        if root.not_valid_before_utc > now:
            raise ValueError("La CA todavia no es valida. Revisar fecha y hora del servidor.")
        if root.not_valid_after_utc <= now + timedelta(days=366):
            raise ValueError("La CA tiene menos de un ano de vigencia. TI debe planificar su sustitucion.")
        root.verify_directly_issued_by(root)
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PriceBot LAN"),
            x509.NameAttribute(NameOID.COMMON_NAME, "PriceBot LAN CA"),
        ])
        root = (
            x509.CertificateBuilder()
            .subject_name(subject).issuer_name(subject).public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=365 * 5))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        # The installer secures this directory's Windows ACL BEFORE calling us.
        _write_private(key_file, ca_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(password),
        ), exclusive=True)
        _write_private(ca_file, root.public_bytes(serialization.Encoding.PEM), exclusive=True)

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    server = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, str(address))]))
        .issuer_name(root.subject).public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(address), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            x509.IPAddress(ipaddress.ip_address("::1")), x509.DNSName("localhost"),
        ]), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False,
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    server.verify_directly_issued_by(root)
    cert_temp = directory / "server-cert.pem.new"
    key_temp = directory / "server-key.pem.new"
    _write_private(cert_temp, server.public_bytes(serialization.Encoding.PEM))
    _write_private(key_temp, server_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ))
    # No live service may be using these files: installer requires closed ports.
    os.replace(key_temp, directory / "server-key.pem")
    os.replace(cert_temp, directory / "server-cert.pem")
    public_der = root.public_bytes(serialization.Encoding.DER)
    (directory / "PriceBot-CA.cer").write_bytes(public_der)
    result = {
        "server_ip": str(address), "allowed_subnet": str(network),
        "ca_sha256": root.fingerprint(hashes.SHA256()).hex().upper(),
        "ca_sha1": root.fingerprint(hashes.SHA1()).hex().upper(),
        "certificate_expires": server.not_valid_after_utc.isoformat(),
        "ca_expires": root.not_valid_after_utc.isoformat(),
    }
    (directory / "certificates.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--server-ip", default="192.168.190.146")
    parser.add_argument("--subnet", default="192.168.190.0/24")
    args = parser.parse_args()
    existing = (args.directory / "ca" / "ca-key-encrypted.pem").exists()
    password = getpass.getpass("Frase de la CA (minimo 16 caracteres, no se muestra): ")
    if len(password) < 16:
        raise SystemExit("La frase de la CA debe tener al menos 16 caracteres.")
    if not existing and password != getpass.getpass("Repetir frase de la CA: "):
        raise SystemExit("Las frases no coinciden. No se genero el certificado.")
    try:
        result = generate(args.directory, args.server_ip, args.subnet, password.encode("utf-8"))
    except (ValueError, OSError, x509.ExtensionNotFound) as exc:
        raise SystemExit(f"No se genero el certificado: {exc}") from None
    print("Certificado generado. SHA-256 de la CA publica:")
    print(result["ca_sha256"])
    print("Vencimiento del servidor:", result["certificate_expires"])


if __name__ == "__main__":
    main()
