"""Log event model — represents a single parsed EverQuest log line."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class LogEventKind(Enum):
    """Coarse category of a parsed log line.

    Fine-grained sub-types belong in domain-specific matchers, not here.
    Add new values as additional log categories are recognised.
    """

    UNKNOWN = auto()
    RAID_LOG = auto()
    ZONE_CHANGE = auto()
    GUILD_CHAT = auto()


@dataclass(frozen=True)
class LogEvent:
    """Immutable snapshot of a single parsed EQ log line."""

    timestamp: datetime
    raw: str
    message: str
    kind: LogEventKind = LogEventKind.UNKNOWN

