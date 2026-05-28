"""WhoLookupOverlay — shows character info when /who returns a single guild member."""
from __future__ import annotations

import html
import json
import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from core.registry import registry
from services.protocols import IGravityBotService, ISettingsService
from theme.spec import ColorRole, FontSize
from ui.overlays.base_overlay_window import BaseOverlayWindow
from ui.widgets import HLine
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel

log = logging.getLogger(__name__)

_TIMEOUT_SECS = 30


class WhoLookupOverlay(BaseOverlayWindow):
    """Transient overlay showing character data after a /who match.

    Signals
    -------
    dismissed():
        Emitted when the overlay closes for any reason.
    """

    dismissed = Signal()

    def __init__(
        self,
        character_name: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__("Character Lookup", parent)
        self._character_name = character_name
        self._seconds_left = _TIMEOUT_SECS
        self._timer: Optional[QTimer] = None

        self._build_content()
        self._fetch_character()
        self._start_countdown()

        self.resize(400, 260)

    # ── Content construction ───────────────────────────────────────────────────

    def _build_content(self) -> None:
        # ── Loading / status label ─────────────────────────────────────────────
        self._status_lbl = ThemedLabel(
            f"Looking up {self._character_name}…",
            font_size=FontSize.MEDIUM,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._status_lbl)

        # ── Character info (hidden until populated) ────────────────────────────
        self._info_widget = QWidget()
        info_layout = QVBoxLayout(self._info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        self._info_widget.hide()
        self.content_layout.addWidget(self._info_widget)

        # Name + bot badge (inline)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.setContentsMargins(0, 0, 0, 0)
        self._name_lbl = ThemedLabel("", font_size=FontSize.XL, color_role=ColorRole.ACCENT_PRIMARY)
        name_row.addWidget(self._name_lbl)

        self._bot_badge = ThemedLabel("  Bot Account  ", font_size=FontSize.SMALL, color_role=ColorRole.ACCENT_ALT)
        self._bot_badge.setObjectName("OverlayBadge")
        self._bot_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._bot_badge.hide()
        name_row.addWidget(self._bot_badge)
        name_row.addStretch()
        info_layout.addLayout(name_row)

        # ────────────────────────────
        info_layout.addWidget(HLine())

        # Operator (bot only)
        operator_header_row = QHBoxLayout()
        operator_header_row.setSpacing(8)
        operator_header_row.setContentsMargins(0, 0, 0, 0)

        self._operator_header_lbl = ThemedLabel("", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        self._operator_header_lbl.hide()
        operator_header_row.addWidget(self._operator_header_lbl)

        self._operator_lbl = ThemedLabel("", font_size=FontSize.XL, color_role=ColorRole.ACCENT_PRIMARY)
        self._operator_lbl.hide()
        operator_header_row.addWidget(self._operator_lbl)
        operator_header_row.addStretch()

        info_layout.addLayout(operator_header_row)

        # Main Character
        main_char_header_row = QHBoxLayout()
        main_char_header_row.setSpacing(8)
        main_char_header_row.setContentsMargins(0, 0, 0, 0)
        self._main_char_header_lbl = ThemedLabel("Main: ", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        main_char_header_row.addWidget(self._main_char_header_lbl)

        self._main_char_lbl = ThemedLabel("", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        main_char_header_row.addWidget(self._main_char_lbl)

        main_char_header_row.addStretch()
        info_layout.addLayout(main_char_header_row)

        # DKP
        dkp_header_row = QHBoxLayout()
        dkp_header_row.setSpacing(8)
        dkp_header_row.setContentsMargins(0, 0, 0, 0)
        self._dkp_header_lbl = ThemedLabel("DKP", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        dkp_header_row.addWidget(self._dkp_header_lbl)

        self._dkp_val_header_lbl = ThemedLabel("", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        dkp_header_row.addWidget(self._dkp_val_header_lbl)

        dkp_header_row.addStretch()
        info_layout.addLayout(dkp_header_row)

        self._dkp_lbl = ThemedLabel("", font_size=FontSize.MEDIUM, color_role=ColorRole.TEXT_SECONDARY)
        info_layout.addWidget(self._dkp_lbl)

        # Alts
        self._alts_header_lbl = ThemedLabel("Other Characters", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        info_layout.addWidget(self._alts_header_lbl)
        self._alts_lbl = ThemedLabel("", font_size=FontSize.MEDIUM, color_role=ColorRole.TEXT_SECONDARY, word_wrap=True)
        info_layout.addWidget(self._alts_lbl)

        # Recent items
        self._items_header_lbl = ThemedLabel("Recent Items", font_size=FontSize.LARGE, color_role=ColorRole.TEXT_PRIMARY)
        info_layout.addWidget(self._items_header_lbl)
        self._items_lbl = ThemedLabel("", font_size=FontSize.MEDIUM, color_role=ColorRole.TEXT_SECONDARY, word_wrap=True)
        info_layout.addWidget(self._items_lbl)

        self.content_layout.addStretch()

        # ── Bottom row: countdown + dismiss ───────────────────────────────────
        self._countdown_lbl = ThemedLabel(
            f"Auto-dismiss in {_TIMEOUT_SECS}s",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
        )

        self._dismiss_btn = ThemedButton("Dismiss", ThemedButton.VARIANT_GHOST)
        self._dismiss_btn.clicked.connect(self.close)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self._countdown_lbl)
        bottom_row.addStretch()
        bottom_row.addWidget(self._dismiss_btn)
        self.content_layout.addLayout(bottom_row)

    # ── Data loading ───────────────────────────────────────────────────────────

    def _fetch_character(self) -> None:
        svc = registry.get(IGravityBotService)
        svc.character_fetched.connect(self._on_character_fetched)
        svc.fetch_character(self._character_name)

    def _on_character_fetched(self, success: bool, body: str) -> None:
        if not success:
            self._status_lbl.setText("Failed to fetch character data")
            self._status_lbl.set_color_role(ColorRole.ERROR)
            return

        try:
            char = json.loads(body)
        except Exception:
            self._status_lbl.setText("Error parsing character data")
            self._status_lbl.set_color_role(ColorRole.ERROR)
            return

        if not char:
            self._status_lbl.setText(f"{self._character_name} not in guild records")
            return

        self._status_lbl.hide()
        self._populate(char)

    def _populate(self, char: dict) -> None:
        self._name_lbl.setText(char.get("name", self._character_name))

        if char.get("is_bot", False):
            self._populate_bot(char)
        else:
            self._populate_player(char)

        self._info_widget.show()

    def _populate_bot(self, char: dict) -> None:
        self._bot_badge.show()
        operator = char.get("operator")
        if operator and operator.get("name"):
            prefix = "Possible Operator" if operator.get("confidence") != "high" else "Operator"
            self._operator_header_lbl.setText(f"{prefix}: ")
            self._operator_lbl.setText(f"{operator['name']}")
            self._operator_header_lbl.show()
            self._operator_lbl.show()
            self._populate_player(operator)
        else:
            self._operator_header_lbl.setText("Operator: ")
            self._operator_lbl.setText("Unknown")
            self._operator_header_lbl.show()
            self._operator_lbl.show()
            self._dkp_header_lbl.hide()
            self._dkp_val_header_lbl.hide()
            self._dkp_lbl.hide()
            self._main_char_header_lbl.hide()
            self._main_char_lbl.hide()
            self._alts_header_lbl.hide()
            self._alts_lbl.hide()
            self._items_header_lbl.hide()
            self._items_lbl.hide()

    def _populate_player(self, char: dict) -> None:
        cfg = registry.get(ISettingsService).settings.who_lookup

        dkp = char.get("dkp")
        if dkp and (cfg.show_current_dkp or cfg.show_earned_dkp or cfg.show_spent_dkp):
            parts: list[str] = []
            if cfg.show_current_dkp:
                self._dkp_header_lbl.setText("DKP: ")
                self._dkp_val_header_lbl.setText(f"{dkp.get('current', 0)}")
            if cfg.show_earned_dkp:
                parts.append(f"{dkp.get('earned', 0)} earned")
            if cfg.show_spent_dkp:
                parts.append(f"{dkp.get('spent', 0)} spent")
            self._dkp_lbl.setText("  |  ".join(parts))
        else:
            self._dkp_header_lbl.hide()
            self._dkp_val_header_lbl.hide()
            self._dkp_lbl.hide()

        main_char = char.get("main_name")
        if main_char:
            self._main_char_lbl.setText(main_char)
        else:
            self._main_char_header_lbl.hide()
            self._main_char_lbl.hide()

        alts = char.get("alts", [])
        if alts:
            self._alts_lbl.setText(", ".join(alts))
        else:
            self._alts_header_lbl.hide()
            self._alts_lbl.hide()

        items = char.get("recent_items", [])
        if items and cfg.show_recent_items:
            lines = [f"· {html.unescape(item.get('name', ''))}  —  {item.get('value', 0):g} dkp" for item in items[:5]]
            self._items_lbl.setText("\n".join(lines))
        else:
            self._items_header_lbl.hide()
            self._items_lbl.hide()

    # ── Countdown ──────────────────────────────────────────────────────────────

    def _start_countdown(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1_000)

    def _tick(self) -> None:
        self._seconds_left -= 1
        self._countdown_lbl.setText(f"Auto-dismiss in {self._seconds_left}s")
        if self._seconds_left <= 0:
            self.close()

    # ── Close ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self._timer:
            self._timer.stop()
        try:
            svc = registry.get(IGravityBotService)
            svc.character_fetched.disconnect(self._on_character_fetched)
        except RuntimeError:
            pass
        self.dismissed.emit()
        super().closeEvent(event)
