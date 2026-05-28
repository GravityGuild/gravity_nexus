"""ThemedLabel — a QLabel that expresses colour, font-family, and font-size
via semantic theme tokens rather than inline style strings.

Usage::

    from theme.spec import ColorRole, FontRole, FontSize
    from ui.widgets.themed_label import ThemedLabel

    # Static declaration
    lbl = ThemedLabel("Status:", font_size=FontSize.SMALL, color_role=ColorRole.TEXT_SECONDARY)

    # Runtime state update (triggers QSS repolish automatically)
    lbl.set_color_role(ColorRole.SUCCESS)
    lbl.set_font_size(FontSize.LARGE)
    lbl.set_font_role(FontRole.DISPLAY)

No ``setStyleSheet`` call is made at any point — all styling is driven by Qt
property selectors in the generated application QSS.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QLabel, QWidget

from theme.spec import ColorRole, FontRole, FontSize


class ThemedLabel(QLabel):
    """QLabel whose colour, font size, and font family are governed by the
    global theme via Qt property selectors.

    Parameters
    ----------
    text:
        Initial label text (may be empty).
    font_size:
        Semantic size token — resolved to a scaled px value by the active QSS.
        Defaults to ``FontSize.MEDIUM`` (the body / base size).
    color_role:
        Semantic colour token.  Defaults to ``ColorRole.TEXT_PRIMARY``.
    font_role:
        Semantic font-family token.  Defaults to ``FontRole.BODY``; set to
        ``FontRole.DISPLAY`` for Orbitron or ``FontRole.MONO`` for monospace.
        When ``FontRole.BODY`` the ``fontRole`` property is *not* set so the
        global ``QWidget`` body-font declaration takes precedence naturally.
    word_wrap:
        Whether to enable word wrapping (convenience pass-through).
    parent:
        Optional parent widget.
    """

    def __init__(
        self,
        text: str = "",
        font_size: FontSize = FontSize.MEDIUM,
        color_role: ColorRole = ColorRole.TEXT_PRIMARY,
        font_role: FontRole = FontRole.BODY,
        word_wrap: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self.setWordWrap(word_wrap)
        # Set properties without triggering a repolish on each one
        self.setProperty("fontScale", font_size.value)
        self.setProperty("colorRole", color_role.value)
        if font_role != FontRole.BODY:
            self.setProperty("fontRole", font_role.value)
        self._repolish()

    # ── State-update helpers ────────────────────────────────────────────────────

    def set_color_role(self, role: ColorRole) -> None:
        """Change the label colour to *role* and repolish immediately.

        Use this for state-driven colour changes (e.g. success / error feedback)
        instead of calling ``setStyleSheet``.
        """
        self.setProperty("colorRole", role.value)
        self._repolish()

    def set_font_size(self, size: FontSize) -> None:
        """Change the font size to *size* and repolish immediately."""
        self.setProperty("fontScale", size.value)
        self._repolish()

    def set_font_role(self, role: FontRole) -> None:
        """Change the font family to *role* and repolish immediately."""
        if role == FontRole.BODY:
            self.setProperty("fontRole", None)
        else:
            self.setProperty("fontRole", role.value)
        self._repolish()

    # ── Private ────────────────────────────────────────────────────────────────

    def _repolish(self) -> None:
        """Ask Qt's style engine to re-evaluate this widget's style rules."""
        style = self.style()
        if style:
            style.unpolish(self)
            style.polish(self)

