"""CampMatcher — detects EverQuest camp-out countdown messages.

EQ emits this sequence as a character prepares to camp::

    It will take you about 30 seconds to prepare your camp.
    It will take about 25 more seconds to prepare your camp.
    ...
    It will take about 5 more seconds to prepare your camp.

The log file stops receiving writes immediately after the 5-second message.
``camped_out`` is emitted on that final message; actual character-state
transitions are driven by ``CampDbgMatcher`` and ``CharSelectDbgMatcher``
from dgb.txt, which fire after the camp fully completes.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# Matches the final countdown line (5 seconds) — point of no return.
_CAMP_FINAL_RE = re.compile(r"^It will take about 5 more seconds to prepare your camp\.$")


class CampMatcher(LogMatcher):
    """Emits ``camped_out`` when the final camp countdown message is seen.

    No UI toggle — this is internal infrastructure for the character-tracking
    feature and should always be active.
    """

    ENABLED_BY_DEFAULT = True

    camped_out = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        bracket_idx = event.raw.find("] ")
        body = event.raw[bracket_idx + 2:] if bracket_idx != -1 else event.raw
        if _CAMP_FINAL_RE.match(body):
            log.debug("Camp-out detected — emitting camped_out")
            self.camped_out.emit()
