"""Small static server with defensive headers for PriceBot's local frontend."""

from __future__ import annotations

import argparse
import os
import ssl
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class SecureStaticHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        connect_sources = os.getenv(
            "PRICEBOT_CSP_CONNECT_SRC",
            "'self' http://127.0.0.1:8000 http://localhost:8000 "
            "https://127.0.0.1:8000 https://localhost:8000 "
            "https://192.168.190.146:8000",
        ).strip()
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("X-Permitted-Cross-Domain-Policies", "none")
        self.send_header(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "script-src 'self'",
                    "style-src 'self' 'unsafe-inline'",
                    "img-src 'self' data:",
                    f"connect-src {connect_sources}",
                    "object-src 'none'",
                    "base-uri 'none'",
                    "frame-ancestors 'none'",
                    "form-action 'self'",
                ]
            ),
        )
        if isinstance(self.connection, ssl.SSLSocket):
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

    def log_message(self, format, *args):
        # Do not persist URLs or query strings (confirmation tokens) in access logs.
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument(
        "--directory", default=str(Path(__file__).resolve().parent / "frontend")
    )
    parser.add_argument("--ssl-certfile", default="")
    parser.add_argument("--ssl-keyfile", default="")
    args = parser.parse_args()

    directory = Path(args.directory).resolve(strict=True)
    handler = partial(SecureStaticHandler, directory=str(directory))
    server = ThreadingHTTPServer((args.bind, args.port), handler)

    if bool(args.ssl_certfile) != bool(args.ssl_keyfile):
        raise SystemExit("SSL requires both --ssl-certfile and --ssl-keyfile")
    scheme = "http"
    if args.ssl_certfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.ssl_certfile, args.ssl_keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"

    print(f"PriceBot frontend: {scheme}://{args.bind}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
