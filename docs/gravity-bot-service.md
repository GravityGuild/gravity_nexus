# Gravity Bot Service

`GravityBotService` (`app/services/gravity_bot_service.py`) manages communication with the Gravity Bot server.

- **WebSocket** — persistent connection via `_WsThread`; auto-reconnects with exponential backoff (1 s → 60 s). Tokens are refreshed on every reconnect attempt.
- **REST** — calls run in a temporary `_RestSubmitThread` so the main thread is never blocked.
- Signals cross the worker thread → main thread via Qt queued connections; no manual locking needed in callsites.
