"""Feature flag registry — single source of truth for all in-development features.

To add a new flag:
1. Append a FeatureFlag entry to FEATURE_REGISTRY.
2. Check it in code with: feature_enabled("your_flag_key", settings)

The flag will automatically appear in the Feature Flags settings page.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.settings_model import AppSettings


@dataclass(frozen=True)
class FeatureFlag:
    key: str
    label: str
    description: str
    default: bool = False


FEATURE_REGISTRY: list[FeatureFlag] = [
    FeatureFlag(
        key="notifications_page",
        label="Notifications Page",
        description="Show the Notifications page in the sidebar navigation.",
        default=False,
    ),
    FeatureFlag(
        key="quick_toolbar",
        label="Quick Toolbar Overlay",
        description="Show the draggable Quick Action Toolbar overlay on startup.",
        default=False,
    ),
    FeatureFlag(
        key="theme_selector",
        label="Theme Selector",
        description="Show the Theme selector card on the Appearance page.",
        default=False,
    ),
    FeatureFlag(
        key="typography_options",
        label="Typography Options",
        description="Show the Typography card on the Appearance page.",
        default=False,
    ),
    FeatureFlag(
        key="overlay_always_on_top",
        label="Overlay: Always on Top",
        description="Show the 'Always on top' toggle on the Overlays page.",
        default=False,
    ),
    FeatureFlag(
        key="overlay_click_through",
        label="Overlay: Click-Through Mode",
        description="Show the 'Click-through mode (Windows)' toggle on the Overlays page.",
        default=False,
    ),
    FeatureFlag(
        key="reduce_update_rate_in_background",
        label="Reduce Update Rate in Background",
        description="Show the 'Reduce update rate in background' toggle on the General page.",
        default=False,
    ),
]


def feature_enabled(key: str, settings: AppSettings) -> bool:
    """Return whether a feature flag is enabled, falling back to its registered default."""
    flag = next((f for f in FEATURE_REGISTRY if f.key == key), None)
    if flag is None:
        return False
    return settings.feature_flags.flags.get(key, flag.default)
