"""CharSelectDbgMatcher — detects character select screen load from dgb.txt.

EQ writes this line to dgb.txt whenever the character select UI is initialised::

    2026-05-27 07:38:08	Initializing character select UI.

This is distinct from the "Resetting character select UI." line that appears
during zone transitions.  It fires for two paths:

- After ``/camp`` — character camped from game back to character select.
- After logging back in from the login screen — arrived at character select.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

_CHAR_SELECT_RE = re.compile(r"^Initializing character select UI\.$")


class CharSelectDbgMatcher(LogMatcher):
    """Emits ``character_at_select`` when dgb.txt confirms the character select screen loaded."""

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    character_at_select = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        if _CHAR_SELECT_RE.match(event.message):
            log.debug("dgb.txt character select UI initialised — emitting character_at_select")
            self.character_at_select.emit()
