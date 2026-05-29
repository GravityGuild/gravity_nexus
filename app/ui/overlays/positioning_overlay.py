"""PositioningOverlay — draggable placeholder used while positioning overlays.

Each registered overlay type gets one of these when the user enters
"Position Overlays" mode from the Overlays settings page.  The actual
overlay content is replaced by a crosshair label so the window is light-
weight and clearly marked as a positioning aid.
"""
from __future__ import annotations

from typing import Optional, cast

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from theme.colors import ACCENT_CYAN_RGB, SUCCESS
from theme.spec import ColorRole, FontSize
from ui.overlays.base_overlay_window import BaseOverlayWindow
from ui.widgets.icon_label import icon_pixmap, inline_icon_html, AppIcon
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel


class PositioningOverlay(BaseOverlayWindow):
    """Transparent, draggable placeholder used to set the saved position
    of an overlay whose key is *overlay_key*.

    Parameters
    ----------
    overlay_key:
        The string key used in ``OverlaySettings.positions`` (e.g.
        ``"raid_submit"``).
    display_label:
        Human-readable name shown inside the placeholder (e.g.
        ``"Raid Submit"``).
    default_size:
        ``(width, height)`` matching the real overlay so the placeholder
        occupies the same screen area.
    """

    saved = Signal(str)      # emits overlay_key
    cancelled = Signal(str)  # emits overlay_key

    def __init__(
        self,
        overlay_key: str,
        display_label: str,
        default_size: tuple[int, int] = (460, 320),
        show_body: bool = True,
        min_size: tuple[int, int] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(f"{display_label}", parent)
        self._button_height = 32
        self._button_width = 32

        self._overlay_key = overlay_key
        if show_body:
            self._build_positioning_content()
        self._build_button_row()
        self.resize(*default_size)
        if not show_body:
            self.setFixedHeight(default_size[1])
        if min_size is not None:
            self.setMinimumSize(*min_size)
        self._reposition_buttons()
        self._setup_body_drag()

    # ── Public ─────────────────────────────────────────────────────────────────

    @property
    def overlay_key(self) -> str:
        return self._overlay_key

    # ── Internal ───────────────────────────────────────────────────────────────

    def _build_positioning_content(self) -> None:
        r, g, b = ACCENT_CYAN_RGB
        _check_icon = inline_icon_html(AppIcon.CHECK_BOLD, size=13, color=SUCCESS)
        arrow_all_icon = inline_icon_html(AppIcon.ARROW_ALL, size=18, color=QColor(r, g, b, 200))
        hint = ThemedLabel(
            f"{arrow_all_icon} drag to reposition",
            font_size=FontSize.MEDIUM,
            color_role=ColorRole.ACCENT_PRIMARY,
            word_wrap=True,
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(hint)

    def _build_button_row(self) -> None:
        self._save_btn = ThemedButton("", ThemedButton.VARIANT_PRIMARY)
        self._save_btn.setIcon(QIcon(icon_pixmap(AppIcon.CHECK_BOLD, size=14, color=SUCCESS)))
        self._save_btn.setToolTip("Save position")
        self._save_btn.setFixedSize(self._button_width, self._button_height)
        self._save_btn.setStyleSheet("min-height: 0px; padding: 2px 4px;")
        self._save_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._save_btn.clicked.connect(self._on_save)

        self._cancel_btn = ThemedButton("", ThemedButton.VARIANT_GHOST)
        self._cancel_btn.setIcon(QIcon(icon_pixmap(AppIcon.CLOSE, size=14)))
        self._cancel_btn.setToolTip("Restore original position")
        self._cancel_btn.setFixedSize(self._button_width, self._button_height)
        self._cancel_btn.setStyleSheet("min-height: 0px; padding: 2px 4px;")
        self._cancel_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)

        # Float the buttons as direct children of the overlay window so they
        # don't touch the frame layout.  _reposition_buttons keeps them pinned
        # to the top-right of the handle bar area whenever the window resizes.
        self._save_btn.setParent(self)
        self._cancel_btn.setParent(self)
        self._save_btn.raise_()
        self._cancel_btn.raise_()
        self._save_btn.show()
        self._cancel_btn.show()

        # Reserve title-text space so the painted title doesn't run into the buttons.
        # cancel(32) + gap(4) + save(32) + right-pad(4) = 72 px from frame edge
        self._handle.set_right_reserved(72)

    def _reposition_buttons(self) -> None:
        """Pin the floating buttons to the top-right of the handle bar area."""
        _SHADOW = 6   # BaseOverlayWindow outer margin
        _HANDLE_H = 24
        y = _SHADOW + 8 + (_HANDLE_H - self._button_height) // 2
        save_x = self.width() - _SHADOW - 4 - self._button_width
        self._save_btn.move(save_x, y)
        self._cancel_btn.move(save_x - 4 - self._button_width, y)

    def _on_save(self) -> None:
        self.saved.emit(self._overlay_key)

    def _on_cancel(self) -> None:
        self.cancelled.emit(self._overlay_key)

    def _setup_body_drag(self) -> None:
        """Make the content area draggable so clicking anywhere moves the overlay."""
        targets = [self._content_widget, *self._content_widget.findChildren(QWidget)]
        for w in targets:
            w.installEventFilter(self)
            w.setCursor(Qt.CursorShape.SizeAllCursor)

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: ANN001
        t = event.type()
        if t in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.MouseButtonRelease):
            me = cast(QMouseEvent, event)
            if t == QEvent.Type.MouseButtonPress and me.button() == Qt.MouseButton.LeftButton:
                self.start_drag(me.globalPosition().toPoint())
                return True
            if t == QEvent.Type.MouseMove and me.buttons() & Qt.MouseButton.LeftButton:
                self.do_drag(me.globalPosition().toPoint())
                return True
            if t == QEvent.Type.MouseButtonRelease and me.button() == Qt.MouseButton.LeftButton:
                self.stop_drag()
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._reposition_buttons()

    # ── Painting — dashed border to distinguish from real overlays ─────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r, g, b = ACCENT_CYAN_RGB
        pen = QPen(QColor(r, g, b, 80))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        rect = self.rect().adjusted(8, 8, -8, -8)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.drawPath(path)
        p.end()
