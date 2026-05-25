# Gravity Nexus

Raid tools and integration with Gravity's Discord bot and DKP website, for Project 1999.

---

## Table of Contents

- [Installation](#installation)
- [Setup & Configuration](#setup--configuration)
- [Features](#features)
  - [Raid Tools](#raid-tools)
  - [Gravity Bot Integration](#gravity-bot-integration)
  - [Overlays](#overlays)
- [Developers](#developers)

---

## Installation

### Requirements

- Windows 10 or later

### Steps

1. Download the latest installer from the [Releases](https://github.com/GravityGuild/gravity_nexus/releases) page.
2. Run `GravityNexus_Setup_x.x.x.exe` and follow the on-screen prompts.
3. Launch **Gravity Nexus** from the Start Menu or Desktop shortcut.

---

## Setup & Configuration

### First Launch

1. **Sign in** — On first launch you will be prompted to sign in. Click **Sign in with Browser** and complete the login on the Gravity DKP site. The app will detect the successful login automatically.

2. **Setup Wizard** — After signing in, a one-time setup wizard will guide you through:
   - **EQ Logs Directory** — Point Gravity Nexus to your EverQuest `Logs` folder (e.g. `C:\EverQuest\Logs`). The app auto-detects your character's log file.
   - **Startup Preferences** — Choose whether to start with Windows, minimize to tray on close, and auto-start the log parser.

3. **You're ready** — All preferences can be changed later.

## Features

**Software updates** — Gravity Nexus can check for and install new releases automatically. Provide a GitHub Personal Access Token in Settings → General to enable this. The token is stored securely in your system credential store.


### Raid Tools

The **Raid Log Capture** tool captures raid attendance from `/who` output and submits it to the Gravity Discord bot.

**How to use:**

1. Type `/t nexusraidlog` in EverQuest chat to start a raid log capture.
2. Type `/who` to take the raid log.
3. The **Raid Submit** overlay will appear — select the raid from the dropdown and confirm.

> **Tip:** Combine the two commands into a social for easy one-button use.

**Quick Raid Logs** — When enabled (Settings → Raid Tools), typing `/who` twice within 5 seconds will automatically trigger a capture without needing the `/t nexusraidlog` step.

### Gravity Bot Integration

Gravity Nexus connects to the Gravity Bot to relay in-game events to Discord.

- **Guild chat relay** — Guild chat lines are forwarded to the bot in real time so they can be displayed in the guild-chat-stream channel  (toggle in Settings → General).


### Overlays

**Positioning overlays:** Go to **Settings → Overlays** and click **Position Overlays** to drag all overlays to your preferred screen positions. Click **Save Positions** when done.

Global overlay options include enabling/disabling all overlays and adjusting opacity.


---

## Developers

### Quick Start

```bash
# 1. Activate venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download bundled fonts (Orbitron — one-time)
python scripts/download_fonts.py

# 4. Launch
python app/main.py
```

### Project Structure

```
gravity_nexus/
├── app/
│   ├── main.py                      # Entry point; bootstraps auth, services, and MainWindow
│   ├── _version.py                  # Single source of truth for the version string
│   ├── feature_flags.py             # Feature-flag evaluation helpers
│   ├── auth/
│   │   ├── auth_manager.py          # OAuth browser-login flow coordinator
│   │   ├── callback_server.py       # Local HTTP server that receives the OAuth callback
│   │   └── api_client.py            # Authenticated HTTP client for the DKP API
│   ├── core/
│   │   └── registry.py              # Service-locator registry (IoC container)
│   ├── theme/
│   │   ├── colors.py                # Colour constants (single source of truth)
│   │   ├── spec.py                  # ColorRole / FontRole / FontSize enums
│   │   ├── qss_builder.py           # Programmatic QSS stylesheet builder
│   │   └── theme_manager.py         # Singleton — loads fonts and applies QSS
│   ├── ui/
│   │   ├── main_window.py           # Frameless application shell
│   │   ├── sidebar.py               # Animated navigation sidebar
│   │   ├── titlebar.py              # Draggable custom title bar
│   │   ├── statusbar.py             # Bottom status strip
│   │   ├── login_dialog.py          # Sign-in modal (browser OAuth flow)
│   │   ├── setup_wizard.py          # First-run configuration wizard
│   │   ├── loading_spinner.py       # Animated loading indicator widget
│   │   ├── pages/
│   │   │   ├── page_config.py       # PageConfig dataclass (label, icon, factory)
│   │   │   ├── general_page.py      # General / startup settings
│   │   │   ├── parsing_page.py      # Log-handler toggles
│   │   │   ├── raid_tools_page.py   # Raid Log Capture configuration
│   │   │   ├── gravity_bot_page.py  # WebSocket options
│   │   │   ├── overlays_page.py     # Overlay settings and positioning
│   │   │   └── pages.py             # Appearance, Notifications, Advanced, About pages
│   │   ├── cards/
│   │   │   ├── settings_card.py     # SettingsCard container widget
│   │   │   └── tool_card.py         # ToolCard with Overview / Instructions / Settings tabs
│   │   ├── widgets/                 # Reusable themed widget primitives
│   │   └── overlays/
│   │       ├── base_overlay_window.py      # Frameless, translucent, always-on-top base
│   │       ├── raid_submit_overlay.py      # Raid attendance submission popup
│   │       ├── quick_toolbar_overlay.py    # Compact always-on-top toolbar
│   │       └── positioning_overlay.py      # Draggable placeholder for positioning mode
│   ├── models/
│   │   ├── settings_model.py        # Typed dataclass settings model (AppSettings)
│   │   ├── log_event.py             # LogEvent dataclass
│   │   └── who_entry.py             # WhoEntry dataclass (parsed /who line)
│   ├── services/
│   │   ├── protocols.py             # Service interfaces (ISettingsService, etc.)
│   │   ├── settings_service.py      # QSettings persistence (native registry)
│   │   ├── log_parser_service.py    # Log file tailer and event dispatch
│   │   ├── gravity_bot_service.py   # WebSocket client for Gravity Bot
│   │   ├── update_service.py        # GitHub release checker and installer
│   │   ├── mock_data_provider.py    # Simulated data for overlay preview
│   │   └── matchers/
│   │       ├── base.py              # BaseMatcher abstract class
│   │       ├── guild_chat_matcher.py
│   │       ├── who_list_matcher.py
│   │       ├── zone_matcher.py
│   │       └── raid_log_matcher.py
│   └── utils/
│       ├── platform_utils.py        # Win32 click-through, AUMID, startup registry
│       └── resource_utils.py        # Dev / Nuitka path resolution
├── scripts/
│   └── download_fonts.py            # One-time Orbitron font downloader
├── build_nuitka.py                  # Nuitka standalone build script
└── requirements.txt
```

### Nuitka Build

```bash
python build_nuitka.py
# Produces dist/main.exe (standalone, no console window)
```

### Architecture Notes

| Concern | Approach |
|---------|----------|
| **Auth** | `AuthManager` opens a browser to the DKP site OAuth page and spins up a local `CallbackServer` to receive the token. Credentials are stored in the system keychain via `keyring`. |
| **Service registry** | `core/registry.py` is a lightweight IoC container. Services are registered at startup and resolved by interface type throughout the UI. |
| **Theme** | `ThemeManager` singleton builds and applies QSS via `QssBuilder` using `ColorRole` / `FontRole` enums. No hardcoded colours in widgets. |
| **Settings** | `SettingsService` wraps `QSettings("GravityNexus","GravityNexus")`. Typed `AppSettings` dataclass is the in-memory model; `load()` / `save()` sync it to the registry. |
| **Log parsing** | `LogParserService` tails the active log file on a background thread and dispatches `LogEvent` objects to registered `BaseMatcher` instances. Each matcher is independently enable/disable-able. |
| **Overlays** | `BaseOverlayWindow` — frameless, translucent, always-on-top. Click-through uses `WS_EX_TRANSPARENT` via ctypes (Windows only). |
| **Updates** | `UpdateService` checks GitHub Releases via the API (requires a PAT), downloads the installer to a temp path, and launches it with `/SILENT` flags before quitting. |
| **Feature flags** | `feature_flags.py` gates experimental UI sections. Flags are evaluated against `AppSettings` and can be toggled from the Feature Flags dev page. |
