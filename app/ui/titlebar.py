"""CustomTitleBar — frameless window title bar with drag and window controls."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPixmap, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import icon_pixmap, AppIcon
from utils.resource_utils import get_asset

_ICON_SIZE = 32  # px — title bar logo display size


class TitleBar(QWidget):
    """Frameless custom title bar that drives the parent window's drag, minimize,
    maximize/restore, and close actions."""

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._drag_pos: Optional[QPoint] = None
        self._maximized = False

        self.setObjectName("TitleBar")
        self.setFixedHeight(44)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(0)

        # App icon
        icon_label = QLabel()
        # icon_path = get_asset("icons/full_logo.ico")
        icon_path = get_asset("icons/only_logo.ico")

        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                _ICON_SIZE, _ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pix)
        icon_label.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        layout.addWidget(icon_label)
        layout.addSpacing(8)

        # Logo text box
        logo_box = QVBoxLayout()
        logo_box.setSpacing(0)

        app_title = QLabel("GRAVITY NEXUS")
        app_title.setObjectName("AppTitleLabel")
        logo_box.addWidget(app_title)

        layout.addLayout(logo_box)
        layout.addStretch()

        # Window control buttons
        for icon, obj_name, btn_type, slot in [
            (QIcon(icon_pixmap(AppIcon.WINDOW_MINIMIZE)), "TitleBarBtn_min", "minimize", self._on_minimize),
            (QIcon(icon_pixmap(AppIcon.WINDOW_MAXIMIZE)), "TitleBarBtn_max", "maximize", self._on_maximize),
            (QIcon(icon_pixmap(AppIcon.WINDOW_CLOSE)), "TitleBarBtn_cls", "close", self._on_close),
        ]:
            btn = QPushButton()
            btn.setObjectName("TitleBarBtn")
            btn.setProperty("btnType", btn_type)
            btn.setIcon(icon)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
            layout.addSpacing(2)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_minimize(self) -> None:
        self._window.showMinimized()

    def _on_maximize(self) -> None:
        if self._maximized:
            self._window.showNormal()
            self._maximized = False
        else:
            self._window.showMaximized()
            self._maximized = True

    def _on_close(self) -> None:
        self._window.close()

    # ── Drag ───────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self._maximized:
                self._window.showNormal()
                self._maximized = False
                self._drag_pos = QPoint(self._window.width() // 2, 22)
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize()
        super().mouseDoubleClickEvent(event)

