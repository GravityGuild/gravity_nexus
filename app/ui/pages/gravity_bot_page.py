"""GravityBotPage — connection settings for Gravity Bot integration."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.protocols import IGravityBotService, ISettingsService
from theme.spec import ColorRole, FontRole, FontSize
from ui.cards.settings_card import SettingsCard
from ui.widgets.status_widgets import StatusIndicator
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.themed_widgets import ThemedLineEdit
from ui.widgets.toggle_switch import ToggleSwitch


class GravityBotPage(QWidget):
    """Settings page for configuring and connecting to Gravity Bot."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._bot_svc = registry.get(IGravityBotService)
        self._build_ui()
        self._load_values()
        self._bot_svc.connected_changed.connect(self._on_connected_changed)

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
            "Connect to the Gravity guild bot for raid log submission "
            "and real-time notifications.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        sub.setObjectName("PageSubtitle")
        vl.addWidget(sub)
        vl.addSpacing(4)

        # ── Card: Connection ──────────────────────────────────────────────────
        conn_card = SettingsCard(
            "Connection",
            "Bot server address and authentication token.",
        )
        vl.addWidget(conn_card)

        # Bot URL
        url_row = QHBoxLayout()
        url_lbl = ThemedLabel("Bot URL:")
        url_lbl.setFixedWidth(96)
        self._url_edit = ThemedLineEdit("https://bot.gravityp99.com")
        url_row.addWidget(url_lbl)
        url_row.addWidget(self._url_edit)
        conn_card.add_layout(url_row)

        # Auth token (masked)
        token_row = QHBoxLayout()
        token_lbl = ThemedLabel("Auth Token:")
        token_lbl.setFixedWidth(96)
        self._token_edit = ThemedLineEdit("Paste your bot token here")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        token_row.addWidget(token_lbl)
        token_row.addWidget(self._token_edit)
        conn_card.add_layout(token_row)

        # Connection status indicator
        status_row = QHBoxLayout()
        self._conn_status = StatusIndicator("Disconnected", "offline")
        status_row.addWidget(self._conn_status)
        status_row.addStretch()
        conn_card.add_layout(status_row)

        # Connect / Disconnect buttons
        btn_row = QHBoxLayout()
        self._connect_btn = ThemedButton("Connect", ThemedButton.VARIANT_PRIMARY)
        self._disconnect_btn = ThemedButton("Disconnect", ThemedButton.VARIANT_DANGER)
        self._disconnect_btn.setEnabled(False)
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        btn_row.addWidget(self._connect_btn)
        btn_row.addWidget(self._disconnect_btn)
        btn_row.addStretch()
        conn_card.add_layout(btn_row)

        note = ThemedLabel(
            "Note: OAuth login is planned for a future release. "
            "Use a manual bot token for now.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        conn_card.add_widget(note)

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
        self._url_edit.setText(gb.bot_url)
        self._token_edit.setText(gb.auth_token)
        self._ws_toggle.set_checked(gb.ws_enabled, animated=False)
        self._auto_toggle.set_checked(gb.auto_connect, animated=False)
        self._on_connected_changed(self._bot_svc.is_connected)

    def _save(self) -> None:
        gb = self._svc.settings.gravity_bot
        gb.bot_url = self._url_edit.text().strip()
        gb.auth_token = self._token_edit.text().strip()
        gb.ws_enabled = self._ws_toggle.is_checked()
        gb.auto_connect = self._auto_toggle.is_checked()
        self._svc.save()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_connect(self) -> None:
        self._save()
        self._conn_status.set_status("connecting", "Connecting…")
        self._connect_btn.setEnabled(False)
        self._bot_svc.connect_bot()

    def _on_disconnect(self) -> None:
        self._bot_svc.disconnect_bot()

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_connected_changed(self, connected: bool) -> None:
        if connected:
            self._conn_status.set_status("online", "Connected")
            self._connect_btn.setEnabled(False)
            self._disconnect_btn.setEnabled(True)
        else:
            self._conn_status.set_status("offline", "Disconnected")
            self._connect_btn.setEnabled(True)
            self._disconnect_btn.setEnabled(False)
