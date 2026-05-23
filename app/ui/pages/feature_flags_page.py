"""Feature Flags settings page — toggle in-development features on/off."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from core.registry import registry
from feature_flags import FEATURE_REGISTRY
from services.protocols import ISettingsService
from theme.spec import ColorRole, FontSize
from ui.cards.settings_card import SettingsCard
from ui.pages.pages import _make_page_scroll, _page_header
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.toggle_switch import ToggleSwitch


def _flag_row(label: str, description: str, checked: bool) -> tuple[QVBoxLayout, ToggleSwitch]:
    """Return a two-line flag row (name + description) with a toggle on the right."""
    vl = QVBoxLayout()
    vl.setSpacing(2)

    hl = QHBoxLayout()
    hl.setSpacing(12)

    name_lbl = QLabel(label)
    name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    toggle = ToggleSwitch(checked=checked)

    hl.addWidget(name_lbl)
    hl.addWidget(toggle)
    vl.addLayout(hl)

    if description:
        desc_lbl = QLabel(description)
        desc_lbl.setProperty("secondary", "true")
        desc_lbl.setWordWrap(True)
        desc_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        vl.addWidget(desc_lbl)

    return vl, toggle


class FeatureFlagsPage(QWidget):
    """Settings page for toggling in-development feature flags."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)

        scroll, vl = _make_page_scroll()
        _page_header(
            vl,
            "Feature Flags",
            "Enable or disable features currently in development.",
        )

        flag_card = SettingsCard(
            "In Development",
            "These features may be incomplete or unstable.",
        )

        if FEATURE_REGISTRY:
            for flag in FEATURE_REGISTRY:
                current = bool(self._svc.settings.feature_flags.flags.get(flag.key, flag.default))
                row, toggle = _flag_row(flag.label, flag.description, current)
                toggle.toggled.connect(
                    lambda enabled, key=flag.key: self._on_toggled(key, enabled)
                )
                flag_card.add_layout(row)
        else:
            empty_lbl = ThemedLabel(
                "No feature flags are registered. Add entries to app/feature_flags.py.",
                font_size=FontSize.SMALL,
                color_role=ColorRole.TEXT_SECONDARY,
                word_wrap=True,
            )
            flag_card.add_widget(empty_lbl)

        vl.addWidget(flag_card)
        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_toggled(self, key: str, enabled: bool) -> None:
        self._svc.settings.feature_flags.flags[key] = enabled
        self._svc.save()
