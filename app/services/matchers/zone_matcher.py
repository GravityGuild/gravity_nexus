"""ZoneMatcher — detects EQ zone-transition log lines.

Matches the format::

    [Thu Apr 17 11:29:13 2025] You have entered The Wakening Lands.

and emits ``zone_changed(zone_name: str)`` on the main thread whenever the
character enters a new zone.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogEventKind
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# Matches: "You have entered <Zone Name>."
# The zone name may contain spaces, apostrophes, dashes, etc.
_ZONE_RE: re.Pattern = re.compile(r"^You have entered (.+)\.$")


class ZoneMatcher(LogMatcher):
    """Detects EQ zone-entry messages and emits the new zone name.

    Example matched line (body only, after the EQ timestamp is stripped)::

        You have entered The Wakening Lands.

    Signals
    -------
    zone_changed(str):
        Emitted with the zone name (e.g. ``"The Wakening Lands"``) each time
        the character enters a zone.
    """

    DISPLAY_NAME = "Zone Changes"
    DESCRIPTION = "Detects zone-entry messages and tracks the current zone."
    MATCHER_KEY = "zone_changes"
    ENABLED_BY_DEFAULT = True

    zone_changed = Signal(str)  # zone name

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_zone: str = ""

    # ── LogMatcher interface ────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:
        """Emit ``zone_changed`` if *event* is a zone-entry message."""
        # The raw line includes the full EQ timestamp; extract the body after "] "
        bracket_idx = event.raw.find("] ")
        body = event.raw[bracket_idx + 2:] if bracket_idx != -1 else event.raw

        m = _ZONE_RE.match(body)
        if not m:
            return

        zone = m.group(1)
        if zone != self._current_zone:
            self._current_zone = zone
            log.info("Zone changed → %s", zone)
            self.zone_changed.emit(zone)

    # ── Accessors ───────────────────────────────────────────────────────────────

    @property
    def current_zone(self) -> str:
        """The most recently detected zone name, or empty string if unknown."""
        return self._current_zone

    def reset(self) -> None:
        """Clear the cached zone (e.g. when the parser is stopped)."""
        self._current_zone = ""

