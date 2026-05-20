"""Color palette — single source of truth.

Import these constants everywhere instead of raw hex strings.
"""
from __future__ import annotations

# ── Backgrounds ────────────────────────────────────────────────────────────────
NAVY_BG: str = "#081120"
DEEP_BLUE: str = "#0B1730"
CARD_BG: str = "#112240"
CARD_ALT: str = "#162B4D"

# ── Accents ───────────────────────────────────────────────────────────────────
ACCENT_GOLD: str = "#D8B36A"
ACCENT_CYAN: str = "#57C7FF"

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY: str = "#E6EDF7"
TEXT_SECONDARY: str = "#93A4C3"

# ── State ─────────────────────────────────────────────────────────────────────
SUCCESS: str = "#78E08F"
WARNING: str = "#F6C177"
ERROR: str = "#FF6B6B"

# ── RGBA strings (used in QSS templates and QPainter) ─────────────────────────
CARD_BG_RGBA: str = "rgba(17, 34, 64, 210)"
CARD_ALT_RGBA: str = "rgba(22, 43, 77, 210)"
NAVY_BG_RGBA: str = "rgba(8, 17, 32, 230)"
DEEP_BLUE_RGBA: str = "rgba(11, 23, 48, 245)"
SIDEBAR_BG: str = "rgba(8, 17, 32, 245)"

ACCENT_CYAN_DIM: str = "rgba(87, 199, 255, 40)"
ACCENT_CYAN_MED: str = "rgba(87, 199, 255, 110)"
ACCENT_CYAN_BRIGHT: str = "rgba(87, 199, 255, 200)"
ACCENT_GOLD_DIM: str = "rgba(216, 179, 106, 40)"
ACCENT_GOLD_MED: str = "rgba(216, 179, 106, 110)"

SUCCESS_RGBA: str = "rgba(120, 224, 143, 200)"
WARNING_RGBA: str = "rgba(246, 193, 119, 200)"
ERROR_RGBA: str = "rgba(255, 107, 107, 200)"

# ── RGB integer tuples (for QColor / QPainter use) ───────────────────────────
NAVY_BG_RGB: tuple[int, int, int] = (8, 17, 32)
DEEP_BLUE_RGB: tuple[int, int, int] = (11, 23, 48)
CARD_BG_RGB: tuple[int, int, int] = (17, 34, 64)
CARD_ALT_RGB: tuple[int, int, int] = (22, 43, 77)
ACCENT_GOLD_RGB: tuple[int, int, int] = (216, 179, 106)
ACCENT_CYAN_RGB: tuple[int, int, int] = (87, 199, 255)
TEXT_PRIMARY_RGB: tuple[int, int, int] = (230, 237, 247)
TEXT_SECONDARY_RGB: tuple[int, int, int] = (147, 164, 195)
SUCCESS_RGB: tuple[int, int, int] = (120, 224, 143)
WARNING_RGB: tuple[int, int, int] = (246, 193, 119)
ERROR_RGB: tuple[int, int, int] = (255, 107, 107)

