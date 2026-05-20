#!/usr/bin/env python3
"""Download required font assets for Gravity Nexus.

Run once before first launch::

    python scripts/download_fonts.py

Fonts are saved to app/assets/fonts/ and loaded by ThemeManager at startup.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "app" / "assets" / "fonts"

# Google Fonts CDN — Orbitron variable-weight TTF
FONTS: dict[str, str] = {
    "Orbitron-Variable.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"
    ),
}


def download_fonts() -> int:
    """Download all required fonts. Returns 0 on success, 1 on any failure."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0

    for filename, url in FONTS.items():
        dest = FONTS_DIR / filename
        if dest.exists():
            print(f"  ✓ {filename} already present — skipping")
            continue
        print(f"  ↓ Downloading {filename} …", end="", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  done ({dest.stat().st_size // 1024} KB)")
        except Exception as exc:  # noqa: BLE001
            print(f"\n  ✗ Failed: {exc}")
            errors += 1

    if errors == 0:
        print("\nAll fonts ready. Run the app with:  python app/main.py")
    return errors


if __name__ == "__main__":
    sys.exit(download_fonts())

