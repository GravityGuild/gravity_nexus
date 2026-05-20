"""BaseOverlayWindow — frameless, transparent, always-on-top overlay base class.

Subclass this to create domain-specific overlay panels (DPS, timers, etc.).
Click-through mode uses Win32 on Windows; it is silently ignored elsewhere.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from theme.colors import ACCENT_CYAN_RGB, NAVY_BG_RGB
from utils.platform_utils import set_window_click_through


class BaseOverlayWindow(QWidget):
    """Frameless, translucent, always-on-top overlay base.

    Features
    --------
    - Draggable via left-mouse on the handle bar area.
    - ``set_click_through(True)`` makes the window transparent to mouse events
      on Windows (Win32 WS_EX_TRANSPARENT); no-op on other platforms.
    - ``set_overlay_opacity(0.0 – 1.0)`` controls window-level opacity.
    - Subclasses add content to ``self.content_layout`` (a QVBoxLayout).
    """

    def __init__(
        self,
        title: str = "Overlay",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._title = title
        self._click_through = False
        self._drag_pos: Optional[QPoint] = None

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)  # shadow margin
        outer.setSpacing(0)

        self._frame = QWidget()
        self._frame.setObjectName("BaseOverlay")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Handle bar (drag target + title)
        self._handle = _HandleBar(self._title, self)
        self._handle.setObjectName("OverlayHandleBar")
        frame_layout.addWidget(self._handle)

        # Content area — subclasses populate this
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self._content_widget)
        self.content_layout.setContentsMargins(8, 6, 8, 8)
        self.content_layout.setSpacing(6)
        frame_layout.addWidget(self._content_widget)

        outer.addWidget(self._frame)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_click_through(self, enabled: bool) -> None:
        """Enable or disable Win32 click-through mode."""
        hwnd = int(self.winId())
        ok = set_window_click_through(hwnd, enabled)
        if ok:
            self._click_through = enabled

    @property
    def click_through(self) -> bool:
        return self._click_through

    def set_overlay_opacity(self, opacity: float) -> None:
        """Set window opacity in the range 0.0 – 1.0."""
        self.setWindowOpacity(max(0.1, min(1.0, opacity)))

    # ── Drag support ───────────────────────────────────────────────────────────

    def start_drag(self, pos: QPoint) -> None:
        self._drag_pos = pos

    def do_drag(self, pos: QPoint) -> None:
        if self._drag_pos is not None:
            delta = pos - self._drag_pos
            self.move(self.pos() + delta)

    def stop_drag(self) -> None:
        self._drag_pos = None

    # ── Painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        # Semi-transparent drop-shadow via the outer margin
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        shadow = QColor(0, 0, 0, 60)
        for i in range(5, 0, -1):
            shadow.setAlpha(12 * i)
            p.setPen(QPen(shadow, i * 2))
            p.drawRoundedRect(self.rect().adjusted(i, i, -i, -i), 10, 10)
        p.end()


# ── Private handle bar ────────────────────────────────────────────────────────


class _HandleBar(QWidget):
    """Thin drag bar at the top of an overlay window."""

    def __init__(self, title: str, overlay: BaseOverlayWindow) -> None:
        super().__init__(overlay)
        self._overlay = overlay
        self._title = title
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._overlay.start_drag(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._overlay.do_drag(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._overlay.stop_drag()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(*ACCENT_CYAN_RGB, 180))
        p.setFont(self.font())
        p.drawText(
            self.rect().adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"◈  {self._title}",
        )
        p.end()

