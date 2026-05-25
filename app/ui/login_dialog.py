"""LoginDialog — method selection and browser login waiting screen."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from theme.spec import ColorRole, FontRole, FontSize
from ui.widgets import ThemedButton, ThemedLabel, ThemedLineEdit

if TYPE_CHECKING:
    from auth.auth_manager import AuthManager

log = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Modal login dialog with a method-selection screen.

    Page 0: choose a login method (currently only browser OAuth).
    Page 1: waiting screen while the browser flow completes.
    """

    def __init__(
        self,
        auth_manager: "AuthManager",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth_manager
        self._url_confirmed = True

        self.setWindowTitle("Sign In — Gravity Nexus")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._build_ui()
        self._connect_signals()

        if not self._url_confirmed:
            self._browser_method_btn.setEnabled(False)

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 28)
        root.setSpacing(0)

        title = ThemedLabel(
            "Sign In to Gravity Nexus",
            font_size=FontSize.XL,
            font_role=FontRole.DISPLAY,
            color_role=ColorRole.ACCENT_PRIMARY,
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addSpacing(20)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_select_page())
        self._stack.addWidget(self._build_waiting_page())

    def _build_select_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # URL section — shown only when no URL is saved
        self._url_section = QWidget()
        url_layout = QVBoxLayout(self._url_section)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(6)
        url_lbl = ThemedLabel("EQdkp Site URL", color_role=ColorRole.TEXT_SECONDARY)
        url_layout.addWidget(url_lbl)
        self._site_url_input = ThemedLineEdit("https://gravityp99.com")
        self._site_url_input.textChanged.connect(self._on_url_text_changed)
        url_layout.addWidget(self._site_url_input)
        layout.addWidget(self._url_section)
        self._url_section.setVisible(not self._url_confirmed)
        if not self._url_confirmed:
            layout.addSpacing(16)

        self._browser_method_btn = ThemedButton("Sign in with Browser", "primary")
        layout.addWidget(self._browser_method_btn)
        layout.addSpacing(12)

        cancel_row = QHBoxLayout()
        self._cancel_btn_select = ThemedButton("Cancel", "ghost")
        cancel_row.addStretch()
        cancel_row.addWidget(self._cancel_btn_select)
        layout.addLayout(cancel_row)

        return page

    def _build_waiting_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._instruction_label = ThemedLabel(
            "Your browser has been opened to the login page.\nComplete sign-in there.",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        self._instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._instruction_label)
        layout.addSpacing(6)

        self._status_label = ThemedLabel(
            "Waiting for browser…",
            color_role=ColorRole.TEXT_MUTED,
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)
        layout.addSpacing(20)

        self._error_label = ThemedLabel("", color_role=ColorRole.ERROR, word_wrap=True)
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)
        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._cancel_btn_waiting = ThemedButton("Cancel", "ghost")
        self._open_browser_btn = ThemedButton("Open Browser Again", "secondary")
        btn_row.addWidget(self._cancel_btn_waiting)
        btn_row.addStretch()
        btn_row.addWidget(self._open_browser_btn)
        layout.addLayout(btn_row)

        return page

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._auth.logged_in.connect(self.accept)
        self._auth.auth_error.connect(self._on_auth_error)
        self._browser_method_btn.clicked.connect(self._on_start_browser_flow)
        self._open_browser_btn.clicked.connect(self._on_retry_browser)
        self._cancel_btn_select.clicked.connect(self._on_cancel)
        self._cancel_btn_waiting.clicked.connect(self._on_cancel)

    # ── Slots ──────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_url_text_changed(self, text: str) -> None:
        self._browser_method_btn.setEnabled(bool(text.strip()))

    @Slot()
    def _on_start_browser_flow(self) -> None:
        self._error_label.setVisible(False)
        self._status_label.setText("Waiting for browser…")
        self._stack.setCurrentIndex(1)
        self._auth.start_browser_login()

    @Slot()
    def _on_retry_browser(self) -> None:
        self._error_label.setVisible(False)
        self._status_label.setText("Waiting for browser…")
        self._auth.start_browser_login()

    @Slot(str)
    def _on_auth_error(self, msg: str) -> None:
        self._error_label.setText(msg)
        self._error_label.setVisible(True)
        self._status_label.setText("Login failed.")

    @Slot()
    def _on_cancel(self) -> None:
        if self._auth._callback_server is not None:
            self._auth._callback_server.stop()
        self.reject()
