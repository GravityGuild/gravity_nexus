"""Shared UI helpers for tool widgets."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget

from theme.spec import ColorRole, FontRole, FontSize
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.toggle_switch import ToggleSwitch


def setting_row(label: str, description: str, checked: bool) -> tuple[QWidget, ToggleSwitch]:
    """A labeled setting row with a toggle on the right."""
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 4, 0, 4)
    hl.setSpacing(12)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    text_col.addWidget(ThemedLabel(label, color_role=ColorRole.TEXT_PRIMARY))
    if description:
        desc = ThemedLabel(
            description,
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        text_col.addWidget(desc)
    hl.addLayout(text_col, 1)

    toggle = ToggleSwitch(checked=checked)
    hl.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
    return row, toggle


def copy_row(prefix: str, command: str) -> QWidget:
    """A labelled command string with a clipboard copy button on the right."""
    w = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(10)
    hl.addWidget(ThemedLabel(
        f"{prefix}  {command}" if prefix else command,
        font_size=FontSize.SMALL,
        color_role=ColorRole.TEXT_SECONDARY,
        font_role=FontRole.MONO,
        word_wrap=False,
    ))
    hl.addStretch()
    copy_btn = ThemedButton("Copy", ThemedButton.VARIANT_GHOST)

    def _on_copy() -> None:
        QApplication.clipboard().setText(command)
        copy_btn.setText("✓ Copied")
        QTimer.singleShot(1_500, lambda: copy_btn.setText("Copy"))

    copy_btn.clicked.connect(_on_copy)
    hl.addWidget(copy_btn)
    return w
