# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Windows desktop app (PySide6/Qt) for Project 1999 EverQuest — log parsing, raid tools, integration with discord bot and eqdkp plus website.


## Guidelines
- Prefer smaller files with single responsibilities
- Group related files under a common package
- Follow SOLID design principles and clean coding practices
- Use styles defined under @app/theme adding new generic styles when needed avoiding setStyleSheet() calls in components

## Commands

```bash
venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_fonts.py   # one-time Orbitron font download
python app/main.py                 # run
python build_nuitka.py             # build standalone exe
python release.py                  # update release files and build installer
```

Dev `.env` at project root: `EQDKP_WEBSITE_URL`, `GRAVITY_BOT_URL` (both default to `https://gravityp99.com`).

## Build and Release

- Nuitka to build.
- Inno Setup to compile Windows Installer
  - @installer/gravity_nexus_setup.iss


## Architecture

- **[IoC / Service Registry](docs/ioc-registry.md)** — services registered in `app/main.py`, resolved via `registry.get(IFooService)` everywhere else.
- **[Log Parsing](docs/log-parsing.md)** — `LogParserService` tails EQ log files on a background thread; extend `LogMatcher` to react to events.
- **[Auth](docs/auth.md)** — browser OAuth flow via `AuthManager` + local `CallbackServer`; tokens in system keychain.
- **[UI Structure](docs/ui-structure.md)** — frameless `MainWindow` with lazy-loaded pages; overlays extend `BaseOverlayWindow`.
- **[Theme](docs/theme.md)** — all colours via `ColorRole` enums in `app/theme/`; never hardcode values.
- **[Settings](docs/settings.md)** — `AppSettings` dataclass tree persisted via `QSettings` (Windows registry).
- **[Feature Flags](docs/feature-flags.md)** — add to `FEATURE_REGISTRY` in `app/feature_flags.py`; check with `feature_enabled()`.
- **[Gravity Bot Service](docs/gravity-bot-service.md)** — persistent WebSocket with auto-reconnect; REST calls on background threads.
