"""ThemedButton — styled QPushButton with variant support.

Variants: "primary" | "secondary" | "danger" | "ghost"
Set via ``button.set_variant("primary")``.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QPushButton, QWidget


class ThemedButton(QPushButton):
    """A QPushButton with themed variant styling driven by QSS properties."""

    VARIANT_PRIMARY = "primary"
    VARIANT_SECONDARY = "secondary"
    VARIANT_DANGER = "danger"
    VARIANT_GHOST = "ghost"
    VARIANT_DEFAULT = ""

    def __init__(
        self,
        text: str = "",
        variant: str = VARIANT_DEFAULT,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        if variant:
            self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        """Apply a QSS variant to this button (triggers stylesheet re-polish)."""
        self.setProperty("variant", variant)
        self._repolish()

    def _repolish(self) -> None:
        style = self.style()
        if style:
            style.unpolish(self)
            style.polish(self)

