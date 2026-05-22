"""ThemeSpec — colour palette, font families, and semantic font-size tokens.

``ColorRole``, ``FontRole``, and ``FontSize`` are the vocabulary UI code uses to
express *intent*.  The QssBuilder translates intent into concrete pixel values
and hex strings via the active ThemeSpec.

No UI widget should ever import a raw hex string or a hard-coded pixel size.
Import these enums and use them instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ── Colour roles ───────────────────────────────────────────────────────────────

class ColorRole(str, Enum):
    """Semantic colour tokens.

    Widgets declare *what* a colour is for, not *what* it looks like.
    The active ThemeSpec maps each role to a concrete hex/rgba string.
    """

    TEXT_PRIMARY   = "text_primary"
    TEXT_SECONDARY = "text_secondary"
    TEXT_MUTED     = "text_muted"
    ACCENT_PRIMARY = "accent_primary"   # cyan
    ACCENT_ALT     = "accent_alt"       # gold
    SUCCESS        = "success"
    WARNING        = "warning"
    ERROR          = "error"


# ── Font roles ─────────────────────────────────────────────────────────────────

class FontRole(str, Enum):
    """Semantic font-family tokens."""

    BODY    = "body"     # default UI font (Segoe UI)
    DISPLAY = "display"  # branded / heading font (Orbitron)
    MONO    = "mono"     # monospace for live feeds / code (Consolas)


# ── Font size tokens ───────────────────────────────────────────────────────────

class FontSize(str, Enum):
    """Semantic font-size tokens.

    The underlying ``FONT_SIZE_BASE_PX`` mapping defines a base ``px`` value
    for each token at the 13 px reference scale (``QSS_BASE_PX``).
    ThemeManager scales every token proportionally when the user adjusts their
    base font-size preference.
    """

    TINY    = "tiny"     # 9 px at base scale
    SMALL   = "small"    # 11 px
    MEDIUM  = "medium"   # 13 px  (body / reference)
    LARGE   = "large"    # 15 px
    XL      = "xl"       # 18 px
    HEADING = "heading"  # 22 px  (page titles)


# Authored px values for each FontSize token at the 13-px reference scale.
# QssBuilder uses these together with the user's chosen base-pt to derive the
# actual px value that goes into the generated QSS.
FONT_SIZE_BASE_PX: dict[FontSize, int] = {
    FontSize.TINY:    9,
    FontSize.SMALL:   11,
    FontSize.MEDIUM:  13,
    FontSize.LARGE:   15,
    FontSize.XL:      18,
    FontSize.HEADING: 22,
}


# ── ThemeSpec ──────────────────────────────────────────────────────────────────

@dataclass
class ThemeSpec:
    """Immutable description of a visual theme.

    Parameters
    ----------
    name:    Human-readable display name shown in the Appearance settings.
    palette: Mapping of ``ColorRole`` → CSS colour string (hex or rgba(…)).
    fonts:   Mapping of ``FontRole``  → font-family name string.
    """

    name:    str
    palette: dict[ColorRole, str]
    fonts:   dict[FontRole, str]

    def color(self, role: ColorRole) -> str:
        """Return the colour string for *role*."""
        return self.palette[role]

    def font_family(self, role: FontRole) -> str:
        """Return the font-family name string for *role*."""
        return self.fonts[role]


# ── Built-in themes ────────────────────────────────────────────────────────────

#: Default dark theme — deep-space navy with cyan and gold accents.
DARK_NAVY = ThemeSpec(
    name="Dark Navy",
    palette={
        ColorRole.TEXT_PRIMARY:   "#E6EDF7",
        ColorRole.TEXT_SECONDARY: "#93A4C3",
        ColorRole.TEXT_MUTED:     "rgba(147, 164, 195, 160)",
        ColorRole.ACCENT_PRIMARY: "#57C7FF",
        ColorRole.ACCENT_ALT:     "#D8B36A",
        ColorRole.SUCCESS:        "#78E08F",
        ColorRole.WARNING:        "#F6C177",
        ColorRole.ERROR:          "#FF6B6B",
    },
    fonts={
        FontRole.BODY:    "Segoe UI",
        FontRole.DISPLAY: "Orbitron",
        FontRole.MONO:    "Consolas",
    },
)

