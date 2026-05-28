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
    svc.raid_log_detected.connect(my_raid_handler)
    svc.active_file_changed.connect(on_char_change)
    svc.status_changed.connect(on_status)
    svc.start("C:/EverQuest/Logs")
    ...
    svc.stop()
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from models.log_event import LogEvent, LogEventKind, LogSource
from services.matchers.base import LogMatcher
from services.matchers.camp_matcher import CampMatcher
from services.matchers.dbg.camp_dbg_matcher import CampDbgMatcher
from services.matchers.dbg.char_select_dbg_matcher import CharSelectDbgMatcher
from services.matchers.dbg.disconnect_dbg_matcher import DisconnectDbgMatcher
from services.matchers.dbg.enter_game_dbg_matcher import EnterGameDbgMatcher
from services.matchers.dbg.startup_dbg_matcher import StartupDbgMatcher
from services.matchers.dbg.zone_dbg_matcher import ZoneDbgMatcher
from services.matchers.guild_chat_matcher import GuildChatMatcher
from services.matchers.raid_log_matcher import RaidLogMatcher
from services.matchers.who_list_matcher import WhoListMatcher
from services.matchers.zone_matcher import ZoneMatcher

log = logging.getLogger(__name__)

# How many bytes from the end of dbg.txt to scan synchronously at startup.
# Covers weeks of state transitions for a typical player.
_DBG_SCAN_BYTES = 100_000

# ── EQ log line timestamp pattern ─────────────────────────────────────────────
_EQ_TS_RE = re.compile(
    r"^\[([A-Za-z]{3} [A-Za-z]{3} +\d{1,2} \d{2}:\d{2}:\d{2} \d{4})\]\s*(.*)$"
)
_EQ_TS_FMT = "%a %b %d %H:%M:%S %Y"

# ── dbg.txt line timestamp pattern ────────────────────────────────────────────
# Format: "2026-05-27 07:36:42\tMessage body"
_DBG_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\t(.*)$")
_DBG_TS_FMT = "%Y-%m-%d %H:%M:%S"


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

    def __init__(
        self,
        log_path: str,
        parent: Optional[QObject] = None,
        *,
        seek_to_end: bool = True,
        start_offset: int = 0,
    ) -> None:
        super().__init__(parent)
        self._path = log_path
        self._running = False
        self._poll_ms = self._POLL_MS  # mutable — updated by set_poll_ms()
        self._seek_to_end = seek_to_end
        self._start_offset = start_offset

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
                if self._start_offset > 0:
                    fh.seek(self._start_offset)
                elif self._seek_to_end:
                    fh.seek(0, 2)
                while self._running:
                    line = fh.readline()
                    if line:
                        self.line_available.emit(line.rstrip("\n"))
                    else:
                        try:
                            if os.path.getsize(self._path) < fh.tell():
                                fh.seek(0)
                        except OSError:
                            pass
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
    raid_log_detected(list[str]):
        Relayed from the built-in ``RaidLogMatcher`` for convenience.
    active_file_changed(str):
        Fired when the service starts tailing a new file.  Carries the
        character name extracted from the filename.
    status_changed(str):
        Fired when state changes: ``"idle"`` | ``"running"`` | ``"error"``.
    """

    line_parsed = Signal(object)        # LogEvent
    raid_log_detected = Signal(list)   # list[str]
    who_list_detected = Signal(list, int)  # list[WhoEntry] (filtered), int (total parsed)
    active_file_changed = Signal(str)   # character name

    game_started = Signal()              # EQ process launched (dbg.txt startup line)
    startup_scan_started = Signal()     # dbg.txt historical scan about to begin
    startup_scan_complete = Signal()    # dbg.txt historical scan finished; live tail about to begin
    character_offline = Signal()        # character camped or inactivity timeout
    character_at_select = Signal()      # character arrived at character select screen
    character_entered_game = Signal()   # character entered a game zone

    zone_changed = Signal(str)          # zone name (EQ log)
    zone_connected = Signal(str, str)   # (character, zone) from dgb.txt — fires before zone_changed
    guild_message = Signal(str, str)    # (character, message)
    status_changed = Signal(str)        # "idle" | "running" | "error"

    # How often to check for a more-recently-modified log file (milliseconds)
    _MONITOR_INTERVAL_MS = 5_000
    _MONITOR_INTERVAL_MS_BACKGROUND = 10_000

    def __init__(self) -> None:
        super().__init__()
        self._thread: Optional[_TailThread] = None
        self._dbg_thread: Optional[_TailThread] = None
        self._matchers: list[LogMatcher] = []
        self._status = "idle"
        self._log_directory: Optional[Path] = None
        self._current_path: Optional[Path] = None

        # Built-in raid-log matcher
        self._raid_log_matcher = RaidLogMatcher(self)
        self._raid_log_matcher.raid_log_detected.connect(self.raid_log_detected)
        self.active_file_changed.connect(self._raid_log_matcher.set_active_character)
        self.register_matcher(self._raid_log_matcher)

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

        # Built-in camp matcher (EQ log countdown — no longer drives state directly;
        # camp_complete from dgb.txt is the definitive signal)
        self._camp_matcher = CampMatcher(self)
        self.register_matcher(self._camp_matcher)

        # dgb.txt matchers — character state transitions
        self._camp_dbg_matcher = CampDbgMatcher(self)
        # camp_complete fires after /camp or /camp desktop finishes.  For /camp,
        # CharSelectDbgMatcher will also fire character_at_select moments later
        # (harmless duplicate).  For /camp desktop, DisconnectDbgMatcher follows.
        self._camp_dbg_matcher.camp_complete.connect(self.character_at_select)
        self.register_matcher(self._camp_dbg_matcher)

        self._zone_dbg_matcher = ZoneDbgMatcher(self)
        self._zone_dbg_matcher.zone_connected.connect(self.zone_connected)
        self.register_matcher(self._zone_dbg_matcher)

        self._char_select_dbg_matcher = CharSelectDbgMatcher(self)
        self._char_select_dbg_matcher.character_at_select.connect(self.character_at_select)
        self.register_matcher(self._char_select_dbg_matcher)

        self._enter_game_dbg_matcher = EnterGameDbgMatcher(self)
        self._enter_game_dbg_matcher.character_entered_game.connect(self.character_entered_game)
        self.register_matcher(self._enter_game_dbg_matcher)

        self._disconnect_dbg_matcher = DisconnectDbgMatcher(self)
        self._disconnect_dbg_matcher.character_offline.connect(self.character_offline)
        self.register_matcher(self._disconnect_dbg_matcher)

        self._startup_dbg_matcher = StartupDbgMatcher(self)
        self._startup_dbg_matcher.game_started.connect(self.game_started)
        self.register_matcher(self._startup_dbg_matcher)

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
    def active_log_filename(self) -> str:
        """Filename (not full path) of the log being tailed, or empty string."""
        if self._current_path is None:
            return ""
        return self._current_path.name

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

        self.startup_scan_started.emit()
        self._switch_to_file(active)
        dgb = directory / "dbg.txt"
        offset = self._scan_recent_dbg(dgb) if dgb.exists() else 0
        self._start_dbg_tail(directory, offset)
        self._dir_monitor.start()
        self.startup_scan_complete.emit()

    def stop(self) -> None:
        """Stop tailing and shut down the directory monitor."""
        self._dir_monitor.stop()
        self._stop_tail()
        self._stop_dbg_tail()
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
        if self._dbg_thread is not None:
            self._dbg_thread.set_poll_ms(poll_ms)
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
            self._thread.finished.disconnect()
            self._thread.stop()
            self._thread.wait(2_000)
            self._thread = None

    def _scan_recent_dbg(self, dbg_path: Path) -> int:
        """Synchronously process recent dbg.txt history to establish current state.

        Reads the last ``_DBG_SCAN_BYTES`` bytes of *dbg_path*, dispatches each
        line through the normal matcher pipeline, and returns the file position
        at end of scan so the async tail can start exactly there.

        Because all signal connections are direct (same-thread) when ``start()``
        is called, slots in GravityBotService run synchronously here — state is
        correct before ``start()`` returns.
        """
        end_pos = 0
        try:
            size = dbg_path.stat().st_size
            with open(dbg_path, encoding="utf-8", errors="replace") as fh:
                seek_to = max(0, size - _DBG_SCAN_BYTES)
                fh.seek(seek_to)
                if seek_to > 0:
                    fh.readline()  # discard partial line at the seek boundary
                for line in fh:
                    self._dispatch(self._parse_dbg(line.rstrip("\n")))
                end_pos = fh.tell()
            log.debug("dbg.txt scan complete: read from offset=%d, end_pos=%d", seek_to, end_pos)
        except OSError as exc:
            log.warning("dbg.txt scan failed: %s", exc)
        return end_pos

    def _start_dbg_tail(self, directory: Path, offset: int = 0) -> None:
        """Start tailing dbg.txt in *directory* from *offset*, if the file exists."""
        self._stop_dbg_tail()
        dgb = directory / "dbg.txt"
        if not dgb.exists():
            log.debug("dbg.txt not found in %s — dbg tail not started", directory)
            return
        self._dbg_thread = _TailThread(str(dgb), self, start_offset=offset)
        self._dbg_thread.line_available.connect(self._on_dbg_line)
        self._dbg_thread.error.connect(self._on_error)
        self._dbg_thread.start()
        log.info("Tailing dbg.txt from offset=%d", offset)

    def _stop_dbg_tail(self) -> None:
        if self._dbg_thread:
            self._dbg_thread.stop()
            self._dbg_thread.wait(2_000)
            self._dbg_thread = None

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
        if active is not None and active != self._current_path:
            log.info(
                "Active log changed: %s → %s",
                self._current_path.name if self._current_path else "none",
                active.name,
            )
            self._switch_to_file(active)
            return  # _switch_to_file resets _dgb_offline_emitted

    def _dispatch(self, event: LogEvent) -> None:
        """Emit *event* to all matchers subscribed to its source."""
        self.line_parsed.emit(event)
        for matcher in self._matchers:
            if not matcher.enabled:
                continue
            if event.source not in matcher.SOURCES:
                continue
            try:
                matcher.process(event)
            except Exception as exc:  # noqa: BLE001
                log.error("Matcher %s raised: %s", matcher.name, exc)

    @Slot(str)
    def _on_line(self, raw: str) -> None:
        self._dispatch(self._parse(raw))

    @Slot(str)
    def _on_dbg_line(self, raw: str) -> None:
        self._dispatch(self._parse_dbg(raw))

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
            message = m.group(2)
        else:
            ts = datetime.now()
            message = raw

        return LogEvent(timestamp=ts, raw=raw, message=message, kind=LogEventKind.UNKNOWN,
                        source=LogSource.EQ_LOG)

    @staticmethod
    def _parse_dbg(raw: str) -> LogEvent:
        """Parse a raw dgb.txt line into a ``LogEvent``.

        dgb.txt format: ``YYYY-MM-DD HH:MM:SS<TAB>message body``
        """
        m = _DBG_TS_RE.match(raw)
        if m:
            try:
                ts = datetime.strptime(m.group(1), _DBG_TS_FMT)
            except ValueError:
                ts = datetime.now()
            message = m.group(2)
        else:
            ts = datetime.now()
            message = raw

        return LogEvent(timestamp=ts, raw=raw, message=message, kind=LogEventKind.UNKNOWN,
                        source=LogSource.DBG_TXT)
