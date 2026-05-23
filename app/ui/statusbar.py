"""AppStatusBar — bottom status strip showing runtime KPIs."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from ui.widgets.status_widgets import StatusIndicator
from ui.widgets.themed_label import ThemedLabel
from theme.spec import ColorRole, FontSize
from _version import __version__


class StatusBar(QWidget):
    """Bottom status bar: parser state, EQ connection, future metrics."""

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

        self._parser_indicator = StatusIndicator("Parser: Stopped", "offline")
        layout.addWidget(self._parser_indicator)

        # layout.addWidget(_make_sep())

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

    def set_parser_running(self, running: bool, log_name: str = "") -> None:
        if running:
            self._parser_indicator.set_status("online", f"Parser: {log_name or 'Running'}")
        else:
            self._parser_indicator.set_status("offline", "Parser: Stopped")

    def set_grav_bot_connected(self, connected: bool) -> None:
        if connected:
            self._eq_indicator.set_status("online", "Gravity Bot: Connected")
        else:
            self._eq_indicator.set_status("offline", "Gravity Bot: Disconnected")

    def set_metrics(self, text: str) -> None:
        self._metrics_label.setText(text)


def _make_sep() -> QFrame:
    """Return a 1 px tall vertical separator styled for the status bar."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFrameShadow(QFrame.Shadow.Plain)
    sep.setFixedSize(10, 14)
    sep.setStyleSheet("color: rgba(87, 199, 255, 30);")
    return sep
