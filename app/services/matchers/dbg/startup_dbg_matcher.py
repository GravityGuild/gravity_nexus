"""StartupDbgMatcher — detects EverQuest process startup from dbg.txt.

EQ writes this line to dbg.txt immediately when launched::

    2026-05-27 12:44:56    Starting EverQuest (Build Oct 31 2005 10:33:37)

Emitting ``game_started`` at this point lets the process watcher arm itself
before the player has reached character select.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

_STARTUP_RE = re.compile(r"^Starting EverQuest \(Build .+\)$")


class StartupDbgMatcher(LogMatcher):
    """Emits ``game_started`` when dbg.txt records the EQ process launching."""

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    game_started = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        if _STARTUP_RE.match(event.message):
            log.debug("dbg.txt EQ startup detected — emitting game_started")
            self.game_started.emit()
