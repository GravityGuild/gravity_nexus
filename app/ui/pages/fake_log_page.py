"""FakeLogPage — developer tool for replaying/injecting fake EQ log lines.

Provides three injection mechanisms:
  1. **Manual** — type any body text and click Inject.
  2. **Presets** — drop-down of canned EQ scenarios (zone changes, guild chat, etc.).
  3. **File Replay** — load a ``.txt`` file and play back each line with a
     configurable delay.

The page also shows a live feed of every line written to the fake log.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.fake_log_service import PRESETS, FakeLogService
from services.protocols import ILogParserService
from ui.cards.settings_card import SettingsCard
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import ThemedComboBox, ThemedLineEdit

log = logging.getLogger(__name__)

# Speed options: (display label, interval_ms)
_SPEED_OPTIONS: list[tuple[str, int]] = [
    ("Slow (1 s / line)", 1000),
    ("Normal (500 ms / line)", 500),
    ("Fast (200 ms / line)", 200),
    ("Very Fast (50 ms / line)", 50),
    ("Instant", 0),
]

# Max lines shown in the live feed
_MAX_FEED_LINES = 200


class FakeLogPage(QWidget):
    """Developer/testing page for injecting fake EQ log lines."""

    def __init__(
        self,
        fake_log_svc: FakeLogService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = fake_log_svc
        self._parser_svc = registry.get(ILogParserService)
        self._replay_file_path: Optional[Path] = None

        self._build_ui()
        self._connect_signals()
        self._refresh_session_state()

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

        # ── Header ────────────────────────────────────────────────────────────
        title = QLabel("Log Replay / Dev Tools")
        title.setObjectName("PageTitle")
        vl.addWidget(title)

        sub = QLabel(
            "Inject fake EQ log lines into the parser pipeline for testing "
            "matchers, overlays, and notifications — no real EverQuest session required."
        )
        sub.setObjectName("PageSubtitle")
        sub.setWordWrap(True)
        vl.addWidget(sub)
        vl.addSpacing(4)

        # ── Session card ──────────────────────────────────────────────────────
        session_card = SettingsCard(
            "Test Session",
            "Start a fake-log session so the parser tails a temporary file. "
            "Any active real-log session will be paused while the test session is running.",
        )
        vl.addWidget(session_card)

        session_btn_row = QHBoxLayout()
        self._start_session_btn = ThemedButton(
            "▶  Start Test Session", ThemedButton.VARIANT_PRIMARY
        )
        self._stop_session_btn = ThemedButton(
            "■  Stop Test Session", ThemedButton.VARIANT_DANGER
        )
        self._stop_session_btn.setEnabled(False)
        session_btn_row.addWidget(self._start_session_btn)
        session_btn_row.addWidget(self._stop_session_btn)
        session_btn_row.addStretch()
        session_card.add_layout(session_btn_row)

        self._session_status_lbl = QLabel("Session inactive")
        self._session_status_lbl.setStyleSheet(
            "color: rgba(147,164,195,160); font-size: 11px; padding-top: 2px;"
        )
        session_card.add_widget(self._session_status_lbl)

        # ── Manual injection card ─────────────────────────────────────────────
        manual_card = SettingsCard(
            "Manual Injection",
            "Type any EQ log message body below. "
            "The EQ timestamp bracket is added automatically.",
        )
        vl.addWidget(manual_card)

        inject_row = QHBoxLayout()
        self._manual_edit = ThemedLineEdit(
            "e.g.  You have entered Plane of Time."
        )
        self._manual_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._manual_btn = ThemedButton("Inject", ThemedButton.VARIANT_SECONDARY)
        self._manual_btn.setEnabled(False)
        inject_row.addWidget(self._manual_edit)
        inject_row.addWidget(self._manual_btn)
        manual_card.add_layout(inject_row)

        self._manual_edit.returnPressed.connect(self._on_inject_manual)
        self._manual_btn.clicked.connect(self._on_inject_manual)

        # ── Preset card ───────────────────────────────────────────────────────
        preset_card = SettingsCard(
            "Preset Scenarios",
            "Inject a pre-built scenario to test specific matchers.",
        )
        vl.addWidget(preset_card)

        preset_row = QHBoxLayout()
        self._preset_combo = ThemedComboBox()
        for name in PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._preset_btn = ThemedButton("Inject Preset", ThemedButton.VARIANT_SECONDARY)
        self._preset_btn.setEnabled(False)
        preset_row.addWidget(self._preset_combo)
        preset_row.addWidget(self._preset_btn)
        preset_card.add_layout(preset_row)
        self._preset_btn.clicked.connect(self._on_inject_preset)

        # ── File replay card ──────────────────────────────────────────────────
        replay_card = SettingsCard(
            "File Replay",
            "Load a plain-text file (one log-line body per line) and replay "
            "it at a chosen speed. EQ timestamps are added automatically.",
        )
        vl.addWidget(replay_card)

        file_row = QHBoxLayout()
        self._replay_file_edit = ThemedLineEdit("No file selected")
        self._replay_file_edit.setReadOnly(True)
        self._replay_file_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        browse_btn = ThemedButton("Browse…", ThemedButton.VARIANT_SECONDARY)
        browse_btn.clicked.connect(self._on_browse_replay_file)
        file_row.addWidget(self._replay_file_edit)
        file_row.addWidget(browse_btn)
        replay_card.add_layout(file_row)

        speed_row = QHBoxLayout()
        speed_lbl = QLabel("Speed:")
        self._speed_combo = ThemedComboBox()
        for label, _ in _SPEED_OPTIONS:
            self._speed_combo.addItem(label)
        self._speed_combo.setCurrentIndex(1)  # Normal by default
        speed_row.addWidget(speed_lbl)
        speed_row.addWidget(self._speed_combo)
        speed_row.addStretch()
        replay_card.add_layout(speed_row)

        # Progress bar (hidden until replay starts)
        self._replay_progress = QProgressBar()
        self._replay_progress.setVisible(False)
        self._replay_progress.setTextVisible(True)
        self._replay_progress.setFixedHeight(16)
        self._replay_progress.setStyleSheet(
            "QProgressBar { background: rgba(15,22,40,180); border: 1px solid rgba(147,164,195,40);"
            " border-radius: 3px; color: #93A4C3; font-size: 10px; }"
            "QProgressBar::chunk { background: rgba(0,212,255,120); border-radius: 2px; }"
        )
        replay_card.add_widget(self._replay_progress)

        replay_btn_row = QHBoxLayout()
        self._replay_start_btn = ThemedButton(
            "▶  Start Replay", ThemedButton.VARIANT_PRIMARY
        )
        self._replay_start_btn.setEnabled(False)
        self._replay_stop_btn = ThemedButton(
            "■  Stop Replay", ThemedButton.VARIANT_DANGER
        )
        self._replay_stop_btn.setEnabled(False)
        replay_btn_row.addWidget(self._replay_start_btn)
        replay_btn_row.addWidget(self._replay_stop_btn)
        replay_btn_row.addStretch()
        replay_card.add_layout(replay_btn_row)
        self._replay_start_btn.clicked.connect(self._on_start_replay)
        self._replay_stop_btn.clicked.connect(self._on_stop_replay)

        # ── Live feed card ────────────────────────────────────────────────────
        feed_card = SettingsCard(
            "Live Feed",
            "Lines injected into the fake log file will appear here in real time.",
        )
        vl.addWidget(feed_card)

        self._feed = QPlainTextEdit()
        self._feed.setReadOnly(True)
        self._feed.setMaximumBlockCount(_MAX_FEED_LINES)
        self._feed.setFixedHeight(220)
        self._feed.setStyleSheet(
            "QPlainTextEdit {"
            "  background: rgba(8,14,30,200);"
            "  color: #B0C4DE;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 11px;"
            "  border: 1px solid rgba(147,164,195,40);"
            "  border-radius: 4px;"
            "  padding: 6px;"
            "}"
        )
        feed_card.add_widget(self._feed)

        clear_feed_btn = ThemedButton("Clear Feed", ThemedButton.VARIANT_SECONDARY)
        clear_feed_btn.clicked.connect(self._feed.clear)
        feed_card.add_widget(clear_feed_btn)

        vl.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Signal wiring ──────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._start_session_btn.clicked.connect(self._on_start_session)
        self._stop_session_btn.clicked.connect(self._on_stop_session)

        self._svc.session_started.connect(self._refresh_session_state)
        self._svc.session_stopped.connect(self._refresh_session_state)
        self._svc.line_injected.connect(self._on_line_injected)
        self._svc.replay_started.connect(self._on_replay_started)
        self._svc.replay_finished.connect(self._on_replay_finished)
        self._svc.replay_progress.connect(self._on_replay_progress)

    # ── Session handlers ───────────────────────────────────────────────────────

    @Slot()
    def _on_start_session(self) -> None:
        self._svc.start(self._parser_svc)

    @Slot()
    def _on_stop_session(self) -> None:
        self._svc.stop()

    @Slot()
    def _refresh_session_state(self) -> None:
        active = self._svc.is_active
        self._start_session_btn.setEnabled(not active)
        self._stop_session_btn.setEnabled(active)
        self._manual_btn.setEnabled(active)
        self._preset_btn.setEnabled(active)
        self._replay_start_btn.setEnabled(
            active and self._replay_file_path is not None
        )
        if active:
            self._session_status_lbl.setText(
                f"✓  Session active — tailing fake log for character "
                f'"{self._svc.character_name}"'
            )
            self._session_status_lbl.setStyleSheet(
                "color: #78E08F; font-size: 11px; padding-top: 2px;"
            )
        else:
            self._session_status_lbl.setText("Session inactive")
            self._session_status_lbl.setStyleSheet(
                "color: rgba(147,164,195,160); font-size: 11px; padding-top: 2px;"
            )

    # ── Manual injection ───────────────────────────────────────────────────────

    @Slot()
    def _on_inject_manual(self) -> None:
        text = self._manual_edit.text().strip()
        if not text or not self._svc.is_active:
            return
        self._svc.inject_line(text)
        self._manual_edit.clear()

    # ── Preset injection ───────────────────────────────────────────────────────

    @Slot()
    def _on_inject_preset(self) -> None:
        name = self._preset_combo.currentText()
        if name and self._svc.is_active:
            self._svc.inject_preset(name)

    # ── File replay ────────────────────────────────────────────────────────────

    @Slot()
    def _on_browse_replay_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Log Replay File",
            "",
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self._replay_file_path = Path(path)
            self._replay_file_edit.setText(path)
            self._replay_start_btn.setEnabled(self._svc.is_active)

    @Slot()
    def _on_start_replay(self) -> None:
        if not self._replay_file_path or not self._svc.is_active:
            return
        try:
            raw_lines = self._replay_file_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError as exc:
            log.error("Failed to read replay file: %s", exc)
            return

        # Strip empty lines
        lines = [ln for ln in raw_lines if ln.strip()]
        if not lines:
            return

        interval_ms = _SPEED_OPTIONS[self._speed_combo.currentIndex()][1]
        self._replay_progress.setValue(0)
        self._replay_progress.setMaximum(len(lines))
        self._svc.replay_lines(lines, interval_ms=interval_ms)

    @Slot()
    def _on_stop_replay(self) -> None:
        self._svc.stop_replay()

    # ── Live feed ──────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_line_injected(self, raw: str) -> None:
        self._feed.appendPlainText(raw)
        # Auto-scroll to bottom
        sb = self._feed.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Replay state callbacks ─────────────────────────────────────────────────

    @Slot()
    def _on_replay_started(self) -> None:
        self._replay_progress.setVisible(True)
        self._replay_start_btn.setEnabled(False)
        self._replay_stop_btn.setEnabled(True)

    @Slot()
    def _on_replay_finished(self) -> None:
        self._replay_stop_btn.setEnabled(False)
        self._replay_start_btn.setEnabled(
            self._svc.is_active and self._replay_file_path is not None
        )
        self._replay_progress.setVisible(False)

    @Slot(int, int)
    def _on_replay_progress(self, current: int, total: int) -> None:
        self._replay_progress.setValue(current)
        self._replay_progress.setFormat(f"{current} / {total} lines")

