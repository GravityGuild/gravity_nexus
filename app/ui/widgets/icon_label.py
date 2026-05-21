"""icon_label.py — reusable inline icon + text label widget.

Provides
--------
``AppIcon``
    Enum of every SVG / PNG icon bundled in ``app/assets/icons/``.
    IDE auto-complete shows all valid values.

``icon_pixmap(icon, size, color)``
    Standalone helper — returns a tinted ``QPixmap`` you can drop into any
    ``QLabel``, ``QPainter`` call, button, etc.

``IconLabel``
    Drop-in ``QWidget`` that renders ``[icon]  [optional text]`` in one line.
    Both the icon and colour can be swapped at runtime.

Quick examples::

    from ui.widgets.icon_label import AppIcon, IconLabel, icon_pixmap
    from theme.colors import ACCENT_CYAN_RGB, ERROR_RGB

    # Standalone pixmap (for use elsewhere — e.g. inside a QPainter)
    px = icon_pixmap(AppIcon.BELL, size=20, color=ACCENT_CYAN_RGB)

    # Icon-only widget
    dot = IconLabel(AppIcon.INFORMATION, color="#57C7FF", size=14)

    # Icon + text
    lbl = IconLabel(AppIcon.ROBOT, "Bot connected", color=ACCENT_CYAN_RGB, size=16)

    # Change at runtime
    lbl.set_icon(AppIcon.BELL_OUTLINE)
    lbl.set_color(ERROR_RGB)
    lbl.set_text("Disconnected")
"""
from __future__ import annotations

import base64
from enum import Enum
from typing import Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from utils.resource_utils import get_asset


# ── Icon catalogue ────────────────────────────────────────────────────────────


class AppIcon(str, Enum):
    """Every icon available in ``app/assets/icons/``.

    The enum value is the bare filename; ``icon_pixmap`` and ``IconLabel``
    resolve the full path automatically via ``get_asset``.
    """

    APPLICATION_BRACKETS = "application-brackets-outline.svg"
    ARROW_ALL = "arrow-all.svg"
    ARROW_EXPAND_ALL = "arrow-expand-all.svg"
    BELL = "bell.svg"
    BELL_OUTLINE = "bell-outline.svg"
    CHART_TIMELINE_VARIANT = "chart-timeline-variant.svg"
    CHECK = "check.svg"
    CHECK_BOLD = "check-bold.svg"
    CLOSE = "close.svg"
    CLOSE_THICK = "close-thick.svg"
    CODE_BRACES = "code-braces.svg"
    CODE_GREATER_THAN = "code-greater-than.svg"
    CROSSHAIRS = "crosshairs.svg"
    HAMMER_WRENCH = "hammer-wrench.svg"
    HOME = "home.svg"
    HOME_CIRCLE_OUTLINE = "home-circle-outline.svg"
    INFORMATION = "information.svg"
    INFORMATION_OUTLINE = "information-outline.svg"
    MONITOR = "monitor.svg"
    MONITOR_DASHBOARD = "monitor-dashboard.svg"
    PALETTE = "palette.svg"
    PALETTE_OUTLINE = "palette-outline.svg"
    ROBOT = "robot.svg"
    ROBOT_OUTLINE = "robot-outline.svg"
    ROBOT_HAPPY = "robot-happy.svg"
    ROBOT_HAPPY_OUTLINE = "robot-happy-outline.svg"
    TEST_TUBE = "test-tube.svg"
    VECTOR_ARRANGE_ABOVE = "vector-arrange-above.svg"


# ── Colour input type ─────────────────────────────────────────────────────────

#: Anything accepted as a colour: ``QColor``, ``(r, g, b)`` tuple, or a CSS
#: hex / named colour string such as ``"#57C7FF"`` or ``"cyan"``.
ColorInput = Union[QColor, tuple[int, int, int], str]


def _to_qcolor(color: ColorInput) -> QColor:
    if isinstance(color, QColor):
        return color
    if isinstance(color, tuple):
        return QColor(*color)
    return QColor(color)  # hex string or named colour


# ── Standalone pixmap helper ──────────────────────────────────────────────────


def icon_pixmap(
    icon: Union[AppIcon, str],
    size: int = 20,
    color: ColorInput = "#E6EDF7",
) -> QPixmap:
    """Return a *size* × *size* tinted ``QPixmap`` for *icon*.

    Parameters
    ----------
    icon:
        An :class:`AppIcon` member **or** a bare filename string
        (e.g. ``"bell.svg"``).  The file is looked up inside
        ``app/assets/icons/``.
    size:
        Square edge length in pixels for the output pixmap.
    color:
        Tint colour — accepts ``QColor``, ``(r, g, b)`` tuple, or any CSS
        hex / named colour string.

    Returns
    -------
    QPixmap
        Fully transparent background; icon shape filled with *color*.
        Returns a blank *size* × *size* pixmap if the file cannot be loaded.

    Examples
    --------
    >>> px = icon_pixmap(AppIcon.BELL, size=18, color=(87, 199, 255))
    >>> px = icon_pixmap("robot.svg", color="#FF6B6B")
    """
    filename = icon.value if isinstance(icon, AppIcon) else icon
    src = QPixmap(str(get_asset(f"icons/{filename}")))

    if src.isNull():
        blank = QPixmap(size, size)
        blank.fill(Qt.GlobalColor.transparent)
        return blank

    scaled = src.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    result = QPixmap(scaled.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, scaled)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), _to_qcolor(color))
    painter.end()
    return result


def inline_icon_html(
    icon: Union[AppIcon, str],
    size: int = 14,
    color: ColorInput = "#E6EDF7",
    vertical_align: str = "middle",
) -> str:
    """Return an HTML ``<img>`` snippet for embedding an icon inside a ``QLabel`` rich-text string.

    The pixmap is base64-encoded so no external file path is required at
    render time.  The result can be spliced directly into any HTML string
    that is set on a ``QLabel`` with ``Qt.TextFormat.RichText``.

    Parameters
    ----------
    icon:
        :class:`AppIcon` member or bare filename string.
    size:
        Square edge length in pixels (default ``14`` — matches body text).
    color:
        Tint colour — ``QColor``, ``(r, g, b)`` tuple, or CSS hex/name string.
    vertical_align:
        CSS ``vertical-align`` value (default ``"middle"``).

    Returns
    -------
    str
        An ``<img src="data:image/png;base64,…" …>`` HTML snippet.

    Examples
    --------
    Build a subtitle string with an inline check icon::

        from ui.widgets.icon_label import AppIcon, inline_icon_html
        from theme.colors import SUCCESS

        check = inline_icon_html(AppIcon.CHECK_BOLD, size=13, color=SUCCESS)
        html = f"Click  {check} Save Positions  when you are done."
        card.set_subtitle_html(html)
    """
    px = icon_pixmap(icon, size, color)
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    px.save(buf, "PNG")
    b64 = base64.b64encode(bytes(buf.data())).decode("ascii")
    buf.close()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'width="{size}" height="{size}" '
        f'style="vertical-align:{vertical_align};">'
    )


# ── IconLabel widget ──────────────────────────────────────────────────────────


class IconLabel(QWidget):
    """Widget that renders ``[icon]  [optional text]`` on a single line.

    Both the icon and its colour can be updated at runtime without recreating
    the widget.

    Parameters
    ----------
    icon:
        :class:`AppIcon` member or bare filename string.
    text:
        Optional label text shown to the right of the icon.  Pass ``""``
        (default) for an icon-only widget.
    color:
        Icon tint — ``QColor``, ``(r, g, b)`` tuple, or CSS hex/name string.
        Defaults to the theme's primary text colour.
    size:
        Icon square size in pixels (default ``16``).
    spacing:
        Gap in pixels between the icon and the text label (default ``6``).
    parent:
        Optional parent widget.

    Examples
    --------
    >>> # Icon only
    >>> w = IconLabel(AppIcon.BELL, color=(87, 199, 255))

    >>> # Icon + text, themed danger colour
    >>> w = IconLabel(AppIcon.INFORMATION, "Warning!", color="#FF6B6B", size=14)

    >>> # Change everything at runtime
    >>> w.set_icon(AppIcon.ROBOT_HAPPY)
    >>> w.set_color((120, 224, 143))
    >>> w.set_text("Online")
    """

    def __init__(
        self,
        icon: Union[AppIcon, str],
        text: str = "",
        *,
        color: ColorInput = "#E6EDF7",
        size: int = 16,
        spacing: int = 6,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self._color = _to_qcolor(color)
        self._size = size

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(size, size)
        self._icon_lbl.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(text)
        self._text_lbl.setVisible(bool(text))
        layout.addWidget(self._text_lbl)

        self._refresh_icon()

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_icon(self, icon: Union[AppIcon, str]) -> None:
        """Swap the displayed icon."""
        self._icon = icon
        self._refresh_icon()

    def set_color(self, color: ColorInput) -> None:
        """Change the icon tint colour."""
        self._color = _to_qcolor(color)
        self._refresh_icon()

    def set_text(self, text: str) -> None:
        """Update the text label.  Pass ``""`` to hide it."""
        self._text_lbl.setText(text)
        self._text_lbl.setVisible(bool(text))

    def set_size(self, size: int) -> None:
        """Resize the icon (does not affect the text label font)."""
        self._size = size
        self._icon_lbl.setFixedSize(size, size)
        self._refresh_icon()

    def text_label(self) -> QLabel:
        """Return the inner ``QLabel`` for fine-grained text styling."""
        return self._text_lbl

    def icon_label(self) -> QLabel:
        """Return the inner icon ``QLabel`` (holds the pixmap)."""
        return self._icon_lbl

    # ── Internal ───────────────────────────────────────────────────────────────

    def _refresh_icon(self) -> None:
        px = icon_pixmap(self._icon, self._size, self._color)
        self._icon_lbl.setPixmap(px)

