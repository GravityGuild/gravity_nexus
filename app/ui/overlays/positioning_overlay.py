"""PositioningOverlay — draggable placeholder used while positioning overlays.

Each registered overlay type gets one of these when the user enters
"Position Overlays" mode from the Overlays settings page.  The actual
overlay content is replaced by a crosshair label so the window is light-
weight and clearly marked as a positioning aid.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from theme.colors import ACCENT_CYAN_RGB, SUCCESS
from theme.spec import ColorRole, FontSize
from ui.overlays.base_overlay_window import BaseOverlayWindow
from ui.widgets.icon_label import inline_icon_html, AppIcon
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

    def __init__(
        self,
        overlay_key: str,
        display_label: str,
        default_size: tuple[int, int] = (460, 320),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(f"⊹  {display_label}  ·  POSITIONING MODE", parent)
        self._overlay_key = overlay_key
        self._build_positioning_content()
        self.resize(*default_size)

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
            f"{arrow_all_icon} drag to reposition<br><br>Click  {_check_icon} Save Positions  in the settings when done.",
            font_size=FontSize.MEDIUM,
            color_role=ColorRole.ACCENT_PRIMARY,
            word_wrap=True,
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(hint)

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
