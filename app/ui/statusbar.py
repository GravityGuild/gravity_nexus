"""AppStatusBar — bottom status strip showing runtime KPIs."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ui.widgets.status_widgets import StatusIndicator
from ui.widgets.themed_label import ThemedLabel
from theme.spec import ColorRole, FontSize
from _version import __version__

_CHAR_STATE_MAP: dict[str, tuple[str, str]] = {
    "in_game":   ("online",  "In Game"),
    "at_select": ("warning", "Character Select"),
    "offline":   ("offline", "Offline"),
}


class StatusBar(QWidget):
    """Bottom status bar: parser state, character info, EQ connection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(28)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(16)

        self._character_indicator = StatusIndicator("No Character", "offline")
        layout.addWidget(self._character_indicator)

        self._state_indicator = StatusIndicator("Offline", "offline")
        layout.addWidget(self._state_indicator)

        self._parser_indicator = StatusIndicator("Parser: Stopped", "offline")
        layout.addWidget(self._parser_indicator)

        self._eq_indicator = StatusIndicator("Gravity Bot: Disconnected", "offline")
        layout.addWidget(self._eq_indicator)

        layout.addStretch()

        # Right side — reserved for future CPU/memory metrics
        self._metrics_label = ThemedLabel(
            "",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        self._metrics_label.setObjectName("StatusBarText")
        self._metrics_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._metrics_label)

        ver = ThemedLabel(
            f"v{__version__}",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
        )
        ver.setObjectName("StatusBarVersion")
        layout.addWidget(ver)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_parser_running(self, running: bool, filename: str = "") -> None:
        if running:
            self._parser_indicator.set_status("online", f"Parser: {filename or 'Active'}")
        else:
            self._parser_indicator.set_status("offline", "Parser: Stopped")

    def set_character(self, character: str) -> None:
        if character:
            self._character_indicator.set_status("online", character)
        else:
            self._character_indicator.set_status("offline", "No Character")

    def set_character_state(self, state: str) -> None:
        dot, label = _CHAR_STATE_MAP.get(state, ("offline", "Offline"))
        self._state_indicator.set_status(dot, label)

    def set_grav_bot_connected(self, connected: bool) -> None:
        if connected:
            self._eq_indicator.set_status("online", "Gravity Bot: Connected")
        else:
            self._eq_indicator.set_status("offline", "Gravity Bot: Disconnected")

    def set_metrics(self, text: str) -> None:
        self._metrics_label.setText(text)
