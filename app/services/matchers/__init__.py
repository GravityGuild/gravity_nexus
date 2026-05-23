"""Log matchers package.

Each concrete ``LogMatcher`` subclass handles a specific category of EQ log
events.  Register instances with ``LogParserService.register_matcher()``.
"""
from services.matchers.base import LogMatcher
from services.matchers.guild_chat_matcher import GuildChatMatcher
from services.matchers.raid_dump_matcher import RaidDumpMatcher
from services.matchers.zone_matcher import ZoneMatcher

__all__ = ["LogMatcher", "GuildChatMatcher", "RaidDumpMatcher", "ZoneMatcher"]
