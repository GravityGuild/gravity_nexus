"""CampDbgMatcher — detects camp completion from dgb.txt.

EQ writes this line to dgb.txt after the character has fully camped out::

    2026-05-27 07:38:04	*** EXITING: I have completed camping.

This fires after the EQ log has already stopped receiving writes, so it
complements the EQ-log-based ``CampMatcher`` (which fires during the countdown)
by confirming the camp actually completed.  It fires for both ``/camp``
(character select) and ``/camp desktop``.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

_CAMP_COMPLETE_RE = re.compile(r"^\*\*\* EXITING: I have completed camping\.$")


class CampDbgMatcher(LogMatcher):
    """Emits ``camp_complete`` when dgb.txt confirms a successful camp-out."""

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    camp_complete = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        if _CAMP_COMPLETE_RE.match(event.message):
            log.debug("dgb.txt camp complete confirmed — emitting camp_complete")
            self.camp_complete.emit()
