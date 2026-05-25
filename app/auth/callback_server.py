"""Temporary local HTTP server that receives the browser OAuth callback."""
from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import cast
from urllib.parse import parse_qs, urlparse

SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Gravity Nexus — Signed In</title>
  <style>
    body { font-family: sans-serif; text-align: center;
           padding: 80px 20px; background: #1a1a2e; color: #eee; }
    h2   { font-size: 1.8rem; margin-bottom: 12px; }
    p    { color: #aaa; font-size: 1rem; }
  </style>
</head>
<body>
  <h2>&#10003; Signed in successfully</h2>
  <p>You can close this tab and return to Gravity Nexus.</p>
</body>
</html>"""


class _CallbackHTTPServer(HTTPServer):
    """HTTPServer subclass that carries the on_callback hook."""

    def __init__(self, *args, on_callback=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.on_callback = on_callback
        self._handled = False


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(_CallbackHTTPServer, self.server)
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        if server._handled:
            self.send_response(404)
            self.end_headers()
            return
        server._handled = True

        params = parse_qs(parsed.query)
        code = params.get("code",  [None])[0]
        state = params.get("state", [None])[0]

        # Respond to the browser before calling on_callback so the page loads
        # even if the token exchange takes a moment.
        body = SUCCESS_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        if server.on_callback:
            server.on_callback(code, state)

        # Shut down in a separate thread — calling shutdown() from inside a
        # request handler deadlocks because serve_forever holds the same lock.
        threading.Thread(target=server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # suppress stdout logging


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class CallbackServer:
    """Temporary HTTP server that listens for the browser OAuth redirect."""

    def __init__(self, on_callback) -> None:
        """
        on_callback: callable(code: str | None, state: str | None)
        Called from the server thread — must be thread-safe (e.g. emit a Qt signal).
        """
        self._port = _find_free_port()
        self._server = _CallbackHTTPServer(
            ("127.0.0.1", self._port), _CallbackHandler, on_callback=on_callback
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self._port

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self._port}/callback"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Stop the server — call if the user cancels before the callback arrives."""
        threading.Thread(target=self._server.shutdown, daemon=True).start()
