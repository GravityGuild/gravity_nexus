"""SettingsService — persists AppSettings via QSettings.

Settings are stored under the organization "GravityNexus" with
application name "GravityNexus" (native registry on Windows).

Usage::

    svc = registry.get(ISettingsService)
    svc.settings.general.log_directory = "C:/EverQuest/Logs"
    svc.save()
"""
from __future__ import annotations

import logging
from typing import Any

import json
import keyring
import keyring.errors

from PySide6.QtCore import QSettings

_BOT_KEYRING_SERVICE = "gravity_nexus"
_BOT_KEYRING_KEY = "bot_auth_token"

from models.settings_model import AppSettings

log = logging.getLogger(__name__)

_ORG = "GravityNexus"
_APP = "GravityNexus"


class SettingsService:
    """Wraps QSettings for typed AppSettings persistence.

    Instantiate once in the composition root (``main.py``) and register as
    ``ISettingsService``.  Resolve via ``registry.get(ISettingsService)``
    everywhere else.
    """

    def __init__(self) -> None:
        self._q = QSettings(_ORG, _APP)
        self._settings = AppSettings()
        self.load()

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
        s.general.log_directory = self._get(q, "log_directory", s.general.log_directory)
        s.general.auto_start_parser = self._get(q, "auto_start_parser", s.general.auto_start_parser)
        s.general.minimize_to_tray = self._get(q, "minimize_to_tray", s.general.minimize_to_tray)
        s.general.start_with_windows = self._get(q, "start_with_windows", s.general.start_with_windows)
        s.general.check_for_updates = self._get(q, "check_for_updates", s.general.check_for_updates)
        s.general.last_update_check_timestamp = float(self._get(q, "last_update_check_timestamp", s.general.last_update_check_timestamp))
        s.general.update_check_interval_hours = int(self._get(q, "update_check_interval_hours", s.general.update_check_interval_hours))
        s.general.debug_logging = self._get(q, "debug_logging", s.general.debug_logging)
        s.general.hardware_accelerated = self._get(q, "hardware_accelerated", s.general.hardware_accelerated)
        s.general.reduce_update_rate_in_background = self._get(
            q, "reduce_update_rate_in_background", s.general.reduce_update_rate_in_background
        )
        q.endGroup()

        # Overlay
        q.beginGroup("overlay")
        s.overlay.enabled = self._get(q, "enabled", s.overlay.enabled)
        s.overlay.opacity = float(self._get(q, "opacity", s.overlay.opacity))
        s.overlay.click_through = self._get(q, "click_through", s.overlay.click_through)
        s.overlay.always_on_top = self._get(q, "always_on_top", s.overlay.always_on_top)
        s.overlay.scale = float(self._get(q, "scale", s.overlay.scale))
        positions_raw = q.value("positions")
        if positions_raw:
            try:
                loaded = json.loads(positions_raw)
                rebuilt: dict[str, tuple[int, int, int, int]] = {}
                for k, v in loaded.items():
                    if len(v) >= 4:
                        rebuilt[k] = (int(v[0]), int(v[1]), int(v[2]), int(v[3]))
                    elif len(v) == 2:
                        # Migrate legacy (x, y)-only entries — size will be 0 (use default)
                        rebuilt[k] = (int(v[0]), int(v[1]), 0, 0)
                s.overlay.positions = rebuilt
            except Exception:
                pass
        q.endGroup()

        # Gravity Bot
        q.beginGroup("gravity_bot")
        if q.contains("auth_token"):  # one-time migration: clear plaintext token from registry
            q.remove("auth_token")
        s.gravity_bot.ws_enabled = self._get(q, "ws_enabled", s.gravity_bot.ws_enabled)
        s.gravity_bot.auto_connect = self._get(q, "auto_connect", s.gravity_bot.auto_connect)
        q.endGroup()
        stored_bot_token = keyring.get_password(_BOT_KEYRING_SERVICE, _BOT_KEYRING_KEY)
        if stored_bot_token:
            s.gravity_bot.auth_token = stored_bot_token

        # Parsing
        q.beginGroup("parsing")
        s.parsing.dps_window_seconds = int(self._get(q, "dps_window_seconds", s.parsing.dps_window_seconds))
        s.parsing.show_pets = self._get(q, "show_pets", s.parsing.show_pets)
        s.parsing.show_totals = self._get(q, "show_totals", s.parsing.show_totals)
        s.parsing.update_interval_ms = int(self._get(q, "update_interval_ms", s.parsing.update_interval_ms))
        enabled_raw = q.value("enabled_matchers")
        if enabled_raw:
            try:
                s.parsing.enabled_matchers = json.loads(enabled_raw)
            except Exception:
                pass
        s.parsing.quick_raid_logs = self._get(q, "quick_raid_logs", s.parsing.quick_raid_logs)
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

        # Toolbar
        q.beginGroup("toolbar")
        s.toolbar.enabled = self._get(q, "enabled", s.toolbar.enabled)
        s.toolbar.collapsed = self._get(q, "collapsed", s.toolbar.collapsed)
        s.toolbar.orientation = self._get(q, "orientation", s.toolbar.orientation)
        keys_raw = q.value("button_keys")
        if keys_raw:
            try:
                s.toolbar.button_keys = json.loads(keys_raw)
            except Exception:
                pass
        q.endGroup()

        # Feature Flags
        q.beginGroup("feature_flags")
        flags_raw = q.value("flags")
        if flags_raw:
            try:
                s.feature_flags.flags = json.loads(flags_raw)
            except Exception:
                pass
        q.endGroup()

        # Top-level
        geom = q.value("window_geometry")
        if geom is not None:
            s.window_geometry = bytes(geom)
        s.setup_wizard_completed = self._get(q, "setup_wizard_completed", s.setup_wizard_completed)

        log.debug("Settings loaded from %s", self._q.fileName())

    def save(self) -> None:
        """Flush the in-memory model back to the native store."""
        q = self._q
        s = self._settings

        q.beginGroup("general")
        q.setValue("log_directory", s.general.log_directory)
        q.setValue("auto_start_parser", s.general.auto_start_parser)
        q.setValue("minimize_to_tray", s.general.minimize_to_tray)
        q.setValue("start_with_windows", s.general.start_with_windows)
        q.setValue("check_for_updates", s.general.check_for_updates)
        q.setValue("last_update_check_timestamp", s.general.last_update_check_timestamp)
        q.setValue("update_check_interval_hours", s.general.update_check_interval_hours)
        q.setValue("debug_logging", s.general.debug_logging)
        q.setValue("hardware_accelerated", s.general.hardware_accelerated)
        q.setValue("reduce_update_rate_in_background", s.general.reduce_update_rate_in_background)
        q.endGroup()

        q.beginGroup("overlay")
        q.setValue("enabled", s.overlay.enabled)
        q.setValue("opacity", s.overlay.opacity)
        q.setValue("click_through", s.overlay.click_through)
        q.setValue("always_on_top", s.overlay.always_on_top)
        q.setValue("scale", s.overlay.scale)
        q.setValue("positions", json.dumps({k: list(v) for k, v in s.overlay.positions.items()}))
        q.endGroup()

        q.beginGroup("gravity_bot")
        q.setValue("ws_enabled", s.gravity_bot.ws_enabled)
        q.setValue("auto_connect", s.gravity_bot.auto_connect)
        q.endGroup()
        if s.gravity_bot.auth_token:
            keyring.set_password(_BOT_KEYRING_SERVICE, _BOT_KEYRING_KEY, s.gravity_bot.auth_token)
        else:
            try:
                keyring.delete_password(_BOT_KEYRING_SERVICE, _BOT_KEYRING_KEY)
            except keyring.errors.PasswordDeleteError:
                pass

        q.beginGroup("parsing")
        q.setValue("dps_window_seconds", s.parsing.dps_window_seconds)
        q.setValue("show_pets", s.parsing.show_pets)
        q.setValue("show_totals", s.parsing.show_totals)
        q.setValue("update_interval_ms", s.parsing.update_interval_ms)
        q.setValue("enabled_matchers", json.dumps(s.parsing.enabled_matchers))
        q.setValue("quick_raid_logs", s.parsing.quick_raid_logs)
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

        q.beginGroup("toolbar")
        q.setValue("enabled", s.toolbar.enabled)
        q.setValue("collapsed", s.toolbar.collapsed)
        q.setValue("orientation", s.toolbar.orientation)
        q.setValue("button_keys", json.dumps(s.toolbar.button_keys))
        q.endGroup()

        q.beginGroup("feature_flags")
        q.setValue("flags", json.dumps(s.feature_flags.flags))
        q.endGroup()

        q.setValue("window_geometry", s.window_geometry)
        q.setValue("setup_wizard_completed", s.setup_wizard_completed)
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

