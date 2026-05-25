"""GravityBotPage — WebSocket options for Gravity Bot integration."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.protocols import ISettingsService
from theme.spec import ColorRole, FontRole, FontSize
from ui.cards.settings_card import SettingsCard
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.toggle_switch import ToggleSwitch


class GravityBotPage(QWidget):
    """Settings page for configuring Gravity Bot options."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._build_ui()
        self._load_values()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("PageWrapper")
        vl = QVBoxLayout(container)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(16)

        # Page header
        title = ThemedLabel(
            "Gravity Bot",
            font_size=FontSize.XL,
            color_role=ColorRole.TEXT_PRIMARY,
            font_role=FontRole.DISPLAY,
        )
        title.setObjectName("PageTitle")
        vl.addWidget(title)

        sub = ThemedLabel(
            "WebSocket and startup options for the Gravity Bot integration.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        sub.setObjectName("PageSubtitle")
        vl.addWidget(sub)
        vl.addSpacing(4)

        # ── Card: Options ─────────────────────────────────────────────────────
        opts_card = SettingsCard("Options", "WebSocket and startup behaviour.")
        vl.addWidget(opts_card)

        ws_row = QHBoxLayout()
        ws_lbl = ThemedLabel("Enable WebSocket")
        ws_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._ws_toggle = ToggleSwitch(checked=True)
        ws_row.addWidget(ws_lbl)
        ws_row.addWidget(self._ws_toggle)
        opts_card.add_layout(ws_row)

        auto_row = QHBoxLayout()
        auto_lbl = ThemedLabel("Auto-connect on startup")
        auto_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._auto_toggle = ToggleSwitch(checked=False)
        auto_row.addWidget(auto_lbl)
        auto_row.addWidget(self._auto_toggle)
        opts_card.add_layout(auto_row)

        # ── Save button ───────────────────────────────────────────────────────
        save_btn = ThemedButton("Save Settings", ThemedButton.VARIANT_SECONDARY)
        save_btn.clicked.connect(self._save)
        vl.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        vl.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Data binding ───────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        gb = self._svc.settings.gravity_bot
        self._ws_toggle.set_checked(gb.ws_enabled, animated=False)
        self._auto_toggle.set_checked(gb.auto_connect, animated=False)

    def _save(self) -> None:
        gb = self._svc.settings.gravity_bot
        gb.ws_enabled = self._ws_toggle.is_checked()
        gb.auto_connect = self._auto_toggle.is_checked()
        self._svc.save()
