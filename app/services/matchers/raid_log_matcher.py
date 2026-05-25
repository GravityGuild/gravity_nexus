"""RaidLogMatcher — detects and accumulates EQ raid attendance log lines.

This is the first concrete LogMatcher and also serves as the reference
implementation of the accumulator pattern for multi-line log sequences.

To activate, replace ``_PATTERN`` with the real EverQuest regex once the exact
log format is confirmed.  No other code needs to change.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from models.log_event import LogEvent
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# ── Compiled patterns ─────────────────────────────────────────────────────────

# Start-of-log marker (body after EQ timestamp is stripped)
# When user sends /t nexusraidlog or /t nexusraidlogs start looking for logs so they can make a social in game to trigger them
_TELL_START_TRIGGER_RE: re.Pattern = re.compile(r"^nexusraidlogs? is not online at this time\.$")

_WHO_START_RE: re.Pattern = re.compile(r"^Players on EverQuest:\s*$")

# End-of-log summary e.g. "There are 19 players in East Commonlands."
_WHO_END_RE: re.Pattern = re.compile(r"^There (?:are|is) \d+ players? in .+\.\s*$")

# Individual player line:
#   optional "AFK " prefix
#   [LEVEL CLASS] or [ANONYMOUS]
#   NAME (optional)  (RACE) (optional)  <GUILD> (optional)
_PLAYER_RE: re.Pattern = re.compile(
    r"^\s*(?:(?P<afk>AFK)\s+)?"
    r"\[(?:(?P<level>\d+)\s+(?P<cls>[^\]]+?)|ANONYMOUS)\]\s+"
    r"(?P<name>[A-Za-z]+)"
    r"(?:\s+\((?P<race>[^)]+)\))?"
    r"(?:\s+<(?P<guild>[^>]+)>)?"
    r"\s*$",
)


# ── Raid-log accumulator ─────────────────────────────────────────────────────

class _RaidLogAccumulator:
    """Collects consecutive matching lines and fires a callback when the raid log ends.

    A raid log is considered complete when no new matching line arrives within
    ``_IDLE_MS`` milliseconds, or when ``_MAX_LINES`` is reached.
    """

    _IDLE_MS = 3_000
    _MAX_LINES = 500

    def __init__(self, on_complete, parent: QObject) -> None:  # noqa: ANN001
        self._on_complete = on_complete
        self._lines: list[str] = []
        self._full_log: str = ""
        self._timer = QTimer(parent)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._IDLE_MS)
        self._timer.timeout.connect(self.flush)

    def feed(self, body: str, raw_line: str) -> None:
        """Add a matching line and restart the idle countdown."""
        self._full_log += raw_line + "\n"

        m = _PLAYER_RE.match(body)
        if not m:
            return None

        character = m.group("name")
        level_str = m.group("level")
        is_anonymous = level_str is None
        guild = m.group("guild")
        if guild == "Gravity" or (guild is None and is_anonymous):
            self._lines.append(character)
            self._timer.start()
            if len(self._lines) >= self._MAX_LINES:
                self.flush()

        return None

    def clear(self) -> None:
        """Clear the accumulated lines and stop the timer."""
        self._lines.clear()
        self._full_log = ""
        self._timer.stop()

    def flush(self) -> None:
        if self._lines:
            self._on_complete(list(self._lines), self._full_log)
            self._full_log = ""
            self._lines.clear()
        self._timer.stop()


# ── Matcher ───────────────────────────────────────────────────────────────────
def _strip_timestamp(raw: str) -> str:
    """Return the log body with the leading ``[EQ timestamp] `` removed."""
    idx = raw.find("] ")
    return raw[idx + 2:] if idx != -1 else raw


class RaidLogMatcher(LogMatcher):
    """Detects EQ raid attendance log lines and batches them for submission.

    Consecutive matching lines are buffered by ``_RaidLogAccumulator``; a
    ``raid_log_detected`` signal fires once the sequence finishes (3 s gap or
    500-line cap).

    Two trigger modes:

    * **Tell trigger** — user sends ``/t nexusraidlog`` then ``/who``.
    * **Quick Raid Logs** — two ``/who`` commands within 5 seconds captures
      the second log automatically (enabled via :attr:`quick_raid_logs_enabled`).

    Signals
    -------
    raid_log_detected(list[str]):
        Emitted when a complete raid attendance log has been accumulated.
    """

    DISPLAY_NAME = "Raid Log Detector"
    DESCRIPTION = "Accumulates raid attendance log lines and fires when complete."
    MATCHER_KEY = "raid_log"
    ENABLED_BY_DEFAULT = True

    _QUICK_WINDOW_SECONDS: int = 5

    raid_log_detected = Signal(list)  # list[str]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._collecting = False
        self._collection_start_time: datetime = datetime.now()
        self._collection_timeout_seconds: int = 60
        self._accumulator = _RaidLogAccumulator(self._on_complete, self)

        self._quick_raid_logs_enabled: bool = True
        # States: "idle" | "first_who" | "between"
        self._quick_state: str = "idle"
        self._first_who_end_time: Optional[datetime] = None

    @property
    def quick_raid_logs_enabled(self) -> bool:
        return self._quick_raid_logs_enabled

    @quick_raid_logs_enabled.setter
    def quick_raid_logs_enabled(self, value: bool) -> None:
        self._quick_raid_logs_enabled = value
        if not value:
            self._quick_state = "idle"

    @property
    def is_collecting(self) -> bool:
        collection_end_time = self._collection_start_time + timedelta(seconds=self._collection_timeout_seconds)
        if datetime.now() > collection_end_time:
            return False

        return self._collecting

    # ── LogMatcher interface ────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:
        """Feed *event* through the state machine."""
        body = _strip_timestamp(event.raw)

        if not self.is_collecting:
            if _TELL_START_TRIGGER_RE.match(body):
                self._start_collecting()
                return

            if self._quick_raid_logs_enabled:
                self._update_quick_state(body)
            return

        # Accumulate potential player lines
        self._accumulator.feed(body, event.raw)

        if _WHO_END_RE.match(body):
            self._collecting = False
            self._accumulator.flush()
            self._quick_state = "idle"

    # ── Internals ──────────────────────────────────────────────────────────────

    def _update_quick_state(self, body: str) -> None:
        """Advance the quick-who state machine; starts collection on second /who."""
        if self._quick_state == "idle":
            if _WHO_START_RE.match(body):
                self._quick_state = "first_who"

        elif self._quick_state == "first_who":
            if _WHO_END_RE.match(body):
                self._quick_state = "between"
                self._first_who_end_time = datetime.now()

        elif self._quick_state == "between":
            if _WHO_START_RE.match(body):
                elapsed = (datetime.now() - self._first_who_end_time).total_seconds() if self._first_who_end_time else 999
                if elapsed <= self._QUICK_WINDOW_SECONDS:
                    log.debug("Quick raid log triggered (%.1fs gap)", elapsed)
                    self._start_collecting()
                else:
                    # Gap too long — treat this as a fresh first /who
                    self._quick_state = "first_who"

    def _start_collecting(self):
        log.debug("Raid log collection started")
        self._collection_start_time = datetime.now()
        self._collecting = True
        self._quick_state = "idle"
        self._accumulator.clear()

    def _on_complete(self, lines: list[str], full_who_log: str) -> None:
        log.info("Raid log complete: %d lines", len(lines))
        self.raid_log_detected.emit([lines, full_who_log])
