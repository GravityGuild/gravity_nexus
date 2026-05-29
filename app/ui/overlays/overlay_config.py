from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

from ui.widgets.popup_search_bar import DEFAULT_SEARCH_BAR_WIDTH


class HAlign(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VAlign(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


@dataclass(frozen=True)
class Offset:
    value: float
    unit: Literal["px", "pct"] = "px"

    @staticmethod
    def px(n: float) -> "Offset":
        return Offset(n, "px")

    @staticmethod
    def pct(n: float | int) -> "Offset":
        return Offset(float(n / 100), "pct")


@dataclass(frozen=True)
class OverlayConfig:
    key: str                        # matches OverlaySettings.positions key
    label: str                      # shown in PositioningOverlay title bar
    default_size: tuple[int, int]   # (width, height) for placeholder
    show_body: bool = True          # False hides drag instructions in the positioning placeholder
    feature_flag: Optional[str] = None  # skip this overlay if the named flag is off
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    h_align: HAlign = HAlign.CENTER
    v_align: VAlign = VAlign.CENTER
    h_offset: Offset = field(default_factory=lambda: Offset.px(0))
    v_offset: Offset = field(default_factory=lambda: Offset.px(0))


def resolve_default_position(
    cfg: OverlayConfig,
    overlay_w: int,
    overlay_h: int,
    screen,
) -> tuple[int, int]:
    """Compute default (x, y) from cfg alignment/offset and screen geometry.

    ``screen`` is any QRect-like object (.left, .right, .top, .bottom,
    .center, .width, .height).
    """
    def _off(offset: Offset, dim: int) -> int:
        return int(offset.value if offset.unit == "px" else dim * offset.value)

    h_off = _off(cfg.h_offset, screen.width())
    v_off = _off(cfg.v_offset, screen.height())

    if cfg.h_align == HAlign.LEFT:
        x = screen.left() + h_off
    elif cfg.h_align == HAlign.RIGHT:
        x = screen.right() - overlay_w - h_off
    else:
        x = screen.center().x() - overlay_w // 2 + h_off

    if cfg.v_align == VAlign.TOP:
        y = screen.top() + v_off
    elif cfg.v_align == VAlign.BOTTOM:
        y = screen.bottom() - overlay_h - v_off
    else:
        y = screen.center().y() - overlay_h // 2 + v_off

    return x, y


OVERLAY_CONFIGS: list[OverlayConfig] = [
    OverlayConfig(
        "raid_submit", "Raid Submit", (300, 450),
        h_align=HAlign.RIGHT,  v_align=VAlign.CENTER,
        h_offset=Offset.pct(10), v_offset=Offset.pct(0),
    ),
    OverlayConfig(
        "who_lookup", "Who Lookup", (325, 400),
        h_align=HAlign.LEFT,   v_align=VAlign.CENTER,
        h_offset=Offset.pct(15), v_offset=Offset.pct(0),
    ),
    OverlayConfig(
        "toolbar", "Quick Toolbar", (150, 80),
        feature_flag="quick_toolbar",
        h_align=HAlign.RIGHT,  v_align=VAlign.TOP,
        h_offset=Offset.pct(2), v_offset=Offset.pct(2),
    ),
    OverlayConfig(
        "search_bar", "Search Bar", (DEFAULT_SEARCH_BAR_WIDTH, 54),
        show_body=False,
        min_width=350,
        h_align=HAlign.CENTER, v_align=VAlign.TOP,
        h_offset=Offset.px(0), v_offset=Offset.pct(30),
    ),
]

OVERLAY_CONFIG_MAP: dict[str, OverlayConfig] = {cfg.key: cfg for cfg in OVERLAY_CONFIGS}
