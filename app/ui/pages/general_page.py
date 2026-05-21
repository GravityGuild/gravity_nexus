"""General settings page."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.log_parser_service import LogFileDiscovery
from services.protocols import ISettingsService
from ui.cards.settings_card import SettingsCard
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import ThemedLineEdit
from ui.widgets.toggle_switch import ToggleSwitch


class GeneralPage(QWidget):
    """General / startup settings page."""

    start_parser_requested = Signal(str)  # emits log_directory path
    stop_parser_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._build_ui()
        self._load_values()

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
        self._discovery_lbl = QLabel("")
        self._discovery_lbl.setStyleSheet(
            "color: rgba(147,164,195,160); font-size: 11px; padding-top: 2px;"
        )
        self._discovery_lbl.setWordWrap(True)
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
        self._refresh_discovery_label(g.log_directory)

    def _save(self) -> None:
        g = self._svc.settings.general
        g.log_directory = self._log_dir_edit.text().strip()
        g.auto_start_parser = self._toggle_auto_start.is_checked()
        g.start_with_windows = self._toggle_start_windows.is_checked()
        g.minimize_to_tray = self._toggle_minimize_tray.is_checked()
        g.check_for_updates = self._toggle_check_updates.is_checked()
        self._svc.save()

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
