"""ToggleSwitch — animated custom-painted boolean toggle widget.

Emits ``toggled(bool)`` when the value changes.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from theme.colors import (
    ACCENT_CYAN_RGB,
    CARD_BG_RGB,
    DEEP_BLUE_RGB,
    SUCCESS_RGB,
    TEXT_SECONDARY_RGB,
)

_TRACK_W = 46
_TRACK_H = 24
_THUMB_PAD = 3


class ToggleSwitch(QWidget):
    """Smooth animated on/off toggle switch."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._anim_value: float = 1.0 if checked else 0.0

        self.setFixedSize(_TRACK_W + 4, _TRACK_H + 4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._animation = QPropertyAnimation(self, b"_anim_pos", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool, animated: bool = True) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0
        if animated:
            self._animation.stop()
            self._animation.setStartValue(self._anim_value)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._anim_pos = target  # type: ignore[assignment]

    # ── Qt property for animation ──────────────────────────────────────────────

    def _get_anim_pos(self) -> float:
        return self._anim_value

    def _set_anim_pos(self, value: float) -> None:
        self._anim_value = value
        self.update()

    _anim_pos = Property(float, _get_anim_pos, _set_anim_pos)

    # ── Events ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            new_state = not self._checked
            self.set_checked(new_state)
            self.toggled.emit(new_state)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._anim_value  # 0.0 = off, 1.0 = on

        rect = self.rect().adjusted(2, 2, -2, -2)
        rx = rect.height() / 2

        # ── Track ──────────────────────────────────────────────────────────────
        off_track = QColor(*DEEP_BLUE_RGB)
        off_track.setAlpha(220)
        on_r = int(ACCENT_CYAN_RGB[0] * t + DEEP_BLUE_RGB[0] * (1 - t))
        on_g = int(ACCENT_CYAN_RGB[1] * t + DEEP_BLUE_RGB[1] * (1 - t))
        on_b = int(ACCENT_CYAN_RGB[2] * t + DEEP_BLUE_RGB[2] * (1 - t))
        track_color = QColor(on_r, on_g, on_b, 200)

        painter.setBrush(track_color)
        border_alpha = int(60 + 120 * t)
        painter.setPen(QPen(QColor(*ACCENT_CYAN_RGB, border_alpha), 1))
        painter.drawRoundedRect(rect, rx, rx)

        # ── Thumb ──────────────────────────────────────────────────────────────
        thumb_d = rect.height() - _THUMB_PAD * 2
        travel = rect.width() - thumb_d - _THUMB_PAD * 2
        thumb_x = int(rect.x() + _THUMB_PAD + travel * t)
        thumb_y = rect.y() + _THUMB_PAD

        thumb_color = QColor(
            int(230 - 30 * (1 - t)),
            int(237 - 40 * (1 - t)),
            int(247 - 50 * (1 - t)),
            240,
        )
        painter.setBrush(thumb_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(thumb_x, thumb_y, thumb_d, thumb_d)

        painter.end()

