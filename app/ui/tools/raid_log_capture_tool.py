"""Raid Log Capture tool widget."""
from __future__ import annotations

from typing import Optional, cast

from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.registry import registry
from services.matchers.raid_log_matcher import RaidLogMatcher
from services.protocols import ILogParserService, ISettingsService
from theme.spec import ColorRole, FontSize
from ui.cards.tool_card import ToolCard
from ui.tools.tool_helpers import copy_row, setting_row
from ui.widgets.themed_label import ThemedLabel


class RaidLogCaptureTool(QWidget):
    """Raid Log Capture tool — configures and presents the raid log capture card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._svc = registry.get(ISettingsService)
        self._parser_svc = registry.get(ILogParserService)
        self._raid_matcher: Optional[RaidLogMatcher] = cast(
            Optional[RaidLogMatcher],
            next((m for m in self._parser_svc.builtin_matchers if isinstance(m, RaidLogMatcher)), None),
        )

        saved = self._svc.settings.parsing.enabled_matchers.get(
            "raid_log",
            self._raid_matcher.ENABLED_BY_DEFAULT if self._raid_matcher else True,
        )
        quick_saved = self._svc.settings.parsing.quick_raid_logs
        if self._raid_matcher is not None:
            self._raid_matcher.quick_raid_logs_enabled = quick_saved

        self._card = ToolCard(
            "Raid Log Capture",
            "Captures raid log from /who and submits attendance to discord.",
            enabled=saved,
        )
        self._card.enabled_changed.connect(self._on_enabled_changed)

        self._build_overview()
        self._build_instructions()
        self._build_settings(quick_saved)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._card)

    @property
    def card(self) -> ToolCard:
        return self._card

    def _build_overview(self) -> None:
        self._card.add_overview_widget(ThemedLabel(
            "Captures a raid log using /who in game and displays a pop up window to submit the raid logs to discord. "
            "You must select which raid to submit the logs to from the dropdown. Only unsubmitted raids will be shown.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        ))

    def _build_instructions(self) -> None:
        self._card.add_instructions_widget(ThemedLabel(
            "1. To begin capturing a raid log type the following into chat:",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(copy_row("", "/t nexusraidlog"))
        self._card.add_instructions_widget(ThemedLabel(
            "2. Then take a raid log using:",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(copy_row("", "/who"))
        self._card.add_instructions_widget(ThemedLabel(
            "Tip: Combine these into a social for easy use.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        ))
        self._card.add_instructions_widget(ThemedLabel(
            "If you have Quick Raid Logs enabled in settings, you can also capture a raid log by doing two "
            "/who commands within 5 seconds.",
            color_role=ColorRole.TEXT_PRIMARY,
            word_wrap=True,
        ))

    def _build_settings(self, quick_saved: bool) -> None:
        settings_layout = self._card.add_settings_tab()
        quick_row, self._quick_toggle = setting_row(
            "Quick Raid Logs",
            "When enabled, doing two /who commands within 5 seconds "
            "will capture a raid log and bring up the submission window",
            checked=quick_saved,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, quick_row)
        self._quick_toggle.toggled.connect(self._on_quick_raid_logs_toggled)

    def _on_enabled_changed(self, enabled: bool) -> None:
        self._svc.settings.parsing.enabled_matchers["raid_log"] = enabled
        if self._raid_matcher is not None:
            self._raid_matcher.set_enabled(enabled)
        self._svc.save()

    def _on_quick_raid_logs_toggled(self, enabled: bool) -> None:
        self._svc.settings.parsing.quick_raid_logs = enabled
        if self._raid_matcher is not None:
            self._raid_matcher.quick_raid_logs_enabled = enabled
        self._svc.save()
