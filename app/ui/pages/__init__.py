"""Pages package."""
from ui.pages.dev_tools_page import DevToolsPage
from ui.pages.feature_flags_page import FeatureFlagsPage
from ui.pages.general_page import GeneralPage
from ui.pages.gravity_bot_page import GravityBotPage
from ui.pages.overlays_page import OverlaysPage
from ui.pages.page_config import PageConfig
from ui.pages.parsing_page import ParsingPage
from ui.pages.raid_tools_page import RaidToolsPage
from ui.pages.pages import (
    AboutPage,
    AdvancedPage,
    AppearancePage,
    NotificationsPage,
)

__all__ = [
    "DevToolsPage",
    "FeatureFlagsPage",
    "GeneralPage",
    "GravityBotPage",
    "OverlaysPage",
    "PageConfig",
    "ParsingPage",
    "RaidToolsPage",
    "NotificationsPage",
    "AppearancePage",
    "AdvancedPage",
    "AboutPage",
]
