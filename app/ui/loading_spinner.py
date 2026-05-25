"""LoadingSpinner — frameless startup splash shown while authenticating."""
from __future__ import annotations

import random
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from theme.spec import ColorRole, FontRole, FontSize
from ui.widgets.themed_label import ThemedLabel


# ── Animated arc ───────────────────────────────────────────────────────────────

class _SpinnerArc(QWidget):
    """A rotating arc drawn with QPainter, driven by an internal QTimer."""

    def __init__(self, size: int = 64, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

    def _tick(self) -> None:
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        pen_w = max(4, size // 10)
        margin = pen_w / 2 + 1.0
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        # Dim background ring
        bg_pen = QPen(QColor(87, 199, 255, 28))
        bg_pen.setWidth(pen_w)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Bright animated arc
        arc_pen = QPen(QColor(87, 199, 255, 220))
        arc_pen.setWidth(pen_w)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        start = int((90 - self._angle) * 16)
        span = int(-110 * 16)
        painter.drawArc(rect, start, span)


# ── Card background widget ─────────────────────────────────────────────────────

class _CardWidget(QWidget):
    """Inner widget that paints the card background; transparent shell is handled by the parent."""

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())

        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)

        # Gradient matching the app's #AppContent
        gradient = QLinearGradient(
            rect.x(),
            rect.y(),
            rect.x() + rect.width() * 0.4,
            rect.y() + rect.height(),
        )
        gradient.setColorAt(0.00, QColor(0x0B, 0x17, 0x30))
        gradient.setColorAt(0.45, QColor(0x08, 0x11, 0x20))
        gradient.setColorAt(1.00, QColor(0x0B, 0x17, 0x30))

        painter.fillPath(path, QBrush(gradient))

        painter.setPen(QPen(QColor(87, 199, 255, 30), 1.0))
        painter.drawPath(path)


# ── Public splash window ───────────────────────────────────────────────────────

_FUNNY_SAYINGS = [
    "Looking for more clerics…",
    "Cothing to trips…",
    "BPing yael…",
    "Tunnelquesting…",
    "Spending Diikembe's DKP…",
    "Sending buff requests…",
    "Looking for my corpse…",
    "LOADING, PLEASE WAIT…",
    "You feel yourself starting to appear…",
    "Train to zone!",
    "Sending Valick back to VP…",
    "Thanking Heelur for making me…",
    "Who let Kueryenya ramp tank?"
]


class LoadingSpinner(QWidget):
    """Frameless, always-on-top splash shown immediately on startup.

    Call ``set_status(text)`` to update the status line.
    Call ``close()`` to dismiss before the login dialog or main window appears.
    """

    _SHADOW_MARGIN = 20
    _SAYING_INTERVAL_MS = 2500

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keeps it out of the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setFixedSize(360, 280)
        self._build_ui()
        self._center_on_screen()
        self._start_saying_cycle()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        m = self._SHADOW_MARGIN

        # Outer transparent layout — provides room for the drop shadow
        outer = QVBoxLayout(self)
        outer.setContentsMargins(m, m, m, m)
        outer.setSpacing(0)

        # Inner card with painted background
        card = _CardWidget()

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 26)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = ThemedLabel(
            "GRAVITY NEXUS",
            font_size=FontSize.LARGE,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.ACCENT_ALT,
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        card_layout.addSpacing(6)

        # Subtitle
        subtitle = ThemedLabel(
            "Loading…",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(30)

        # Spinner arc
        arc_row = QHBoxLayout()
        arc_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arc = _SpinnerArc(size=64)
        arc_row.addWidget(self._arc)
        card_layout.addLayout(arc_row)
        card_layout.addSpacing(22)

        # Status line
        self._status_label = ThemedLabel(
            "Authenticating…",
            font_size=FontSize.TINY,
            color_role=ColorRole.TEXT_MUTED,
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._status_label)

        outer.addWidget(card)

    # ── Saying cycle ──────────────────────────────────────────────────────────

    def _start_saying_cycle(self) -> None:
        self._saying_pool = random.sample(_FUNNY_SAYINGS, len(_FUNNY_SAYINGS))
        self._saying_index = 0
        self._saying_timer = QTimer(self)
        self._saying_timer.timeout.connect(self._next_saying)
        self._saying_timer.start(self._SAYING_INTERVAL_MS)
        self._next_saying()

    def _next_saying(self) -> None:
        self._status_label.setText(self._saying_pool[self._saying_index])
        self._saying_index = (self._saying_index + 1) % len(self._saying_pool)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        """Update the status text shown beneath the spinner."""
        self._saying_timer.stop()
        self._status_label.setText(text)

    # ── Positioning ───────────────────────────────────────────────────────────

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.center().x() - self.width() // 2,
                sg.center().y() - self.height() // 2,
            )
