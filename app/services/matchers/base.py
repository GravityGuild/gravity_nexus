"""Log matcher base class.

Any service that needs to react to parsed log lines should subclass
``LogMatcher`` and register an instance with ``LogParserService``.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject

from models.log_event import LogEvent, LogSource


class LogMatcher(QObject):
    """Base class for objects that subscribe to parsed log lines.

    Subclass this to create a domain-specific log react handler.  Register an
    instance with :meth:`LogParserService.register_matcher` so the parser calls
    :meth:`process` for every new :class:`~models.log_event.LogEvent`.

    The parser never imports concrete subclasses — registration is the only
    coupling point.

    UI Integration
    --------------
    Declare these class-level attributes to have the matcher appear
    **automatically** in the Parsing configuration page:

    .. code-block:: python

        class MyMatcher(LogMatcher):
            DISPLAY_NAME = "My Feature"
            DESCRIPTION  = "One sentence shown below the toggle."
            MATCHER_KEY  = "my_feature"   # unique snake_case key for persistence
            ENABLED_BY_DEFAULT = True

    Leave ``MATCHER_KEY`` empty (the default) to exclude the matcher from the
    UI (useful for internal/infrastructure matchers).

    Example
    -------
    .. code-block:: python

        class NamedNPCMatcher(LogMatcher):
            DISPLAY_NAME = "Named NPC Spawns"
            DESCRIPTION  = "Alerts when a named NPC is slain."
            MATCHER_KEY  = "named_npc_spawns"

            npc_spotted = Signal(str)          # NPC name
            _PATTERN = re.compile(r"(\\w+) has been slain")

            def process(self, event: LogEvent) -> None:
                m = self._PATTERN.search(event.raw)
                if m:
                    self.npc_spotted.emit(m.group(1))

        # In a service or MainWindow:
        matcher = NamedNPCMatcher(parent=self)
        matcher.npc_spotted.connect(my_handler)
        LogParserService.instance().register_matcher(matcher)
    """

    # ── UI metadata — override in subclasses ───────────────────────────────────
    #: Human-readable label shown in the Parsing settings page.
    DISPLAY_NAME: str = ""

    #: One-line description shown below the toggle.
    DESCRIPTION: str = ""

    #: Unique snake_case key used to persist the enabled state.
    #: Leave empty to hide the matcher from the UI.
    MATCHER_KEY: str = ""

    #: Whether the matcher should be enabled when first seen (no saved state).
    ENABLED_BY_DEFAULT: bool = True

    #: Which log sources this matcher should receive events from.
    #: Defaults to the main EQ log only.  Override to subscribe to dbg.txt
    #: events (``{LogSource.DBG_TXT}``) or both sources.
    SOURCES: frozenset[LogSource] = frozenset({LogSource.EQ_LOG})

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._enabled: bool = self.ENABLED_BY_DEFAULT

    # ── Enabled state ──────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        """Whether this matcher is active.  When ``False``, the parser skips it."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this matcher at runtime."""
        self._enabled = enabled

    # ── Interface ──────────────────────────────────────────────────────────────

    def process(self, event: LogEvent) -> None:
        """Called by the parser for every new ``LogEvent``.

        Inspect ``event.raw`` (or ``event.timestamp``) and emit signals as
        needed.  This is always called on the **main thread**.

        Subclasses must override this method.
        """
        raise NotImplementedError(f"{type(self).__name__}.process() not implemented")

    @property
    def name(self) -> str:
        """Human-readable identifier used in log messages."""
        return type(self).__name__

