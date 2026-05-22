# Gravity Nexus

Raid tools and integration with Gravity discord bot and DKP Website.

---

## Table of Contents

- [Installation](#installation)
- [Setup & Configuration](#setup--configuration)
- [Features](#features)
  - [Log Parsing](#log-parsing)
  - [Raid Overlays](#raid-overlays)
  - [Gravity Bot Integration](#gravity-bot-integration)
  - [DKP Website Integration](#dkp-website-integration)
  - [Settings](#settings)
- [Developers](#developers)

---

## Installation

### Requirements

- Windows 10 or later

### Steps

1. Download the latest installer from the [Releases](#) page.
2. Run `GravityNexus_Setup_x.x.x.exe` and follow the on-screen prompts.
3. Launch **Gravity Nexus** from the Start Menu or Desktop shortcut.

---

## Setup & Configuration

1. **EverQuest Log Path** — On first launch, open **Settings** and point the log file path to your P99 log folder (e.g. `C:\EverQuest\Logs`).
2. **Discord Webhook** — Paste your Gravity Discord bot webhook URL into the **Bot Integration** settings field.
3. **DKP Site** — Enter your DKP website credentials / API key under **DKP Settings** to allow loot submission.
4. **Overlays** — Configure which overlays are visible and their screen positions under **Overlays** settings.
5. Click **Save** — settings are persisted between sessions automatically.

---

## Features

### Settings

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
│   ├── main.py                      # Entry point
│   ├── theme/
│   │   ├── colors.py                # Colour constants (single source of truth)
│   │   ├── styles.qss               # Master QSS stylesheet
│   │   └── theme_manager.py         # Singleton — loads fonts + QSS
│   ├── ui/
│   │   ├── main_window.py           # Frameless application shell
│   │   ├── sidebar.py               # Animated navigation sidebar
│   │   ├── titlebar.py              # Custom drag-able title bar
│   │   ├── statusbar.py             # Bottom status strip
│   │   ├── pages/                   # Page modules (General, Overlays, …)
│   │   ├── widgets/                 # Reusable themed widget primitives
│   │   ├── cards/                   # SettingsCard container
│   │   └── overlays/                # BaseOverlayWindow + subclasses
│   ├── models/
│   │   └── settings_model.py        # Typed dataclass settings model
│   ├── services/
│   │   ├── settings_service.py      # QSettings persistence (native registry)
│   │   └── mock_data_provider.py    # Simulated real-time combat data
│   └── utils/
│       ├── platform_utils.py        # Win32 click-through + AUMID helpers
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
| **Theme** | `ThemeManager` singleton loads `styles.qss` and Orbitron from `assets/fonts/`. No hardcoded colours in widgets — every colour references `theme/colors.py`. |
| **Settings** | `SettingsService` wraps native `QSettings("GravityNexus","GravityNexus")`. Typed `AppSettings` dataclass is the in-memory model; `load()` / `save()` sync them. |
| **Overlays** | `BaseOverlayWindow` — frameless, translucent, always-on-top. Click-through uses `WS_EX_TRANSPARENT` via ctypes (Windows only); silent no-op elsewhere. |
| **Mock data** | `MockDataProvider` fires `data_updated` signals every 2 s to drive `OverlayPreviewPanel` with realistic combat data. |
| **Nuitka** | `app/main.py` adds `app/` to `sys.path` at runtime. `build_nuitka.py` bundles `assets/` and `theme/styles.qss` as data files next to the executable. |
