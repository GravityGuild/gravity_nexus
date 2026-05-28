"""WhoListMatcher — detects and parses EQ ``/who`` output blocks.

Recognises the multi-line ``/who`` output format produced by EverQuest::

    [timestamp] Players on EverQuest:
    [timestamp] ---------------------------
    [timestamp] [60 Warlord] Satoshibtc (Barbarian) <Gravity>
    [timestamp]  AFK [ANONYMOUS] Horza
    [timestamp] [ANONYMOUS] Reprobate
    [timestamp] [ANONYMOUS] Sugarfoot  <Fuse>
    [timestamp] There are 6 players in East Commonlands.

The matcher uses a simple state machine:

* **IDLE** — waiting for the "Players on EverQuest:" header line.
* **COLLECTING** — accumulating player lines until the summary line arrives.

On completion each player line is parsed into a :class:`~models.who_entry.WhoEntry`
and filtered according to :attr:`~models.who_entry.WhoEntry.should_submit`.
The ``who_list_detected`` signal carries only the filtered entries.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent
from models.who_entry import WhoEntry
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# ── Compiled patterns ─────────────────────────────────────────────────────────

# Start-of-log marker (body after EQ timestamp is stripped)
_WHO_START_RE: re.Pattern = re.compile(r"^Players (?:on|in) EverQuest:\s*$")

# Separator line e.g. "---------------------------"
_WHO_SEP_RE: re.Pattern = re.compile(r"^-+\s*$")

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
    r"(?:\s+ZONE:\s*(?P<zone>\S+))?"
    r"(?:\s+LFG)?"
    r"\s*$",
)


def _strip_timestamp(raw: str) -> str:
    """Return the log body with the leading ``[EQ timestamp] `` removed."""
    idx = raw.find("] ")
    return raw[idx + 2:] if idx != -1 else raw


def parse_who_line(raw: str) -> Optional[WhoEntry]:
    """Parse a single raw EQ log line into a :class:`WhoEntry`.

    Returns ``None`` if the line does not match the expected player format
    (e.g. the start/separator/end lines).

    Parameters
    ----------
    raw:
        A complete EQ log line including the timestamp prefix, e.g.
        ``"[Wed May 20 22:18:04 2026] [60 Warlord] Satoshibtc (Barbarian) <Gravity>"``.
    """
    body = _strip_timestamp(raw)
    m = _PLAYER_RE.match(body)
    if not m:
        return None

    level_str = m.group("level")
    return WhoEntry(
        name=m.group("name"),
        is_anonymous=level_str is None,
        level=int(level_str) if level_str else None,
        char_class=m.group("cls"),
        race=m.group("race"),
        guild=m.group("guild"),
        is_afk=m.group("afk") is not None,
        raw_line=raw,
        zone=m.group("zone"),
    )


# ── Matcher ───────────────────────────────────────────────────────────────────

class WhoListMatcher(LogMatcher):
    """Detects ``/who`` output blocks and emits filtered :class:`WhoEntry` lists.

    Only entries that satisfy :attr:`~models.who_entry.WhoEntry.should_submit`
    are included in the emitted list:

    * Characters in ``<Gravity>`` (always forwarded).
    * ``[ANONYMOUS]`` characters with no guild tag (bot resolves membership).

    Signals
    -------
    who_list_detected(list):
        Emitted when a complete ``/who`` block has been parsed.
        Carries a ``list[WhoEntry]`` of *filtered* entries only.
    """

    DISPLAY_NAME = "Who-List Parser"
    DESCRIPTION = (
        "Detects /who output, parses player entries, and forwards "
        "Gravity members and unresolved anonymouses to the bot."
    )
    MATCHER_KEY = "who_list"
    ENABLED_BY_DEFAULT = True

    who_list_detected = Signal(list, int)  # list[WhoEntry] (filtered), int (total parsed)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._collecting = False
        self._raw_lines: list[str] = []

    # ── LogMatcher interface ────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:  # noqa: C901
        """Feed *event* through the state machine."""
        body = _strip_timestamp(event.raw)

        if not self._collecting:
            if _WHO_START_RE.match(body):
                log.debug("Who-list started")
                self._collecting = True
                self._raw_lines = []
            return

        # Currently collecting — look for separator, player lines, or end
        if _WHO_SEP_RE.match(body):
            return  # skip separator lines

        if _WHO_END_RE.match(body):
            self._collecting = False
            self._flush()
            return

        # Accumulate potential player lines
        self._raw_lines.append(event.raw)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _flush(self) -> None:
        """Parse accumulated lines, filter, and emit the result."""
        entries: list[WhoEntry] = []
        skipped = 0

        for raw in self._raw_lines:
            entry = parse_who_line(raw)
            if entry is None:
                log.debug("Who-list: unparseable line skipped: %r", raw)
                continue
            if entry.should_submit:
                entries.append(entry)
            else:
                skipped += 1

        total = len(entries) + skipped
        log.info(
            "Who-list complete: %d total parsed, %d to submit, %d excluded",
            total,
            len(entries),
            skipped,
        )

        self._raw_lines.clear()

        if entries:
            self.who_list_detected.emit(entries, total)
        else:
            log.debug("Who-list: no submittable entries — signal suppressed")

