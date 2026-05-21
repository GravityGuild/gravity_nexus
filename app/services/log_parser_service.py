"""LogParserService — tails an EverQuest log file and dispatches typed events.

Architecture
------------
A ``_TailThread`` (QThread subclass) runs in the background, reading new lines
from the configured log file every 50 ms.  Each raw line is emitted back to the
main thread via ``line_available``.  ``LogParserService`` (singleton QObject on
the main thread) parses each string into a ``LogEvent``, then passes it to
every registered :class:`~services.matchers.base.LogMatcher`.

Log-file discovery
------------------
The service is started with a **directory** path (the EverQuest ``Logs``
folder), not a specific file.  ``LogFileDiscovery`` scans for files matching
``eqlog_{CharName}_project1999.txt`` and picks the one with the most recent
modification time as the currently-active log.

A ``QTimer`` re-runs discovery every 5 seconds.  If a different file has
become the most-recently-modified one (i.e. the player has switched
characters), the current tail is stopped and a new one is started
transparently.  ``active_file_changed`` is emitted with the new character name
each time this happens.

Matcher registry
----------------
Any service can subscribe to specific log events without the parser knowing
about it::

    from services.matchers.base import LogMatcher
    from services.log_parser_service import LogParserService
    import re

    class MyMatcher(LogMatcher):
        something_happened = Signal(str)
        _RE = re.compile(r"You have entered (.+)\\.")

        def process(self, event: LogEvent) -> None:
            m = self._RE.search(event.raw)
            if m:
                self.something_happened.emit(m.group(1))

    matcher = MyMatcher(parent=some_qobject)
    matcher.something_happened.connect(my_slot)
    LogParserService.instance().register_matcher(matcher)

Usage
-----
    svc = registry.get(ILogParserService)
    svc.line_parsed.connect(my_handler)
    svc.raid_dump_detected.connect(my_raid_handler)
    svc.active_file_changed.connect(on_char_change)
    svc.status_changed.connect(on_status)
    svc.start("C:/EverQuest/Logs")
    ...
    svc.stop()
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from models.log_event import LogEvent, LogEventKind
from services.matchers.base import LogMatcher
from services.matchers.guild_chat_matcher import GuildChatMatcher
from services.matchers.raid_dump_matcher import RaidDumpMatcher
from services.matchers.who_list_matcher import WhoListMatcher
from services.matchers.zone_matcher import ZoneMatcher

log = logging.getLogger(__name__)

# ── EQ log line timestamp pattern ─────────────────────────────────────────────
_EQ_TS_RE = re.compile(
    r"^\[([A-Za-z]{3} [A-Za-z]{3} +\d{1,2} \d{2}:\d{2}:\d{2} \d{4})\]\s*(.*)$"
)
_EQ_TS_FMT = "%a %b %d %H:%M:%S %Y"


# ── Log file discovery ─────────────────────────────────────────────────────────

class LogFileDiscovery:
    """Locates and ranks EverQuest log files inside the EQ Logs directory.

    Matches the filename pattern ``eqlog_{CharacterName}_project1999.txt``
    (case-insensitive).  The file with the most recent modification time is
    considered the currently-active one — EverQuest updates the mtime on every
    write, so this reliably identifies which character is logged in.
    """

    _PATTERN: re.Pattern = re.compile(
        r"^eqlog_(.+)_project1999\.txt$", re.IGNORECASE
    )

    @classmethod
    def find_all(cls, directory: Path) -> list[Path]:
        """Return all matching log files in *directory*, newest-mtime first."""
        if not directory.is_dir():
            return []
        files = [
            p for p in directory.glob("eqlog_*_project1999.txt")
            if cls._PATTERN.match(p.name)
        ]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    @classmethod
    def find_active(cls, directory: Path) -> Optional[Path]:
        """Return the most-recently-modified matching log file, or ``None``."""
        files = cls.find_all(directory)
        return files[0] if files else None

    @classmethod
    def character_name(cls, path: Path) -> str:
        """Extract the character name from a matching log filename."""
        m = cls._PATTERN.match(path.name)
        return m.group(1) if m else path.stem


# ── Private tail thread ────────────────────────────────────────────────────────

class _TailThread(QThread):
    """Continuously reads new lines appended to *log_path*.

    Signals
    -------
    line_available(str):
        Emitted for every new raw log line (trailing newline stripped).
    error(str):
        Emitted on ``OSError`` (file not found, permission denied, etc.).
    """

    line_available = Signal(str)
    error = Signal(str)

    _POLL_MS = 50
    _POLL_MS_BACKGROUND = 250

    def __init__(self, log_path: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._path = log_path
        self._running = False
        self._poll_ms = self._POLL_MS  # mutable — updated by set_poll_ms()

    def stop(self) -> None:
        """Request the thread to exit on its next poll iteration."""
        self._running = False

    def set_poll_ms(self, ms: int) -> None:
        """Update the polling interval in milliseconds (takes effect on next sleep)."""
        self._poll_ms = max(10, ms)

    def run(self) -> None:  # executed in the background thread
        self._running = True
        try:
            with open(self._path, encoding="utf-8", errors="replace") as fh:
                fh.seek(0, 2)  # start at end — ignore history
                while self._running:
                    line = fh.readline()
                    if line:
                        self.line_available.emit(line.rstrip("\n"))
                    else:
                        self.msleep(self._poll_ms)
        except OSError as exc:
            self.error.emit(str(exc))


# ── Public service ─────────────────────────────────────────────────────────────

class LogParserService(QObject):
    """Tails an EQ log file and dispatches typed events to registered matchers.

    Instantiate once in the composition root (``main.py``) and register as
    ``ILogParserService``.  Resolve via ``registry.get(ILogParserService)``
    everywhere else.

    Signals
    -------
    line_parsed(LogEvent):
        Fired for every new log line, before matchers are called.
    raid_dump_detected(list[str]):
        Relayed from the built-in ``RaidDumpMatcher`` for convenience.
    active_file_changed(str):
        Fired when the service starts tailing a new file.  Carries the
        character name extracted from the filename.
    status_changed(str):
        Fired when state changes: ``"idle"`` | ``"running"`` | ``"error"``.
    """

    line_parsed = Signal(object)        # LogEvent
    raid_dump_detected = Signal(list)   # list[str]
    who_list_detected = Signal(list)    # list[WhoEntry]
    active_file_changed = Signal(str)   # character name
    zone_changed = Signal(str)          # zone name
    guild_message = Signal(str, str)    # (character, message)
    status_changed = Signal(str)        # "idle" | "running" | "error"

    # How often to check for a more-recently-modified log file (milliseconds)
    _MONITOR_INTERVAL_MS = 5_000
    _MONITOR_INTERVAL_MS_BACKGROUND = 10_000

    def __init__(self) -> None:
        super().__init__()
        self._thread: Optional[_TailThread] = None
        self._matchers: list[LogMatcher] = []
        self._status = "idle"
        self._log_directory: Optional[Path] = None
        self._current_path: Optional[Path] = None

        # Built-in raid-dump matcher
        self._raid_dump_matcher = RaidDumpMatcher(self)
        self._raid_dump_matcher.raid_dump_detected.connect(self.raid_dump_detected)
        self.register_matcher(self._raid_dump_matcher)

        # Built-in zone matcher
        self._zone_matcher = ZoneMatcher(self)
        self._zone_matcher.zone_changed.connect(self.zone_changed)
        self.register_matcher(self._zone_matcher)

        # Built-in guild chat matcher
        self._guild_chat_matcher = GuildChatMatcher(self)
        self._guild_chat_matcher.guild_message.connect(self.guild_message)
        self.register_matcher(self._guild_chat_matcher)

        # Built-in who-list matcher
        self._who_list_matcher = WhoListMatcher(self)
        self._who_list_matcher.who_list_detected.connect(self.who_list_detected)
        self.register_matcher(self._who_list_matcher)

        # Ordered list of built-in matchers exposed to the UI (those with MATCHER_KEY set)
        self._builtin_matchers: list[LogMatcher] = [
            m for m in self._matchers if m.MATCHER_KEY
        ]

        # Directory monitor — runs on the main thread, cheap stat() checks only
        self._dir_monitor = QTimer(self)
        self._dir_monitor.setInterval(self._MONITOR_INTERVAL_MS)
        self._dir_monitor.timeout.connect(self._check_active_file)

    # ── Matcher registry ───────────────────────────────────────────────────────

    def register_matcher(self, matcher: LogMatcher) -> None:
        """Add *matcher* to the registry.  Duplicate registrations are no-ops."""
        if matcher not in self._matchers:
            self._matchers.append(matcher)
            log.debug("Matcher registered: %s", matcher.name)

    def unregister_matcher(self, matcher: LogMatcher) -> None:
        """Remove *matcher* from the registry.  No-op if not registered."""
        try:
            self._matchers.remove(matcher)
            log.debug("Matcher unregistered: %s", matcher.name)
        except ValueError:
            pass

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status == "running"

    @property
    def builtin_matchers(self) -> list[LogMatcher]:
        """Ordered list of built-in matchers that have UI metadata (``MATCHER_KEY`` set)."""
        return list(self._builtin_matchers)

    @property
    def active_character(self) -> str:
        """Character name of the file currently being tailed, or empty string."""
        if self._current_path is None:
            return ""
        return LogFileDiscovery.character_name(self._current_path)

    @property
    def current_zone(self) -> str:
        """Most recently detected zone name, or empty string if unknown."""
        return self._zone_matcher.current_zone

    def start(self, log_directory: str) -> None:
        """Start watching *log_directory* for EQ log files.

        Discovers whichever ``eqlog_*_project1999.txt`` file has the most
        recent modification time and begins tailing it.  A background timer
        re-checks every 5 seconds and switches automatically when a different
        file becomes active (e.g. after a character swap).
        """
        if self.is_running:
            self.stop()

        directory = Path(log_directory)
        if not directory.is_dir():
            log.error("EQ Logs directory not found: %s", log_directory)
            self._set_status("error")
            return

        self._log_directory = directory
        active = LogFileDiscovery.find_active(directory)

        if active is None:
            log.warning(
                "No eqlog_*_project1999.txt files found in: %s", log_directory
            )
            self._set_status("error")
            return

        self._switch_to_file(active)
        self._dir_monitor.start()

    def stop(self) -> None:
        """Stop tailing and shut down the directory monitor."""
        self._dir_monitor.stop()
        self._stop_tail()
        self._log_directory = None
        self._current_path = None
        self._zone_matcher.reset()
        self._set_status("idle")
        log.info("Parser stopped")

    def set_background_mode(self, background: bool) -> None:
        """Throttle (or restore) polling rates when the application is in the background.

        When *background* is ``True`` the log-line poll interval is increased
        from 50 ms → 500 ms and the directory-monitor interval from 5 s → 30 s.
        Passing ``False`` restores the normal foreground rates.
        """
        if background:
            poll_ms = _TailThread._POLL_MS_BACKGROUND
            monitor_ms = self._MONITOR_INTERVAL_MS_BACKGROUND
        else:
            poll_ms = _TailThread._POLL_MS
            monitor_ms = self._MONITOR_INTERVAL_MS

        if self._thread is not None:
            self._thread.set_poll_ms(poll_ms)
        self._dir_monitor.setInterval(monitor_ms)
        log.debug(
            "Parser background mode %s: poll=%dms dir_monitor=%dms",
            "ON" if background else "OFF",
            poll_ms,
            monitor_ms,
        )

    # ── Internals ──────────────────────────────────────────────────────────────

    def _switch_to_file(self, log_path: Path) -> None:
        """Tear down the current tail and start a new one for *log_path*."""
        self._stop_tail()
        self._current_path = log_path
        char = LogFileDiscovery.character_name(log_path)
        log.info("Tailing: %s  (character: %s)", log_path.name, char)

        self._thread = _TailThread(str(log_path), self)
        self._thread.line_available.connect(self._on_line)
        self._thread.error.connect(self._on_error)
        self._thread.finished.connect(lambda: self._set_status("idle"))
        self._thread.start()

        self._set_status("running")
        self.active_file_changed.emit(char)

    def _stop_tail(self) -> None:
        if self._thread:
            self._thread.stop()
            self._thread.wait(2_000)
            self._thread = None

    def _set_status(self, status: str) -> None:
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)

    @Slot()
    def _check_active_file(self) -> None:
        """Switch to a more-recently-modified log file if one has appeared."""
        if self._log_directory is None:
            return
        active = LogFileDiscovery.find_active(self._log_directory)
        if active is None or active == self._current_path:
            return
        log.info(
            "Active log changed: %s → %s",
            self._current_path.name if self._current_path else "none",
            active.name,
        )
        self._switch_to_file(active)

    @Slot(str)
    def _on_line(self, raw: str) -> None:
        event = self._parse(raw)
        self.line_parsed.emit(event)
        for matcher in self._matchers:
            if not matcher.enabled:
                continue
            try:
                matcher.process(event)
            except Exception as exc:  # noqa: BLE001
                log.error("Matcher %s raised: %s", matcher.name, exc)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        log.error("Parser error: %s", message)
        self._set_status("error")

    @staticmethod
    def _parse(raw: str) -> LogEvent:
        """Parse a raw EQ log line into a ``LogEvent``.

        ``kind`` is always ``UNKNOWN`` — categorisation is the
        responsibility of registered ``LogMatcher`` subclasses.
        """
        m = _EQ_TS_RE.match(raw)
        if m:
            try:
                ts = datetime.strptime(m.group(1), _EQ_TS_FMT)
            except ValueError:
                ts = datetime.now()
        else:
            ts = datetime.now()

        return LogEvent(timestamp=ts, raw=raw, kind=LogEventKind.UNKNOWN)
