"""AuthManager — browser OAuth login, token storage, and silent refresh."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from PySide6.QtCore import QMetaObject, QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

log = logging.getLogger(__name__)

KEYRING_SERVICE = "gravity_nexus"
KEYRING_USER_KEY = "__last_user__"


# ── Background threads ─────────────────────────────────────────────────────────

class _TokenExchangeThread(QThread):
    """POSTs auth code to /auth/token and emits the result."""

    exchange_done = Signal(bool, dict, str)  # success, response_data, error_msg

    def __init__(self, base_url: str, code: str, state: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._code = code
        self._state = state

    def run(self) -> None:
        import httpx  # noqa: PLC0415
        try:
            with httpx.Client(timeout=httpx.Timeout(30, connect=10)) as client:
                resp = client.post(
                    f"{self._base_url}/auth/token",
                    json={"code": self._code, "state": self._state},
                )
            resp.raise_for_status()
            self.exchange_done.emit(True, resp.json(), "")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                self.exchange_done.emit(False, {}, "Authentication failed. Please try again.")
            else:
                self.exchange_done.emit(
                    False, {}, f"Server error ({exc.response.status_code}). Please try again."
                )
        except Exception:
            self.exchange_done.emit(
                False, {}, "Cannot reach server. Check the URL and your connection."
            )


class _RefreshThread(QThread):
    """POSTs a refresh token to /auth/refresh and emits the result."""

    refresh_done = Signal(bool, dict, str)  # success, response_data, error_msg

    def __init__(
        self,
        base_url: str,
        refresh_token: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._refresh_token = refresh_token

    def run(self) -> None:
        import httpx  # noqa: PLC0415
        try:
            with httpx.Client(timeout=httpx.Timeout(30, connect=10)) as client:
                resp = client.post(
                    f"{self._base_url}/auth/refresh",
                    json={"refresh_token": self._refresh_token},
                )
            resp.raise_for_status()
            self.refresh_done.emit(True, resp.json(), "")
        except Exception as exc:
            self.refresh_done.emit(False, {}, str(exc))


# ── AuthManager ────────────────────────────────────────────────────────────────

class AuthManager(QObject):
    """Manages browser-based OAuth login, token storage, and proactive refresh."""

    # Public signals
    logged_in = Signal()
    logged_out = Signal()
    session_expired = Signal()
    auth_error = Signal(str)

    # Private signal — hops the callback from the stdlib server thread to the
    # Qt main thread.  Must be declared at class level for Qt's auto-queuing.
    _callback_received = Signal(str, str)   # code, state

    def __init__(self, bot_base_url: str = "", website_base_url: str = "", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._bot_base_url: str = bot_base_url
        if self._bot_base_url.startswith(("localhost", "127.0.0.1")):
            # TODO: Only allow localhost for local development
            self._bot_base_url = "http://" + self._bot_base_url
        elif not self._bot_base_url.startswith(("https://", "http://")):
            self.auth_error.emit("Gravity bot URL must start with https:// or http://")
            return

        self._website_base_url: str = website_base_url
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._username: Optional[str] = None
        self._pending_state: Optional[str] = None
        self._callback_server = None  # CallbackServer | None
        self._pending_threads: list[QThread] = []

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._proactive_refresh)

        self._callback_received.connect(self._handle_auth_callback)

    # ── Public API ─────────────────────────────────────────────────────────────

    def start_browser_login(self) -> None:
        """Generate a state token, start the callback server, and open the browser."""
        from auth.callback_server import CallbackServer  # noqa: PLC0415

        if not self._website_base_url:
            self.auth_error.emit("No site URL configured.")
            return

        if self._website_base_url.startswith(("localhost", "127.0.0.1")):
            # TODO: Only allow localhost for local development
            self._website_base_url = "http://" + self._website_base_url
        elif not self._website_base_url.startswith(("https://", "http://")):
            self.auth_error.emit("Website URL must start with https:// or http://")
            return

        if self._callback_server is not None:
            self._callback_server.stop()

        self._pending_state = secrets.token_hex(16)
        self._callback_server = CallbackServer(on_callback=self._on_callback_received)
        self._callback_server.start()

        url = (
            f"{self._website_base_url.rstrip('/')}/index.php/GravitybotAuthStart"
            f"?state={self._pending_state}"
            f"&redirect_uri={self._callback_server.redirect_uri}"
        )
        log.info("Opening browser for auth: %s", url)
        opened = QDesktopServices.openUrl(QUrl(url))
        if not opened:
            log.warning("QDesktopServices.openUrl failed — URL: %s", url)
            self.auth_error.emit(
                "Could not open browser automatically. "
                "Please open the link manually or click 'Open Browser Again'."
            )

    def try_silent_login(self) -> bool:
        """Attempt to restore a session from a stored refresh token.  Blocking."""
        import keyring  # noqa: PLC0415

        username = keyring.get_password(KEYRING_SERVICE, KEYRING_USER_KEY)
        if not username:
            return False
        token = keyring.get_password(KEYRING_SERVICE, username)
        if not token:
            return False

        self._username = username
        if self._refresh_access_token_sync():
            return True

        # Stored token is no longer valid — clear it
        self._clear_keyring(username)
        self._username = None
        return False

    def get_access_token(self) -> Optional[str]:
        """Return the current access token, refreshing proactively if near expiry."""
        if self._access_token is None:
            return None
        if self._token_expiry is not None:
            remaining = (self._token_expiry - datetime.now(timezone.utc)).total_seconds()
            if remaining < 60:
                self._refresh_access_token_sync()
        return self._access_token

    def is_authenticated(self) -> bool:
        return (
            self._access_token is not None
            and self._token_expiry is not None
            and self._token_expiry > datetime.now(timezone.utc)
        )

    def logout(self) -> None:
        """Invalidate tokens, clear keyring, and emit logged_out."""
        import httpx    # noqa: PLC0415
        import keyring  # noqa: PLC0415

        if self._access_token:
            token = (
                keyring.get_password(KEYRING_SERVICE, self._username)
                if self._username else None
            )
            try:
                with httpx.Client(timeout=httpx.Timeout(5)) as client:
                    client.post(
                        f"{self._bot_base_url.rstrip('/')}/auth/logout",
                        json={"refresh_token": token} if token else {},
                    )
            except Exception:
                pass  # best-effort

        self._refresh_timer.stop()
        if self._callback_server is not None:
            self._callback_server.stop()
            self._callback_server = None

        username = self._username
        self._access_token = None
        self._token_expiry = None
        self._username = None
        self._pending_state = None

        if username:
            self._clear_keyring(username)

        self.logged_out.emit()

    # ── Private — callback flow ────────────────────────────────────────────────

    def _on_callback_received(self, code: Optional[str], state: Optional[str]) -> None:
        """Called from the CallbackServer stdlib thread — emit to hop to main thread."""
        self._callback_received.emit(code or "", state or "")

    @Slot(str, str)
    def _handle_auth_callback(self, code: str, state: str) -> None:
        """Runs on the main thread.  Validates state, then exchanges the code."""
        if not code:
            self.auth_error.emit("No auth code received. Please try again.")
            return
        if state != self._pending_state:
            log.warning(
                "Auth state mismatch — expected=%s received=%s",
                self._pending_state, state,
            )
            self.auth_error.emit(
                "State mismatch — possible security issue. Please try again."
            )
            return

        self._pending_state = None
        self._callback_server = None

        thread = _TokenExchangeThread(self._bot_base_url, code, state, self)
        thread.exchange_done.connect(self._on_exchange_done)
        thread.finished.connect(
            lambda t=thread: self._pending_threads.remove(t)
            if t in self._pending_threads else None
        )
        self._pending_threads.append(thread)
        thread.start()

    @Slot(bool, dict, str)
    def _on_exchange_done(self, success: bool, data: dict, error_msg: str) -> None:
        if not success:
            self.auth_error.emit(error_msg)
            return
        self._store_tokens(data)
        self.logged_in.emit()

    # ── Private — token refresh ────────────────────────────────────────────────

    def _refresh_access_token_sync(self) -> bool:
        """Blocking refresh — safe to call from any thread."""
        import httpx    # noqa: PLC0415
        import keyring  # noqa: PLC0415

        username = self._username or keyring.get_password(KEYRING_SERVICE, KEYRING_USER_KEY)
        token = keyring.get_password(KEYRING_SERVICE, username) if username else None
        if not token or not self._bot_base_url:
            return False

        try:
            with httpx.Client(timeout=httpx.Timeout(30, connect=10)) as client:
                resp = client.post(
                    f"{self._bot_base_url.rstrip('/')}/auth/refresh",
                    json={"refresh_token": token},
                )
            resp.raise_for_status()
            self._store_tokens(resp.json())
            return True
        except Exception as exc:
            log.warning("Token refresh failed: %s", exc)
            return False

    @Slot()
    def _proactive_refresh(self) -> None:
        """Called by QTimer — spawns a thread so the main thread is not blocked."""
        import keyring  # noqa: PLC0415

        username = self._username or keyring.get_password(KEYRING_SERVICE, KEYRING_USER_KEY)
        token = keyring.get_password(KEYRING_SERVICE, username) if username else None
        if not token:
            self.session_expired.emit()
            return

        thread = _RefreshThread(self._bot_base_url, token, self)
        thread.refresh_done.connect(self._on_proactive_refresh_done)
        thread.finished.connect(
            lambda t=thread: self._pending_threads.remove(t)
            if t in self._pending_threads else None
        )
        self._pending_threads.append(thread)
        thread.start()

    @Slot(bool, dict, str)
    def _on_proactive_refresh_done(self, success: bool, data: dict, error_msg: str) -> None:
        if not success:
            log.warning("Proactive token refresh failed: %s", error_msg)
            self.session_expired.emit()
        else:
            self._store_tokens(data)

    # ── Private — token storage ────────────────────────────────────────────────

    def _store_tokens(self, data: dict) -> None:
        """Store tokens from a successful exchange or refresh response.
        Thread-safe — may be called from main thread or a worker thread.
        """
        import jwt as pyjwt  # noqa: PLC0415
        import keyring       # noqa: PLC0415

        self._access_token = data["access_token"]

        try:
            payload = pyjwt.decode(
                data["access_token"], options={"verify_signature": False}
            )
            self._token_expiry = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except Exception as exc:
            log.warning("Could not decode JWT expiry: %s", exc)
            self._token_expiry = None

        if "user" in data:  # present on initial exchange, not on refresh
            self._username = data["user"]["username"]

        if self._username and "refresh_token" in data:
            keyring.set_password(KEYRING_SERVICE, self._username, data["refresh_token"])
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER_KEY, self._username)

        # Schedule timer on the main thread — safe even when called from a worker.
        QMetaObject.invokeMethod(
            self, "_start_refresh_timer", Qt.ConnectionType.QueuedConnection
        )

    @Slot()
    def _start_refresh_timer(self) -> None:
        if self._token_expiry is None:
            return
        remaining = (self._token_expiry - datetime.now(timezone.utc)).total_seconds()
        delay_ms  = max(0, int((remaining - 60) * 1000))
        self._refresh_timer.start(delay_ms)
        log.debug("Refresh timer set: %.0f s", max(0.0, remaining - 60))

    # ── Private — helpers ──────────────────────────────────────────────────────

    def _clear_keyring(self, username: str) -> None:
        import keyring  # noqa: PLC0415
        for key in (username, KEYRING_USER_KEY):
            try:
                keyring.delete_password(KEYRING_SERVICE, key)
            except Exception:
                pass
