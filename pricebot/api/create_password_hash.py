"""Generate a PRICEBOT_USERS record without exposing the password.

Usage:
    python create_password_hash.py usuario

Copy the printed record to PRICEBOT_USERS. Multiple records are separated by
commas, for example: usuario1$...$...,usuario2$...$...
"""

import base64
import getpass
import hashlib
import secrets
import sys


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


if len(sys.argv) != 2 or not sys.argv[1].strip():
    raise SystemExit("Uso: python create_password_hash.py NOMBRE_DE_USUARIO")

username = sys.argv[1].strip()
password = getpass.getpass("Contraseña (no se mostrará): ")
confirmation = getpass.getpass("Repetir contraseña: ")
if not password or password != confirmation:
    raise SystemExit("Las contraseñas no coinciden o están vacías.")

salt = secrets.token_bytes(16)
digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
print(f"{username}${encode(salt)}${encode(digest)}")
