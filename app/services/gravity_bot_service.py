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
A plain bearer token is stored in ``GravityBotSettings.auth_token`` and sent as
``Authorization: Bearer <token>`` on both channels.
OAuth is planned for a future release; only the header construction in the two
thread classes will need updating.

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
import threading
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot

from models.bot_notification import BotNotification, KIND_UNKNOWN

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


# ── WebSocket thread ───────────────────────────────────────────────────────────

class _WsThread(QThread):
    """Maintains a persistent WebSocket connection to Gravity Bot.

    Reconnects automatically with exponential backoff (1 s → 60 s max).
    Reads bot_url and auth_token from SettingsService on each (re)connect
    attempt so settings changes take effect without restarting.
    """

    connected_changed = Signal(bool)
    notification_received = Signal(object)  # BotNotification

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._running = False
        self._ws = None
        self._lock = threading.Lock()

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

        from core.registry import registry
        from services.protocols import ISettingsService

        self._running = True
        backoff = 1.0

        while self._running:
            settings = registry.get(ISettingsService).settings.gravity_bot

            if not settings.bot_url or not settings.auth_token:
                self.msleep(2_000)
                continue

            ws_url = _to_ws_url(settings.bot_url.rstrip("/")) + "/ws"

            try:
                ws = ws_connect(
                    ws_url,
                    additional_headers={
                        "X-API-Key": f"{settings.auth_token}"
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
            notif = BotNotification(
                kind=data.get("kind", KIND_UNKNOWN),
                payload=data.get("payload", {}),
            )
            self.notification_received.emit(notif)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to parse bot message: %s | raw=%r", exc, raw)


# ── REST submit thread ─────────────────────────────────────────────────────────

class _RestSubmitThread(QThread):
    """One-shot thread: POSTs a raid log to the bot REST API then exits."""

    submit_done = Signal(bool, str)  # success, message

    def __init__(
        self,
        bot_url: str,
        token: str,
        lines: list[str],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._bot_url = bot_url.rstrip("/")
        self._token = token
        self._lines = lines

    def run(self) -> None:
        try:
            import httpx  # noqa: PLC0415

            endpoint = f"{self._bot_url}/api/raid-logs"
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    endpoint,
                    json={"lines": self._lines},
                    headers={"Authorization": f"Bearer {self._token}"},
                )
            success = resp.is_success
            msg = resp.text[:300]
            log.info("Raid log submit: status=%d", resp.status_code)
            self.submit_done.emit(success, msg)
        except Exception as exc:  # noqa: BLE001
            log.error("Raid log submit error: %s", exc)
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

    def __init__(self) -> None:
        super().__init__()
        self._ws_thread: Optional[_WsThread] = None
        self._submit_threads: list[_RestSubmitThread] = []
        self._connected = False
        self._seq: int = 0  # monotonically increasing per session; reset on reconnect
        self.connected_changed.connect(self._on_connected_changed)

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

        if not settings.bot_url or not settings.auth_token:
            log.warning("Gravity Bot URL or token not configured")
            return

        if self._ws_thread and self._ws_thread.isRunning():
            log.debug("WebSocket thread already running")
            return

        self._ws_thread = _WsThread(self)
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

    def submit_raid_log(self, lines: list[str]) -> None:
        """Non-blocking POST of *lines* to the bot's raid-log endpoint."""
        from core.registry import registry
        from services.protocols import ISettingsService

        settings = registry.get(ISettingsService).settings.gravity_bot

        if not settings.bot_url or not settings.auth_token:
            self.submit_result.emit(False, "Gravity Bot is not configured")
            return

        thread = _RestSubmitThread(settings.bot_url, settings.auth_token, lines, self)
        thread.submit_done.connect(self.submit_result)
        thread.finished.connect(lambda: self._submit_threads.remove(thread))
        self._submit_threads.append(thread)
        thread.start()

    def send_guild_chat(self, character: str, message: str) -> None:
        """Forward a parsed guild-chat message to the bot over the WebSocket.

        Sends ``{"type": "guild_chat", "seq": <n>, "character": "<name>", "message": "<text>"}``
        if the WebSocket is currently connected.  Silently dropped otherwise.

        ``seq`` is a monotonically increasing integer scoped to the current
        WebSocket session.  It resets to 0 on each new connection and is
        useful for reconnect detection, replay detection, dropped-message
        diagnostics, and ordering within the client stream.
        """
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

    def shutdown(self) -> None:
        """Gracefully stop all background threads.  Call from MainWindow.closeEvent."""
        self.disconnect_bot()
        for t in list(self._submit_threads):
            t.wait(2_000)

    # ── Private ────────────────────────────────────────────────────────────────

    @Slot(bool)
    def _on_connected_changed(self, connected: bool) -> None:
        if connected and not self._connected:
            self._seq = 0  # reset sequence counter for the new session
        self._connected = connected






