"""ZoneDbgMatcher — detects zone connections from dgb.txt.

EQ writes this line to dgb.txt when the zone server accepts the player::

    2026-05-27 07:29:00	Player = Floppur, zone = City of Mist

This fires during the zone-loading sequence, before the EQ-log-based
``ZoneMatcher`` (which fires when the "You have entered ..." message arrives).
The character name embedded in the line can be used to confirm or update the
active character.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# "Player = Floppur, zone = City of Mist"
_ZONE_CONNECT_RE = re.compile(r"^Player = (.+), zone = (.+)$")


class ZoneDbgMatcher(LogMatcher):
    """Emits ``zone_connected`` when dgb.txt reports a successful zone connection.

    Carries the character name and zone name from the dgb.txt line.
    """

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    zone_connected = Signal(str, str)  # (character, zone)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        m = _ZONE_CONNECT_RE.match(event.message)
        if m:
            character, zone = m.group(1), m.group(2)
            log.debug("dgb.txt zone connect: %s → %s", character, zone)
            self.zone_connected.emit(character, zone)
