"""Theme package — semantic tokens, spec, builder, and manager.

Typical imports::

    from theme import ThemeManager, ColorRole, FontRole, FontSize
    from theme import DARK_NAVY, FONT_SIZE_OPTIONS
"""
from theme.spec import (
    ColorRole,
    FontRole,
    FontSize,
    FONT_SIZE_BASE_PX,
    ThemeSpec,
    DARK_NAVY,
)
from theme.theme_manager import (
    ThemeManager,
    FONT_SIZE_OPTIONS,
    _DEFAULT_FONT_PT as DEFAULT_FONT_PT,
)

__all__ = [
    "ColorRole",
    "FontRole",
    "FontSize",
    "FONT_SIZE_BASE_PX",
    "ThemeSpec",
    "DARK_NAVY",
    "ThemeManager",
    "FONT_SIZE_OPTIONS",
    "DEFAULT_FONT_PT",
]
