"""Sidebar — navigation panel with animated buttons and status display."""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QAbstractButton,
)

from theme.colors import (
    ACCENT_CYAN_RGB,
    TEXT_PRIMARY_RGB,
    TEXT_SECONDARY_RGB,
)
from ui.widgets.icon_label import AppIcon, icon_pixmap


# Navigation item definitions: (label, icon, page_index, feature_flag_key | None)
# Items with a feature_flag_key are hidden unless that flag is enabled in settings.
# Items with label in _DEV_ONLY_LABELS are additionally hidden unless DEV_MODE=1.
_DEV_ONLY_LABELS: frozenset[str] = frozenset({"Dev Tools", "Feature Flags"})

NAV_ITEMS: list[tuple[str, AppIcon, int, str | None]] = [
    ("General",        AppIcon.HOME,                    0, None),
    ("Overlays",       AppIcon.MONITOR_DASHBOARD,       1, None),
    ("Parsing",        AppIcon.APPLICATION_BRACKETS,    2, None),
    ("Notifications",  AppIcon.BELL,                    3, "notifications_page"),
    ("Appearance",     AppIcon.PALETTE,                 4, None),
    ("Advanced",       AppIcon.HAMMER_WRENCH,           5, None),
    ("Gravity Bot",    AppIcon.ROBOT,                   6, None),
    ("Dev Tools",      AppIcon.TEST_TUBE,               7, None),
    ("Feature Flags",  AppIcon.CODE_BRACES,             8, None),
    ("About",          AppIcon.INFORMATION,             9, None),
]


class NavButton(QAbstractButton):
    """Animated sidebar navigation button with selected-state glow."""

    def __init__(
        self,
        label: str,
        icon: AppIcon,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._icon = icon
        self._selected = False
        self._hover_value: float = 0.0

        # Pre-render a white-tinted pixmap; opacity & colour are handled in paintEvent.
        self._icon_pixmap: QPixmap = icon_pixmap(icon, size=20, color=(255, 255, 255))

        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"_hover_anim", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # ── Selection state ────────────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if not selected:
            # Reset frozen hover state that built up while the button was selected.
            # If the cursor is still physically over this button keep it at 1.0 so
            # the normal hover highlight shows; otherwise snap to 0 immediately.
            self._anim.stop()
            self._hover_value = 1.0 if self.underMouse() else 0.0
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

        # Icon — pixmap or text/emoji
        # TODO: Update to use icon module
        icon_rect = r.adjusted(16, 0, -(r.width() - 44), 0)
        if self._icon_pixmap is not None:
            # Scale the pixmap to fit a 20×20 box centred in the icon slot
            icon_size = 20
            scaled = self._icon_pixmap.scaled(
                icon_size, icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            draw_x = icon_rect.x() + (icon_rect.width() - scaled.width()) // 2
            draw_y = icon_rect.y() + (icon_rect.height() - scaled.height()) // 2

            if self._selected:
                opacity = 1.0
            elif self._hover_value > 0.001:
                opacity = 0.55 + 0.45 * self._hover_value
            else:
                opacity = 0.55

            p.setOpacity(opacity)
            p.drawPixmap(draw_x, draw_y, scaled)
            p.setOpacity(1.0)
        else:
            icon_font = self.font()
            icon_font.setPointSize(14)
            p.setFont(icon_font)
            p.setPen(icon_color)
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
    logout_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)

        self._nav_buttons: list[NavButton] = []
        self._active_index = 0
        self._current_username: Optional[str] = None
        self._popup: Optional[_ProfilePopup] = None
        self._popup_visible_at_press = False

        self._build_ui()
        self._select(0)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # layout.addWidget(self._build_logo())
        # layout.addSpacing(8)
        layout.addWidget(self._build_nav_section())
        layout.addStretch()
        layout.addWidget(self._build_profile_section())
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

        from core.registry import registry                          # noqa: PLC0415
        from feature_flags import feature_enabled                   # noqa: PLC0415
        from services.protocols import ISettingsService             # noqa: PLC0415

        dev_mode = os.environ.get("DEV_MODE", "").lower() in ("1", "true", "yes")
        settings = registry.get(ISettingsService).settings
        for label, icon, page_idx, flag_key in NAV_ITEMS:
            if label in _DEV_ONLY_LABELS and not dev_mode:
                continue
            if flag_key and not feature_enabled(flag_key, settings):
                continue
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda checked=False, idx=page_idx: self._on_nav_clicked(idx))
            self._nav_buttons.append(btn)
            vl.addWidget(btn)

        return container

    def _build_profile_section(self) -> QWidget:
        self._profile_section = _ProfileSection()
        self._profile_section.clicked.connect(self._on_profile_clicked)
        return self._profile_section

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: ANN001
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
        ):
            section_rect = QRect(
                self._profile_section.mapToGlobal(QPoint(0, 0)),
                self._profile_section.size(),
            )
            if section_rect.contains(event.globalPosition().toPoint()):
                self._popup_visible_at_press = (
                    self._popup is not None and self._popup.isVisible()
                )
        return False

    def _on_profile_clicked(self) -> None:
        if self._popup_visible_at_press:
            self._popup_visible_at_press = False
            return
        self._popup = _ProfilePopup(self._current_username)
        self._popup.logout_clicked.connect(self.logout_requested)
        self._popup.setFixedWidth(self.width())
        self._popup.adjustSize()
        global_pos = self._profile_section.mapToGlobal(QPoint(0, 0))
        self._popup.move(global_pos.x(), global_pos.y() - self._popup.height() - 4)
        self._popup.show()

    # ── Public API (auth) ──────────────────────────────────────────────────────

    def set_user(self, username: str) -> None:
        self._current_username = username
        self._profile_section.set_user(username)

    def clear_user(self) -> None:
        self._current_username = None
        self._profile_section.clear_user()

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


class _StatusDot(QWidget):
    def __init__(self, status: str = "offline") -> None:
        super().__init__()
        self._status = status
        self.setFixedSize(8, 8)

    def set_status(self, status: str) -> None:
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        from theme.colors import SUCCESS_RGB, TEXT_SECONDARY_RGB  # noqa: PLC0415
        rgb = SUCCESS_RGB if self._status == "online" else TEXT_SECONDARY_RGB
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*rgb, 200))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 6, 6)
        p.end()


class _AvatarWidget(QWidget):
    """Circle with the user's first initial."""

    def __init__(self) -> None:
        super().__init__()
        self._letter = "?"
        self.setFixedSize(32, 32)

    def set_letter(self, letter: str) -> None:
        self._letter = letter.upper() if letter else "?"
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        from theme.colors import ACCENT_CYAN_RGB, TEXT_PRIMARY_RGB  # noqa: PLC0415
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*ACCENT_CYAN_RGB, 50))
        p.setPen(QColor(*ACCENT_CYAN_RGB, 160))
        p.drawEllipse(1, 1, 29, 29)
        font = self.font()
        font.setPointSize(12)
        p.setFont(font)
        p.setPen(QColor(*TEXT_PRIMARY_RGB))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._letter)
        p.end()


class _ProfileSection(QWidget):
    """Clickable profile row at the bottom of the sidebar."""

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._hover = False
        self._pressed = False
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.setSpacing(10)

        self._avatar = _AvatarWidget()
        self._avatar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        hl.addWidget(self._avatar)

        self._name_lbl = QLabel("Not signed in")
        self._name_lbl.setObjectName("ProfileUsername")
        self._name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        hl.addWidget(self._name_lbl, 1)

    def set_user(self, username: str) -> None:
        self._name_lbl.setText(username)
        self._avatar.set_letter(username[0] if username else "?")

    def clear_user(self) -> None:
        self._name_lbl.setText("Not signed in")
        self._avatar.set_letter("?")

    def enterEvent(self, event) -> None:  # noqa: ANN001
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        from theme.colors import ACCENT_CYAN_RGB  # noqa: PLC0415
        p = QPainter(self)
        r = self.rect()
        if self._hover:
            p.fillRect(r, QColor(*ACCENT_CYAN_RGB, 18))
        p.setPen(QColor(*ACCENT_CYAN_RGB, 25))
        p.drawLine(0, 0, r.width(), 0)
        p.end()


class _ProfilePopup(QWidget):
    """Floating panel shown above the profile row when clicked."""

    logout_clicked = Signal()

    def __init__(self, username: Optional[str]) -> None:
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui(username)

    def _build_ui(self, username: Optional[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(6)

        if username:
            header = QLabel("Signed in as")
            header.setObjectName("ProfilePopupHeader")
            layout.addWidget(header)

            name_lbl = QLabel(username)
            name_lbl.setObjectName("ProfilePopupName")
            layout.addWidget(name_lbl)
        else:
            name_lbl = QLabel("Not signed in")
            name_lbl.setObjectName("ProfilePopupHeader")
            layout.addWidget(name_lbl)

        if username:
            sep = QWidget()
            sep.setObjectName("ProfilePopupSep")
            sep.setFixedHeight(1)
            layout.addSpacing(6)
            layout.addWidget(sep)
            layout.addSpacing(4)

            from ui.widgets.themed_button import ThemedButton  # noqa: PLC0415
            logout_btn = ThemedButton("Log Out", ThemedButton.VARIANT_DANGER)
            logout_btn.clicked.connect(self._on_logout)
            layout.addWidget(logout_btn)

    def _on_logout(self) -> None:
        self.close()
        self.logout_clicked.emit()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        from theme.colors import CARD_BG_RGB, ACCENT_CYAN_RGB  # noqa: PLC0415
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*CARD_BG_RGB, 252))
        p.setPen(QColor(*ACCENT_CYAN_RGB, 65))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        p.end()
