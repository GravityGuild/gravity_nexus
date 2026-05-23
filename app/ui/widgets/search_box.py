"""SearchBox — themed QLineEdit with leading search icon and clear button."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class SearchBox(QWidget):
    """A search-bar widget combining an icon, line edit, and clear button.

    Styled entirely via QSS rules targeting the ``#SearchBox*`` object names
    defined in ``QssBuilder``.  No ``setStyleSheet`` calls are made here.
    """

    text_changed = Signal(str)
    search_submitted = Signal(str)

    def __init__(
        self,
        placeholder: str = "Search…",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SearchBox")
        self._build_ui(placeholder)

    # ── Public API ─────────────────────────────────────────────────────────────

    def text(self) -> str:
        return self._edit.text()

    def set_text(self, text: str) -> None:
        self._edit.setText(text)

    def clear(self) -> None:
        self._edit.clear()

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_ui(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)
        self.setMinimumHeight(34)

        icon = QLabel("⌕")
        icon.setObjectName("SearchBoxIcon")
        icon.setFixedWidth(18)
        layout.addWidget(icon)

        self._edit = QLineEdit()
        self._edit.setObjectName("SearchBoxEdit")
        self._edit.setPlaceholderText(placeholder)
        self._edit.setFrame(False)
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.returnPressed.connect(self._on_return)
        layout.addWidget(self._edit)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("SearchBoxClearBtn")
        self._clear_btn.setFixedSize(16, 16)
        self._clear_btn.hide()
        self._clear_btn.clicked.connect(self._edit.clear)
        layout.addWidget(self._clear_btn)

    def _on_text_changed(self, text: str) -> None:
        self._clear_btn.setVisible(bool(text))
        self.text_changed.emit(text)

    def _on_return(self) -> None:
        self.search_submitted.emit(self._edit.text())
