"""Pages package."""
from ui.pages.fake_log_page import FakeLogPage
from ui.pages.feature_flags_page import FeatureFlagsPage
from ui.pages.general_page import GeneralPage
from ui.pages.gravity_bot_page import GravityBotPage
from ui.pages.overlays_page import OverlaysPage
from ui.pages.parsing_page import ParsingPage
from ui.pages.pages import (
    AboutPage,
    AdvancedPage,
    AppearancePage,
    NotificationsPage,
)

__all__ = [
    "FakeLogPage",
    "FeatureFlagsPage",
    "GeneralPage",
    "GravityBotPage",
    "OverlaysPage",
    "ParsingPage",
    "NotificationsPage",
    "AppearancePage",
    "AdvancedPage",
    "AboutPage",
]
