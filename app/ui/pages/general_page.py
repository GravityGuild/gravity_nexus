"""General settings page."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from services.settings_service import SettingsService
from ui.cards.settings_card import SettingsCard
from ui.widgets.status_widgets import SectionHeader
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import ThemedComboBox, ThemedLineEdit
from ui.widgets.toggle_switch import ToggleSwitch


class GeneralPage(QWidget):
    """General / startup settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = SettingsService.instance()
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

        sub = QLabel("Application startup and log file configuration.")
        sub.setObjectName("PageSubtitle")
        vl.addWidget(sub)

        vl.addSpacing(4)

        # ── Card: Log File ────────────────────────────────────────────────────
        log_card = SettingsCard("Log File", "Path to your EverQuest log file.")
        vl.addWidget(log_card)

        path_row = QHBoxLayout()
        self._log_path_edit = ThemedLineEdit("C:\\EverQuest\\Logs\\eqlog_Character_Server.txt")
        self._log_path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        browse_btn = ThemedButton("Browse…", ThemedButton.VARIANT_SECONDARY)
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse_log_file)
        path_row.addWidget(self._log_path_edit)
        path_row.addWidget(browse_btn)
        log_card.add_layout(path_row)

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

        # ── Card: Profile ─────────────────────────────────────────────────────
        profile_card = SettingsCard("Active Profile", "Select the character/server profile to use.")
        vl.addWidget(profile_card)

        self._profile_combo = ThemedComboBox()
        for p in ["Default", "Warrior Main", "Cleric Alt", "Wizard Twink"]:
            self._profile_combo.addItem(p)
        profile_card.add_widget(self._profile_combo)

        save_btn = ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY)
        save_btn.setFixedWidth(160)
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
        self._log_path_edit.setText(g.log_file_path)
        self._toggle_auto_start.set_checked(g.auto_start_parser, animated=False)
        self._toggle_start_windows.set_checked(g.start_with_windows, animated=False)
        self._toggle_minimize_tray.set_checked(g.minimize_to_tray, animated=False)
        self._toggle_check_updates.set_checked(g.check_for_updates, animated=False)

    def _save(self) -> None:
        g = self._svc.settings.general
        g.log_file_path = self._log_path_edit.text()
        g.auto_start_parser = self._toggle_auto_start.is_checked()
        g.start_with_windows = self._toggle_start_windows.is_checked()
        g.minimize_to_tray = self._toggle_minimize_tray.is_checked()
        g.check_for_updates = self._toggle_check_updates.is_checked()
        self._svc.save()

    def _browse_log_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select EverQuest Log File", "", "Log Files (*.txt);;All Files (*)"
        )
        if path:
            self._log_path_edit.setText(path)

