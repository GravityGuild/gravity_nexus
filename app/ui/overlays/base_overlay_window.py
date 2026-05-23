"""BaseOverlayWindow — frameless, transparent, always-on-top overlay base class.

Subclass this to create domain-specific overlay panels (DPS, timers, etc.).
Click-through mode uses Win32 on Windows; it is silently ignored elsewhere.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from theme.colors import ACCENT_CYAN_RGB, TEXT_PRIMARY_RGB
from utils.platform_utils import set_window_click_through

# Minimum size the overlay may be shrunk to (pixels)
_MIN_W = 120
_MIN_H = 60
# Size of the invisible corner grab area
_GRIP = 14


class _Corner(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class BaseOverlayWindow(QWidget):
    """Frameless, translucent, always-on-top overlay base.

    Features
    --------
    - Draggable via left-mouse on the handle bar area.
    - Corner-drag resizing via invisible grip widgets at each corner.
    - ``set_click_through(True)`` makes the window transparent to mouse events
      on Windows (Win32 WS_EX_TRANSPARENT); no-op on other platforms.
    - ``set_overlay_opacity(0.0 – 1.0)`` controls window-level opacity.
    - ``set_overlay_scale(0.5 – 3.0)`` scales the window size proportionally
      relative to the natural (100%) size set by the subclass via ``resize()``.
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
        self._base_size: Optional[tuple[int, int]] = None  # captured on first scale call
        self._overlay_scale: float = 1.0
        self._corner_grips: list[_CornerGrip] = []

        self._build_ui()
        self._build_corner_grips()

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
        self.content_layout = QVBoxLayout(self._content_widget)
        self.content_layout.setContentsMargins(8, 6, 8, 8)
        self.content_layout.setSpacing(6)
        frame_layout.addWidget(self._content_widget)

        outer.addWidget(self._frame)

    def _build_corner_grips(self) -> None:
        for corner in _Corner:
            grip = _CornerGrip(corner, self)
            self._corner_grips.append(grip)
            grip.raise_()
        self._reposition_grips()

    def _reposition_grips(self) -> None:
        w, h = self.width(), self.height()
        g = _GRIP
        for grip in self._corner_grips:
            c = grip.corner
            if c == _Corner.TOP_LEFT:
                grip.move(0, 0)
            elif c == _Corner.TOP_RIGHT:
                grip.move(w - g, 0)
            elif c == _Corner.BOTTOM_LEFT:
                grip.move(0, h - g)
            elif c == _Corner.BOTTOM_RIGHT:
                grip.move(w - g, h - g)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._reposition_grips()

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

    def set_overlay_scale(self, scale: float) -> None:
        """Resize the window proportionally to *scale* (1.0 = 100%).

        The first time this is called the current window size is stored as the
        100 % baseline.  Subsequent calls resize relative to that baseline so
        calling ``set_overlay_scale(1.25)`` twice in a row is idempotent.
        """
        scale = max(0.25, min(4.0, scale))
        if self._base_size is None:
            s = self.size()
            self._base_size = (s.width(), s.height())
        bw, bh = self._base_size
        self._overlay_scale = scale
        self.resize(max(80, round(bw * scale)), max(40, round(bh * scale)))

    @property
    def overlay_scale(self) -> float:
        """Currently applied scale factor."""
        return self._overlay_scale

    # ── Drag support ───────────────────────────────────────────────────────────

    def start_drag(self, pos: QPoint) -> None:
        self._drag_pos = pos

    def do_drag(self, pos: QPoint) -> None:
        if self._drag_pos is not None:
            delta = pos - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = pos  # advance reference so delta stays incremental

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

        font = p.font()
        font.setPointSize(14)
        p.setFont(font)

        rect = self.rect().adjusted(8, 0, -8, 0)
        align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # Draw accent glyph in cyan
        p.setPen(QColor(*ACCENT_CYAN_RGB))
        p.drawText(rect, align, "◈  ")

        # Measure glyph width so title text starts after it
        glyph_w = p.fontMetrics().horizontalAdvance("◈  ")
        title_rect = rect.adjusted(glyph_w, 0, 0, 0)

        # Draw title in high-contrast primary text colour
        p.setPen(QColor(*TEXT_PRIMARY_RGB))
        p.drawText(title_rect, align, self._title)

        p.end()


# ── Corner resize grips ───────────────────────────────────────────────────────


class _CornerGrip(QWidget):
    """Invisible grab widget placed at each corner of a ``BaseOverlayWindow``.

    Dragging any corner resizes the window in the appropriate direction while
    keeping the opposite corner anchored to the screen.
    """

    # Cursors for each corner
    _CURSORS = {
        _Corner.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
        _Corner.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
        _Corner.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
        _Corner.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    }

    def __init__(self, corner: _Corner, overlay: "BaseOverlayWindow") -> None:
        super().__init__(overlay)
        self._corner = corner
        self._overlay = overlay
        self._drag_start_global: Optional[QPoint] = None
        self._drag_start_geo: Optional[QRect] = None

        self.setFixedSize(_GRIP, _GRIP)
        self.setCursor(self._CURSORS[corner])
        # Transparent so it doesn't obscure the shadow/content
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    @property
    def corner(self) -> _Corner:
        return self._corner

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_global = event.globalPosition().toPoint()
            geo = self._overlay.geometry()
            self._drag_start_geo = QRect(geo)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_global is None or self._drag_start_geo is None:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        delta = event.globalPosition().toPoint() - self._drag_start_global
        geo = QRect(self._drag_start_geo)
        dx, dy = delta.x(), delta.y()

        if self._corner == _Corner.TOP_LEFT:
            geo.setLeft(min(geo.left() + dx, geo.right() - _MIN_W))
            geo.setTop(min(geo.top() + dy, geo.bottom() - _MIN_H))
        elif self._corner == _Corner.TOP_RIGHT:
            geo.setRight(max(geo.right() + dx, geo.left() + _MIN_W))
            geo.setTop(min(geo.top() + dy, geo.bottom() - _MIN_H))
        elif self._corner == _Corner.BOTTOM_LEFT:
            geo.setLeft(min(geo.left() + dx, geo.right() - _MIN_W))
            geo.setBottom(max(geo.bottom() + dy, geo.top() + _MIN_H))
        elif self._corner == _Corner.BOTTOM_RIGHT:
            geo.setRight(max(geo.right() + dx, geo.left() + _MIN_W))
            geo.setBottom(max(geo.bottom() + dy, geo.top() + _MIN_H))

        self._overlay.setGeometry(geo)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start_global = None
        self._drag_start_geo = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        """Draw a subtle accent triangle in the corner as a visual hint."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r, g, b = ACCENT_CYAN_RGB
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(r, g, b, 60))

        size = _GRIP - 2
        c = self._corner
        from PySide6.QtGui import QPolygon  # noqa: PLC0415
        from PySide6.QtCore import QPoint as _QP  # noqa: PLC0415
        if c == _Corner.BOTTOM_RIGHT:
            pts = [_QP(size, 0), _QP(size, size), _QP(0, size)]
        elif c == _Corner.BOTTOM_LEFT:
            pts = [_QP(0, 0), _QP(size, size), _QP(0, size)]
        elif c == _Corner.TOP_RIGHT:
            pts = [_QP(0, 0), _QP(size, 0), _QP(size, size)]
        else:  # TOP_LEFT
            pts = [_QP(0, 0), _QP(size, 0), _QP(0, size)]

        p.drawPolygon(QPolygon(pts))
        p.end()

