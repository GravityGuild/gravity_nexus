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
import sys
from pathlib import Path

from _version import __version__

# ── Ensure app/ is first on the path so all sub-module imports resolve ────────
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# ── Enable High DPI before QApplication is created ────────────────────────────
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QSurfaceFormat
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

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
from ui.main_window import MainWindow
from utils.platform_utils import set_app_user_model_id
from utils.resource_utils import get_asset

# ── Composition root — only place that imports concrete service classes ────────
from core.registry import registry
from services.protocols import IGravityBotService, ILogParserService, ISettingsService
from services.gravity_bot_service import GravityBotService
from services.log_parser_service import LogParserService
from services.settings_service import SettingsService

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
    gravity_bot_svc = GravityBotService()
    registry.register(IGravityBotService, gravity_bot_svc)

    # Forward guild-chat messages to the bot WebSocket when connected
    log_parser_svc.guild_message.connect(gravity_bot_svc.send_guild_chat)

    # Apply theme before creating any windows, using the persisted font size
    ThemeManager.instance().apply(app, base_font_size_pt=settings_svc.settings.appearance.font_size)

    # Set application-wide icon (taskbar, Alt+Tab, window decorations)
    app_icon_path = get_asset("icons/full_logo.ico")
    app_icon = QIcon(str(app_icon_path)) if app_icon_path.exists() else QIcon()
    app.setWindowIcon(app_icon)

    window = MainWindow()

    # ── Auto-connect Gravity Bot if configured ────────────────────────────────
    gravity_bot_cfg = settings_svc.settings.gravity_bot
    if gravity_bot_cfg.auto_connect:
        if gravity_bot_cfg.bot_url and gravity_bot_cfg.auth_token:
            log.info("auto_connect=True — connecting to Gravity Bot: %s", gravity_bot_cfg.bot_url)
            gravity_bot_svc.connect_bot()
        else:
            log.warning("auto_connect=True but Gravity Bot URL or token not configured — skipping")

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

    log.info("Gravity Nexus started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

