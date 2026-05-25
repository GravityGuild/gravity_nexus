"""Raid Tools page — Raid Log Detector configuration and in-game instructions."""
from __future__ import annotations

from typing import Optional, cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget

from core.registry import registry
from services.matchers.raid_log_matcher import RaidLogMatcher
from services.protocols import ILogParserService, ISettingsService
from theme.spec import ColorRole, FontRole, FontSize
from ui.cards.tool_card import ToolCard
from ui.pages.pages import _make_page_scroll, _page_header
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.toggle_switch import ToggleSwitch


def _setting_row(label: str, description: str, checked: bool) -> tuple[QWidget, ToggleSwitch]:
    """A labeled setting row with a toggle on the right."""
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 4, 0, 4)
    hl.setSpacing(12)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    text_col.addWidget(ThemedLabel(label, color_role=ColorRole.TEXT_PRIMARY))
    if description:
        desc = ThemedLabel(
            description,
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        text_col.addWidget(desc)
    hl.addLayout(text_col, 1)

    toggle = ToggleSwitch(checked=checked)
    hl.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
    return row, toggle


def _copy_row(prefix: str, command: str) -> QWidget:
    """A labelled command string with a clipboard copy button on the right."""
    w = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(10)
    hl.addWidget(ThemedLabel(
        f"{prefix}  {command}" if prefix else command,
        font_size=FontSize.SMALL,
        color_role=ColorRole.TEXT_SECONDARY,
        font_role=FontRole.MONO,
        word_wrap=False,
    ))
    hl.addStretch()
    copy_btn = ThemedButton("Copy", ThemedButton.VARIANT_GHOST)

    def _on_copy() -> None:
        QApplication.clipboard().setText(command)
        copy_btn.setText("✓ Copied")
        QTimer.singleShot(1_500, lambda: copy_btn.setText("Copy"))

    copy_btn.clicked.connect(_on_copy)
    hl.addWidget(copy_btn)
    return w


class RaidToolsPage(QWidget):
    """Configuration and instructions for the Raid Log Detector."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._parser_svc = registry.get(ILogParserService)
        self._raid_matcher: Optional[RaidLogMatcher] = cast(
            Optional[RaidLogMatcher],
            next((m for m in self._parser_svc.builtin_matchers if isinstance(m, RaidLogMatcher)), None),
        )

        scroll, vl = _make_page_scroll()
        _page_header(vl, "Raid Tools", "Tools and utilities to help manage raids.")

        saved = self._svc.settings.parsing.enabled_matchers.get(
            "raid_log",
            self._raid_matcher.ENABLED_BY_DEFAULT if self._raid_matcher else True,
        )
        quick_saved = self._svc.settings.parsing.quick_raid_logs
        if self._raid_matcher is not None:
            self._raid_matcher.quick_raid_logs_enabled = quick_saved

        # ── Card: Raid Log Detector ───────────────────────────────────────────
        detector_card = ToolCard(
            "Raid Log Capture",
            "Captures raid log from /who and submits attendance to discord.",
            enabled=saved,
        )
        vl.addWidget(detector_card)
        detector_card.enabled_changed.connect(self._on_detector_toggled)

        # Overview tab
        detector_card.add_overview_widget(ThemedLabel(
            "Captures a raid log using /who in game and displays a pop up window to submit the raid logs to discord. "
            "You must select which raid to submit the logs to from the dropdown. Only unsubmitted raids will be shown.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        ))

        # Instructions tab
        detector_card.add_instructions_widget(ThemedLabel(
            "1. To begin capturing a raid log type the following into chat:",
            color_role=ColorRole.TEXT_PRIMARY,
        ))
        detector_card.add_instructions_widget(_copy_row("", "/t nexusraidlog"))
        detector_card.add_instructions_widget(ThemedLabel(
            "2. Then take a raid log using:",
            color_role=ColorRole.TEXT_PRIMARY,
        ))
        detector_card.add_instructions_widget(_copy_row("", "/who"))
        detector_card.add_instructions_widget(ThemedLabel(
            "Tip: Combine these into a social for easy use.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        ))
        detector_card.add_instructions_widget(ThemedLabel(
            "If you have Quick Raid Logs enabled in settings, you can also capture a raid log by doing two "
            "/who commands within 5 seconds.",
            color_role=ColorRole.TEXT_PRIMARY,
        ))

        # Settings tab
        settings_layout = detector_card.add_settings_tab()
        quick_row, self._quick_toggle = _setting_row(
            "Quick Raid Logs",
            "When enabled, doing two /who commands within 5 seconds "
            "will capture a raid log and bring up the submission window",
            checked=quick_saved,
        )
        settings_layout.insertWidget(settings_layout.count() - 1, quick_row)
        self._quick_toggle.toggled.connect(self._on_quick_raid_logs_toggled)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_detector_toggled(self, enabled: bool) -> None:
        self._svc.settings.parsing.enabled_matchers["raid_log"] = enabled
        if self._raid_matcher is not None:
            self._raid_matcher.set_enabled(enabled)
        self._svc.save()

    def _on_quick_raid_logs_toggled(self, enabled: bool) -> None:
        self._svc.settings.parsing.quick_raid_logs = enabled
        if self._raid_matcher is not None:
            self._raid_matcher.quick_raid_logs_enabled = enabled
        self._svc.save()
