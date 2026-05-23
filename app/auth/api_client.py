"""ApiClient — authenticated HTTP wrapper that auto-attaches bearer tokens."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import httpx

from auth.auth_manager import AuthManager

log = logging.getLogger(__name__)


class ApiClient:
    """Thin HTTP client that attaches Authorization headers and retries once on 401.

    All network calls in the app should go through this class after the user
    has authenticated.  The client is synchronous — callers should invoke it
    from a background thread (QThread) to avoid blocking the event loop.

    Call ``warmup_async()`` once after authentication to pre-establish the TCP
    connection so the first real request (e.g. loading the raids dropdown)
    doesn't pay the connection-setup cost.
    """

    def __init__(self, auth_manager: AuthManager, base_url: str) -> None:
        self._auth = auth_manager
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Content-Type": "application/json"},
            timeout=httpx.Timeout(30, connect=10),
        )

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: Optional[dict] = None, **kwargs) -> httpx.Response:
        return self._request("POST", path, json=json, **kwargs)

    def warmup_async(self) -> None:
        """GET /auth/me in a daemon thread to validate the token and pre-warm the
        connection pool.  Fire-and-forget — the result is only logged."""
        def _run() -> None:
            try:
                t0 = time.perf_counter()
                resp = self.get("/auth/me")
                ms = (time.perf_counter() - t0) * 1000
                log.info("connection warmup: GET /auth/me status=%d  %.1f ms", resp.status_code, ms)
            except Exception as exc:  # noqa: BLE001
                log.warning("connection warmup failed: %s", exc)

        threading.Thread(target=_run, daemon=True, name="api-warmup").start()

    def close(self) -> None:
        """Release the underlying connection pool.  Call from closeEvent."""
        try:
            self._client.close()
        except Exception:
            pass

    def _headers(self) -> dict:
        token = self._auth.get_access_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _request(
        self, method: str, path: str, _retry: bool = True, **kwargs
    ) -> httpx.Response:
        url = f"{self._base}{path}"
        resp = self._client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401 and _retry:
            if self._auth._refresh_access_token_sync():
                return self._request(method, path, _retry=False, **kwargs)
            self._auth.session_expired.emit()
            resp.raise_for_status()
        resp.raise_for_status()
        return resp
