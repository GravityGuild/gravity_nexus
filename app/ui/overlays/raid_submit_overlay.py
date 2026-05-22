"""RaidSubmitOverlay — prompts the user to submit a detected raid log to Gravity Bot."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QSizePolicy,
    QWidget,
)

from theme.spec import ColorRole, FontSize
from ui.overlays.base_overlay_window import BaseOverlayWindow
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel

log = logging.getLogger(__name__)

_TIMEOUT_SECS = 60


class RaidSubmitOverlay(BaseOverlayWindow):
    """Frameless overlay shown when a raid attendance dump is detected.

    Displays a preview of the captured log lines and a Submit / Dismiss choice.
    Auto-dismisses after ``_TIMEOUT_SECS`` seconds if the user takes no action.

    Signals
    -------
    dismissed():
        Emitted when the overlay closes for any reason.
    submitted(list):
        Emitted immediately after the user confirms submission (before REST reply).
    """

    dismissed = Signal()
    submitted = Signal(list)  # list[str]

    def __init__(
        self,
        raw_lines: list[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__("Raid Log Detected", parent)
        self._lines = raw_lines
        self._seconds_left = _TIMEOUT_SECS
        self._submitted = False
        self._timer: Optional[QTimer] = None

        self._build_content()
        self._wire_submit_result()
        self._start_countdown()

        self.resize(500, 360)

    # ── Content construction ───────────────────────────────────────────────────

    def _build_content(self) -> None:
        # ── Line-count badge ──────────────────────────────────────────────────
        badge = ThemedLabel(
            f"  {len(self._lines)} lines captured  ",
            font_size=FontSize.SMALL,
            color_role=ColorRole.ACCENT_ALT,
        )
        badge.setObjectName("OverlayBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(26)
        self.content_layout.addWidget(badge)

        # ── Preview label ─────────────────────────────────────────────────────
        preview_lbl = ThemedLabel(
            "Preview (first 20 lines):",
            font_size=FontSize.MEDIUM,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        self.content_layout.addWidget(preview_lbl)

        # ── Scrollable log preview ────────────────────────────────────────────
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFixedHeight(130)
        self._preview.setPlainText("\n".join(self._lines[:20]))
        self.content_layout.addWidget(self._preview)

        # ── Status label (empty initially) ────────────────────────────────────
        self._status_lbl = ThemedLabel("", font_size=FontSize.MEDIUM)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.content_layout.addWidget(self._status_lbl)

        # ── Countdown label ───────────────────────────────────────────────────
        self._countdown_lbl = ThemedLabel(
            f"Auto-dismiss in {_TIMEOUT_SECS}s",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        self._countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._countdown_lbl)

        # ── Action buttons ────────────────────────────────────────────────────
        self._submit_btn = ThemedButton(
            "Submit to Gravity Bot", ThemedButton.VARIANT_PRIMARY
        )
        self._dismiss_btn = ThemedButton("Dismiss", ThemedButton.VARIANT_GHOST)
        self._submit_btn.clicked.connect(self._on_submit)
        self._dismiss_btn.clicked.connect(self.close)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._submit_btn)
        btn_row.addWidget(self._dismiss_btn)
        self.content_layout.addLayout(btn_row)

    def _wire_submit_result(self) -> None:
        """Connect to GravityBotService.submit_result (disconnected on close)."""
        from core.registry import registry
        from services.protocols import IGravityBotService

        registry.get(IGravityBotService).submit_result.connect(self._on_submit_result)

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

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_submit(self) -> None:
        from core.registry import registry
        from services.protocols import IGravityBotService

        svc = registry.get(IGravityBotService)
        if not svc.is_connected:
            self._set_status(
                "⚠  Not connected to Gravity Bot — check the Gravity Bot page",
                ColorRole.ERROR,
            )
            return

        self._submit_btn.setEnabled(False)
        self._dismiss_btn.setEnabled(False)
        if self._timer:
            self._timer.stop()
        self._countdown_lbl.setText("")

        self._set_status("Submitting…", ColorRole.ACCENT_PRIMARY)
        self._submitted = True
        self.submitted.emit(self._lines)
        svc.submit_raid_log(self._lines)

    def _on_submit_result(self, success: bool, message: str) -> None:
        if not self._submitted:
            return  # belongs to a different overlay instance

        if success:
            self._set_status("✓  Submitted successfully!", ColorRole.SUCCESS)
            QTimer.singleShot(2_000, self.close)
        else:
            short = message[:80]
            self._set_status(f"✗  Error: {short}", ColorRole.ERROR)
            self._submit_btn.setEnabled(True)
            self._dismiss_btn.setEnabled(True)
            self._seconds_left = _TIMEOUT_SECS
            self._start_countdown()

    def _set_status(self, text: str, color_role: ColorRole) -> None:
        """Update the status label text and colour role."""
        self._status_lbl.setText(text)
        self._status_lbl.set_color_role(color_role)

    # ── Close ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self._timer:
            self._timer.stop()
        # Disconnect to prevent dangling signal handlers
        try:
            from core.registry import registry
            from services.protocols import IGravityBotService

            registry.get(IGravityBotService).submit_result.disconnect(
                self._on_submit_result
            )
        except RuntimeError:
            pass
        self.dismissed.emit()
        super().closeEvent(event)
