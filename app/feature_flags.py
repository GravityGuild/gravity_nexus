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
]


def feature_enabled(key: str, settings: AppSettings) -> bool:
    """Return whether a feature flag is enabled, falling back to its registered default."""
    flag = next((f for f in FEATURE_REGISTRY if f.key == key), None)
    if flag is None:
        return False
    return settings.feature_flags.flags.get(key, flag.default)
