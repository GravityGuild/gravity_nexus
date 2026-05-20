#!/usr/bin/env python3
"""Nuitka build script for Gravity Nexus.

Produces a standalone Windows executable in dist/gravity_nexus/.

Usage::

    python build_nuitka.py

Requirements: nuitka installed in the active Python environment.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
DIST_DIR = ROOT / "dist"
ENTRY_POINT = APP_DIR / "main.py"

ICON_ICO = APP_DIR / "assets" / "icons" / "full_logo.ico"


def build() -> int:
    print("Building Gravity Nexus …\n")

    if not ICON_ICO.exists():
        print(f"  ✗ Icon not found: {ICON_ICO}")
        raise SystemExit(1)
    print(f"  ✓ Using icon: {ICON_ICO.name}")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        # Output
        f"--output-dir={DIST_DIR}",
        "--standalone",
        "--onefile",
        # Windows-specific — native .ico required by Nuitka
        "--windows-console-mode=disable",
        "--windows-product-name=Gravity Nexus",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "--windows-file-description=EverQuest Overlay Parser",
        f"--windows-icon-from-ico={ICON_ICO}",
        # PySide6 plugin
        "--enable-plugin=pyside6",
        # Bundle assets and stylesheet
        f"--include-data-dir={APP_DIR / 'assets'}=assets",
        f"--include-data-files={APP_DIR / 'theme' / 'styles.qss'}=theme/styles.qss",
        # Follow all imports
        "--follow-imports",
        # Optimisation
        "--python-flag=no_site",
        # Entry point
        str(ENTRY_POINT),
    ]

    print("Command:", " ".join(cmd))
    print()
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(build())

