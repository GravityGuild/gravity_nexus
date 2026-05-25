"""WhoEntry — represents a single player line from an EQ /who.

Parsed from the EverQuest log format produced by the ``/who`` command::

    [Wed May 20 22:18:04 2026] [60 Warlord] Satoshibtc (Barbarian) <Gravity>
    [Wed May 20 22:18:04 2026]  AFK [ANONYMOUS] Horza
    [Wed May 20 22:18:04 2026] [ANONYMOUS] Reprobate
    [Wed May 20 22:18:04 2026] [ANONYMOUS] Sugarfoot  <Fuse>

Filtering rules (see :attr:`should_submit`)
-------------------------------------------
* **Always include** — players tagged with ``<Gravity>``.
* **Include for lookup** — ``[ANONYMOUS]`` players with **no** guild tag.
  The bot needs to resolve these to determine guild membership.
* **Exclude** — everyone else (known non-Gravity guild or has level/class
  info without a Gravity tag).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

GRAVITY_GUILD = "Gravity"


@dataclass
class WhoEntry:
    """Parsed representation of one player line from a ``/who``.

    Attributes
    ----------
    name:
        Character name (always present).
    is_anonymous:
        ``True`` when the line used ``[ANONYMOUS]`` instead of ``[LEVEL CLASS]``.
    level:
        Character level, or ``None`` if anonymous.
    char_class:
        Character class string (e.g. ``"Warlord"``), or ``None`` if anonymous.
    race:
        Race string (e.g. ``"Barbarian"``), or ``None`` if not shown.
    guild:
        Guild tag (e.g. ``"Gravity"``), or ``None`` if unguilded / not shown.
    is_afk:
        ``True`` when the line had the ``AFK`` prefix.
    raw_line:
        The original raw log line, including the EQ timestamp prefix.
    """

    name: str
    is_anonymous: bool
    level: Optional[int]
    char_class: Optional[str]
    race: Optional[str]
    guild: Optional[str]
    is_afk: bool
    raw_line: str

    # ── Convenience predicates ─────────────────────────────────────────────────

    @property
    def is_gravity(self) -> bool:
        """``True`` when this character is tagged with ``<Gravity>``."""
        return self.guild == GRAVITY_GUILD

    @property
    def should_submit(self) -> bool:
        """``True`` when this entry should be forwarded to the Gravity Bot.

        Includes:

        * Characters explicitly in ``<Gravity>`` (regardless of anonymous status).
        * ``[ANONYMOUS]`` characters with **no** guild tag (bot resolves membership).

        Excludes all other characters (non-Gravity guild members or unguilded
        players whose level/class is visible, confirming they are not anonymous
        guild members).
        """
        if self.is_gravity:
            return True
        if self.is_anonymous and self.guild is None:
            return True
        return False

    # ── Serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict representation."""
        return {
            "name": self.name,
            "anonymous": self.is_anonymous,
            "level": self.level,
            "class": self.char_class,
            "race": self.race,
            "guild": self.guild,
            "afk": self.is_afk,
        }

