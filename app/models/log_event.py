"""Log event model — represents a single parsed EverQuest log line."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class LogSource(Enum):
    """Which log file a ``LogEvent`` originated from."""

    EQ_LOG = auto()   # eqlog_{Character}_project1999.txt
    DBG_TXT = auto()  # dgb.txt (client debug log)


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
    source: LogSource = field(default=LogSource.EQ_LOG)

