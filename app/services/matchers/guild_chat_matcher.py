"""GuildChatMatcher — detects EQ guild-chat log lines.

Matches the following formats::

    [Wed May 20 20:41:49 2026] Zandakon tells the guild, 'Hello everyone!'
    [Wed May 20 22:02:36 2026] You say to your guild, 'test'

For the second format the active character name is substituted for ``"You"``
by querying ``ILogParserService.active_character`` from the service registry.

Emits ``guild_message(character: str, message: str)`` on the main thread
whenever a guild-chat message is parsed.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import QObject, Signal

from models.log_event import LogEvent
from services.matchers.base import LogMatcher

log = logging.getLogger(__name__)

# Matches: "<Character> tells the guild, '<message>'"
# Character name may include upper/lower-case letters only (EQ names).
# Message may contain any characters including apostrophes.
_GUILD_RE: re.Pattern = re.compile(
    r"^([A-Za-z]+) tells the guild, '(.*)'$"
)

# Matches the first-person variant sent by the local player:
# "You say to your guild, '<message>'"
_YOU_GUILD_RE: re.Pattern = re.compile(
    r"^You say to your guild, '(.*)'$"
)


class GuildChatMatcher(LogMatcher):
    """Detects EQ guild-chat messages and emits character + message text.

    Handles both the third-person format (other players) and the first-person
    format (local player).  In the first-person case, ``"You"`` is replaced
    with the currently active character obtained from ``ILogParserService``.

    Example matched lines (body only, after the EQ timestamp is stripped)::

        Zandakon tells the guild, 'Hello everyone!'
        You say to your guild, 'test'

    Signals
    -------
    guild_message(str, str):
        Emitted with ``(character, message)`` for each guild-chat line parsed.
    """

    DISPLAY_NAME = "Guild Chat"
    DESCRIPTION = "Captures guild-chat messages with the sender's name."
    MATCHER_KEY = "guild_chat"
    ENABLED_BY_DEFAULT = True

    guild_message = Signal(str, str)  # (character, message)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    # ── LogMatcher interface ────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:
        """Emit ``guild_message`` if *event* is a guild-chat message."""
        # Strip the EQ timestamp prefix "[...] " before matching
        bracket_idx = event.raw.find("] ")
        body = event.raw[bracket_idx + 2:] if bracket_idx != -1 else event.raw

        # Third-person format: "<Character> tells the guild, '<message>'"
        m = _GUILD_RE.match(body)
        if m:
            character = m.group(1)
            message = m.group(2)
            log.debug("Guild chat from %s: %s", character, message)
            self.guild_message.emit(character, message)
            return

        # First-person format: "You say to your guild, '<message>'"
        m = _YOU_GUILD_RE.match(body)
        if m:
            message = m.group(1)
            from core.registry import registry
            from services.protocols import ILogParserService
            character = registry.get(ILogParserService).active_character or "You"
            log.debug("Guild chat from %s (local): %s", character, message)
            self.guild_message.emit(character, message)
