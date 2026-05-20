"""Themed widget primitives — ComboBox, LineEdit, ScrollArea, Table, ProgressBar."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QWidget,
)
from PySide6.QtCore import Qt


class ThemedComboBox(QComboBox):
    """QComboBox pre-styled via QSS."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(30)


class ThemedLineEdit(QLineEdit):
    """QLineEdit pre-styled via QSS with optional placeholder."""

    def __init__(
        self,
        placeholder: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setMinimumHeight(30)


class ThemedScrollArea(QScrollArea):
    """QScrollArea with transparent viewport and custom scrollbars (via QSS)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        vp = self.viewport()
        if vp:
            vp.setAutoFillBackground(False)


class ThemedTable(QTableWidget):
    """QTableWidget with full-row selection and themed headers."""

    def __init__(
        self,
        rows: int = 0,
        cols: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(rows, cols, parent)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.verticalHeader().hide()
        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setShowGrid(True)

    def set_column_headers(self, headers: list[str]) -> None:
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)


class ThemedProgressBar(QProgressBar):
    """QProgressBar with QSS colour variant support.

    bar_color: "cyan" (default) | "gold" | "success" | "danger"
    """

    def __init__(
        self,
        bar_color: str = "cyan",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(14)
        self.set_bar_color(bar_color)

    def set_bar_color(self, color: str) -> None:
        self.setProperty("barColor", color)
        s = self.style()
        if s:
            s.unpolish(self)
            s.polish(self)

