"""MainWindow — frameless application shell.

Layout::

    ┌─ TitleBar (44px) ────────────────────────────────────────┐
    │ ┌─ Sidebar (240px) ─┐ ┌─ QStackedWidget ───────────────┐ │
    │ │                   │ │  Pages (scrollable)             │ │
    │ │                   │ │                                 │ │
    │ │  Navigation       │ │  SettingsCards                  │ │
    │ │  Status           │ │  OverlayPreview                 │ │
    │ └───────────────────┘ └─────────────────────────────────┘ │
    ├─ StatusBar (28px) ───────────────────────────────────────┤
    └──────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.fake_log_service import FakeLogService
from services.protocols import IGravityBotService, ILogParserService, ISettingsService
from services.mock_data_provider import MockDataProvider
from ui.overlays.raid_submit_overlay import RaidSubmitOverlay
from ui.overlays.positioning_overlay import PositioningOverlay
from ui.overlays.quick_toolbar_overlay import QuickToolbarOverlay
from utils.resource_utils import get_asset
from ui.pages import (
    AboutPage,
    AdvancedPage,
    AppearancePage,
    FakeLogPage,
    FeatureFlagsPage,
    GeneralPage,
    GravityBotPage,
    NotificationsPage,
    OverlaysPage,
    ParsingPage,
)
from ui.sidebar import Sidebar
from ui.statusbar import StatusBar
from ui.titlebar import TitleBar


class MainWindow(QWidget):
    """Application main window — frameless with translucent drop shadow."""

    def __init__(
        self,
        auth=None,      # AuthManager | None
        api=None,       # ApiClient | None
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth
        self._api = api
        self._svc = registry.get(ISettingsService)
        self._mock_provider = MockDataProvider(update_interval_ms=2000)
        self._parser_svc = registry.get(ILogParserService)
        self._bot_svc = registry.get(IGravityBotService)
        self._fake_log_svc = FakeLogService(self)
        self._raid_overlay: Optional[RaidSubmitOverlay] = None
        self._toolbar_overlay: Optional[QuickToolbarOverlay] = None
        self._active_character: str = ""
        self._positioning_overlays: list[PositioningOverlay] = []
        self._position_snapshot: dict[str, tuple[int, int]] = {}  # pre-drag snapshot
        self._quitting: bool = False  # True when a real quit is in progress

        # Frameless + transparent background for drop shadow
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)
        self.setWindowTitle("Gravity Nexus")

        # Window icon (taskbar / Alt+Tab)
        icon_path = get_asset("icons/full_logo.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._connect_signals()
        self._init_auth_state()
        self._restore_geometry()
        self._show_toolbar_overlay()

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
        self._general_page = GeneralPage()
        self._overlays_page = OverlaysPage(self._mock_provider)
        self._parsing_page = ParsingPage()
        pages = [
            self._general_page,       # 0
            self._overlays_page,      # 1
            self._parsing_page,       # 2
            NotificationsPage(),      # 3
            AppearancePage(),         # 4
            AdvancedPage(),           # 5
            GravityBotPage(),         # 6
            FakeLogPage(self._fake_log_svc),  # 7  (Dev Tools in nav)
            FeatureFlagsPage(),       # 8
            AboutPage(),              # 9
        ]
        for page in pages:
            self._stack.addWidget(page)

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._sidebar.page_requested.connect(self._stack.setCurrentIndex)

        if self._auth is not None:
            self._auth.session_expired.connect(self._on_session_expired)
            self._auth.logged_in.connect(self._on_logged_in)
            self._auth.logged_out.connect(self._sidebar.clear_user)
            self._sidebar.logout_requested.connect(self._auth.logout)

        # Log parser
        self._parser_svc.status_changed.connect(self._on_parser_status_changed)
        self._parser_svc.active_file_changed.connect(self._on_active_file_changed)
        self._parser_svc.raid_dump_detected.connect(self._on_raid_dump_detected)

        # Gravity Bot
        self._bot_svc.connected_changed.connect(self._status_bar.set_grav_bot_connected)

        # General page — directory save on start (no longer owns buttons)
        self._general_page.start_parser_requested.connect(self._on_start_parser_requested)

        # Sidebar parser controls
        self._parsing_page.start_parser_requested.connect(self._on_sidebar_start_parser)
        self._parsing_page.stop_parser_requested.connect(self._parser_svc.stop)

        # Overlay positioning
        self._overlays_page.position_overlays_requested.connect(self._on_position_overlays_requested)
        self._overlays_page.cancel_position_overlays_requested.connect(self._cancel_positioning_overlays)
        self._overlays_page.opacity_changed.connect(self._on_overlay_opacity_changed)

        # Background throttling — reduce update rates when the app loses focus
        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state_changed)

    # ── Auth ───────────────────────────────────────────────────────────────────

    def _init_auth_state(self) -> None:
        if self._auth and self._auth.is_authenticated() and self._auth._username:
            self._sidebar.set_user(self._auth._username)

    @Slot()
    def _on_logged_in(self) -> None:
        if self._auth and self._auth._username:
            self._sidebar.set_user(self._auth._username)

    @Slot()
    def _on_session_expired(self) -> None:
        from PySide6.QtWidgets import QDialog as _QDialog  # noqa: PLC0415
        from ui.login_dialog import LoginDialog             # noqa: PLC0415
        dialog = LoginDialog(self._auth, registry.get(ISettingsService), self)
        if dialog.exec() != _QDialog.DialogCode.Accepted:
            QApplication.quit()

    # ── Parser / overlay handlers ──────────────────────────────────────────────

    @Slot(object)
    def _on_app_state_changed(self, state) -> None:
        """Throttle (or restore) service poll rates based on whether the app is active."""
        if not self._svc.settings.general.reduce_update_rate_in_background:
            return
        background = state != Qt.ApplicationState.ApplicationActive
        self._parser_svc.set_background_mode(background)
        # MockDataProvider: 2 s foreground → 10 s background
        self._mock_provider.set_update_interval(10_000 if background else 2_000)

    def _on_start_parser_requested(self, log_directory: str) -> None:
        self._parser_svc.start(log_directory)

    def _on_sidebar_start_parser(self) -> None:
        """Start the parser using the directory saved in settings."""
        directory = self._svc.settings.general.log_directory
        if directory:
            self._parser_svc.start(directory)
        else:
            # No directory configured — navigate to General page so the user can set one
            self._stack.setCurrentIndex(0)
            self._sidebar.set_active_page(0)

    def _on_active_file_changed(self, character: str) -> None:
        """Called when the parser locks onto a (new) log file."""
        self._active_character = character
        self._status_bar.set_parser_running(True, character)
        self._parsing_page.set_parser_status(True, character)
        self._general_page.update_parser_status(True, character)

    def _on_parser_status_changed(self, status: str) -> None:
        if status == "running":
            return  # active_file_changed handles the "running" UI update
        self._active_character = ""
        running = False
        self._status_bar.set_parser_running(running)
        self._parsing_page.set_parser_status(running)
        self._general_page.update_parser_status(running)

    def _on_raid_dump_detected(self, arg_vals: list) -> None:
        raw_lines = arg_vals[0]
        full_who_log: str = arg_vals[1]
        """Show (or replace) the raid submit overlay."""
        if self._raid_overlay is not None:
            try:
                self._raid_overlay.close()
            except RuntimeError:
                pass

        self._raid_overlay = RaidSubmitOverlay(raw_names=raw_lines, full_who_log=full_who_log)
        self._raid_overlay.dismissed.connect(self._on_raid_overlay_dismissed)

        # Apply saved opacity and scale
        self._raid_overlay.set_overlay_opacity(self._svc.settings.overlay.opacity)
        self._raid_overlay.set_overlay_scale(self._svc.settings.overlay.scale)

        # Restore saved geometry (position + size), fall back to primary-screen centre
        saved = self._svc.settings.overlay.positions.get("raid_submit")
        if saved:
            x, y, w, h = saved
            if w > 0 and h > 0:
                self._raid_overlay.resize(w, h)
            self._raid_overlay.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            self._raid_overlay.move(
                screen.center().x() - 250,
                screen.center().y() - 180,
            )

        self._raid_overlay.show()

    def _on_raid_overlay_dismissed(self) -> None:
        if self._raid_overlay is not None:
            p = self._raid_overlay.pos()
            s = self._raid_overlay.size()
            self._svc.settings.overlay.positions["raid_submit"] = (p.x(), p.y(), s.width(), s.height())
            self._svc.save()

    @Slot(float)
    def _on_overlay_opacity_changed(self, opacity: float) -> None:
        """Apply the new opacity to all currently visible overlay windows."""
        if self._raid_overlay is not None:
            try:
                self._raid_overlay.set_overlay_opacity(opacity)
            except RuntimeError:
                pass
        if self._toolbar_overlay is not None:
            try:
                self._toolbar_overlay.set_overlay_opacity(opacity)
            except RuntimeError:
                pass
        for w in self._positioning_overlays:
            try:
                w.set_overlay_opacity(opacity)
            except RuntimeError:
                pass

    # ── Overlay positioning ────────────────────────────────────────────────────

    #: Maps overlay key → (display_label, default_size)
    _OVERLAY_REGISTRY: dict[str, tuple[str, tuple[int, int]]] = {
        "raid_submit": ("Raid Submit", (500, 360)),
        "toolbar":     ("Quick Toolbar", (150, 80)),
    }

    def _on_position_overlays_requested(self, active: bool) -> None:
        if active:
            self._show_positioning_overlays()
        else:
            self._save_and_close_positioning_overlays()

    def _show_positioning_overlays(self) -> None:
        """Spawn a draggable placeholder for every registered overlay type."""
        self._save_and_close_positioning_overlays()  # clear any leftovers

        # Hide the live toolbar so the positioning placeholder is unobstructed.
        if self._toolbar_overlay is not None:
            try:
                self._toolbar_overlay.hide()
            except RuntimeError:
                pass

        # Snapshot current positions so Cancel can restore them
        self._position_snapshot = dict(self._svc.settings.overlay.positions)

        screen = QApplication.primaryScreen().geometry()
        for key, (label, size) in self._OVERLAY_REGISTRY.items():
            w = PositioningOverlay(key, label, size)
            # Apply opacity/scale FIRST so _base_size is captured from the natural
            # default size.  The saved size is then applied as a hard override
            # afterwards, preventing compounding growth on each save/restore cycle.
            w.set_overlay_opacity(self._svc.settings.overlay.opacity)
            w.set_overlay_scale(self._svc.settings.overlay.scale)
            saved = self._svc.settings.overlay.positions.get(key)
            if saved:
                x, y, sw, sh = saved
                if sw > 0 and sh > 0:
                    w.resize(sw, sh)
                w.move(x, y)
            else:
                w.move(
                    screen.center().x() - size[0] // 2,
                    screen.center().y() - size[1] // 2,
                )
            w.show()
            self._positioning_overlays.append(w)

    def _save_and_close_positioning_overlays(self) -> None:
        """Persist current geometry (position + size) and close all positioning windows."""
        for w in self._positioning_overlays:
            try:
                p = w.pos()
                sz = w.size()
                self._svc.settings.overlay.positions[w.overlay_key] = (
                    p.x(), p.y(), sz.width(), sz.height()
                )
                w.close()
            except RuntimeError:
                pass
        self._positioning_overlays.clear()
        self._position_snapshot.clear()
        self._svc.save()
        # Re-show toolbar at its (possibly new) saved position.
        self._restore_toolbar_position()

    def _cancel_positioning_overlays(self) -> None:
        """Close positioning windows and restore positions to the pre-drag snapshot."""
        for w in self._positioning_overlays:
            try:
                w.close()
            except RuntimeError:
                pass
        self._positioning_overlays.clear()
        # Restore the snapshot — overwrite any keys that were added/changed
        self._svc.settings.overlay.positions = dict(self._position_snapshot)
        self._position_snapshot.clear()
        self._svc.save()
        # Re-show toolbar at its original (snapshot) position.
        self._restore_toolbar_position()

    def _restore_toolbar_position(self) -> None:
        """Move the toolbar to its saved position and make it visible."""
        if self._toolbar_overlay is None:
            return
        try:
            saved = self._svc.settings.overlay.positions.get("toolbar")
            if saved:
                x, y, _w, _h = saved
                self._toolbar_overlay.move(x, y)
            self._toolbar_overlay.show()
        except RuntimeError:
            pass

    # ── Quick toolbar overlay ──────────────────────────────────────────────────

    def _show_toolbar_overlay(self) -> None:
        """Instantiate and show the Quick Toolbar if toolbar.enabled and the feature flag is on."""
        from feature_flags import feature_enabled  # noqa: PLC0415
        if not feature_enabled("quick_toolbar", self._svc.settings):
            return
        if not self._svc.settings.toolbar.enabled:
            return

        self._toolbar_overlay = QuickToolbarOverlay()
        self._toolbar_overlay.set_overlay_opacity(self._svc.settings.overlay.opacity)
        self._toolbar_overlay.set_overlay_scale(self._svc.settings.overlay.scale)

        # Restore saved position
        saved = self._svc.settings.overlay.positions.get("toolbar")
        if saved:
            x, y, w, h = saved
            self._toolbar_overlay.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            self._toolbar_overlay.move(
                screen.center().x() - 60,
                screen.top() + 80,
            )

        self._toolbar_overlay.position_changed.connect(self._on_toolbar_position_changed)
        self._toolbar_overlay.show()

    def _on_toolbar_position_changed(self) -> None:
        """Persist the toolbar position whenever it moves."""
        if self._toolbar_overlay is None:
            return
        try:
            p = self._toolbar_overlay.pos()
            sz = self._toolbar_overlay.size()
            self._svc.settings.overlay.positions["toolbar"] = (
                p.x(), p.y(), sz.width(), sz.height()
            )
            self._svc.save()
        except RuntimeError:
            pass

    # ── Geometry persistence ───────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        geom = self._svc.settings.window_geometry
        if geom:
            self.restoreGeometry(geom)

    def force_quit(self) -> None:
        """Perform a real application quit regardless of the minimize-to-tray setting."""
        self._quitting = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        # When minimize-to-tray is enabled and this is not an explicit quit,
        # intercept the close, hide the window, and show a tray balloon instead.
        if not self._quitting and self._svc.settings.general.minimize_to_tray:
            event.ignore()
            self.hide()
            # Find the application tray icon (set on the QApplication instance)
            tray: Optional[QSystemTrayIcon] = QApplication.instance().property("tray_icon")
            if tray and tray.supportsMessages():
                tray.showMessage(
                    "Gravity Nexus",
                    "Running in the system tray. Double-click the icon to restore.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            return

        self._mock_provider.stop()
        self._parser_svc.stop()
        self._bot_svc.shutdown()
        self._fake_log_svc.stop()
        if self._api is not None:
            self._api.close()
        if self._toolbar_overlay is not None:
            try:
                self._toolbar_overlay.close()
            except RuntimeError:
                pass
        self._svc.settings.window_geometry = bytes(self.saveGeometry())
        self._svc.save()
        super().closeEvent(event)
        QApplication.quit()

    # ── Paint (outer transparent area has no visible content) ─────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        # Required when WA_TranslucentBackground is set to keep Qt happy
        super().paintEvent(event)
