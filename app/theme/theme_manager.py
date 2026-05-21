"""ThemeManager — loads QSS, registers fonts, applies to the application.

Usage::

    ThemeManager.instance().apply(app)
    ThemeManager.instance().set_font_scale(app, base_pt=15)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)

# Paths relative to this file (reliable in both dev and Nuitka builds)
_THEME_DIR = Path(__file__).resolve().parent
_QSS_PATH = _THEME_DIR / "styles.qss"
_ASSETS_FONTS_DIR = _THEME_DIR.parent / "assets" / "fonts"

# Fonts to register with Qt — filename → family hint
_FONT_FILES: list[str] = [
    "Orbitron-Variable.ttf",
]


# Base font size the QSS was authored at (px).
# All font-size values in styles.qss are relative to this.
_QSS_BASE_PX: int = 13

# Font sizes exposed to the UI (pt).  Qt maps pt→px via screen DPI.
# 14 pt is the shipped "Normal" — all other sizes are spaced proportionally.
FONT_SIZE_OPTIONS: list[tuple[str, int]] = [
    ("Small (11 pt)",       11),
    ("Normal (14 pt)",      14),
    ("Large (16 pt)",       16),
    ("Extra Large (19 pt)", 19),
    ("Huge (23 pt)",        23),
]

_DEFAULT_FONT_PT: int = 14


class ThemeManager:
    """Centralised theme controller.

    Singleton — access via ``ThemeManager.instance()``.
    """

    _instance: Optional["ThemeManager"] = None

    def __init__(self) -> None:
        self._stylesheet: str = ""
        self._fonts_loaded: bool = False
        self._current_font_pt: int = _QSS_BASE_PX

    # ── Singleton ──────────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "ThemeManager":
        """Return the global ThemeManager, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────────

    def apply(self, app: QApplication, base_font_size_pt: int = _DEFAULT_FONT_PT) -> None:
        """Register fonts and apply the stylesheet to *app*.

        Parameters
        ----------
        app:
            The running QApplication instance.
        base_font_size_pt:
            Point size for the UI base font.  All QSS font-size values are
            scaled proportionally relative to the 13 px they were authored at.
        """
        self._register_fonts()
        self._load_stylesheet()
        self._apply_font_and_qss(app, base_font_size_pt)
        log.debug(
            "Theme applied — font %d pt, %d bytes of QSS",
            base_font_size_pt,
            len(self._stylesheet),
        )

    def set_font_scale(self, app: QApplication, base_font_size_pt: int) -> None:
        """Change the font scale at runtime and immediately re-apply the stylesheet.

        Call this from the Appearance page when the user changes the font size.
        The raw QSS is re-read from the cached string (no disk I/O) so it is fast.
        """
        self._apply_font_and_qss(app, base_font_size_pt)
        log.info("Font scale changed → %d pt", base_font_size_pt)

    def reload(self, app: QApplication) -> None:
        """Reload the QSS from disk and re-apply at the current font scale."""
        self._load_stylesheet()
        self._apply_font_and_qss(app, self._current_font_pt)
        log.info("Theme reloaded")

    @property
    def current_font_pt(self) -> int:
        """Currently active base font size in points."""
        return self._current_font_pt

    @property
    def stylesheet(self) -> str:
        """Return the raw (unscaled) loaded QSS string."""
        return self._stylesheet

    # ── Private helpers ────────────────────────────────────────────────────────

    def _apply_font_and_qss(self, app: QApplication, pt: int) -> None:
        """Scale QSS font sizes and set both the stylesheet and the app font."""
        self._current_font_pt = pt
        scaled_qss = self._scale_qss_fonts(self._stylesheet, pt)
        app.setStyleSheet(scaled_qss)
        app.setFont(QFont("Segoe UI", pt))

    def _scale_qss_fonts(self, qss: str, target_pt: int) -> str:
        """Return *qss* with every ``font-size: Npx`` scaled to *target_pt*.

        The scale factor is  target_pt / _QSS_BASE_PX  so all font sizes
        remain proportional to the originals in styles.qss.
        A minimum of 8 px is enforced to keep labels readable.
        """
        if target_pt == _DEFAULT_FONT_PT:
            # Fast path: pre-cache the scaled QSS at the shipped default so
            # startup and the most common case avoid regex work entirely.
            if not hasattr(self, "_default_scaled_qss"):
                self._default_scaled_qss = self._do_scale(qss, _DEFAULT_FONT_PT)
            return self._default_scaled_qss

        return self._do_scale(qss, target_pt)

    @staticmethod
    def _do_scale(qss: str, target_pt: int) -> str:
        """Apply the actual regex font-size and tagged min-height substitution.

        Values tagged with ``/* scaleable */`` in the QSS (e.g. interactive
        widget ``min-height`` values) are scaled proportionally alongside
        ``font-size`` rules so that buttons and inputs can always accommodate
        the chosen font size without clipping.
        """
        scale = target_pt / _QSS_BASE_PX

        def _replace_font(match: re.Match) -> str:
            original_px = int(match.group(1))
            scaled_px = max(8, round(original_px * scale))
            return f"font-size: {scaled_px}px"

        def _replace_min_height(match: re.Match) -> str:
            original_px = int(match.group(1))
            scaled_px = max(20, round(original_px * scale))
            return f"min-height: {scaled_px}px; /* scaleable */"

        qss = re.sub(r"font-size:\s*(\d+)px", _replace_font, qss)
        qss = re.sub(
            r"min-height:\s*(\d+)px;\s*/\*\s*scaleable\s*\*/",
            _replace_min_height,
            qss,
        )
        return qss

    def _register_fonts(self) -> None:
        """Register bundled fonts with Qt's font database."""
        if self._fonts_loaded:
            return

        for filename in _FONT_FILES:
            font_path = _ASSETS_FONTS_DIR / filename
            if font_path.exists():
                fid = QFontDatabase.addApplicationFont(str(font_path))
                if fid == -1:
                    log.warning("Failed to register font: %s", filename)
                else:
                    families = QFontDatabase.applicationFontFamilies(fid)
                    log.debug("Registered font %s → %s", filename, families)
            else:
                log.info(
                    "Font not found — run scripts/download_fonts.py: %s", font_path
                )

        self._fonts_loaded = True

    def _load_stylesheet(self) -> None:
        """Read styles.qss from disk into the internal cache."""
        if not _QSS_PATH.exists():
            log.error("QSS file missing: %s", _QSS_PATH)
            self._stylesheet = ""
            return
        self._stylesheet = _QSS_PATH.read_text(encoding="utf-8")
        # Invalidate the pre-scaled default cache so reload() picks up changes
        if hasattr(self, "_default_scaled_qss"):
            del self._default_scaled_qss

