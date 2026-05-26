"""Service interface definitions (Protocols).

Depend on these rather than on concrete service classes.  The registry maps
each interface to a concrete implementation registered at startup.

Signals are typed as ``Any`` — they are PySide6 class-level descriptors and
cannot be expressed as Protocol members.  Connect to them in code that already
holds the concrete type (e.g. the composition root in ``main.py``).
"""
from __future__ import annotations

from typing import Any, Protocol

from models.settings_model import AppSettings
from services.matchers.base import LogMatcher


class ISettingsService(Protocol):
    """Read/write typed, persisted application settings."""

    @property
    def settings(self) -> AppSettings: ...

    def load(self) -> None: ...

    def save(self) -> None: ...


class ILogParserService(Protocol):
    """Tails an EQ log file and dispatches typed events to registered matchers."""

    # Qt Signals — typed as Any; connect after resolving from registry
    line_parsed: Any         # Signal(LogEvent)
    raid_log_detected: Any  # Signal(list[str])
    active_file_changed: Any # Signal(str) — character name
    zone_changed: Any        # Signal(str) — zone name
    status_changed: Any      # Signal(str)

    @property
    def status(self) -> str: ...

    @property
    def is_running(self) -> bool: ...

    @property
    def builtin_matchers(self) -> list[LogMatcher]: ...

    @property
    def active_character(self) -> str: ...

    @property
    def current_zone(self) -> str: ...

    def start(self, log_directory: str) -> None: ...

    def stop(self) -> None: ...

    def set_background_mode(self, background: bool) -> None: ...

    def register_matcher(self, matcher: LogMatcher) -> None: ...

    def unregister_matcher(self, matcher: LogMatcher) -> None: ...


class IAuthService(Protocol):
    """Authentication state and token access."""

    @property
    def username(self) -> str | None: ...
    def get_access_token(self) -> str | None: ...
    def is_authenticated(self) -> bool: ...


class IUpdateService(Protocol):
    """Manages application update checking and installation."""

    # Qt Signals — typed as Any; connect after resolving from registry
    update_available: Any   # Signal(str, str) — (version, download_url)
    update_downloaded: Any  # Signal(str, str) — (version, installer_path)
    download_progress: Any  # Signal(int) — 0–100
    update_status: Any      # Signal(str)
    update_error: Any       # Signal(str)
    restart_requested: Any  # Signal()

    def start(self) -> None: ...

    def check_for_updates(self) -> None: ...

    def download_update(self, version: str, url: str) -> None: ...

    def install_and_restart(self, installer_path: str) -> None: ...

    def shutdown(self) -> None: ...


class IGravityBotService(Protocol):
    """Manages REST + WebSocket communication with Gravity Bot."""

    # Qt Signals — typed as Any; connect after resolving from registry
    connected_changed: Any      # Signal(bool)
    notification_received: Any  # Signal(BotNotification)
    submit_result: Any          # Signal(bool, str)
    raids_fetched: Any          # Signal(bool, str) — success, json_body

    @property
    def is_connected(self) -> bool: ...

    def connect_bot(self) -> None: ...

    def disconnect_bot(self) -> None: ...

    def fetch_raids(self, date_from: str | None = None, limit: int | None = None) -> None: ...

    def fetch_raids_cached(self, max_age_secs: float = 30.0, date_from: str | None = None, limit: int | None = None) -> None: ...

    def submit_raid_log(self, channel_id: int, full_who_log: str) -> None: ...

    def send_guild_chat(self, character: str, message: str) -> None: ...

    def shutdown(self) -> None: ...

