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

# ── Ensure app/ is first on the path so all sub-module imports resolve ────────
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# ── Enable High DPI before QApplication is created ────────────────────────────
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

# ── Remaining imports (after sys.path is set) ─────────────────────────────────
from theme.theme_manager import ThemeManager
from ui.main_window import MainWindow
from utils.platform_utils import set_app_user_model_id
from utils.resource_utils import get_asset
from services.settings_service import SettingsService

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gravity_nexus")


def main() -> int:
    """Application entry point. Returns exit code."""
    # Windows taskbar identity
    set_app_user_model_id("com.gravitynexus.app")

    app = QApplication(sys.argv)
    app.setApplicationName("Gravity Nexus")
    app.setOrganizationName("GravityNexus")
    app.setApplicationVersion("1.0.0")

    # Apply theme before creating any windows, using the persisted font size
    svc = SettingsService.instance()
    ThemeManager.instance().apply(app, base_font_size_pt=svc.settings.appearance.font_size)

    # Set application-wide icon (taskbar, Alt+Tab, window decorations)
    app_icon_path = get_asset("icons/full_logo.ico")
    app_icon = QIcon(str(app_icon_path)) if app_icon_path.exists() else QIcon()
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    # System tray icon
    tray_icon_path = get_asset("icons/only_logo.ico")
    tray_icon = QIcon(str(tray_icon_path)) if tray_icon_path.exists() else app_icon
    tray = QSystemTrayIcon(tray_icon, app)
    tray_menu = QMenu()
    tray_menu.addAction("Show", lambda: (window.showNormal(), window.activateWindow()))
    tray_menu.addSeparator()
    tray_menu.addAction("Quit", app.quit)
    tray.setContextMenu(tray_menu)
    tray.setToolTip("Gravity Nexus")
    tray.activated.connect(
        lambda reason: (window.showNormal(), window.activateWindow())
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )
    tray.show()

    log.info("Gravity Nexus started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

