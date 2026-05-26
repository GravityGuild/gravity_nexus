"""General settings page."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.log_parser_service import LogFileDiscovery
from services.protocols import ISettingsService, IUpdateService
from theme.spec import ColorRole, FontSize
from ui.cards.settings_card import SettingsCard
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.themed_widgets import ThemedLineEdit
from ui.widgets.toggle_switch import ToggleSwitch


class GeneralPage(QWidget):
    """General / startup settings page."""

    start_parser_requested = Signal(str)  # emits log_directory path
    stop_parser_requested = Signal()

    # Update state: "idle" | "checking" | "available" | "downloading" | "ready" | "error"
    _update_state: str = "idle"
    _pending_version: str = ""
    _pending_asset: str = ""
    _pending_path: str = ""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._update_svc = registry.get(IUpdateService)
        self._build_ui()
        self._load_values()
        self._connect_update_signals()

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

        # Page title
        title = QLabel("General")
        title.setObjectName("PageTitle")
        vl.addWidget(title)

        sub = QLabel("Application startup and log directory configuration.")
        sub.setObjectName("PageSubtitle")
        vl.addWidget(sub)

        vl.addSpacing(4)

        # ── Card: EQ Logs Directory ───────────────────────────────────────────
        log_card = SettingsCard(
            "EQ Logs Directory",
            "Path to the EverQuest Logs folder (e.g. C:\\EverQuest\\Logs). "
            "The parser will auto-detect the active character's log file.",
        )
        vl.addWidget(log_card)

        path_row = QHBoxLayout()
        self._log_dir_edit = ThemedLineEdit("C:\\EverQuest\\Logs")
        self._log_dir_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        browse_btn = ThemedButton("Browse…", ThemedButton.VARIANT_SECONDARY)
        browse_btn.clicked.connect(self._browse_log_directory)
        path_row.addWidget(self._log_dir_edit)
        path_row.addWidget(browse_btn)
        log_card.add_layout(path_row)

        # Discovery info label — updates when the directory text changes
        self._discovery_lbl = ThemedLabel(
            "",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        log_card.add_widget(self._discovery_lbl)
        self._log_dir_edit.textChanged.connect(self._refresh_discovery_label)

        # ── Card: Startup ─────────────────────────────────────────────────────
        startup_card = SettingsCard("Startup Behaviour", "Control how the application launches.")
        vl.addWidget(startup_card)

        for label, attr in [
            ("Auto-start parser on launch", "auto_start"),
            ("Start with Windows", "start_windows"),
            ("Minimize to system tray on close", "minimize_tray"),
            ("Check for updates automatically", "check_updates"),
        ]:
            self._add_toggle_row(startup_card, label, attr)

        # ── Card: Integrations ───────────────────────────────────────────────
        integrations_card = SettingsCard(
            "Integrations",
            "Control how Gravity Nexus connects with external services.",
        )
        vl.addWidget(integrations_card)

        self._add_toggle_row(
            integrations_card,
            "Send guild chat to Gravity Bot",
            "send_guild_chat",
        )

        # ── Card: Software Updates ────────────────────────────────────────────
        update_card = SettingsCard(
            "Software Updates",
            "Download and install new releases.",
        )
        vl.addWidget(update_card)

        status_row = QHBoxLayout()
        self._update_status_lbl = ThemedLabel(
            "",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        self._update_status_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_action_btn = ThemedButton("Check Now", ThemedButton.VARIANT_SECONDARY)
        self._update_action_btn.clicked.connect(self._on_update_action_clicked)
        status_row.addWidget(self._update_status_lbl)
        status_row.addWidget(self._update_action_btn)
        update_card.add_layout(status_row)

        self._download_progress_bar = QProgressBar()
        self._download_progress_bar.setRange(0, 100)
        self._download_progress_bar.setTextVisible(False)
        self._download_progress_bar.setFixedHeight(6)
        self._download_progress_bar.hide()
        update_card.add_widget(self._download_progress_bar)

        save_btn = ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY)
        save_btn.clicked.connect(self._save)
        vl.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        vl.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _add_toggle_row(self, card: SettingsCard, label: str, attr: str) -> None:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        toggle = ToggleSwitch()
        toggle.setObjectName(f"toggle_{attr}")
        row.addWidget(lbl)
        row.addWidget(toggle)
        card.add_layout(row)
        setattr(self, f"_toggle_{attr}", toggle)

    def _load_values(self) -> None:
        g = self._svc.settings.general
        self._log_dir_edit.setText(g.log_directory)
        self._toggle_auto_start.set_checked(g.auto_start_parser, animated=False)
        self._toggle_start_windows.set_checked(g.start_with_windows, animated=False)
        self._toggle_minimize_tray.set_checked(g.minimize_to_tray, animated=False)
        self._toggle_check_updates.set_checked(g.check_for_updates, animated=False)
        self._toggle_send_guild_chat.set_checked(
            self._svc.settings.gravity_bot.send_guild_chat, animated=False
        )
        self._refresh_discovery_label(g.log_directory)
        self._refresh_update_controls()

    def _save(self) -> None:
        g = self._svc.settings.general
        g.log_directory = self._log_dir_edit.text().strip()
        g.auto_start_parser = self._toggle_auto_start.is_checked()
        g.start_with_windows = self._toggle_start_windows.is_checked()
        g.minimize_to_tray = self._toggle_minimize_tray.is_checked()
        g.check_for_updates = self._toggle_check_updates.is_checked()
        self._svc.settings.gravity_bot.send_guild_chat = self._toggle_send_guild_chat.is_checked()
        self._svc.save()
        self._refresh_update_controls()

    def _refresh_update_controls(self) -> None:
        self._toggle_check_updates.setEnabled(True)
        if self._update_state == "idle":
            self._update_action_btn.setEnabled(True)
            self._update_status_lbl.setText(
                self._format_last_checked(self._svc.settings.general.last_update_check_timestamp)
            )

    def _browse_log_directory(self) -> None:
        start = self._log_dir_edit.text() or "C:\\"
        path = QFileDialog.getExistingDirectory(
            self, "Select EverQuest Logs Directory", start
        )
        if path:
            self._log_dir_edit.setText(path)

    def _refresh_discovery_label(self, directory: str) -> None:
        """Scan *directory* and update the discovery info label."""
        if not directory:
            self._discovery_lbl.setText("")
            return
        files = LogFileDiscovery.find_all(Path(directory))
        if not files:
            self._discovery_lbl.setText("⚠  No eqlog_*_project1999.txt files found")
        else:
            chars = [LogFileDiscovery.character_name(f) for f in files]
            most_recent = chars[0]
            count = len(chars)
            extra = f"  (+{count - 1} more)" if count > 1 else ""
            self._discovery_lbl.setText(
                f"✓  {count} log file{'s' if count != 1 else ''} found — "
                f"active: {most_recent}{extra}"
            )

    def _on_start_parser(self) -> None:
        directory = self._log_dir_edit.text().strip()
        if directory:
            self._save()
            self.start_parser_requested.emit(directory)

    def update_parser_status(self, running: bool, log_name: str = "") -> None:
        """No-op — parser status is now shown in the sidebar."""

    # ── Update section ─────────────────────────────────────────────────────────

    def _connect_update_signals(self) -> None:
        self._update_svc.update_available.connect(self._on_update_available)
        self._update_svc.update_downloaded.connect(self._on_update_downloaded)
        self._update_svc.download_progress.connect(self._on_download_progress)
        self._update_svc.update_status.connect(self._on_update_status)
        self._update_svc.update_error.connect(self._on_update_error)

    def _on_update_action_clicked(self) -> None:
        if self._update_state in ("idle", "error"):
            self._update_state = "checking"
            self._update_status_lbl.setText("Checking for updates…")
            self._update_action_btn.setText("Checking…")
            self._update_action_btn.setEnabled(False)
            self._update_svc.check_for_updates()
        elif self._update_state == "available":
            self._update_state = "downloading"
            self._download_progress_bar.setRange(0, 0)  # indeterminate until first progress signal
            self._download_progress_bar.show()
            self._update_status_lbl.setText(f"Downloading v{self._pending_version}…")
            self._update_action_btn.setText("Downloading…")
            self._update_action_btn.setEnabled(False)
            self._update_svc.download_update(self._pending_version, self._pending_asset)
        elif self._update_state == "ready":
            reply = QMessageBox.question(
                self,
                "Install Update",
                f"Install v{self._pending_version} now?\n\nThe app will close and restart automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._update_svc.install_and_restart(self._pending_path)

    @Slot(str, str)
    def _on_update_available(self, version: str, asset_name: str) -> None:
        self._pending_version = version
        self._pending_asset = asset_name
        self._update_state = "available"
        self._update_status_lbl.setText(f"Update available: v{version}")
        self._update_status_lbl.setProperty("colorRole", "success")
        self._update_action_btn.setText("Download & Install")
        self._update_action_btn.setEnabled(True)

    @Slot(str, str)
    def _on_update_downloaded(self, version: str, path: str) -> None:
        self._pending_path = path
        self._update_state = "ready"
        self._download_progress_bar.hide()
        self._update_status_lbl.setText(f"v{version} ready to install — app will restart")
        self._update_action_btn.setText("Install Now")
        self._update_action_btn.setEnabled(True)

    @Slot(int)
    def _on_download_progress(self, pct: int) -> None:
        self._update_state = "downloading"
        if self._download_progress_bar.maximum() == 0:
            self._download_progress_bar.setRange(0, 100)
        self._download_progress_bar.setValue(pct)

    @Slot(str)
    def _on_update_status(self, msg: str) -> None:
        if self._update_state in ("available", "downloading", "ready", "error"):
            return
        self._download_progress_bar.hide()
        self._update_status_lbl.setText(msg)
        self._update_action_btn.setText("Check Now")
        self._update_action_btn.setEnabled(True)
        self._update_state = "idle"

    @Slot(str)
    def _on_update_error(self, msg: str) -> None:
        self._update_state = "error"
        self._download_progress_bar.hide()
        self._update_status_lbl.setText(f"Error: {msg}")
        self._update_action_btn.setText("Try Again")
        self._update_action_btn.setEnabled(True)

    @staticmethod
    def _format_last_checked(timestamp: float) -> str:
        if timestamp == 0.0:
            return "Never checked"
        elapsed = time.time() - timestamp
        if elapsed < 60:
            return "Last checked: just now"
        if elapsed < 3600:
            mins = int(elapsed / 60)
            return f"Last checked: {mins} minute{'s' if mins != 1 else ''} ago"
        hours = int(elapsed / 3600)
        return f"Last checked: {hours} hour{'s' if hours != 1 else ''} ago"
