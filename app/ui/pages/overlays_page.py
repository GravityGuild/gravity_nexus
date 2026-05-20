"""Overlays page — overlay configuration with live preview panel."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from services.mock_data_provider import MockDataProvider
from services.settings_service import SettingsService
from ui.cards.settings_card import SettingsCard
from ui.widgets.overlay_preview import OverlayPreviewPanel
from ui.widgets.status_widgets import SectionHeader
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import ThemedComboBox
from ui.widgets.toggle_switch import ToggleSwitch


class OverlaysPage(QWidget):
    """Overlay configuration and live preview page."""

    def __init__(
        self,
        mock_provider: MockDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = SettingsService.instance()
        self._provider = mock_provider
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        # Two-column layout: settings left, preview right
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left: scrollable settings ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(380)

        settings_widget = QWidget()
        settings_widget.setObjectName("PageWrapper")
        vl = QVBoxLayout(settings_widget)
        vl.setContentsMargins(24, 20, 16, 20)
        vl.setSpacing(16)

        title = QLabel("Overlays")
        title.setObjectName("PageTitle")
        vl.addWidget(title)

        sub = QLabel("Configure in-game overlay windows and appearance.")
        sub.setObjectName("PageSubtitle")
        vl.addWidget(sub)
        vl.addSpacing(4)

        # ── Card: Global overlay settings ─────────────────────────────────────
        global_card = SettingsCard("Global Overlay Settings", "Applied to all overlay windows.")
        vl.addWidget(global_card)

        self._toggle_enabled = ToggleSwitch(checked=True)
        global_card.add_layout(self._row("Enable overlays", self._toggle_enabled))

        self._toggle_always_top = ToggleSwitch(checked=True)
        global_card.add_layout(self._row("Always on top", self._toggle_always_top))

        self._toggle_click_through = ToggleSwitch(checked=False)
        global_card.add_layout(self._row("Click-through mode (Windows)", self._toggle_click_through))

        # ── Card: Opacity ─────────────────────────────────────────────────────
        opacity_card = SettingsCard("Opacity", "Global overlay transparency.")
        vl.addWidget(opacity_card)

        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(20, 100)
        self._opacity_slider.setValue(85)
        self._opacity_slider.setFixedHeight(20)
        self._opacity_label = QLabel("85%")
        self._opacity_label.setFixedWidth(36)
        self._opacity_label.setProperty("accent", "cyan")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        opacity_card.add_layout(opacity_row)

        # ── Card: Scale ───────────────────────────────────────────────────────
        scale_card = SettingsCard("UI Scale", "Scale the overlay HUD elements.")
        vl.addWidget(scale_card)

        self._scale_combo = ThemedComboBox()
        for s in ["75%", "100%", "125%", "150%", "175%", "200%"]:
            self._scale_combo.addItem(s)
        self._scale_combo.setCurrentText("100%")
        scale_card.add_widget(self._scale_combo)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        save_btn = ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY)
        save_btn.clicked.connect(self._save)
        reset_btn = ThemedButton("Reset Defaults", ThemedButton.VARIANT_GHOST)
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        vl.addLayout(btn_row)

        vl.addStretch()
        scroll.setWidget(settings_widget)
        outer.addWidget(scroll)

        # ── Right: overlay preview ────────────────────────────────────────────
        preview_container = QWidget()
        preview_container.setObjectName("PageWrapper")
        preview_vl = QVBoxLayout(preview_container)
        preview_vl.setContentsMargins(8, 20, 24, 20)
        preview_vl.setSpacing(10)

        preview_title = QLabel("Live Preview")
        preview_title.setObjectName("PageTitle")
        preview_title.setStyleSheet("font-size: 14px;")
        preview_vl.addWidget(preview_title)

        preview_hint = QLabel("Simulated overlay — updates every 2 seconds.")
        preview_hint.setObjectName("PageSubtitle")
        preview_vl.addWidget(preview_hint)

        self._preview = OverlayPreviewPanel(self._provider)
        preview_vl.addWidget(self._preview)
        preview_vl.addStretch()
        outer.addWidget(preview_container)

    @staticmethod
    def _row(label: str, widget: QWidget) -> QHBoxLayout:
        hl = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hl.addWidget(lbl)
        hl.addWidget(widget)
        return hl

    def _load_values(self) -> None:
        ov = self._svc.settings.overlay
        self._toggle_enabled.set_checked(ov.enabled, animated=False)
        self._toggle_always_top.set_checked(ov.always_on_top, animated=False)
        self._toggle_click_through.set_checked(ov.click_through, animated=False)
        pct = int(ov.opacity * 100)
        self._opacity_slider.setValue(pct)
        self._opacity_label.setText(f"{pct}%")

    def _save(self) -> None:
        ov = self._svc.settings.overlay
        ov.enabled = self._toggle_enabled.is_checked()
        ov.always_on_top = self._toggle_always_top.is_checked()
        ov.click_through = self._toggle_click_through.is_checked()
        ov.opacity = self._opacity_slider.value() / 100.0
        self._svc.save()

    def _reset(self) -> None:
        from models.settings_model import OverlaySettings
        self._svc.settings.overlay = OverlaySettings()
        self._load_values()

