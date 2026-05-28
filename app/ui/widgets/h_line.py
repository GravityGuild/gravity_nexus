"""HLine — themed horizontal separator widget."""
from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from theme.colors import ACCENT_CYAN_RGB


class HLine(QWidget):
    """A 1 px horizontal rule drawn in the accent cyan colour."""

    def __init__(
        self,
        color: tuple[int, int, int] = ACCENT_CYAN_RGB,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(*self._color, 35), 1))
        mid = self.height() // 2
        p.drawLine(0, mid, self.width(), mid)
        p.end()
