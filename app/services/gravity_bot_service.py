"""GravityBotService — REST + WebSocket client for Gravity Bot.

Architecture
------------
REST calls (e.g. raid log submission) run in a temporary ``_RestSubmitThread``
so the main thread is never blocked.

The WebSocket connection is maintained by a long-lived ``_WsThread`` that
reconnects automatically with exponential backoff.  Both threads communicate
back to the main thread exclusively through Qt signals — no explicit UI locking
is required in callsites.

Auth
----
An OAuth access token is obtained from ``AuthManager`` and sent as
``Authorization: Bearer <token>`` on the WebSocket channel.
The token is refreshed automatically on each reconnect attempt.

Usage
-----
    svc = GravityBotService.instance()
    svc.connected_changed.connect(status_bar.set_grav_bot_connected)
    svc.notification_received.connect(on_notification)
    svc.connect_bot()               # reads settings internally
    ...
    svc.submit_raid_log(lines)      # non-blocking REST POST
    ...
    svc.disconnect_bot()
"""
from __future__ import annotations

import json
import logging
import os
import threading
from enum import Enum
from typing import Callable, Optional

import httpx

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from auth.api_client import ApiClient
from auth.auth_manager import AuthManager
from models.bot_notification import BotNotification, KIND_CHARACTER_SET_RESULT, KIND_UNKNOWN

log = logging.getLogger(__name__)


def _to_ws_url(http_url: str) -> str:
    """Convert an http(s) base URL to its ws(s) equivalent."""
    if http_url.startswith("https://"):
        return "wss://" + http_url[8:]
    if http_url.startswith("http://"):
        return "ws://" + http_url[7:]
    if http_url.startswith("localhost") or http_url.startswith("127.0.0.1") or http_url.startswith("0.0.0.0"):
        return "ws://" + http_url
    return http_url  # already ws:// or wss://


# TODO: Move api calls to core service
class HttpRequestType(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


# ── WebSocket thread ───────────────────────────────────────────────────────────

class _WsThread(QThread):
    """Maintains a persistent WebSocket connection to Gravity Bot.

    Reconnects automatically with exponential backoff (1 s → 60 s max).
    Reads GRAVITY_BOT_URL from the environment and fetches a fresh OAuth token
    on each (re)connect attempt so an expired token is never reused.
    """

    connected_changed = Signal(bool)
    notification_received = Signal(object)  # BotNotification

    def __init__(self, get_token: Callable[[], Optional[str]], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._running = False
        self._ws = None
        self._lock = threading.Lock()
        self._get_token = get_token

    def stop(self) -> None:
        """Signal the run loop to exit and immediately close any open socket."""
        self._running = False
        with self._lock:
            if self._ws is not None:
                try:
                    self._ws.close()
                except Exception:  # noqa: BLE001
                    pass

    def send_message(self, payload: dict) -> bool:
        """Send *payload* as a JSON text frame.  Returns ``True`` on success.

        Safe to call from any thread.  If the socket is not connected the
        message is silently dropped and ``False`` is returned.
        """
        with self._lock:
            ws = self._ws
        if ws is None:
            return False
        try:
            ws.send(json.dumps(payload))
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("WS send error: %s", exc)
            return False

    def run(self) -> None:  # noqa: C901
        try:
            from websockets.sync.client import connect as ws_connect
        except ImportError:
            log.error(
                "websockets package not installed — WebSocket connection disabled. "
                "Run: pip install websockets>=12.0"
            )
            return

        self._running = True
        backoff = 1.0

        while self._running:
            bot_url = os.environ.get("GRAVITY_BOT_URL", "https://gravityp99.com")

            token = self._get_token()
            if not token:
                self.msleep(2_000)
                continue

            ws_url = _to_ws_url(bot_url.rstrip("/")) + "/api/ws"

            try:
                ws = ws_connect(
                    ws_url,
                    additional_headers={
                        "Authorization": f"Bearer {token}"
                    },
                    open_timeout=10,
                )
                with self._lock:
                    self._ws = ws

                self.connected_changed.emit(True)
                backoff = 1.0
                log.info("Connected to Gravity Bot WS: %s", ws_url)

                try:
                    while self._running:
                        try:
                            message = ws.recv(timeout=5.0)
                            self._handle_message(message)
                        except TimeoutError:
                            continue  # keepalive tick — check _running
                except Exception as inner_exc:
                    log.warning("WS receive error: %s", inner_exc)
                finally:
                    with self._lock:
                        self._ws = None
                    try:
                        ws.close()
                    except Exception:  # noqa: BLE001
                        pass

            except Exception as exc:
                log.warning("WS connect failed (%s): %s", ws_url, exc)

            if self._running:
                self.connected_changed.emit(False)
                self.msleep(min(int(backoff * 1_000), 60_000))
                backoff = min(backoff * 2, 60.0)

        self.connected_changed.emit(False)

    def _handle_message(self, raw: str | bytes) -> None:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            if "kind" in data:
                # Legacy kind/payload envelope
                kind = data.get("kind", KIND_UNKNOWN)
                payload = data.get("payload", {})
            else:
                # Flat type-keyed messages (e.g. character_set_result)
                kind = data.get("type", KIND_UNKNOWN)
                payload = {k: v for k, v in data.items() if k != "type"}
            self.notification_received.emit(BotNotification(kind=kind, payload=payload))
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to parse bot message: %s | raw=%r", exc, raw)


# ── REST submit thread ─────────────────────────────────────────────────────────

class _RestSubmitThread(QThread):
    """One-shot thread: makes a single REST request through the shared ApiClient."""

    submit_done = Signal(bool, str)  # success, body

    def __init__(
        self,
        api: ApiClient,
        request_type: HttpRequestType,
        request_url: str,
        request_body: dict | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._request_type = request_type
        self._request_url = request_url
        self._request_body = request_body
        self._headers = headers or {}
        self._params = params

    def run(self) -> None:
        import time  # noqa: PLC0415
        try:
            t0 = time.perf_counter()
            if self._request_type == HttpRequestType.POST:
                resp = self._api.post(self._request_url, json=self._request_body, headers=self._headers)
            elif self._request_type == HttpRequestType.GET:
                resp = self._api.get(self._request_url, params=self._params)
            else:
                raise ValueError(f"Unhandled request type: {self._request_type}")
            http_ms = (time.perf_counter() - t0) * 1000
            log.info(
                "REST %s %s: status=%d  body=%d bytes  http=%.1f ms",
                self._request_type.value,
                self._request_url,
                resp.status_code,
                len(resp.text),
                http_ms,
            )
            t1 = time.perf_counter()
            self.submit_done.emit(True, resp.text)
            log.debug("submit_done signal queued in %.2f ms", (time.perf_counter() - t1) * 1000)
        except httpx.HTTPStatusError as exc:
            log.warning(
                "REST %s %s: status=%d",
                self._request_type.value, self._request_url, exc.response.status_code,
            )
            self.submit_done.emit(False, exc.response.text)
        except Exception as exc:  # noqa: BLE001
            log.error("REST error: %s", exc)
            self.submit_done.emit(False, str(exc)[:300])


# ── Public service ─────────────────────────────────────────────────────────────

class GravityBotService(QObject):
    """Manages REST + WebSocket communication with Gravity Bot.

    Instantiate once in the composition root (``main.py``) and register as
    ``IGravityBotService``.  Resolve via ``registry.get(IGravityBotService)``
    everywhere else.

    Signals
    -------
    connected_changed(bool):
        ``True`` on WebSocket handshake, ``False`` on disconnect or error.
    notification_received(BotNotification):
        Emitted for every push frame received from the bot.
    submit_result(bool, str):
        Emitted after a raid log REST submission.
        ``(True, body)`` on HTTP 2xx, ``(False, error)`` otherwise.
    """

    connected_changed = Signal(bool)
    notification_received = Signal(object)   # BotNotification
    submit_result = Signal(bool, str)
    raids_fetched = Signal(bool, str)        # success, json_body
    character_fetched = Signal(bool, str)    # success, json_body

    _CHARACTER_SET_MAX_RETRIES = 3
    _CHARACTER_SET_RETRY_MS = 2_000
    # No log activity for this long → assume force-quit or crashed client
    _INACTIVITY_TIMEOUT_MS = 1_800_000  # 30 minutes

    _WHO_DEDUP_WINDOW: float = 30.0    # seconds — suppress identical who_result within this window
    _WHO_REFRESH_WINDOW: float = 300.0  # seconds — force re-send after this long for last-seen refresh

    _WHO_DEDUP_WINDOW: float = 30.0    # seconds — suppress identical who_result within this window
    _WHO_REFRESH_WINDOW: float = 300.0 # seconds — force re-send after this long for last-seen refresh

    # Character state values sent in the ``state`` field of ``character_set``
    STATE_IN_GAME = "IN_GAME"
    STATE_CHARACTER_SELECT = "CHARACTER_SELECT"
    STATE_AVAILABLE = "AVAILABLE"
    NO_CHARACTER = "NO_CHARACTER"

    def __init__(self, auth_manager: AuthManager, api_client: ApiClient) -> None:
        super().__init__()
        self._auth_manager = auth_manager
        self._api = api_client
        self._ws_thread: Optional[_WsThread] = None
        self._submit_threads: list[_RestSubmitThread] = []
        self._connected = False
        self._seq: int = 0  # monotonically increasing per session; reset on reconnect
        self._current_character: Optional[str] = None
        self._current_state: str = self.STATE_IN_GAME
        self._character_set_retries: int = 0
        self._character_set_retry_timer = QTimer(self)
        self._character_set_retry_timer.setSingleShot(True)
        self._character_set_retry_timer.timeout.connect(self._retry_character_set)
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(self._INACTIVITY_TIMEOUT_MS)
        self._inactivity_timer.timeout.connect(self._on_inactivity_timeout)
        self._raids_cache: Optional[tuple[bool, str]] = None
        self._raids_cache_ts: float = 0.0
        self._raids_fetch_in_flight: bool = False
        self._scan_in_progress: bool = False
        self._last_who_hash: str | None = None
        self._last_who_sent: float = 0.0
        self.connected_changed.connect(self._on_connected_changed)
        self.notification_received.connect(self._on_notification)
        self.raids_fetched.connect(self._cache_raids_result)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Public API ─────────────────────────────────────────────────────────────

    def connect_bot(self) -> None:
        """Start the WebSocket connection.  Reads settings via the registry."""
        from core.registry import registry
        from services.protocols import ISettingsService

        settings = registry.get(ISettingsService).settings.gravity_bot

        if not settings.ws_enabled:
            log.info("WebSocket disabled in settings — skipping connect")
            return

        if not self._auth_manager.is_authenticated():
            log.warning("Gravity Bot: not authenticated, skipping connect")
            return

        if self._ws_thread and self._ws_thread.isRunning():
            log.debug("WebSocket thread already running")
            return

        self._ws_thread = _WsThread(self._auth_manager.get_access_token, self)
        self._ws_thread.connected_changed.connect(self.connected_changed)
        self._ws_thread.notification_received.connect(self.notification_received)
        self._ws_thread.start()
        log.info("WebSocket thread started")

    def disconnect_bot(self) -> None:
        """Stop the WebSocket connection and wait for the thread to exit."""
        if self._ws_thread:
            self._ws_thread.stop()
            self._ws_thread.wait(3_000)
            self._ws_thread = None
        log.info("Gravity Bot disconnected")

    def fetch_raids(self, date_from: str | None = None, limit: int | None = None) -> None:
        """Non-blocking GET of /api/raids from the bot."""
        import time  # noqa: PLC0415
        t0 = time.perf_counter()
        self._raids_cache = None  # invalidate stale cache before a fresh request
        self._raids_fetch_in_flight = True
        params: dict = {}
        if date_from is not None:
            params["date_from"] = date_from
        if limit is not None:
            params["limit"] = limit
        thread = _RestSubmitThread(
            api=self._api,
            request_type=HttpRequestType.GET,
            request_url="/api/v1/raids",
            params=params or None,
            parent=self,
        )
        thread.submit_done.connect(self.raids_fetched)
        thread.finished.connect(lambda: self._submit_threads.remove(thread))
        self._submit_threads.append(thread)
        thread.start()
        log.debug("fetch_raids: thread started in %.2f ms", (time.perf_counter() - t0) * 1000)

    def fetch_raids_cached(self, max_age_secs: float = 30.0, date_from: str | None = None, limit: int | None = None) -> None:
        """Emit raids_fetched from cache if fresh; otherwise call fetch_raids().

        Use this from the overlay so a pre-triggered fetch_raids() call from
        main_window populates the dropdown without a second network round-trip.
        """
        import time  # noqa: PLC0415

        if self._raids_cache is not None and (time.monotonic() - self._raids_cache_ts) < max_age_secs:
            cached = self._raids_cache
            log.debug("fetch_raids_cached: serving from cache (age=%.1f s)", time.monotonic() - self._raids_cache_ts)
            QTimer.singleShot(0, lambda: self.raids_fetched.emit(cached[0], cached[1]))
            return
        # Cache is empty (in-flight) or stale — if a fetch is already running,
        # the raids_fetched signal will fire naturally; if not, start one.
        if self._raids_fetch_in_flight:
            log.debug("fetch_raids_cached: fetch already in flight, waiting for signal")
        else:
            self.fetch_raids(date_from=date_from, limit=limit)

    def fetch_character(self, name: str) -> None:
        """Non-blocking GET of /api/v1/characters for a single character by name."""
        thread = _RestSubmitThread(
            api=self._api,
            request_type=HttpRequestType.GET,
            request_url="/api/v1/characters",
            params={"name": name, "limit": 1, "include": "alts,dkp,items"},
            parent=self,
        )
        thread.submit_done.connect(self.character_fetched)
        thread.finished.connect(lambda: self._submit_threads.remove(thread))
        self._submit_threads.append(thread)
        thread.start()

    def submit_raid_log(self, channel_id: int, full_who_log: str) -> None:
        """Non-blocking POST of the who-log to the bot's raid attendance endpoint."""
        thread = _RestSubmitThread(
            api=self._api,
            request_type=HttpRequestType.POST,
            request_url=f"/api/v1/raids/{channel_id}/attendance",
            request_body={"raidlog": full_who_log},
            headers={"X-Source": "gravitynexus"},
            parent=self,
        )
        thread.submit_done.connect(self.submit_result)
        thread.finished.connect(lambda: self._submit_threads.remove(thread))
        self._submit_threads.append(thread)
        thread.start()

    @Slot(str)
    def set_character(self, character: str, state: str = STATE_IN_GAME) -> None:
        """Identify the active character and notify the bot over the WebSocket.

        Pass an empty string or ``NO_CHARACTER`` to declare no active character.
        *state* is one of ``IN_GAME``, ``CHARACTER_SELECT``, or ``AVAILABLE`` and
        is ignored when *character* resolves to ``NO_CHARACTER``.
        """
        if not character:
            character = self.NO_CHARACTER
        self._character_set_retry_timer.stop()
        self._character_set_retries = 0
        self._current_character = character
        self._current_state = state if character != self.NO_CHARACTER else self.STATE_AVAILABLE
        log.info("set_character: Character=%s - State=%s", self._current_character, self._current_state)

        if character != self.NO_CHARACTER:
            self._inactivity_timer.start()
        else:
            self._inactivity_timer.stop()
        self._send_character_set()

    def update_character_state(self, state: str) -> None:
        """Send a state-only update for the current character.

        Silently ignored if no character has been set or the character is
        ``NO_CHARACTER``.  Use this to transition between ``IN_GAME``,
        ``CHARACTER_SELECT``, and ``AVAILABLE`` without re-identifying.
        """
        log.info("update_character_state: Character=%s - State=%s", self._current_character, state)
        if not self._current_character or self._current_character == self.NO_CHARACTER:
            return

        self._current_state = state
        if state == self.STATE_CHARACTER_SELECT:
            self._inactivity_timer.stop()
        self._send_character_set()

    @Slot()
    def notify_log_activity(self) -> None:
        """Reset the inactivity timer.  Call this on every parsed log line."""
        if self._current_character:
            self._inactivity_timer.start()

    def send_guild_chat(self, character: str, message: str) -> None:
        """Forward a parsed guild-chat message to the bot over the WebSocket.

        Sends ``{"type": "guild_chat", "seq": <n>, "character": "<name>", "message": "<text>"}``
        if the WebSocket is currently connected.  Silently dropped otherwise.

        ``seq`` is a monotonically increasing integer scoped to the current
        WebSocket session.  It resets to 0 on each new connection and is
        useful for reconnect detection, replay detection, dropped-message
        diagnostics, and ordering within the client stream.
        """
        from core.registry import registry
        from services.protocols import ISettingsService

        if not registry.get(ISettingsService).settings.gravity_bot.send_guild_chat:
            return
        if not self._connected or self._ws_thread is None:
            return
        self._seq += 1
        payload = {
            "type": "guild_chat",
            "seq": self._seq,
            "character": character,
            "message": message,
        }
        sent = self._ws_thread.send_message(payload)
        if sent:
            log.debug("Guild chat forwarded to bot (seq=%d): [%s] %s", self._seq, character, message)

    def send_who_result(self, entries: list) -> None:
        """Forward a /who result to the bot over the WebSocket.

        Sends ``{"type": "who_result", "characters": [...]}`` with the names
        from *entries*.  Identical results are suppressed within
        ``_WHO_DEDUP_WINDOW`` seconds; after ``_WHO_REFRESH_WINDOW`` the same
        list is re-sent so the bot can update last-seen timestamps.
        """
        import time

        from core.registry import registry
        from services.protocols import ISettingsService

        if not registry.get(ISettingsService).settings.gravity_bot.send_who_result:
            return
        if not self._connected or self._ws_thread is None:
            return

        names = sorted(e.name for e in entries)
        current_hash = ",".join(names)
        now = time.monotonic()
        elapsed = now - self._last_who_sent

        if current_hash == self._last_who_hash and elapsed < self._WHO_REFRESH_WINDOW:
            return  # identical and not yet due for a last-seen refresh

        self._last_who_hash = current_hash
        self._last_who_sent = now
        payload = {"type": "who_result", "characters": names}
        sent = self._ws_thread.send_message(payload)
        if sent:
            log.debug("who_result sent: %d characters", len(names))

    def shutdown(self) -> None:
        """Gracefully stop all background threads.  Call from MainWindow.closeEvent."""
        self.disconnect_bot()
        for t in list(self._submit_threads):
            t.wait(2_000)

    # ── Private ────────────────────────────────────────────────────────────────

    @Slot(bool, str)
    def _cache_raids_result(self, success: bool, body: str) -> None:
        import time  # noqa: PLC0415
        self._raids_cache = (success, body)
        self._raids_cache_ts = time.monotonic()
        self._raids_fetch_in_flight = False

    @Slot()
    def begin_scan(self) -> None:
        """Suppress WebSocket character_set sends while dbg.txt history is replayed."""
        self._scan_in_progress = True
        log.debug("bot scan-suppression: ON")

    @Slot()
    def end_scan(self) -> None:
        """Re-enable WebSocket sends and flush the final character state."""
        self._scan_in_progress = False
        log.debug("bot scan-suppression: OFF")
        self._send_character_set()

    def _send_character_set(self) -> None:
        """Build and send the current character_set message over the WebSocket."""
        if self._scan_in_progress:
            return
        if not self._connected or self._ws_thread is None:
            return
        payload: dict = {"type": "character_set", "character": self._current_character}
        if self._current_character != self.NO_CHARACTER:
            payload["state"] = self._current_state
        self._ws_thread.send_message(payload)
        log.debug("character_set sent: %s (state=%s)", self._current_character, self._current_state)

    @Slot(bool)
    def _on_connected_changed(self, connected: bool) -> None:
        was_connected = self._connected
        self._connected = connected
        if connected and not was_connected:
            self._seq = 0  # reset sequence counter for the new session
            if self._current_character is not None:
                self._send_character_set()

    @Slot(object)
    def _on_notification(self, notif: BotNotification) -> None:
        if notif.kind != KIND_CHARACTER_SET_RESULT:
            return
        if notif.payload.get("success"):
            self._character_set_retries = 0
            log.debug(
                "character_set confirmed: character=%s guild_member=%s state=%s",
                notif.payload.get("character"),
                notif.payload.get("is_guild_member"),
                notif.payload.get("state"),
            )
        else:
            reason = notif.payload.get("reason", "unknown")
            if self._character_set_retries < self._CHARACTER_SET_MAX_RETRIES:
                self._character_set_retries += 1
                log.warning(
                    "character_set failed (reason=%s), retry %d/%d in %d ms",
                    reason, self._character_set_retries, self._CHARACTER_SET_MAX_RETRIES,
                    self._CHARACTER_SET_RETRY_MS,
                )
                self._character_set_retry_timer.start(self._CHARACTER_SET_RETRY_MS)
            else:
                log.warning(
                    "character_set failed (reason=%s) after %d retries, giving up",
                    reason, self._CHARACTER_SET_MAX_RETRIES,
                )
                self._character_set_retries = 0

    @Slot()
    def _retry_character_set(self) -> None:
        if self._current_character is not None:
            self._send_character_set()
            log.debug(
                "character_set retry %d/%d: %s",
                self._character_set_retries, self._CHARACTER_SET_MAX_RETRIES, self._current_character,
            )

    @Slot()
    def _on_inactivity_timeout(self) -> None:
        log.info(
            "No log activity for %d s — clearing character (was: %s)",
            self._INACTIVITY_TIMEOUT_MS // 1000,
            self._current_character,
        )
        self.set_character("")






