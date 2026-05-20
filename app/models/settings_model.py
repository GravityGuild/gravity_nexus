"""Application settings data model.

All persistent settings live here as typed dataclass fields.
Default values are always valid so a fresh install works without a config file.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GeneralSettings:
    log_file_path: str = ""
    auto_start_parser: bool = False
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    check_for_updates: bool = True


@dataclass
class OverlaySettings:
    enabled: bool = True
    opacity: float = 0.85
    click_through: bool = False
    always_on_top: bool = True
    scale: float = 1.0
    # Position is stored per-overlay by name
    positions: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class ParsingSettings:
    dps_window_seconds: int = 60
    show_pets: bool = True
    show_totals: bool = True
    update_interval_ms: int = 500


@dataclass
class NotificationSettings:
    sound_enabled: bool = True
    raid_timer_alerts: bool = True
    named_spawn_alerts: bool = True
    volume: int = 70


@dataclass
class AppearanceSettings:
    theme_name: str = "cosmic"
    font_size: int = 14          # pt — matches _DEFAULT_FONT_PT in theme_manager
    use_orbitron_headings: bool = True


@dataclass
class AppSettings:
    """Top-level settings container — one per application instance."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    parsing: ParsingSettings = field(default_factory=ParsingSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    active_profile: str = "Default"
    window_geometry: bytes = field(default_factory=bytes)

