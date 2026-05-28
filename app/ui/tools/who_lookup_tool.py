"""Who Character Lookup tool widget."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.registry import registry
from services.protocols import ISettingsService
from theme.spec import ColorRole, FontSize
from ui.cards.tool_card import ToolCard
from ui.tools.tool_helpers import setting_row
from ui.widgets import HLine
from ui.widgets.themed_label import ThemedLabel


class WhoLookupTool(QWidget):
    """Who Character Lookup tool — configures character info display on /who."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._svc = registry.get(ISettingsService)

        saved_enabled = self._svc.settings.who_lookup.enabled
        saved_own = self._svc.settings.who_lookup.show_own_character

        self._card = ToolCard(
            "Who Character Lookup",
            "Use /who character or /whot in game to lookup guild member info.",
            enabled=saved_enabled,
        )
        self._card.enabled_changed.connect(self._on_enabled_changed)

        self._build_overview()
        self._build_instructions()
        self._build_settings(saved_own)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._card)

    @property
    def card(self) -> ToolCard:
        return self._card

    def _build_overview(self) -> None:
        self._card.add_overview_widget(ThemedLabel(
            "Displays character data (DKP, alts, recent items) in an overlay when doing /who character in game.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        ))

    def _build_instructions(self) -> None:
        self._card.add_instructions_widget(ThemedLabel(
            "Character overlay will display when /who returns a single result. The targeted character must be a guild tagged character or bot.",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(HLine())

        self._card.add_instructions_widget(ThemedLabel(
            "Who with character name:",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(ThemedLabel(
            "/who heelur",
            color_role=ColorRole.TEXT_SECONDARY,
            font_size=FontSize.SMALL,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(ThemedLabel(
            "Target character in game and use:",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(ThemedLabel(
            "/whot",
            color_role=ColorRole.TEXT_SECONDARY,
            font_size=FontSize.SMALL,
            word_wrap=True,
        ))

    def _build_settings(self, show_own: bool) -> None:
        s = self._svc.settings.who_lookup
        settings_layout = self._card.add_settings_tab()

        own_row, self._own_toggle = setting_row(
            "Show my own character",
            "When enabled, the overlay also appears when you /who yourself",
            checked=show_own,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, own_row)
        self._own_toggle.toggled.connect(self._on_show_own_toggled)

        current_row, self._current_dkp_toggle = setting_row(
            "Show current DKP",
            "Display current DKP balance on the overlay",
            checked=s.show_current_dkp,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, current_row)
        self._current_dkp_toggle.toggled.connect(
            lambda v: self._save_flag("show_current_dkp", v)
        )

        earned_row, self._earned_dkp_toggle = setting_row(
            "Show earned DKP",
            "Display total earned DKP on the overlay",
            checked=s.show_earned_dkp,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, earned_row)
        self._earned_dkp_toggle.toggled.connect(
            lambda v: self._save_flag("show_earned_dkp", v)
        )

        spent_row, self._spent_dkp_toggle = setting_row(
            "Show spent DKP",
            "Display total spent DKP on the overlay",
            checked=s.show_spent_dkp,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, spent_row)
        self._spent_dkp_toggle.toggled.connect(
            lambda v: self._save_flag("show_spent_dkp", v)
        )

        items_row, self._recent_items_toggle = setting_row(
            "Show recent items",
            "Display recent items on the overlay",
            checked=s.show_recent_items,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, items_row)
        self._recent_items_toggle.toggled.connect(
            lambda v: self._save_flag("show_recent_items", v)
        )

    def _on_enabled_changed(self, enabled: bool) -> None:
        self._svc.settings.who_lookup.enabled = enabled
        self._svc.save()

    def _on_show_own_toggled(self, enabled: bool) -> None:
        self._svc.settings.who_lookup.show_own_character = enabled
        self._svc.save()

    def _save_flag(self, attr: str, value: bool) -> None:
        setattr(self._svc.settings.who_lookup, attr, value)
        self._svc.save()
