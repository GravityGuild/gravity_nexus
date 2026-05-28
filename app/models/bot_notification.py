"""Gravity Bot notification model.

Represents a push frame received from the bot over WebSocket.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Known notification kind constants ─────────────────────────────────────────
KIND_RAID_LOG_ACK = "RAID_LOG_ACK"  # bot confirmed receipt of a submitted raid log
KIND_ANNOUNCEMENT = "ANNOUNCEMENT"  # broadcast message sent to all connected clients
KIND_CHARACTER_SET_RESULT = "character_set_result"  # server response to a character_set message
KIND_UNKNOWN = "UNKNOWN"  # forward-compat catch-all for unrecognised frames


@dataclass
class BotNotification:
    """A push notification received from Gravity Bot over WebSocket.

    The ``payload`` contents vary by ``kind`` — consumers should check ``kind``
    before accessing specific payload keys.
    """

    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_raid_log_ack(self) -> bool:
        return self.kind == KIND_RAID_LOG_ACK

    @property
    def is_announcement(self) -> bool:
        return self.kind == KIND_ANNOUNCEMENT

