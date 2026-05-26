"""SetupWizard — first-run configuration wizard.

Shown once after the first successful authentication.  Collects the EQ log
directory and key startup preferences, then marks itself complete so it never
appears again.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.log_parser_service import LogFileDiscovery
from services.protocols import ISettingsService
from theme.spec import ColorRole, FontRole, FontSize
from ui.widgets import ThemedButton, ThemedLabel, ToggleSwitch
from ui.widgets.themed_widgets import ThemedLineEdit

log = logging.getLogger(__name__)

_STEPS = ["Welcome", "EQ Logs", "Preferences", "Done"]


class SetupWizard(QDialog):
    """Multi-step first-run wizard.

    Page 0: Welcome
    Page 1: EQ log directory picker
    Page 2: Startup preferences (start with Windows, minimize to tray)
    Page 3: Completion screen
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._svc = registry.get(ISettingsService)
        self._step = 0

        self.setWindowTitle("Setup — Gravity Nexus")
        self.setMinimumWidth(540)
        self.setMinimumHeight(460)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._build_ui()
        self._sync_step()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_step_bar())

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)
        self._stack.addWidget(self._build_welcome_page())
        self._stack.addWidget(self._build_log_dir_page())
        self._stack.addWidget(self._build_prefs_page())
        self._stack.addWidget(self._build_done_page())

        root.addWidget(self._build_nav_bar())

    def _build_step_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("WizardStepBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 14, 40, 14)
        layout.setSpacing(6)

        self._step_lbls: list[ThemedLabel] = []
        for i, name in enumerate(_STEPS):
            if i > 0:
                sep = ThemedLabel("›", color_role=ColorRole.TEXT_MUTED)
                layout.addWidget(sep)
            lbl = ThemedLabel(f"{i + 1}. {name}", color_role=ColorRole.TEXT_MUTED)
            self._step_lbls.append(lbl)
            layout.addWidget(lbl)

        layout.addStretch()
        return bar

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(48, 40, 48, 40)
        vl.setSpacing(16)
        vl.addStretch()

        title = ThemedLabel(
            "Welcome to Gravity Nexus",
            font_size=FontSize.XL,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.ACCENT_PRIMARY,
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(title)

        vl.addSpacing(8)

        body = ThemedLabel(
            "Let's get you set up in just a few steps.\n\n"
            "We'll ask for your EverQuest Project 1999 log folder and a couple of "
            "startup preferences. You can change any of these later in Settings.",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(body)

        vl.addStretch()
        return page

    def _build_log_dir_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(48, 36, 48, 36)
        vl.setSpacing(12)

        title = ThemedLabel(
            "EverQuest Log Directory",
            font_size=FontSize.LARGE,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.TEXT_PRIMARY,
        )
        vl.addWidget(title)

        desc = ThemedLabel(
            "Point Gravity Nexus to your EverQuest Logs folder. "
            "It is usually inside your EverQuest installation directory.",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        vl.addWidget(desc)

        vl.addSpacing(12)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._log_dir_edit = ThemedLineEdit("C:\\EverQuest\\Logs")
        saved = self._svc.settings.general.log_directory
        if saved:
            self._log_dir_edit.setText(saved)
        self._log_dir_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._log_dir_edit.textChanged.connect(self._refresh_discovery)
        browse_btn = ThemedButton("Browse…", ThemedButton.VARIANT_SECONDARY)
        browse_btn.clicked.connect(self._browse_log_dir)
        path_row.addWidget(self._log_dir_edit)
        path_row.addWidget(browse_btn)
        vl.addLayout(path_row)

        self._discovery_lbl = ThemedLabel(
            "",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        vl.addWidget(self._discovery_lbl)
        self._refresh_discovery(self._log_dir_edit.text())

        vl.addStretch()
        return page

    def _build_prefs_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(48, 36, 48, 36)
        vl.setSpacing(12)

        title = ThemedLabel(
            "Startup Preferences",
            font_size=FontSize.LARGE,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.TEXT_PRIMARY,
        )
        vl.addWidget(title)

        desc = ThemedLabel(
            "Choose how Gravity Nexus behaves at startup and when you close it.",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        vl.addWidget(desc)

        vl.addSpacing(16)

        row1 = QHBoxLayout()
        lbl1 = QLabel("Start with Windows")
        lbl1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._toggle_startup = ToggleSwitch(
            checked=self._svc.settings.general.start_with_windows
        )
        row1.addWidget(lbl1)
        row1.addWidget(self._toggle_startup)
        vl.addLayout(row1)

        sub1 = ThemedLabel(
            "Gravity Nexus will launch automatically when you log in to Windows.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        vl.addWidget(sub1)

        vl.addSpacing(16)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Minimize to tray on close")
        lbl2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._toggle_tray = ToggleSwitch(
            checked=self._svc.settings.general.minimize_to_tray
        )
        row2.addWidget(lbl2)
        row2.addWidget(self._toggle_tray)
        vl.addLayout(row2)

        sub2 = ThemedLabel(
            "Closing the window keeps the app running in the system tray. "
            "Use the tray icon or Quit to fully exit.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        vl.addWidget(sub2)

        vl.addSpacing(16)

        row3 = QHBoxLayout()
        lbl3 = QLabel("Auto-start log parser on launch")
        lbl3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._toggle_auto_start = ToggleSwitch(
            checked=self._svc.settings.general.auto_start_parser
        )
        row3.addWidget(lbl3)
        row3.addWidget(self._toggle_auto_start)
        vl.addLayout(row3)

        sub3 = ThemedLabel(
            "Automatically begins watching your EQ log file when the app starts.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_MUTED,
            word_wrap=True,
        )
        vl.addWidget(sub3)

        vl.addStretch()
        return page

    def _build_done_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(48, 40, 48, 40)
        vl.setSpacing(16)
        vl.addStretch()

        title = ThemedLabel(
            "You're all set!",
            font_size=FontSize.XL,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.ACCENT_PRIMARY,
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(title)

        vl.addSpacing(8)

        body = ThemedLabel(
            "Gravity Nexus is configured and ready to go.\n\n"
            "Head to Settings → General any time to adjust these preferences.",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(body)

        vl.addStretch()
        return page

    def _build_nav_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("WizardNavBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 12, 40, 16)
        layout.setSpacing(10)

        self._back_btn = ThemedButton("Back", ThemedButton.VARIANT_GHOST)
        self._back_btn.clicked.connect(self._on_back)
        layout.addWidget(self._back_btn)

        layout.addStretch()

        self._skip_btn = ThemedButton("Skip Setup", ThemedButton.VARIANT_GHOST)
        self._skip_btn.clicked.connect(self._on_skip)
        layout.addWidget(self._skip_btn)

        self._next_btn = ThemedButton("Next", ThemedButton.VARIANT_PRIMARY)
        self._next_btn.setMinimumWidth(90)
        self._next_btn.clicked.connect(self._on_next)
        layout.addWidget(self._next_btn)

        return bar

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _sync_step(self) -> None:
        last = len(_STEPS) - 1
        self._stack.setCurrentIndex(self._step)
        self._back_btn.setVisible(self._step > 0)
        self._skip_btn.setVisible(self._step < last)
        self._next_btn.setText("Launch" if self._step == last else "Next")

        for i, lbl in enumerate(self._step_lbls):
            if i == self._step:
                lbl.set_color_role(ColorRole.ACCENT_PRIMARY)
            elif i < self._step:
                lbl.set_color_role(ColorRole.SUCCESS)
            else:
                lbl.set_color_role(ColorRole.TEXT_MUTED)

    @Slot()
    def _on_next(self) -> None:
        if self._step == len(_STEPS) - 1:
            self._finish()
        else:
            self._step += 1
            self._sync_step()

    @Slot()
    def _on_back(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._sync_step()

    @Slot()
    def _on_skip(self) -> None:
        self._finish()

    def _finish(self) -> None:
        self._apply_settings()
        self.accept()

    def _apply_settings(self) -> None:
        g = self._svc.settings.general
        g.log_directory = self._log_dir_edit.text().strip()
        g.start_with_windows = self._toggle_startup.is_checked()
        g.minimize_to_tray = self._toggle_tray.is_checked()
        g.auto_start_parser = self._toggle_auto_start.is_checked()
        self._svc.settings.setup_wizard_completed = True
        self._svc.save()

        from utils.platform_utils import apply_startup_with_windows  # noqa: PLC0415
        apply_startup_with_windows(g.start_with_windows)

    # ── Slots ──────────────────────────────────────────────────────────────────

    @Slot()
    def _browse_log_dir(self) -> None:
        start = self._log_dir_edit.text() or "C:\\"
        path = QFileDialog.getExistingDirectory(
            self, "Select EverQuest Logs Directory", start
        )
        if path:
            self._log_dir_edit.setText(path)

    @Slot(str)
    def _refresh_discovery(self, directory: str) -> None:
        if not directory:
            self._discovery_lbl.setText("")
            return
        files = LogFileDiscovery.find_all(Path(directory))
        if not files:
            self._discovery_lbl.setText(
                "No eqlog_*_project1999.txt files found in this folder"
            )
        else:
            chars = [LogFileDiscovery.character_name(f) for f in files]
            count = len(chars)
            extra = f" (+{count - 1} more)" if count > 1 else ""
            self._discovery_lbl.setText(
                f"{count} log file{'s' if count != 1 else ''} found"
                f" — active: {chars[0]}{extra}"
            )
