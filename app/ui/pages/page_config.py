"""PageConfig — single-record description of a navigable settings page."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from ui.widgets.icon_label import AppIcon


@dataclass
class PageConfig:
    label: str
    icon: "AppIcon"
    factory: "Callable[[], QWidget]"
    feature_flag: str | None = None
    dev_only: bool = False
