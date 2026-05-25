"""Log matchers package.

Each concrete ``LogMatcher`` subclass handles a specific category of EQ log
events.  Register instances with ``LogParserService.register_matcher()``.
"""
from services.matchers.base import LogMatcher
from services.matchers.guild_chat_matcher import GuildChatMatcher
from services.matchers.raid_log_matcher import RaidLogMatcher
from services.matchers.zone_matcher import ZoneMatcher

__all__ = ["LogMatcher", "GuildChatMatcher", "RaidLogMatcher", "ZoneMatcher"]
