"""Overlays page — overlay configuration with live preview panel."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.protocols import ISettingsService
from services.mock_data_provider import MockDataProvider
from theme.colors import ERROR, SUCCESS
from ui.cards.settings_card import SettingsCard
from ui.widgets.icon_label import AppIcon, icon_pixmap, inline_icon_html
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import NoScrollSlider
from ui.widgets.toggle_switch import ToggleSwitch


class OverlaysPage(QWidget):
    """Overlay configuration and live preview page."""

    #: Emitted when the user toggles positioning mode.
    #: ``True`` = enter positioning mode, ``False`` = exit & save.
    position_overlays_requested = Signal(bool)

    #: Emitted when the user cancels positioning without saving.
    cancel_position_overlays_requested = Signal()

    #: Emitted in real-time as the opacity slider moves (value 0.0 – 1.0).
    opacity_changed = Signal(float)


    def __init__(
        self,
        mock_provider: MockDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._position_overlay_icon: QIcon = QIcon(
            icon_pixmap(
                AppIcon.VECTOR_ARRANGE_ABOVE,
                size=ThemedButton.ICON_SIZE,
            )
        )

        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._provider = mock_provider
        self._positioning_active = False
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

        # ── Position Overlays button ──────────────────────────────────────────
        _check_icon = inline_icon_html(AppIcon.CHECK_BOLD, size=13, color=SUCCESS)
        position_card = SettingsCard(
            "Overlay Positioning",
            f"Show all overlay windows as draggable placeholders so you can arrange them on screen."
            f" Click {_check_icon} Save Positions &nbsp;when you are done."
        )

        vl.addWidget(position_card)

        pos_btn_row = QHBoxLayout()
        self._position_btn = ThemedButton("Position Overlays", ThemedButton.VARIANT_SECONDARY)
        self._position_btn.setIcon(self._position_overlay_icon)
        self._position_btn.setIconSize(QSize(ThemedButton.ICON_SIZE, ThemedButton.ICON_SIZE))
        self._position_btn.clicked.connect(self._toggle_positioning)

        self._cancel_position_btn = ThemedButton("Cancel", ThemedButton.VARIANT_GHOST)
        self._cancel_position_btn.setIcon(QIcon(icon_pixmap(AppIcon.CLOSE, size=ThemedButton.ICON_SIZE, color=ERROR)))
        self._cancel_position_btn.clicked.connect(self._cancel_positioning)
        self._cancel_position_btn.setVisible(False)

        pos_btn_row.addWidget(self._position_btn)
        pos_btn_row.addWidget(self._cancel_position_btn)
        pos_btn_row.addStretch()
        position_card.add_layout(pos_btn_row)

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
        self._opacity_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(20, 100)
        self._opacity_slider.setValue(85)
        self._opacity_slider.setFixedHeight(20)
        self._opacity_label = QLabel("85%")
        self._opacity_label.setProperty("accent", "cyan")
        self._opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        opacity_card.add_layout(opacity_row)

        vl.addStretch()
        scroll.setWidget(settings_widget)
        outer.addWidget(scroll)

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

    @staticmethod
    def _row(label: str, widget: QWidget) -> QHBoxLayout:
        hl = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hl.addWidget(lbl)
        hl.addWidget(widget)
        return hl

    def _on_opacity_slider_changed(self, value: int) -> None:
        """Update the label and emit the live opacity signal."""
        self._opacity_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

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

    def _toggle_positioning(self) -> None:
        """Enter or exit overlay positioning mode."""
        self._positioning_active = not self._positioning_active
        if self._positioning_active:
            self._position_btn.setIcon(QIcon(icon_pixmap(AppIcon.CHECK_BOLD, size=ThemedButton.ICON_SIZE, color=SUCCESS)))
            self._position_btn.setIconSize(QSize(ThemedButton.ICON_SIZE, ThemedButton.ICON_SIZE))
            self._position_btn.setText("Save Positions")
            self._position_btn.setProperty("variant", ThemedButton.VARIANT_PRIMARY)
            self._cancel_position_btn.setVisible(True)
        else:
            self._position_btn.setIcon(self._position_overlay_icon)
            self._position_btn.setIconSize(QSize(ThemedButton.ICON_SIZE, ThemedButton.ICON_SIZE))
            self._position_btn.setText("Position Overlays")
            self._position_btn.setProperty("variant", ThemedButton.VARIANT_SECONDARY)
            self._cancel_position_btn.setVisible(False)
        # Re-polish so the style sheet picks up the new variant property
        self._position_btn.style().unpolish(self._position_btn)
        self._position_btn.style().polish(self._position_btn)
        self.position_overlays_requested.emit(self._positioning_active)

    def _cancel_positioning(self) -> None:
        """Discard new positions and exit positioning mode."""
        self._positioning_active = False
        self._position_btn.setIcon(self._position_overlay_icon)
        self._position_btn.setIconSize(QSize(ThemedButton.ICON_SIZE, ThemedButton.ICON_SIZE))
        self._position_btn.setText("Position Overlays")
        self._position_btn.setProperty("variant", ThemedButton.VARIANT_SECONDARY)
        self._position_btn.style().unpolish(self._position_btn)
        self._position_btn.style().polish(self._position_btn)
        self._cancel_position_btn.setVisible(False)
        self.cancel_position_overlays_requested.emit()

    def reset_positioning_button(self) -> None:
        """Called by MainWindow when positioning mode ends externally (e.g. overlays closed)."""
        self._positioning_active = False
        self._position_btn.setIcon(self._position_overlay_icon)
        self._position_btn.setIconSize(QSize(ThemedButton.ICON_SIZE, ThemedButton.ICON_SIZE))
        self._position_btn.setText("Position Overlays")
        self._position_btn.setProperty("variant", ThemedButton.VARIANT_SECONDARY)
        self._position_btn.style().unpolish(self._position_btn)
        self._position_btn.style().polish(self._position_btn)
        self._cancel_position_btn.setVisible(False)

