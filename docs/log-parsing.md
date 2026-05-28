# Log Parsing Pipeline

`LogParserService` (`app/services/log_parser_service.py`) runs a background `_TailThread` (QThread) polling the active EQ log every 50 ms. Lines are emitted to the main thread and dispatched to registered `LogMatcher` instances.

- Watches a directory for `eqlog_{CharName}_project1999.txt`; auto-switches on character change every 5 s.
- Also tails `dbg.txt` for logout/crash detection (`LogSource.DBG_TXT`).

Built-in matchers: `RaidLogMatcher`, `ZoneMatcher`, `GuildChatMatcher`, `WhoListMatcher`, `CampMatcher`.

## Adding a matcher

1. Subclass `LogMatcher` (`app/services/matchers/base.py`) and override `process(event)`.
2. Set `SOURCES` to control which log source(s) the matcher receives (`EQ_LOG`, `DBG_TXT`, or both).
3. Set `MATCHER_KEY` (snake_case) to expose a toggle in the Parsing settings UI; leave empty to hide it.
4. Register: `log_parser_svc.register_matcher(matcher)`.
