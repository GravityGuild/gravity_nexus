"""Raid Tools page — aggregates individual tool widgets."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.pages.pages import _make_page_scroll, _page_header
from ui.tools.raid_log_capture_tool import RaidLogCaptureTool


class RaidToolsPage(QWidget):
    """Configuration and instructions for Raid Tools."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")

        scroll, vl = _make_page_scroll()
        _page_header(vl, "Raid Tools", "Tools and utilities to help manage raids.")

        vl.addWidget(RaidLogCaptureTool())

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
