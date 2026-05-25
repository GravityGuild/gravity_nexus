"""Gravity Nexus — application entry point.

Run from the project root::

    python app/main.py
    # or:
    python -m app.main   (from gravity_nexus/)

Nuitka build entry point::

    nuitka --follow-imports --standalone app\\main.py
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from _version import __version__

# ── Ensure app/ is first on the path so all sub-module imports resolve ────────
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# ── Load .env from project root (if present) for local development ────────────
from dotenv import load_dotenv  # noqa: E402
if not getattr(sys, "frozen", False):
    load_dotenv(_APP_DIR.parent / ".env")

# ── Enable High DPI before QApplication is created ────────────────────────────
from PySide6.QtCore import Qt, QEventLoop, QThread, Signal
from PySide6.QtGui import QIcon, QSurfaceFormat
from PySide6.QtWidgets import QApplication, QDialog, QSystemTrayIcon, QMenu

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)


# ── Hardware-acceleration backend — must be chosen before QApplication ─────────
def _read_hw_accel_pre_app() -> bool:
    """Read hardware_accelerated from the settings store before QApplication exists.

    QSettings with an explicit org/app reads the Windows registry (or a plain
    INI file on other platforms) directly — no QCoreApplication required.
    """
    try:
        from PySide6.QtCore import QSettings  # noqa: PLC0415
        q = QSettings("GravityNexus", "GravityNexus")
        val = q.value("general/hardware_accelerated")
        if val is None:
            return True  # first run → default True
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)
    except Exception:  # noqa: BLE001
        return True


_hw_accel = _read_hw_accel_pre_app()
if _hw_accel:
    # Desktop (native) OpenGL backed by the GPU driver
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
else:
    # Mesa software renderer — predictable but CPU-only
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)


# ── Remaining imports (after sys.path is set) ─────────────────────────────────
from theme.theme_manager import ThemeManager
from ui.loading_spinner import LoadingSpinner
from ui.main_window import MainWindow
from utils.platform_utils import set_app_user_model_id
from utils.resource_utils import get_asset

# ── Composition root — only place that imports concrete service classes ────────
from core.registry import registry
from services.protocols import IAuthService, IGravityBotService, ILogParserService, ISettingsService, IUpdateService
from services.gravity_bot_service import GravityBotService
from services.log_parser_service import LogParserService
from services.settings_service import SettingsService
from services.update_service import UpdateService

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gravity_nexus")


def _apply_debug_logging(settings_svc: "SettingsService") -> None:
    """Set root logger level based on the persisted debug_logging setting."""
    if settings_svc.settings.general.debug_logging:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Debug logging ENABLED (restored from settings).")


def _apply_surface_format(hw_accel: bool) -> None:
    """Configure the default QSurfaceFormat before any windows are created.

    Called after QApplication is up but before MainWindow is constructed so
    the format applies to every surface (including translucent overlays).
    """
    fmt = QSurfaceFormat()
    if hw_accel:
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setVersion(3, 2)          # OpenGL 3.2 Core — broadly supported
        fmt.setSamples(4)             # 4× MSAA — smoother custom-painted edges
        fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setSwapInterval(1)        # vsync on
    else:
        fmt.setSamples(0)
        fmt.setSwapInterval(0)
    QSurfaceFormat.setDefaultFormat(fmt)
    log.debug(
        "QSurfaceFormat applied — hw_accel=%s samples=%d vsync=%s",
        hw_accel, fmt.samples(), fmt.swapInterval() == 1,
    )


class _SilentLoginThread(QThread):
    """Runs AuthManager.try_silent_login() off the main thread.

    Keeps the Qt event loop alive during the network call so animated
    widgets (e.g. LoadingSpinner) continue to repaint.
    """

    result = Signal(bool)

    def __init__(self, auth, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth

    def run(self) -> None:
        ok = self._auth.try_silent_login()
        self.result.emit(ok)


def _run_silent_login(auth) -> bool:
    """Return try_silent_login()'s result; runs it in a background thread."""
    outcome: list[bool] = [False]

    def _capture(ok: bool) -> None:
        outcome[0] = ok

    thread = _SilentLoginThread(auth)
    thread.result.connect(_capture)

    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    thread.start()
    loop.exec()

    return outcome[0]


def main() -> int:
    """Application entry point. Returns exit code."""
    # Windows taskbar identity
    set_app_user_model_id("com.gravitynexus.app")

    app = QApplication(sys.argv)
    app.setApplicationName("Gravity Nexus")
    app.setOrganizationName("GravityNexus")
    app.setApplicationVersion(__version__)
    # Keep the process alive even when the main window is hidden to the tray
    app.setQuitOnLastWindowClosed(False)

    # ── Bootstrap service registry ────────────────────────────────────────────
    settings_svc = SettingsService()
    registry.register(ISettingsService, settings_svc)
    _apply_debug_logging(settings_svc)
    _apply_surface_format(settings_svc.settings.general.hardware_accelerated)
    log.info(
        "Rendering backend: %s",
        "hardware (OpenGL)" if settings_svc.settings.general.hardware_accelerated else "software",
    )

    log_parser_svc = LogParserService()
    registry.register(ILogParserService, log_parser_svc)

    update_svc = UpdateService(settings_svc)
    registry.register(IUpdateService, update_svc)

    # Apply theme before creating any windows, using the persisted font size
    ThemeManager.instance().apply(
        app,
        base_font_size_pt=settings_svc.settings.appearance.font_size,
        use_orbitron_headings=settings_svc.settings.appearance.use_orbitron_headings,
    )

    # Set application-wide icon (taskbar, Alt+Tab, window decorations)
    app_icon_path = get_asset("icons/full_logo.ico")
    app_icon = QIcon(str(app_icon_path)) if app_icon_path.exists() else QIcon()
    app.setWindowIcon(app_icon)

    # ── Startup spinner ────────────────────────────────────────────────────────
    spinner = LoadingSpinner()
    spinner.show()
    app.processEvents()

    # ── Auth bootstrap ─────────────────────────────────────────────────────────
    from auth.auth_manager import AuthManager   # noqa: PLC0415
    from auth.api_client import ApiClient       # noqa: PLC0415
    from ui.login_dialog import LoginDialog     # noqa: PLC0415

    website_base_url = os.environ.get("EQDKP_WEBSITE_URL", "https://gravityp99.com")
    gravity_bot_url = os.environ.get("GRAVITY_BOT_URL", "https://bot.gravityp99.com")
    auth = AuthManager(bot_base_url=gravity_bot_url, website_base_url=website_base_url)
    registry.register(IAuthService, auth)
    api = ApiClient(auth, gravity_bot_url)

    silent_ok = _run_silent_login(auth)

    if not silent_ok:
        spinner.close()
        spinner = None
        dialog = LoginDialog(auth)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            api.close()
            sys.exit(0)

    # ── First-run setup wizard ────────────────────────────────────────────────
    if not settings_svc.settings.setup_wizard_completed:
        if spinner is not None:
            spinner.close()
            spinner = None
        from ui.setup_wizard import SetupWizard  # noqa: PLC0415
        SetupWizard().exec()
    # ──────────────────────────────────────────────────────────────────────────

    # Warm the connection pool before the window shows so the first user-triggered
    # request reuses a live connection (avoids DNS + TCP + TLS on the hot path).
    # Run in a thread and pump processEvents() so the spinner stays animated.
    import threading as _threading
    _warmup_done = _threading.Event()
    _threading.Thread(
        target=lambda: (api.warmup(), _warmup_done.set()),
        daemon=True,
        name="api-warmup",
    ).start()
    while not _warmup_done.wait(timeout=0.016):  # ~60 fps pump
        app.processEvents()

    # Need to run after authentication
    gravity_bot_svc = GravityBotService(auth, api)
    registry.register(IGravityBotService, gravity_bot_svc)

    # Forward guild-chat messages to the bot WebSocket when connected
    log_parser_svc.guild_message.connect(gravity_bot_svc.send_guild_chat)

    # Start the WS connection and block (pumping the event loop) until the
    # handshake resolves — so the main window opens with connection status ready.
    # connected_changed crosses the WS thread → main thread via a queued signal;
    # it is only delivered during processEvents(), same as the warmup loop above.
    if settings_svc.settings.gravity_bot.ws_enabled and auth.is_authenticated():
        import time as _ws_time

        if spinner is not None:
            spinner.set_status("Connecting to Gravity Bot…")
            app.processEvents()

        _ws_resolved = _threading.Event()

        def _on_ws_startup_result(_: bool) -> None:
            _ws_resolved.set()

        gravity_bot_svc.connected_changed.connect(_on_ws_startup_result)
        gravity_bot_svc.connect_bot()

        _WS_STARTUP_TIMEOUT = 12.0  # slightly beyond open_timeout=10 in _WsThread
        _t0 = _ws_time.monotonic()
        while not _ws_resolved.wait(timeout=0.016):
            app.processEvents()
            if _ws_time.monotonic() - _t0 > _WS_STARTUP_TIMEOUT:
                log.warning("Gravity Bot WS connect timed out during startup")
                break

        gravity_bot_svc.connected_changed.disconnect(_on_ws_startup_result)
        log.info("Gravity Bot WS startup wait complete — connected=%s", gravity_bot_svc.is_connected)
    elif settings_svc.settings.gravity_bot.ws_enabled:
        log.warning("ws_enabled=True but not authenticated — skipping WebSocket connect")

    window = MainWindow(auth=auth, api=api)

    if spinner is not None:
        spinner.close()
        spinner = None

    window.show()

    # System tray icon
    tray_icon_path = get_asset("icons/only_logo.ico")
    tray_icon = QIcon(str(tray_icon_path)) if tray_icon_path.exists() else app_icon
    tray = QSystemTrayIcon(tray_icon, app)
    tray_menu = QMenu()
    tray_menu.addAction("Show", lambda: (window.showNormal(), window.activateWindow()))
    tray_menu.addSeparator()
    tray_menu.addAction("Quit", window.force_quit)
    tray.setContextMenu(tray_menu)
    tray.setToolTip("Gravity Nexus")
    tray.activated.connect(
        lambda reason: (window.showNormal(), window.activateWindow())
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )
    tray.show()
    # Store on the app instance so MainWindow can find it for balloon messages
    app.setProperty("tray_icon", tray)

    # ── Update service ────────────────────────────────────────────────────────
    update_svc.update_available.connect(
        lambda version, _url: tray.showMessage(
            "Gravity Nexus",
            f"Update available: v{version}. Go to Settings → General to install.",
            QSystemTrayIcon.MessageIcon.Information,
            8000,
        ) if tray.supportsMessages() else None
    )
    update_svc.restart_requested.connect(window.force_quit)
    update_svc.start()

    # ── Auto-start services based on settings (after window is wired up) ──────
    general = settings_svc.settings.general
    if general.auto_start_parser and general.log_directory:
        log.info(
            "auto_start_parser=True — starting log parser for: %s",
            general.log_directory,
        )
        log_parser_svc.start(general.log_directory)
    elif general.auto_start_parser:
        log.warning(
            "auto_start_parser=True but log_directory is not configured — skipping"
        )
        if tray.supportsMessages():
            tray.showMessage(
                "Gravity Nexus",
                "Parser not started: no log directory configured. Go to Settings → General.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )

    log.info("Gravity Nexus started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

