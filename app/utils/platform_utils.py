"""Platform utilities — Windows-specific helpers with safe no-ops elsewhere."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    import ctypes.wintypes

    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    _GWL_EXSTYLE = -20
    _WS_EX_LAYERED = 0x00080000
    _WS_EX_TRANSPARENT = 0x00000020


def set_window_click_through(hwnd: int, enabled: bool) -> bool:
    """Toggle Windows click-through (transparent to mouse events) on *hwnd*.

    Returns True if the operation succeeded.
    On non-Windows platforms this is always a no-op that returns False.
    """
    if not _IS_WINDOWS:
        log.debug("set_window_click_through() is a no-op on %s", sys.platform)
        return False

    try:
        style: int = _user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        if enabled:
            style |= _WS_EX_LAYERED | _WS_EX_TRANSPARENT
        else:
            style &= ~_WS_EX_TRANSPARENT
            # Keep WS_EX_LAYERED so translucency still works
        result: int = _user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, style)
        if result == 0 and ctypes.GetLastError() != 0:
            log.warning(
                "SetWindowLongW failed (hwnd=%s, enabled=%s)", hwnd, enabled
            )
            return False
        log.debug("Click-through %s on hwnd %s", "enabled" if enabled else "disabled", hwnd)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("set_window_click_through error: %s", exc)
        return False


def apply_startup_with_windows(enabled: bool) -> None:
    """Add or remove Gravity Nexus from the Windows startup registry.

    Uses HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run so no
    elevated permissions are needed.  No-op on non-Windows platforms.
    """
    if not _IS_WINDOWS:
        return
    import winreg  # stdlib, Windows-only  # noqa: PLC0415
    _RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _VALUE_NAME = "GravityNexus"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        if enabled:
            exe = sys.executable
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, f'"{exe}"')
            log.debug("Added startup registry entry: %s", exe)
        else:
            try:
                winreg.DeleteValue(key, _VALUE_NAME)
                log.debug("Removed startup registry entry")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not update startup registry key: %s", exc)


def set_app_user_model_id(app_id: str) -> None:
    """Set the Windows Application User Model ID for taskbar grouping.

    Must be called before the first window is shown. No-op on other platforms.
    """
    if not _IS_WINDOWS:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type: ignore[attr-defined]
        log.debug("AppUserModelID set to %s", app_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not set AppUserModelID: %s", exc)

