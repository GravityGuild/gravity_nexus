"""DisconnectDbgMatcher — detects all paths that make a character fully offline.

EQ writes one of these lines to dgb.txt depending on how the player exits:

- ``/q`` (quit to login screen)::

      *** DISCONNECTING: Quit command received.

- ``/exit`` (exit to desktop from game)::

      *** DISCONNECTING: Exit command received.

- ``/camp desktop`` (camp then exit to desktop)::

      Exiting normally.

- Quit button from character select screen::

      Quitting normally.

All four cases mean the character is no longer occupying a slot and is
available for another client to log in.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent, LogSource
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

_DISCONNECT_RE = re.compile(
    r"^(?:"
    r"\*\*\* DISCONNECTING: Quit command received\."
    r"|\*\*\* DISCONNECTING: Exit command received\."
    r"|Exiting normally\."
    r"|Quitting normally\."
    r")$"
)


class DisconnectDbgMatcher(LogMatcher):
    """Emits ``character_offline`` when dgb.txt indicates the character is fully offline."""

    ENABLED_BY_DEFAULT = True
    SOURCES = frozenset({LogSource.DBG_TXT})

    character_offline = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def process(self, event: LogEvent) -> None:
        if _DISCONNECT_RE.match(event.message):
            log.debug("dgb.txt disconnect event (%r) — emitting character_offline", event.message)
            self.character_offline.emit()
