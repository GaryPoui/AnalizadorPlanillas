"""Persistent users and email verification for PriceBot."""

from __future__ import annotations

import hashlib
import hmac
import html
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )


class UserStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    confirmed INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    confirmation_token_hash TEXT,
                    token_expires_at INTEGER,
                    created_at INTEGER NOT NULL,
                    confirmed_at INTEGER
                )
                """
            )

    @staticmethod
    def normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if len(normalized) > 254 or not EMAIL_RE.fullmatch(normalized):
            raise ValueError("Ingresá una dirección de correo válida")
        return normalized

    @staticmethod
    def validate_password(password: str) -> None:
        if len(password) < 10:
            raise ValueError("La contraseña debe tener al menos 10 caracteres")
        if len(password) > 256:
            raise ValueError("La contraseña es demasiado larga")

    def create_pending_user(
        self, email: str, password: str, token_ttl_seconds: int
    ) -> tuple[str, str]:
        email = self.normalize_email(email)
        self.validate_password(password)
        salt = secrets.token_bytes(16)
        digest = password_digest(password, salt)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = int(time.time())

        with self._connection() as connection:
            existing = connection.execute(
                "SELECT confirmed FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing and existing["confirmed"]:
                raise ValueError("Ese correo ya pertenece a un usuario confirmado")
            connection.execute(
                """
                INSERT INTO users (
                    email, password_salt, password_hash, confirmed, enabled,
                    confirmation_token_hash, token_expires_at, created_at
                ) VALUES (?, ?, ?, 0, 1, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    password_salt = excluded.password_salt,
                    password_hash = excluded.password_hash,
                    confirmed = 0,
                    enabled = 1,
                    confirmation_token_hash = excluded.confirmation_token_hash,
                    token_expires_at = excluded.token_expires_at,
                    confirmed_at = NULL
                """,
                (email, salt, digest, token_hash, now + token_ttl_seconds, now),
            )
        return email, token

    def regenerate_confirmation_token(
        self, email: str, token_ttl_seconds: int
    ) -> tuple[str, str]:
        email = self.normalize_email(email)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = int(time.time()) + token_ttl_seconds
        with self._connection() as connection:
            row = connection.execute(
                "SELECT confirmed, enabled FROM users WHERE email = ?", (email,)
            ).fetchone()
            if not row:
                raise ValueError("El usuario no existe")
            if row["confirmed"]:
                raise ValueError("El usuario ya confirmó su correo")
            if not row["enabled"]:
                raise ValueError("El usuario está deshabilitado")
            connection.execute(
                """
                UPDATE users
                SET confirmation_token_hash = ?, token_expires_at = ?
                WHERE email = ?
                """,
                (token_hash, expires_at, email),
            )
        return email, token

    def confirm(self, token: str) -> str:
        if not token or len(token) > 512:
            raise ValueError("El enlace de confirmación no es válido")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = int(time.time())
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT email, token_expires_at, enabled
                FROM users
                WHERE confirmation_token_hash = ? AND confirmed = 0
                """,
                (token_hash,),
            ).fetchone()
            if not row:
                raise ValueError("El enlace de confirmación no es válido o ya fue usado")
            if not row["enabled"]:
                raise ValueError("El usuario está deshabilitado")
            if not row["token_expires_at"] or row["token_expires_at"] < now:
                raise ValueError("El enlace de confirmación venció; solicitá uno nuevo")
            connection.execute(
                """
                UPDATE users
                SET confirmed = 1, confirmed_at = ?,
                    confirmation_token_hash = NULL, token_expires_at = NULL
                WHERE email = ?
                """,
                (now, row["email"]),
            )
            return str(row["email"])

    def authenticate(self, email: str, password: str) -> str | None:
        try:
            email = self.normalize_email(email)
        except ValueError:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT password_salt, password_hash
                FROM users
                WHERE email = ? AND confirmed = 1 AND enabled = 1
                """,
                (email,),
            ).fetchone()
        if not row:
            return None
        actual = password_digest(password, bytes(row["password_salt"]))
        return email if hmac.compare_digest(actual, bytes(row["password_hash"])) else None

    def is_active(self, email: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM users
                WHERE email = ? AND confirmed = 1 AND enabled = 1
                """,
                (email.strip().lower(),),
            ).fetchone()
        return row is not None

    def has_active_users(self) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE confirmed = 1 AND enabled = 1 LIMIT 1"
            ).fetchone()
        return row is not None

    def list_users(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT email, confirmed, enabled, created_at, confirmed_at,
                       token_expires_at
                FROM users
                ORDER BY created_at DESC, email
                """
            ).fetchall()
        return [
            {
                "email": row["email"],
                "confirmed": bool(row["confirmed"]),
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "confirmed_at": row["confirmed_at"],
                "confirmation_expired": bool(
                    not row["confirmed"]
                    and row["token_expires_at"]
                    and row["token_expires_at"] < int(time.time())
                ),
            }
            for row in rows
        ]

    def set_enabled(self, email: str, enabled: bool) -> None:
        email = self.normalize_email(email)
        with self._connection() as connection:
            result = connection.execute(
                "UPDATE users SET enabled = ? WHERE email = ?",
                (int(enabled), email),
            )
            if result.rowcount != 1:
                raise ValueError("El usuario no existe")


def build_confirmation_url(public_url: str, token: str) -> str:
    return f"{public_url.rstrip('/')}/?confirm={quote(token, safe='')}"


def send_confirmation_email(
    *,
    recipient: str,
    confirmation_url: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    smtp_from: str,
    smtp_starttls: bool,
    smtp_ssl: bool,
) -> None:
    if not smtp_host or not smtp_from:
        raise RuntimeError("El envío de correo SMTP todavía no está configurado")

    message = EmailMessage()
    message["Subject"] = "Confirmá tu acceso a PriceBot"
    message["From"] = smtp_from
    message["To"] = recipient
    message.set_content(
        "Se creó un acceso a PriceBot para este correo.\n\n"
        f"Confirmalo desde este enlace:\n{confirmation_url}\n\n"
        "Si no esperabas este mensaje, podés ignorarlo."
    )
    message.add_alternative(
        """
        <html><body style="font-family:Arial,sans-serif;color:#222">
          <h2>Confirmá tu acceso a PriceBot</h2>
          <p>Se creó un acceso a PriceBot para este correo.</p>
          <p><a href="{url}" style="display:inline-block;padding:12px 18px;background:#7c3aed;color:white;text-decoration:none;border-radius:6px">Confirmar correo</a></p>
          <p>Si no esperabas este mensaje, podés ignorarlo.</p>
        </body></html>
        """.format(url=html.escape(confirmation_url, quote=True)),
        subtype="html",
    )

    context = ssl.create_default_context()
    if smtp_ssl:
        server_context = smtplib.SMTP_SSL(
            smtp_host, smtp_port, timeout=20, context=context
        )
    else:
        server_context = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
    with server_context as server:
        if not smtp_ssl and smtp_starttls:
            server.starttls(context=context)
        if smtp_username:
            server.login(smtp_username, smtp_password)
        server.send_message(message)
