"""MainWindow — frameless application shell.

Layout::

    ┌─ TitleBar (44px) ────────────────────────────────────────┐
    │ ┌─ Sidebar (240px) ─┐ ┌─ QStackedWidget ───────────────┐ │
    │ │                   │ │  Pages (scrollable)             │ │
    │ │  Logo             │ │                                 │ │
    │ │  Navigation       │ │  SettingsCards                  │ │
    │ │  Status           │ │  OverlayPreview                 │ │
    │ └───────────────────┘ └─────────────────────────────────┘ │
    ├─ StatusBar (28px) ───────────────────────────────────────┤
    └──────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.mock_data_provider import MockDataProvider
from services.settings_service import SettingsService
from utils.resource_utils import get_asset
from ui.pages import (
    AboutPage,
    AdvancedPage,
    AppearancePage,
    GeneralPage,
    NotificationsPage,
    OverlaysPage,
    ParsingPage,
    ProfilesPage,
)
from ui.sidebar import Sidebar
from ui.statusbar import StatusBar
from ui.titlebar import TitleBar


class MainWindow(QWidget):
    """Application main window — frameless with translucent drop shadow."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._svc = SettingsService.instance()
        self._mock_provider = MockDataProvider(update_interval_ms=2000)

        # Frameless + transparent background for drop shadow
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)
        self.setWindowTitle("Gravity Nexus — EQ Overlay Parser")

        # Window icon (taskbar / Alt+Tab)
        icon_path = get_asset("icons/full_logo.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._connect_signals()
        self._restore_geometry()

        self._mock_provider.start()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Outer layout provides the transparent shadow margin
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)

        # Inner content frame (the visible window body)
        self._content = QWidget()
        self._content.setObjectName("AppContent")

        # Drop shadow on the content frame
        shadow = QGraphicsDropShadowEffect(self._content)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self._content.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar(self)
        content_layout.addWidget(self._title_bar)

        # Body: sidebar + page stack
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        body.addWidget(self._stack)

        content_layout.addLayout(body, stretch=1)

        # Status bar
        self._status_bar = StatusBar()
        content_layout.addWidget(self._status_bar)

        outer.addWidget(self._content)
        self._populate_pages()

    def _populate_pages(self) -> None:
        """Create and register all page widgets in the QStackedWidget."""
        pages = [
            GeneralPage(),
            OverlaysPage(self._mock_provider),
            ParsingPage(),
            NotificationsPage(),
            AppearancePage(),
            ProfilesPage(),
            AdvancedPage(),
            AboutPage(),
        ]
        for page in pages:
            self._stack.addWidget(page)

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._sidebar.page_requested.connect(self._stack.setCurrentIndex)
        self._status_bar.set_active_profile(self._svc.settings.active_profile)

    # ── Geometry persistence ───────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        geom = self._svc.settings.window_geometry
        if geom:
            self.restoreGeometry(geom)

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self._mock_provider.stop()
        self._svc.settings.window_geometry = bytes(self.saveGeometry())
        self._svc.save()
        super().closeEvent(event)

    # ── Paint (outer transparent area has no visible content) ─────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        # Required when WA_TranslucentBackground is set to keep Qt happy
        super().paintEvent(event)

