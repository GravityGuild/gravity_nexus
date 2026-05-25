"""RaidSubmitOverlay — prompts the user to submit a detected raid log to Gravity Bot."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
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
    """Frameless overlay shown when a raid attendance log is detected.

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
        raw_names: list[str],
        full_who_log: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__("Raid Log Detected", parent)
        self._raw_names = raw_names
        self._full_who_log = full_who_log
        self._seconds_left = _TIMEOUT_SECS
        self._submitted = False
        self._timer: Optional[QTimer] = None

        self._build_content()
        self._wire_submit_result()
        self._fetch_raids()
        self._start_countdown()

        self.resize(500, 420)

    # ── Content construction ───────────────────────────────────────────────────

    def _build_content(self) -> None:
        # ── Line-count badge ──────────────────────────────────────────────────
        badge = ThemedLabel(
            f"  {len(self._raw_names)} lines captured  ",
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
        self._preview.setPlainText("\n".join(self._raw_names[:20]))
        self.content_layout.addWidget(self._preview)

        # ── Raid selector ─────────────────────────────────────────────────────
        raid_lbl = ThemedLabel(
            "Select Raid:",
            font_size=FontSize.MEDIUM,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        self.content_layout.addWidget(raid_lbl)

        self._raid_combo = QComboBox()
        self._raid_combo.addItem("Loading raids…")
        self._raid_combo.setEnabled(False)
        self.content_layout.addWidget(self._raid_combo)

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

    def _fetch_raids(self) -> None:
        import time as _time
        from core.registry import registry
        from services.protocols import IGravityBotService

        self._fetch_raids_t0 = _time.perf_counter()
        log.debug("RAID_TIME fetch_raids requested at t=0")
        svc = registry.get(IGravityBotService)
        svc.raids_fetched.connect(self._on_raids_fetched)
        svc.fetch_raids_cached()

    def _on_raids_fetched(self, success: bool, body: str) -> None:
        import json as _json
        import time as _time

        t_start = _time.perf_counter()
        t0 = getattr(self, "_fetch_raids_t0", t_start)
        log.info("RAID_TIME _on_raids_fetched: entered  wall=%.1f ms  body=%d bytes", (t_start - t0) * 1000, len(body))

        self._raid_combo.clear()
        if not success:
            self._raid_combo.addItem("Failed to load raids")
            return

        t_parse0 = _time.perf_counter()
        try:
            raids = _json.loads(body).get("raids", [])
        except Exception:
            self._raid_combo.addItem("Failed to load raids")
            return
        t_parse1 = _time.perf_counter()
        log.debug("RAID_TIME   json.loads: %.2f ms  (%d raids)", (t_parse1 - t_parse0) * 1000, len(raids))

        # Suppress per-item repaints — a translucent overlay repaints the entire
        # window on every model change, so batching matters with many raids.
        t_combo0 = _time.perf_counter()
        self.setUpdatesEnabled(False)
        try:
            for raid in raids:
                mm_dd = raid["raid_date"][5:10]  # "YYYY-MM-DD ..." → "MM-DD"
                self._raid_combo.addItem(f"{mm_dd} {raid['target']}", raid["channel_id"])
        finally:
            self.setUpdatesEnabled(True)
        t_combo1 = _time.perf_counter()
        log.debug("RAID_TIME   addItem loop: %.2f ms", (t_combo1 - t_combo0) * 1000)

        t_enable0 = _time.perf_counter()
        if raids:
            self._raid_combo.setEnabled(True)
        else:
            self._raid_combo.addItem("No unsubmitted raids")
        t_enable1 = _time.perf_counter()
        log.debug("RAID_TIME   setEnabled: %.2f ms", (t_enable1 - t_enable0) * 1000)

        log.info(
            "RAID_TIME raids dropdown populated: %d items  total=%.1f ms"
            "  (parse=%.1f  addItems=%.1f  setEnabled=%.1f)",
            len(raids),
            (t_enable1 - t_start) * 1000,
            (t_parse1 - t_parse0) * 1000,
            (t_combo1 - t_combo0) * 1000,
            (t_enable1 - t_enable0) * 1000,
        )

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

        channel_id = self._raid_combo.currentData()
        if channel_id is None:
            self._set_status("⚠  Please select a raid first", ColorRole.ERROR)
            return

        self._submit_btn.setEnabled(False)
        self._dismiss_btn.setEnabled(False)
        if self._timer:
            self._timer.stop()
        self._countdown_lbl.setText("")

        self._set_status("Submitting…", ColorRole.ACCENT_PRIMARY)
        self._submitted = True
        self.submitted.emit(self._raw_names)
        svc.submit_raid_log(int(channel_id), self._full_who_log)

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

            svc = registry.get(IGravityBotService)
            svc.submit_result.disconnect(self._on_submit_result)
            svc.raids_fetched.disconnect(self._on_raids_fetched)
        except RuntimeError:
            pass
        self.dismissed.emit()
        super().closeEvent(event)
