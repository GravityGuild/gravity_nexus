"""AppStatusBar — bottom status strip showing runtime KPIs."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.widgets.status_widgets import StatusIndicator


class StatusBar(QWidget):
    """Bottom status bar: parser state, profile, EQ connection, future metrics."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(28)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(16)

        self._parser_indicator = StatusIndicator("Parser: Stopped", "offline")
        layout.addWidget(self._parser_indicator)

        layout.addWidget(_Sep())

        self._eq_indicator = StatusIndicator("Gravity Bot: Disconnected", "offline")
        layout.addWidget(self._eq_indicator)

        layout.addWidget(_Sep())

        self._profile_label = QLabel("Profile: Default")
        self._profile_label.setObjectName("StatusBarText")
        layout.addWidget(self._profile_label)

        layout.addStretch()

        # Right side — reserved for future CPU/memory metrics
        self._metrics_label = QLabel("")
        self._metrics_label.setObjectName("StatusBarText")
        self._metrics_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._metrics_label)

        ver = QLabel("v1.0.0")
        ver.setObjectName("StatusBarText")
        ver.setStyleSheet("color: rgba(147, 164, 195, 60);")
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

    def set_active_profile(self, profile_name: str) -> None:
        self._profile_label.setText(f"Profile: {profile_name}")

    def set_metrics(self, text: str) -> None:
        self._metrics_label.setText(text)


class _Sep(QWidget):
    """Thin vertical separator for the status bar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(1, 14)
        self.setStyleSheet("background: rgba(87, 199, 255, 30);")

