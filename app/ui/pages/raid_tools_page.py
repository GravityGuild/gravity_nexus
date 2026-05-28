"""Raid Tools page — aggregates individual tool widgets."""
from __future__ import annotations

from typing import Optional, Union

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.pages.pages import _make_page_scroll, _page_header
from ui.tools.raid_log_capture_tool import RaidLogCaptureTool
from ui.tools.who_lookup_tool import WhoLookupTool

# TODO: Add tool protocol
_AnyTool = Union[RaidLogCaptureTool, WhoLookupTool]


class RaidToolsPage(QWidget):
    """Configuration and instructions for Raid Tools."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")

        scroll, vl = _make_page_scroll()
        _page_header(vl, "Raid Tools", "Tools and utilities to help manage raids.")

        self._tools: list[_AnyTool] = [RaidLogCaptureTool(), WhoLookupTool()]
        for i, tool in enumerate(self._tools):
            vl.addWidget(tool)
            if i > 0:
                tool.card.set_expanded(False, animated=False)
            tool.card.expanded_changed.connect(
                lambda expanded, t=tool: self._on_tool_expanded(t, expanded)
            )

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_tool_expanded(self, source: _AnyTool, expanded: bool) -> None:
        if not expanded:
            return
        for tool in self._tools:
            if tool is not source:
                tool.card.set_expanded(False)
