"""Application settings data model.

All persistent settings live here as typed dataclass fields.
Default values are always valid so a fresh install works without a config file.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GeneralSettings:
    log_directory: str = ""       # Path to the EverQuest "Logs" folder
    auto_start_parser: bool = False
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    check_for_updates: bool = True
    github_token: str = ""         # stored in credential store, not plain settings
    last_update_check_timestamp: float = 0.0
    update_check_interval_hours: int = 24
    debug_logging: bool = False
    hardware_accelerated: bool = True
    reduce_update_rate_in_background: bool = True


@dataclass
class OverlaySettings:
    enabled: bool = True
    opacity: float = 0.85
    click_through: bool = False
    always_on_top: bool = True
    scale: float = 1.0
    # Geometry is stored per-overlay by name: (x, y, width, height).
    # Legacy entries that only have (x, y) are tolerated on load.
    positions: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)


@dataclass
class ParsingSettings:
    dps_window_seconds: int = 60
    show_pets: bool = True
    show_totals: bool = True
    update_interval_ms: int = 500
    #: Maps MATCHER_KEY → enabled.  Missing keys fall back to ENABLED_BY_DEFAULT.
    enabled_matchers: dict[str, bool] = field(default_factory=dict)
    quick_raid_logs: bool = True


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
class GravityBotSettings:
    """Settings for Gravity Bot integration."""

    auth_token: str = ""    # plain bearer token (no "Bearer " prefix)
    ws_enabled: bool = True  # enable WebSocket connection thread
    auto_connect: bool = False  # connect automatically on app start
    send_guild_chat: bool = True  # forward parsed guild chat to bot via WebSocket


@dataclass
class ToolbarSettings:
    """Settings for the Quick-Action Toolbar overlay."""

    enabled: bool = True
    collapsed: bool = False
    orientation: str = "horizontal"      # "horizontal" | "vertical"
    button_keys: list[str] = field(default_factory=lambda: ["placeholder"])


@dataclass
class FeatureFlagsSettings:
    """Persisted on/off state for in-development feature flags."""

    #: Maps feature key → enabled.  Missing keys fall back to the flag's registered default.
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class AppSettings:
    """Top-level settings container — one per application instance."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    parsing: ParsingSettings = field(default_factory=ParsingSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    gravity_bot: GravityBotSettings = field(default_factory=GravityBotSettings)
    toolbar: ToolbarSettings = field(default_factory=ToolbarSettings)
    feature_flags: FeatureFlagsSettings = field(default_factory=FeatureFlagsSettings)
    window_geometry: bytes = field(default_factory=bytes)
    setup_wizard_completed: bool = False

