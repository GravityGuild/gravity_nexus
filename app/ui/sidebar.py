"""Sidebar — navigation panel with animated buttons and status display."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QAbstractButton,
)

from theme.colors import (
    ACCENT_CYAN_RGB,
    ACCENT_GOLD_RGB,
    CARD_BG_RGB,
    NAVY_BG_RGB,
    TEXT_PRIMARY_RGB,
    TEXT_SECONDARY_RGB,
)

# Navigation item definitions: (label, icon, page_index)
NAV_ITEMS: list[tuple[str, str, int]] = [
    ("General", "⚙", 0),
    ("Overlays", "◈", 1),
    ("Parsing", "⟨/⟩", 2),
    ("Notifications", "🔔", 3),
    ("Appearance", "◑", 4),
    ("Profiles", "◻", 5),
    ("Advanced", "⊛", 6),
    ("About", "◎", 7),
]


class NavButton(QAbstractButton):
    """Animated sidebar navigation button with selected-state glow."""

    def __init__(
        self,
        label: str,
        icon: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._icon = icon
        self._selected = False
        self._hover_value: float = 0.0

        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"_hover_anim", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # ── Selection state ────────────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    @property
    def is_selected(self) -> bool:
        return self._selected

    # ── Qt property for hover animation ───────────────────────────────────────

    def _get_hover(self) -> float:
        return self._hover_value

    def _set_hover(self, v: float) -> None:
        self._hover_value = v
        self.update()

    from PySide6.QtCore import Property as _Prop
    _hover_anim = _Prop(float, _get_hover, _set_hover)

    # ── Events ─────────────────────────────────────────────────────────────────

    def enterEvent(self, event) -> None:  # noqa: ANN001
        if not self._selected:
            self._anim.stop()
            self._anim.setStartValue(self._hover_value)
            self._anim.setEndValue(1.0)
            self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        if not self._selected:
            self._anim.stop()
            self._anim.setStartValue(self._hover_value)
            self._anim.setEndValue(0.0)
            self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r = self.rect()

        if self._selected:
            # Selected: solid accent background + left glow bar
            bg = QColor(*ACCENT_CYAN_RGB, 28)
            p.fillRect(r, bg)

            # Left accent bar
            accent_bar_color = QColor(*ACCENT_CYAN_RGB, 220)
            p.setBrush(accent_bar_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 6, 3, r.height() - 12, 2, 2)

            text_color = QColor(*TEXT_PRIMARY_RGB)
            icon_color = QColor(*ACCENT_CYAN_RGB)

        elif self._hover_value > 0.001:
            # Hover: animated fade
            alpha = int(22 * self._hover_value)
            p.fillRect(r, QColor(*ACCENT_CYAN_RGB, alpha))
            text_color = QColor(
                int(TEXT_PRIMARY_RGB[0]),
                int(TEXT_PRIMARY_RGB[1]),
                int(TEXT_PRIMARY_RGB[2]),
                int(180 + 75 * self._hover_value),
            )
            icon_color = QColor(
                *ACCENT_CYAN_RGB,
                int(140 + 80 * self._hover_value),
            )
        else:
            text_color = QColor(*TEXT_SECONDARY_RGB)
            icon_color = QColor(*TEXT_SECONDARY_RGB, 160)

        # Icon
        icon_font = self.font()
        icon_font.setPointSize(14)
        p.setFont(icon_font)
        p.setPen(icon_color)
        icon_rect = r.adjusted(16, 0, -(r.width() - 44), 0)
        p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self._icon)

        # Label
        label_font = self.font()
        label_font.setPointSize(12)
        if self._selected:
            label_font.setWeight(label_font.Weight.Medium)
        p.setFont(label_font)
        p.setPen(text_color)
        label_rect = r.adjusted(50, 0, -10, 0)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        p.end()


class Sidebar(QWidget):
    """Left sidebar with logo, navigation, and parser status."""

    page_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)

        self._nav_buttons: list[NavButton] = []
        self._active_index = 0

        self._build_ui()
        self._select(0)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # layout.addWidget(self._build_logo())
        # layout.addSpacing(8)
        layout.addWidget(self._build_nav_section())
        layout.addStretch()
        layout.addWidget(self._build_status())
        layout.addSpacing(8)

    def _build_logo(self) -> QWidget:
        logo_area = QWidget()
        logo_area.setObjectName("SidebarLogoArea")
        logo_area.setFixedHeight(74)
        vl = QVBoxLayout(logo_area)
        vl.setContentsMargins(16, 12, 16, 10)
        vl.setSpacing(3)

        title = QLabel("GRAVITY NEXUS")
        title.setObjectName("SidebarLogoTitle")
        vl.addWidget(title)

        sub = QLabel("EQ OVERLAY PARSER v1.0")
        sub.setObjectName("SidebarLogoSub")
        vl.addWidget(sub)

        return logo_area

    def _build_nav_section(self) -> QWidget:
        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(4, 0, 4, 0)
        vl.setSpacing(2)

        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("SidebarSectionLabel")
        vl.addWidget(nav_label)

        for label, icon, page_idx in NAV_ITEMS:
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda checked=False, idx=page_idx: self._on_nav_clicked(idx))
            self._nav_buttons.append(btn)
            vl.addWidget(btn)

        return container

    def _build_status(self) -> QWidget:
        status_widget = QWidget()
        status_widget.setObjectName("ParseStatusWidget")
        vl = QVBoxLayout(status_widget)
        vl.setContentsMargins(16, 10, 12, 10)
        vl.setSpacing(4)

        label = QLabel("PARSER STATUS")
        label.setObjectName("ParseStatusLabel")
        vl.addWidget(label)

        hl = QHBoxLayout()
        dot = _StatusDot("offline")
        hl.addWidget(dot)
        self._status_text = QLabel("Not running")
        self._status_text.setObjectName("StatusBarText")
        self._status_text.setStyleSheet("color: #93A4C3; font-size: 11px;")
        hl.addWidget(self._status_text)
        hl.addStretch()
        vl.addLayout(hl)

        return status_widget

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_nav_clicked(self, index: int) -> None:
        self._select(index)
        self.page_requested.emit(index)

    def _select(self, index: int) -> None:
        for i, btn in enumerate(self._nav_buttons):
            btn.set_selected(i == index)
        self._active_index = index

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_active_page(self, index: int) -> None:
        self._select(index)

    def set_parser_status(self, running: bool, log_name: str = "") -> None:
        if running:
            self._status_text.setText(log_name or "Running")
        else:
            self._status_text.setText("Not running")


class _StatusDot(QWidget):
    def __init__(self, status: str = "offline") -> None:
        super().__init__()
        self._status = status
        self.setFixedSize(8, 8)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        colors = {
            "online": SUCCESS_RGB if "SUCCESS_RGB" in dir() else (120, 224, 143),
            "offline": TEXT_SECONDARY_RGB if "TEXT_SECONDARY_RGB" in dir() else (147, 164, 195),
        }
        from theme.colors import SUCCESS_RGB, TEXT_SECONDARY_RGB  # noqa: PLC0415
        rgb = SUCCESS_RGB if self._status == "online" else TEXT_SECONDARY_RGB
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*rgb, 200))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 6, 6)
        p.end()

