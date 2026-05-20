"""SettingsService — persists AppSettings via QSettings.

Settings are stored under the organization "GravityNexus" with
application name "GravityNexus" (native registry on Windows).

Usage::

    svc = SettingsService.instance()
    svc.settings.general.log_file_path = "/path/to/log"
    svc.save()
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QSettings

from models.settings_model import (
    AppSettings,
    AppearanceSettings,
    GeneralSettings,
    NotificationSettings,
    OverlaySettings,
    ParsingSettings,
)

log = logging.getLogger(__name__)

_ORG = "GravityNexus"
_APP = "GravityNexus"


class SettingsService:
    """Singleton wrapper around QSettings for typed AppSettings persistence."""

    _instance: Optional["SettingsService"] = None

    def __init__(self) -> None:
        self._q = QSettings(_ORG, _APP)
        self._settings = AppSettings()
        self.load()

    # ── Singleton ──────────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "SettingsService":
        """Return the global SettingsService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def load(self) -> None:
        """Load all settings from the native store into the in-memory model."""
        q = self._q
        s = self._settings

        # General
        q.beginGroup("general")
        s.general.log_file_path = self._get(q, "log_file_path", s.general.log_file_path)
        s.general.auto_start_parser = self._get(q, "auto_start_parser", s.general.auto_start_parser)
        s.general.minimize_to_tray = self._get(q, "minimize_to_tray", s.general.minimize_to_tray)
        s.general.start_with_windows = self._get(q, "start_with_windows", s.general.start_with_windows)
        s.general.check_for_updates = self._get(q, "check_for_updates", s.general.check_for_updates)
        q.endGroup()

        # Overlay
        q.beginGroup("overlay")
        s.overlay.enabled = self._get(q, "enabled", s.overlay.enabled)
        s.overlay.opacity = float(self._get(q, "opacity", s.overlay.opacity))
        s.overlay.click_through = self._get(q, "click_through", s.overlay.click_through)
        s.overlay.always_on_top = self._get(q, "always_on_top", s.overlay.always_on_top)
        s.overlay.scale = float(self._get(q, "scale", s.overlay.scale))
        q.endGroup()

        # Parsing
        q.beginGroup("parsing")
        s.parsing.dps_window_seconds = int(self._get(q, "dps_window_seconds", s.parsing.dps_window_seconds))
        s.parsing.show_pets = self._get(q, "show_pets", s.parsing.show_pets)
        s.parsing.show_totals = self._get(q, "show_totals", s.parsing.show_totals)
        s.parsing.update_interval_ms = int(self._get(q, "update_interval_ms", s.parsing.update_interval_ms))
        q.endGroup()

        # Notifications
        q.beginGroup("notifications")
        s.notifications.sound_enabled = self._get(q, "sound_enabled", s.notifications.sound_enabled)
        s.notifications.raid_timer_alerts = self._get(q, "raid_timer_alerts", s.notifications.raid_timer_alerts)
        s.notifications.named_spawn_alerts = self._get(q, "named_spawn_alerts", s.notifications.named_spawn_alerts)
        s.notifications.volume = int(self._get(q, "volume", s.notifications.volume))
        q.endGroup()

        # Appearance
        q.beginGroup("appearance")
        s.appearance.theme_name = self._get(q, "theme_name", s.appearance.theme_name)
        s.appearance.font_size = int(self._get(q, "font_size", s.appearance.font_size))
        s.appearance.use_orbitron_headings = self._get(q, "use_orbitron_headings", s.appearance.use_orbitron_headings)
        q.endGroup()

        # Top-level
        s.active_profile = self._get(q, "active_profile", s.active_profile)
        geom = q.value("window_geometry")
        if geom is not None:
            s.window_geometry = bytes(geom)

        log.debug("Settings loaded from %s", self._q.fileName())

    def save(self) -> None:
        """Flush the in-memory model back to the native store."""
        q = self._q
        s = self._settings

        q.beginGroup("general")
        q.setValue("log_file_path", s.general.log_file_path)
        q.setValue("auto_start_parser", s.general.auto_start_parser)
        q.setValue("minimize_to_tray", s.general.minimize_to_tray)
        q.setValue("start_with_windows", s.general.start_with_windows)
        q.setValue("check_for_updates", s.general.check_for_updates)
        q.endGroup()

        q.beginGroup("overlay")
        q.setValue("enabled", s.overlay.enabled)
        q.setValue("opacity", s.overlay.opacity)
        q.setValue("click_through", s.overlay.click_through)
        q.setValue("always_on_top", s.overlay.always_on_top)
        q.setValue("scale", s.overlay.scale)
        q.endGroup()

        q.beginGroup("parsing")
        q.setValue("dps_window_seconds", s.parsing.dps_window_seconds)
        q.setValue("show_pets", s.parsing.show_pets)
        q.setValue("show_totals", s.parsing.show_totals)
        q.setValue("update_interval_ms", s.parsing.update_interval_ms)
        q.endGroup()

        q.beginGroup("notifications")
        q.setValue("sound_enabled", s.notifications.sound_enabled)
        q.setValue("raid_timer_alerts", s.notifications.raid_timer_alerts)
        q.setValue("named_spawn_alerts", s.notifications.named_spawn_alerts)
        q.setValue("volume", s.notifications.volume)
        q.endGroup()

        q.beginGroup("appearance")
        q.setValue("theme_name", s.appearance.theme_name)
        q.setValue("font_size", s.appearance.font_size)
        q.setValue("use_orbitron_headings", s.appearance.use_orbitron_headings)
        q.endGroup()

        q.setValue("active_profile", s.active_profile)
        q.setValue("window_geometry", s.window_geometry)
        q.sync()
        log.debug("Settings saved")

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _get(q: QSettings, key: str, default: Any) -> Any:
        value = q.value(key)
        if value is None:
            return default
        # QSettings may return strings for booleans on Windows registry
        if isinstance(default, bool):
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        return value

