"""RaidDumpMatcher — detects and accumulates EQ raid attendance dump lines.

This is the first concrete LogMatcher and also serves as the reference
implementation of the accumulator pattern for multi-line log sequences.

To activate, replace ``_PATTERN`` with the real EverQuest regex once the exact
log format is confirmed.  No other code needs to change.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from models.log_event import LogEvent
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# ── Compiled patterns ─────────────────────────────────────────────────────────

# Start-of-dump marker (body after EQ timestamp is stripped)
_WHO_START_RE: re.Pattern = re.compile(r"^Players on EverQuest:\s*$")

# Separator line e.g. "---------------------------"
_WHO_SEP_RE: re.Pattern = re.compile(r"^-+\s*$")

# End-of-dump summary e.g. "There are 19 players in East Commonlands."
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


# ── Raid-dump accumulator ─────────────────────────────────────────────────────

class _RaidDumpAccumulator:
    """Collects consecutive matching lines and fires a callback when the dump ends.

    A dump is considered complete when no new matching line arrives within
    ``_IDLE_MS`` milliseconds, or when ``_MAX_LINES`` is reached.
    """

    _IDLE_MS = 3_000
    _MAX_LINES = 500

    def __init__(self, on_complete, parent: QObject) -> None:  # noqa: ANN001
        self._on_complete = on_complete
        self._lines: list[str] = []
        self._timer = QTimer(parent)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._IDLE_MS)
        self._timer.timeout.connect(self.flush)

    def feed(self, raw_line: str) -> None:
        """Add a matching line and restart the idle countdown."""
        m = _PLAYER_RE.match(raw_line)
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
        self._timer.stop()

    def flush(self) -> None:
        if self._lines:
            self._on_complete(list(self._lines))
            self._lines.clear()
        self._timer.stop()


# ── Matcher ───────────────────────────────────────────────────────────────────
def _strip_timestamp(raw: str) -> str:
    """Return the log body with the leading ``[EQ timestamp] `` removed."""
    idx = raw.find("] ")
    return raw[idx + 2:] if idx != -1 else raw


class RaidDumpMatcher(LogMatcher):
    """Detects EQ raid attendance dump lines and batches them for submission.

    Consecutive matching lines are buffered by ``_RaidDumpAccumulator``; a
    ``raid_dump_detected`` signal fires once the sequence finishes (3 s gap or
    500-line cap).

    Example expected format (placeholder — to be confirmed)::

        [Thu Jan 01 00:00:00 2026] PlayerName is a Level 65 Warrior in Gravity.

    Signals
    -------
    raid_dump_detected(list[str]):
        Emitted when a complete raid attendance dump has been accumulated.
    """

    DISPLAY_NAME = "Raid Dump Detector"
    DESCRIPTION = "Accumulates raid attendance dump lines and fires when complete."
    MATCHER_KEY = "raid_dump"
    ENABLED_BY_DEFAULT = True

    raid_dump_detected = Signal(list)  # list[str]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._collecting = False
        self._accumulator = _RaidDumpAccumulator(self._on_complete, self)

    # ── LogMatcher interface ────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:
        """Feed the line into the accumulator if it matches the raid dump pattern."""
        """Feed *event* through the state machine."""
        body = _strip_timestamp(event.raw)

        # Currently collecting — look for separator, player lines, or end
        if _WHO_SEP_RE.match(body):
            return  # skip separator lines

        if not self._collecting:
            if _WHO_START_RE.match(body):
                log.debug("Who-list dump started")
                self._collecting = True
                self._accumulator.clear()
            return

        # Accumulate potential player lines
        self._accumulator.feed(body)

        if _WHO_END_RE.match(body):
            self._collecting = False
            self._accumulator.flush()
            return

    # ── Internals ──────────────────────────────────────────────────────────────

    def _on_complete(self, lines: list[str]) -> None:
        log.info("Raid dump complete: %d lines", len(lines))
        self.raid_dump_detected.emit(lines)
