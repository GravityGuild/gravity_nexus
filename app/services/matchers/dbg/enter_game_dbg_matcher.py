"""EnterGameDbgMatcher — detects successful game zone entry from dgb.txt.

EQ writes this line to dgb.txt at the end of the zone-loading sequence::

    2026-05-27 07:29:05	Initialization complete.

It appears only during the zone-loading sequence (after selecting a character
and entering the world), not during character select loading.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

_INIT_COMPLETE_RE = re.compile(r"^Initialization complete\.$")


class EnterGameDbgMatcher(LogMatcher):
    """Emits ``character_entered_game`` when dgb.txt confirms the zone has fully loaded."""

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    character_entered_game = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        if _INIT_COMPLETE_RE.match(event.message):
            log.debug("dgb.txt initialization complete — emitting character_entered_game")
            self.character_entered_game.emit()
