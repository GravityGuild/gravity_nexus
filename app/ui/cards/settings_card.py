"""SettingsCard — themed card container for grouped settings content."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SettingsCard(QFrame):
    """A frosted-glass card wrapping a group of related settings.

    Layout::

        ┌─ CardHeader ────────────────────────────────┐
        │  Title                          [actions]   │
        │  Subtitle                                   │
        ├─────────────────────────────────────────────┤
        │  Body content (user-supplied widget/layout)  │
        └─────────────────────────────────────────────┘
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setObjectName("SettingsCardHeader")
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(16, 10, 12, 10)
        header_layout.setSpacing(6)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("SettingsCardTitle")
        title_col.addWidget(self._title_label)

        if subtitle:
            self._subtitle_label = QLabel(subtitle)
            self._subtitle_label.setObjectName("SettingsCardSubtitle")
            title_col.addWidget(self._subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # Placeholder for optional action widgets in the header
        self._header_actions = QHBoxLayout()
        self._header_actions.setSpacing(6)
        header_layout.addLayout(self._header_actions)

        root.addWidget(self._header)

        # ── Body ──────────────────────────────────────────────────────────────
        self._body = QWidget()
        self._body.setObjectName("SettingsCardBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(16, 14, 16, 14)
        self._body_layout.setSpacing(10)
        root.addWidget(self._body)

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def body_layout(self) -> QVBoxLayout:
        """The VBox layout inside the card body — add your widgets here."""
        return self._body_layout

    def add_widget(self, widget: QWidget) -> None:
        """Convenience: append a widget to the body layout."""
        self._body_layout.addWidget(widget)

    def add_layout(self, layout) -> None:  # noqa: ANN001
        """Convenience: append a sub-layout to the body layout."""
        self._body_layout.addLayout(layout)

    def add_header_action(self, widget: QWidget) -> None:
        """Add a widget (e.g. button) to the card header action area."""
        self._header_actions.addWidget(widget)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

