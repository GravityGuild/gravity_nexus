"""SectionHeader and StatusIndicator widgets."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from theme.colors import (
    ACCENT_CYAN_RGB,
    ERROR_RGB,
    SUCCESS_RGB,
    TEXT_SECONDARY_RGB,
    WARNING_RGB,
)

# ── SectionHeader ─────────────────────────────────────────────────────────────


class SectionHeader(QWidget):
    """A labelled divider row used above groups of settings."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(10)

        label = QLabel(title.upper())
        label.setObjectName("SectionHeader")
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        layout.addWidget(label)

        line = _HLine()
        layout.addWidget(line)


class _HLine(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(*ACCENT_CYAN_RGB, 35), 1))
        mid = self.height() // 2
        p.drawLine(0, mid, self.width(), mid)
        p.end()


# ── StatusIndicator ───────────────────────────────────────────────────────────

_STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "online": SUCCESS_RGB,
    "offline": TEXT_SECONDARY_RGB,
    "warning": WARNING_RGB,
    "error": ERROR_RGB,
    "connecting": ACCENT_CYAN_RGB,
}


class StatusIndicator(QWidget):
    """A small coloured dot paired with a text label showing connection state."""

    def __init__(
        self,
        label: str = "",
        status: str = "offline",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._status = status

        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        self._dot = _DotWidget(status)
        hl.addWidget(self._dot)

        self._label = QLabel(label)
        self._label.setObjectName("StatusBarText")
        hl.addWidget(self._label)

    def set_status(self, status: str, label: str | None = None) -> None:
        self._status = status
        self._dot.set_status(status)
        if label is not None:
            self._label.setText(label)

    def set_label(self, label: str) -> None:
        self._label.setText(label)


class _DotWidget(QWidget):
    def __init__(self, status: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._status = status
        self.setFixedSize(8, 8)

    def set_status(self, status: str) -> None:
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        rgb = _STATUS_COLORS.get(self._status, TEXT_SECONDARY_RGB)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*rgb, 220))
        p.setPen(QPen(QColor(*rgb, 100), 1))
        p.drawEllipse(1, 1, 6, 6)
        p.end()

