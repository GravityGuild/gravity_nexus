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

import sys
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.fake_log_service import FakeLogService
from services.protocols import IGravityBotService, ILogParserService, ISettingsService, IUpdateService
from services.mock_data_provider import MockDataProvider
from ui.overlays.overlay_config import OVERLAY_CONFIG_MAP, resolve_default_position
from ui.overlays.raid_submit_overlay import RaidSubmitOverlay
from ui.overlays.who_lookup_overlay import WhoLookupOverlay
from ui.overlays.positioning_overlay_manager import PositioningOverlayManager
from ui.overlays.quick_toolbar_overlay import QuickToolbarOverlay
from utils.resource_utils import get_asset
from ui.pages import (
    AboutPage,
    AdvancedPage,
    AppearancePage,
    DevToolsPage,
    FeatureFlagsPage,
    GeneralPage,
    GravityBotPage,
    NotificationsPage,
    OverlaysPage,
    PageConfig,
    ParsingPage,
    RaidToolsPage,
)
from ui.widgets.icon_label import AppIcon
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
        self._who_overlay: Optional[WhoLookupOverlay] = None
        self._toolbar_overlay: Optional[QuickToolbarOverlay] = None
        self._active_character: str = ""
        self._positioning_manager = PositioningOverlayManager(self._svc)
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
        self._outer_layout = QVBoxLayout(self)
        outer = self._outer_layout
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Inner content frame (the visible window body)
        self._content = QWidget()
        self._content.setObjectName("AppContent")

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
        """Create page widgets, register them in the stack, and configure sidebar nav."""
        self._general_page = GeneralPage()
        self._raid_tools_page = RaidToolsPage()
        self._overlays_page = OverlaysPage(self._mock_provider)
        self._parsing_page = ParsingPage()
        self._advanced_page = AdvancedPage()

        configs: list[PageConfig] = [
            PageConfig("General",
                       AppIcon.HOME,
                       lambda: self._general_page),
            PageConfig("Raid Tools",
                       AppIcon.WRENCH,
                       lambda: self._raid_tools_page),
            PageConfig("Overlays",
                       AppIcon.MONITOR_DASHBOARD,
                       lambda: self._overlays_page),
            PageConfig("Parsing",
                       AppIcon.APPLICATION_BRACKETS,
                       lambda: self._parsing_page,
                       dev_only=True),
            PageConfig("Notifications",
                       AppIcon.BELL,
                       NotificationsPage,
                       feature_flag="notifications_page"),
            PageConfig("Appearance",
                       AppIcon.PALETTE,
                       AppearancePage),
            PageConfig("Advanced",
                       AppIcon.HAMMER_WRENCH,
                       lambda: self._advanced_page),
            PageConfig("Gravity Bot",
                       AppIcon.ROBOT,
                       GravityBotPage,
                       dev_only=True),
            PageConfig("Dev Tools",
                       AppIcon.TEST_TUBE,
                       lambda: DevToolsPage(self._fake_log_svc),
                       dev_only=True),
            PageConfig("Feature Flags",
                       AppIcon.CODE_BRACES,
                       FeatureFlagsPage,
                       dev_only=True),
            PageConfig("About",
                       AppIcon.INFORMATION,
                       AboutPage),
        ]

        for cfg in configs:
            self._stack.addWidget(cfg.factory())

        self._sidebar.set_page_configs(configs)

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._sidebar.page_requested.connect(self._stack.setCurrentIndex)

        if self._auth is not None:
            self._auth.session_expired.connect(self._on_session_expired)
            self._auth.logged_in.connect(self._on_logged_in)
            self._auth.logged_out.connect(self._on_logged_out)
            self._sidebar.logout_requested.connect(self._auth.logout)

        # Log parser
        self._parser_svc.status_changed.connect(self._on_parser_status_changed)
        self._parser_svc.active_file_changed.connect(self._on_active_file_changed)
        self._parser_svc.raid_log_detected.connect(self._on_raid_log_detected)
        self._parser_svc.who_list_detected.connect(self._on_who_list_detected)
        self._parser_svc.character_entered_game.connect(self._on_character_entered_game)
        self._parser_svc.character_at_select.connect(self._on_character_at_select)
        self._parser_svc.character_offline.connect(self._on_character_offline)

        # Gravity Bot
        self._bot_svc.connected_changed.connect(self._status_bar.set_grav_bot_connected)
        self._status_bar.set_grav_bot_connected(self._bot_svc.is_connected)

        # General page — directory save on start (no longer owns buttons)
        self._general_page.start_parser_requested.connect(self._on_start_parser_requested)

        # Advanced page parser controls
        self._advanced_page.start_parser_requested.connect(self._on_sidebar_start_parser)
        self._advanced_page.stop_parser_requested.connect(self._parser_svc.stop)

        # Overlay positioning
        self._overlays_page.position_overlays_requested.connect(self._positioning_manager.on_requested)
        self._overlays_page.cancel_position_overlays_requested.connect(self._positioning_manager.cancel)
        self._overlays_page.opacity_changed.connect(self._on_overlay_opacity_changed)
        self._positioning_manager.set_all_closed_callback(self._overlays_page.reset_positioning_button)

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
        self._bot_svc.connect_bot()
        self.bring_to_foreground()

    @Slot()
    def _on_logged_out(self) -> None:
        self._sidebar.clear_user()
        self._bot_svc.disconnect_bot()
        self.hide()
        from PySide6.QtWidgets import QDialog as _QDialog  # noqa: PLC0415
        from ui.login_dialog import LoginDialog             # noqa: PLC0415
        dialog = LoginDialog(self._auth)
        if dialog.exec() != _QDialog.DialogCode.Accepted:
            QApplication.quit()

    @Slot()
    def _on_session_expired(self) -> None:
        self.hide()
        from PySide6.QtWidgets import QDialog as _QDialog  # noqa: PLC0415
        from ui.login_dialog import LoginDialog             # noqa: PLC0415
        dialog = LoginDialog(self._auth)
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
        self._status_bar.set_parser_running(True, self._parser_svc.active_log_filename)
        self._status_bar.set_character(character)
        self._advanced_page.set_parser_status(True, character)
        self._general_page.update_parser_status(True, character)

    def _on_parser_status_changed(self, status: str) -> None:
        if status == "running":
            return  # active_file_changed handles the "running" UI update
        self._active_character = ""
        self._status_bar.set_parser_running(False)
        self._status_bar.set_character("")
        self._status_bar.set_character_state("offline")
        self._advanced_page.set_parser_status(False)
        self._general_page.update_parser_status(False)

    @Slot()
    def _on_character_entered_game(self) -> None:
        self._status_bar.set_character(self._parser_svc.active_character)
        self._status_bar.set_character_state("in_game")

    @Slot()
    def _on_character_at_select(self) -> None:
        self._status_bar.set_character(self._parser_svc.active_character)
        self._status_bar.set_character_state("at_select")

    @Slot()
    def _on_character_offline(self) -> None:
        self._status_bar.set_character("")
        self._status_bar.set_character_state("offline")

    @Slot()
    def on_game_crashed(self) -> None:
        """EQ exited without a clean disconnect — clear character name and state."""
        self._status_bar.set_character("")
        self._status_bar.set_character_state("offline")

    def _on_raid_log_detected(self, arg_vals: list) -> None:
        raw_lines = arg_vals[0]
        full_who_log: str = arg_vals[1]
        """Show (or replace) the raid submit overlay."""
        # Pre-fetch raids now so the overlay dropdown is ready (or nearly so) by
        # the time the user sees it. Use the same params as the overlay so the
        # cache hit is valid when the overlay calls fetch_raids_cached().
        from datetime import datetime, timedelta, timezone
        _date_from = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")
        self._bot_svc.fetch_raids(date_from=_date_from, limit=5)
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
            x, y = PositioningOverlayManager.clamp_to_screen(x, y, w, h)
            self._raid_overlay.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x, y = resolve_default_position(OVERLAY_CONFIG_MAP["raid_submit"], self._raid_overlay.width(), self._raid_overlay.height(), screen)
            self._raid_overlay.move(x, y)

        self._raid_overlay.show()
        self._raid_overlay.position_changed.connect(self._on_raid_overlay_moved)

    def _on_raid_overlay_dismissed(self) -> None:
        if self._raid_overlay is not None:
            p = self._raid_overlay.pos()
            s = self._raid_overlay.size()
            self._svc.settings.overlay.positions["raid_submit"] = (p.x(), p.y(), s.width(), s.height())
            self._svc.save()

    def _on_raid_overlay_moved(self) -> None:
        if self._raid_overlay is not None:
            try:
                p = self._raid_overlay.pos()
                s = self._raid_overlay.size()
                self._svc.settings.overlay.positions["raid_submit"] = (p.x(), p.y(), s.width(), s.height())
                self._svc.save()
            except RuntimeError:
                pass

    def _on_who_list_detected(self, entries: list, total: int) -> None:
        """Show the who lookup overlay when exactly one character appeared in the /who result."""
        if total != 1 or len(entries) != 1:
            return
        entry = entries[0]
        settings = self._svc.settings
        if not settings.who_lookup.enabled:
            return
        if (self._active_character
                and entry.name.lower() == self._active_character.lower()
                and not settings.who_lookup.show_own_character):
            return
        if self._who_overlay is not None:
            try:
                self._who_overlay.close()
            except RuntimeError:
                pass

        self._who_overlay = WhoLookupOverlay(entry.name)
        self._who_overlay.dismissed.connect(self._on_who_overlay_dismissed)

        self._who_overlay.set_overlay_opacity(settings.overlay.opacity)
        self._who_overlay.set_overlay_scale(settings.overlay.scale)

        saved = settings.overlay.positions.get("who_lookup")
        if saved:
            x, y, w, h = saved
            if w > 0 and h > 0:
                self._who_overlay.resize(w, h)
            x, y = PositioningOverlayManager.clamp_to_screen(x, y, w, h)
            self._who_overlay.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x, y = resolve_default_position(OVERLAY_CONFIG_MAP["who_lookup"], self._who_overlay.width(), self._who_overlay.height(), screen)
            self._who_overlay.move(x, y)

        self._who_overlay.show()

    def _on_who_overlay_dismissed(self) -> None:
        if self._who_overlay is not None:
            p = self._who_overlay.pos()
            s = self._who_overlay.size()
            self._svc.settings.overlay.positions["who_lookup"] = (p.x(), p.y(), s.width(), s.height())
            self._svc.save()

    def _on_who_overlay_moved(self) -> None:
        if self._who_overlay is not None:
            try:
                p = self._who_overlay.pos()
                s = self._who_overlay.size()
                self._svc.settings.overlay.positions["who_lookup"] = (p.x(), p.y(), s.width(), s.height())
                self._svc.save()
            except RuntimeError:
                pass

    @Slot(float)
    def _on_overlay_opacity_changed(self, opacity: float) -> None:
        """Apply the new opacity to all currently visible overlay windows."""
        if self._raid_overlay is not None:
            try:
                self._raid_overlay.set_overlay_opacity(opacity)
            except RuntimeError:
                pass
        if self._who_overlay is not None:
            try:
                self._who_overlay.set_overlay_opacity(opacity)
            except RuntimeError:
                pass
        if self._toolbar_overlay is not None:
            try:
                self._toolbar_overlay.set_overlay_opacity(opacity)
            except RuntimeError:
                pass
        for w in self._positioning_manager.active_overlays:
            try:
                w.set_overlay_opacity(opacity)
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
        self._positioning_manager.set_toolbar_overlay(self._toolbar_overlay)
        self._toolbar_overlay.set_overlay_opacity(self._svc.settings.overlay.opacity)
        self._toolbar_overlay.set_overlay_scale(self._svc.settings.overlay.scale)

        # Restore saved position
        saved = self._svc.settings.overlay.positions.get("toolbar")
        if saved:
            self._toolbar_overlay.move(saved[0], saved[1])
        else:
            screen = QApplication.primaryScreen().geometry()
            x, y = resolve_default_position(OVERLAY_CONFIG_MAP["toolbar"], self._toolbar_overlay.width(), self._toolbar_overlay.height(), screen)
            self._toolbar_overlay.move(x, y)

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
        if registry.is_registered(IUpdateService):
            registry.get(IUpdateService).shutdown()
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

    # ── Window state / native resize+snap ─────────────────────────────────────

    def bring_to_foreground(self) -> None:
        """Show, un-minimize, and forcefully activate the window.

        On Windows, SetForegroundWindow is gated by focus-stealing prevention
        and silently fails when another process owns the foreground (e.g. the
        browser after OAuth).  AttachThreadInput grants our thread the same
        activation rights as the current foreground thread, making the call
        reliable regardless of which app the user was in.
        """
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            fg_hwnd = user32.GetForegroundWindow()
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
            if fg_tid and fg_tid != my_tid:
                user32.AttachThreadInput(fg_tid, my_tid, True)
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(fg_tid, my_tid, False)
            else:
                user32.SetForegroundWindow(hwnd)

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        if sys.platform == "win32" and not hasattr(self, "_win32_frame_applied"):
            self._win32_frame_applied = True
            self._apply_win32_snap_frame()

    def _apply_win32_snap_frame(self) -> None:
        """Add WS_THICKFRAME to the Win32 window style.

        FramelessWindowHint strips this flag, but Windows requires it to trigger
        Aero Snap (drag-to-edge and Win+Arrow).  We add it back here and rely on
        WM_NCCALCSIZE (handled in nativeEvent) to collapse the native frame chrome
        to zero so the window still looks frameless.
        """
        import ctypes

        hwnd = int(self.winId())
        GWL_STYLE = -16
        WS_THICKFRAME = 0x00040000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
        ctypes.windll.user32.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            0x0001 | 0x0002 | 0x0004 | 0x0020,  # NOSIZE|NOMOVE|NOZORDER|FRAMECHANGED
        )

    def nativeEvent(self, event_type, message):  # noqa: ANN001
        """Handle WM_NCCALCSIZE and WM_NCHITTEST for a frameless window that
        still supports native resize handles and Aero Snap."""
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            import ctypes
            import ctypes.wintypes

            msg = ctypes.wintypes.MSG.from_address(int(message))

            if msg.message == 0x0083 and msg.wParam:  # WM_NCCALCSIZE, wParam=TRUE
                if self.isMaximized():
                    # Windows pushes a maximized WS_THICKFRAME window 8 px off each
                    # screen edge. Clamp the proposed rect to the monitor work area
                    # so the content fills the screen without covering the taskbar.
                    hwnd = int(self.winId())
                    monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)

                    class _RECT(ctypes.Structure):
                        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

                    class _MONITORINFO(ctypes.Structure):
                        _fields_ = [("cbSize", ctypes.c_uint32), ("rcMonitor", _RECT),
                                    ("rcWork", _RECT), ("dwFlags", ctypes.c_uint32)]

                    mi = _MONITORINFO()
                    mi.cbSize = ctypes.sizeof(_MONITORINFO)
                    ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(mi))
                    rc = ctypes.cast(msg.lParam, ctypes.POINTER(_RECT))
                    rc[0].left = mi.rcWork.left
                    rc[0].top = mi.rcWork.top
                    rc[0].right = mi.rcWork.right
                    rc[0].bottom = mi.rcWork.bottom

                return True, 0  # collapse native frame chrome → frameless appearance

            if msg.message == 0x0084:  # WM_NCHITTEST
                from PySide6.QtCore import QPoint

                lx = ctypes.c_int16(msg.lParam & 0xFFFF).value
                ly = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                pos = self.mapFromGlobal(QPoint(lx, ly))
                x, y = pos.x(), pos.y()
                w, h = self.width(), self.height()

                BORDER = 8
                TITLE_H = 44
                BTN_WIDTH = 130  # approx width of the three window control buttons

                if not self.isMaximized():
                    if x < BORDER and y < BORDER:
                        return True, 13  # HTTOPLEFT
                    if x > w - BORDER and y < BORDER:
                        return True, 14  # HTTOPRIGHT
                    if x < BORDER and y > h - BORDER:
                        return True, 16  # HTBOTTOMLEFT
                    if x > w - BORDER and y > h - BORDER:
                        return True, 17  # HTBOTTOMRIGHT
                    if y < BORDER:
                        return True, 12  # HTTOP
                    if y > h - BORDER:
                        return True, 15  # HTBOTTOM
                    if x < BORDER:
                        return True, 10  # HTLEFT
                    if x > w - BORDER:
                        return True, 11  # HTRIGHT

                if y <= TITLE_H and x < w - BTN_WIDTH:
                    return True, 2  # HTCAPTION — enables drag and Aero Snap

                return True, 1  # HTCLIENT

        return super().nativeEvent(event_type, message)

    # ── Paint (outer transparent area has no visible content) ─────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        # Required when WA_TranslucentBackground is set to keep Qt happy
        super().paintEvent(event)
