"""OverlayPreviewPanel — simulated live EverQuest HUD preview.

Driven by MockDataProvider signals; renders DPS/healing bars,
a combat log feed, and raid countdown timers using QPainter for
full styling control.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from services.mock_data_provider import MockDataProvider, MockSnapshot
from theme.colors import (
    ACCENT_CYAN_RGB,
    ACCENT_GOLD_RGB,
    CARD_BG_RGB,
    ERROR_RGB,
    NAVY_BG_RGB,
    SUCCESS_RGB,
    TEXT_PRIMARY_RGB,
    TEXT_SECONDARY_RGB,
    WARNING_RGB,
)

_BG = QColor(*NAVY_BG_RGB, 230)
_BORDER = QColor(*ACCENT_CYAN_RGB, 70)
_DIVIDER = QColor(*ACCENT_CYAN_RGB, 28)
_SEG_TITLE = QColor(*ACCENT_CYAN_RGB, 200)
_TEXT = QColor(*TEXT_PRIMARY_RGB)
_TEXT_DIM = QColor(*TEXT_SECONDARY_RGB)
_GOLD = QColor(*ACCENT_GOLD_RGB, 220)
_DPS_BAR = QColor(*ACCENT_CYAN_RGB, 160)
_HEAL_BAR = QColor(*SUCCESS_RGB, 160)
_WARN = QColor(*WARNING_RGB, 200)
_DANGER = QColor(*ERROR_RGB, 200)

_LOG_COLORS = {
    "normal": QColor(*TEXT_SECONDARY_RGB),
    "crit": QColor(*ACCENT_GOLD_RGB, 220),
    "death": QColor(*ERROR_RGB, 200),
    "buff": QColor(*SUCCESS_RGB, 200),
    "debuff": QColor(*WARNING_RGB, 200),
}

_FONT_TINY = QFont("Segoe UI", 8)
_FONT_SMALL = QFont("Segoe UI", 9)
_FONT_NORM = QFont("Segoe UI", 10)
_FONT_BOLD = QFont("Segoe UI", 10)
_FONT_BOLD.setBold(True)
_FONT_TITLE = QFont("Orbitron", 9)
_FONT_TITLE.setBold(True)
_FONT_TITLE.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)

_PAD = 10
_BAR_H = 16
_BAR_GAP = 5
_CORNER = 8

_TIMER_COLORS = {
    "normal": QColor(*ACCENT_CYAN_RGB, 200),
    "warning": QColor(*WARNING_RGB, 200),
    "danger": QColor(*ERROR_RGB, 220),
}


def _fmt_dps(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _fmt_time(s: int) -> str:
    return f"{s // 60:02d}:{s % 60:02d}"


class OverlayPreviewPanel(QWidget):
    """Custom-painted widget that simulates a live EQ HUD overlay."""

    def __init__(
        self,
        provider: MockDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._snapshot: Optional[MockSnapshot] = None
        self._provider = provider

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setObjectName("OverlayPreviewPanel")
        self.setMinimumHeight(420)

        # Seed with initial data
        self._snapshot = provider.get_initial_snapshot()
        provider.data_updated.connect(self._on_update)

    # ── Slot ───────────────────────────────────────────────────────────────────

    def _on_update(self, snapshot: MockSnapshot) -> None:
        self._snapshot = snapshot
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        if self._snapshot is None:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        self._draw_bg(p, rect)

        y = rect.top() + _PAD
        y = self._draw_header(p, rect, y)
        y = self._draw_dps_section(p, rect, y)
        y = self._draw_divider(p, rect, y)
        y = self._draw_heal_section(p, rect, y)
        y = self._draw_divider(p, rect, y)
        y = self._draw_log_section(p, rect, y)
        y = self._draw_divider(p, rect, y)
        self._draw_timer_section(p, rect, y)

        p.end()

    def _draw_bg(self, p: QPainter, rect) -> None:  # noqa: ANN001
        path = QPainterPath()
        path.addRoundedRect(rect, _CORNER, _CORNER)
        p.fillPath(path, _BG)
        p.setPen(QPen(_BORDER, 1))
        p.drawPath(path)

    def _draw_header(self, p: QPainter, rect, y: int) -> int:
        p.setFont(_FONT_TITLE)
        p.setPen(_SEG_TITLE)
        snap = self._snapshot
        title = f"⊹ {snap.fight_name.upper()}  ·  T+{_fmt_time(snap.fight_duration)}"
        p.drawText(rect.left() + _PAD, y + 12, title)

        # LIVE badge
        badge_text = "● LIVE"
        badge_rect_x = rect.right() - 58
        badge_rect = __import__("PySide6.QtCore", fromlist=["QRect"]).QRect(
            badge_rect_x, y, 52, 18
        )
        p.setBrush(QColor(*SUCCESS_RGB, 30))
        p.setPen(QPen(QColor(*SUCCESS_RGB, 140), 1))
        p.drawRoundedRect(badge_rect, 4, 4)
        p.setFont(_FONT_TINY)
        p.setPen(QColor(*SUCCESS_RGB, 220))
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        return y + 24

    def _draw_section_title(self, p: QPainter, rect, y: int, title: str, icon: str) -> int:
        p.setFont(_FONT_SMALL)
        p.setPen(_TEXT_DIM)
        p.drawText(rect.left() + _PAD, y + 11, f"{icon}  {title}")
        return y + 18

    def _draw_dps_section(self, p: QPainter, rect, y: int) -> int:
        y = self._draw_section_title(p, rect, y, "DPS METER", "⚔")
        snap = self._snapshot
        for entry in snap.dps_entries[:5]:
            y = self._draw_bar(
                p, rect, y, entry.name, entry.class_abbr,
                entry.percent, _fmt_dps(entry.dps) + " dps", _DPS_BAR
            )
        return y + 4

    def _draw_heal_section(self, p: QPainter, rect, y: int) -> int:
        y = self._draw_section_title(p, rect, y, "HEALING", "✚")
        snap = self._snapshot
        for entry in snap.healer_entries:
            y = self._draw_bar(
                p, rect, y, entry.name, entry.class_abbr,
                entry.percent, _fmt_dps(entry.hps) + " hps", _HEAL_BAR
            )
        return y + 4

    def _draw_bar(
        self, p: QPainter, rect, y: int,
        name: str, cls: str, pct: float, value_str: str,
        bar_color: QColor
    ) -> int:
        bar_x = rect.left() + _PAD
        bar_w = rect.width() - _PAD * 2
        bar_y = y + 2

        # Track
        p.setBrush(QColor(*CARD_BG_RGB, 120))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, _BAR_H, 3, 3)

        # Fill with gradient
        fill_w = max(4, int(bar_w * pct))
        grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
        fill_dim = QColor(bar_color)
        fill_dim.setAlpha(120)
        grad.setColorAt(0, fill_dim)
        grad.setColorAt(1, bar_color)
        p.setBrush(grad)
        p.drawRoundedRect(bar_x, bar_y, fill_w, _BAR_H, 3, 3)

        # Name + class
        p.setFont(_FONT_SMALL)
        p.setPen(_TEXT)
        label = f"[{cls}] {name}"
        p.drawText(bar_x + 6, bar_y + _BAR_H - 3, label)

        # Value
        p.setPen(_GOLD)
        p.drawText(
            bar_x, bar_y, bar_w - 4, _BAR_H,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            value_str
        )

        return y + _BAR_H + _BAR_GAP

    def _draw_log_section(self, p: QPainter, rect, y: int) -> int:
        y = self._draw_section_title(p, rect, y, "COMBAT LOG", "📋")
        snap = self._snapshot
        lines = snap.combat_log[-6:]
        for line in lines:
            color = _LOG_COLORS.get(line.color_key, _TEXT_DIM)
            p.setFont(_FONT_TINY)
            p.setPen(color)
            p.drawText(rect.left() + _PAD + 4, y + 10, line.text[:70])
            y += 13
        return y + 4

    def _draw_timer_section(self, p: QPainter, rect, y: int) -> int:
        y = self._draw_section_title(p, rect, y, "RAID TIMERS", "⏱")
        snap = self._snapshot
        bar_x = rect.left() + _PAD
        bar_w = rect.width() - _PAD * 2

        for timer in snap.raid_timers:
            color = _TIMER_COLORS.get(timer.color_key, _TIMER_COLORS["normal"])

            # Timer bar track
            p.setBrush(QColor(*CARD_BG_RGB, 100))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bar_x, y + 2, bar_w, _BAR_H - 2, 3, 3)

            # Fill
            ratio = timer.seconds_remaining / timer.max_seconds if timer.max_seconds else 0
            fill_w = max(4, int(bar_w * ratio))
            fill = QColor(color)
            fill.setAlpha(100)
            p.setBrush(fill)
            p.drawRoundedRect(bar_x, y + 2, fill_w, _BAR_H - 2, 3, 3)

            # Labels
            p.setFont(_FONT_SMALL)
            p.setPen(_TEXT_DIM)
            p.drawText(bar_x + 6, y + _BAR_H - 3, timer.label)
            p.setPen(color)
            p.drawText(
                bar_x, y + 2, bar_w - 4, _BAR_H - 2,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                _fmt_time(timer.seconds_remaining)
            )
            y += _BAR_H + _BAR_GAP

        return y

    def _draw_divider(self, p: QPainter, rect, y: int) -> int:
        p.setPen(QPen(_DIVIDER, 1))
        x1 = rect.left() + _PAD
        x2 = rect.right() - _PAD
        p.drawLine(x1, y + 4, x2, y + 4)
        return y + 12

    # ── Size hint ─────────────────────────────────────────────────────────────

    def sizeHint(self):  # noqa: ANN201
        from PySide6.QtCore import QSize
        return QSize(340, 460)

