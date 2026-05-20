"""Parsing, Notifications, Appearance, Profiles, Advanced, and About pages."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.settings_service import SettingsService
from theme.theme_manager import FONT_SIZE_OPTIONS, ThemeManager
from ui.cards.settings_card import SettingsCard
from ui.widgets.status_widgets import SectionHeader
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_widgets import ThemedComboBox, ThemedLineEdit, ThemedTable
from ui.widgets.toggle_switch import ToggleSwitch


# ── Shared helpers ─────────────────────────────────────────────────────────────


def _make_page_scroll() -> tuple[QScrollArea, QVBoxLayout]:
    """Return (scroll_area, inner_vbox) for a standard settings page."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    inner = QWidget()
    inner.setObjectName("PageWrapper")
    vl = QVBoxLayout(inner)
    vl.setContentsMargins(24, 20, 24, 20)
    vl.setSpacing(16)
    scroll.setWidget(inner)
    return scroll, vl


def _toggle_row(label: str, checked: bool = False) -> tuple[QHBoxLayout, ToggleSwitch]:
    hl = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    tog = ToggleSwitch(checked=checked)
    hl.addWidget(lbl)
    hl.addWidget(tog)
    return hl, tog


def _page_header(vl: QVBoxLayout, title: str, subtitle: str) -> None:
    t = QLabel(title)
    t.setObjectName("PageTitle")
    vl.addWidget(t)
    s = QLabel(subtitle)
    s.setObjectName("PageSubtitle")
    vl.addWidget(s)
    vl.addSpacing(4)


# ── Parsing Page ───────────────────────────────────────────────────────────────


class ParsingPage(QWidget):
    """Log parser configuration page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Parsing", "Configure parser windows and data collection.")

        # DPS window card
        dps_card = SettingsCard("DPS Window", "Time window used to calculate DPS.")
        combo = ThemedComboBox()
        for s in ["30 seconds", "60 seconds", "120 seconds", "300 seconds", "Fight total"]:
            combo.addItem(s)
        combo.setCurrentIndex(1)
        dps_card.add_widget(combo)
        vl.addWidget(dps_card)

        # Display options card
        disp_card = SettingsCard("Display Options", "What to show in the DPS overlay.")
        for label, checked in [
            ("Show pets separately", True),
            ("Show healing output", True),
            ("Show total damage column", True),
            ("Highlight critical hits", False),
        ]:
            row, _ = _toggle_row(label, checked)
            disp_card.add_layout(row)
        vl.addWidget(disp_card)

        vl.addWidget(ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY))
        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ── Notifications Page ────────────────────────────────────────────────────────


class NotificationsPage(QWidget):
    """Notification settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Notifications", "Alerts, sounds, and event triggers.")

        alert_card = SettingsCard("Alert Types", "Choose which events trigger notifications.")
        for label, checked in [
            ("Raid timer warnings", True),
            ("Named NPC spawn alerts", True),
            ("Low HP threshold alerts", False),
            ("Emote/text triggers", True),
            ("Spell resist events", False),
        ]:
            row, _ = _toggle_row(label, checked)
            alert_card.add_layout(row)
        vl.addWidget(alert_card)

        sound_card = SettingsCard("Sound", "Audio notifications.")
        row_sound, _ = _toggle_row("Enable sound alerts", True)
        sound_card.add_layout(row_sound)
        vl.addWidget(sound_card)

        vl.addWidget(ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY))
        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ── Appearance Page ───────────────────────────────────────────────────────────


class AppearancePage(QWidget):
    """Visual appearance and font-scale settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = SettingsService.instance()
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Appearance", "Themes, fonts, and visual customisation.")

        # ── Font scale card ───────────────────────────────────────────────────
        font_card = SettingsCard(
            "Font Scale",
            "Scales all UI text proportionally. Takes effect immediately.",
        )
        vl.addWidget(font_card)

        # Size selector row
        size_row = QHBoxLayout()
        size_lbl = QLabel("Base font size:")
        size_lbl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        size_row.addWidget(size_lbl)

        self._font_combo = ThemedComboBox()
        for label, pt in FONT_SIZE_OPTIONS:
            self._font_combo.addItem(label, userData=pt)
        # Select the currently active size
        current_pt = ThemeManager.instance().current_font_pt
        for i, (_, pt) in enumerate(FONT_SIZE_OPTIONS):
            if pt == current_pt:
                self._font_combo.setCurrentIndex(i)
                break
        size_row.addWidget(self._font_combo, stretch=1)
        font_card.add_layout(size_row)

        # Preview label so the change is immediately visible
        self._preview_lbl = QLabel("The quick brown fox jumps over the lazy dog — 0123456789")
        self._preview_lbl.setWordWrap(True)
        self._preview_lbl.setStyleSheet("color: #93A4C3; padding-top: 6px;")
        font_card.add_widget(self._preview_lbl)

        apply_font_btn = ThemedButton("Apply Font Scale", ThemedButton.VARIANT_PRIMARY)
        apply_font_btn.setFixedWidth(180)
        apply_font_btn.clicked.connect(self._apply_font_scale)
        font_card.add_widget(apply_font_btn)

        # ── Theme card ────────────────────────────────────────────────────────
        theme_card = SettingsCard("Theme", "UI colour scheme (future releases).")
        combo = ThemedComboBox()
        for t in ["Cosmic (Default)", "Deep Space", "Amber Alert", "Frost"]:
            combo.addItem(t)
        combo.setEnabled(False)  # placeholder — themes not yet implemented
        theme_card.add_widget(combo)
        vl.addWidget(theme_card)

        # ── Typography card ───────────────────────────────────────────────────
        typo_card = SettingsCard("Typography", "Additional font preferences.")
        for label, checked in [
            ("Use Orbitron for headings", True),
            ("High-contrast mode", False),
        ]:
            row, _ = _toggle_row(label, checked)
            typo_card.add_layout(row)
        vl.addWidget(typo_card)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _apply_font_scale(self) -> None:
        """Read the combo selection, apply scale, and persist to settings."""
        pt: int = self._font_combo.currentData()
        app = QApplication.instance()
        if app:
            ThemeManager.instance().set_font_scale(app, pt)
        self._svc.settings.appearance.font_size = pt
        self._svc.save()


# ── Profiles Page ─────────────────────────────────────────────────────────────


class ProfilesPage(QWidget):
    """Character / server profile manager."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Profiles", "Manage character and server profiles.")

        table_card = SettingsCard("Saved Profiles")
        table = ThemedTable(0, 3)
        table.set_column_headers(["Profile Name", "Character", "Server"])
        table.setFixedHeight(180)
        for row_data in [
            ("Default", "—", "—"),
            ("Warrior Main", "Zandakon", "Bristlebane"),
            ("Cleric Alt", "Sylvindra", "Bristlebane"),
        ]:
            r = table.rowCount()
            table.insertRow(r)
            for c, val in enumerate(row_data):
                from PySide6.QtWidgets import QTableWidgetItem
                table.setItem(r, c, QTableWidgetItem(val))
        table_card.add_widget(table)
        vl.addWidget(table_card)

        btn_row = QHBoxLayout()
        btn_row.addWidget(ThemedButton("New Profile", ThemedButton.VARIANT_SECONDARY))
        btn_row.addWidget(ThemedButton("Delete", ThemedButton.VARIANT_DANGER))
        btn_row.addStretch()
        vl.addLayout(btn_row)
        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ── Advanced Page ─────────────────────────────────────────────────────────────


class AdvancedPage(QWidget):
    """Advanced / developer settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Advanced", "Developer and power-user settings.")

        perf_card = SettingsCard("Performance", "Tuning for long-session stability.")
        for label, checked in [
            ("Enable debug logging", False),
            ("Hardware-accelerated rendering", True),
            ("Reduce update rate in background", True),
        ]:
            row, _ = _toggle_row(label, checked)
            perf_card.add_layout(row)
        vl.addWidget(perf_card)

        danger_card = SettingsCard("⚠ Danger Zone", "Irreversible operations.")
        reset_btn = ThemedButton("Reset All Settings", ThemedButton.VARIANT_DANGER)
        danger_card.add_widget(reset_btn)
        vl.addWidget(danger_card)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ── About Page ────────────────────────────────────────────────────────────────


class AboutPage(QWidget):
    """About / version information page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()

        title = QLabel("GRAVITY NEXUS")
        title.setObjectName("AppTitleLabel")
        title.setStyleSheet(
            "font-family: 'Orbitron', 'Segoe UI'; font-size: 26px;"
            "color: #D8B36A; letter-spacing: 4px;"
        )
        vl.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        for text, style in [
            ("EverQuest Overlay Parser — UI Foundation", "color: #93A4C3; font-size: 13px;"),
            ("Version 1.0.0 — Built with PySide6", "color: #93A4C3; font-size: 12px;"),
            ("", ""),
            ("© 2026 Gravity Nexus Contributors", "color: rgba(147,164,195,80); font-size: 11px;"),
        ]:
            if not text:
                vl.addSpacing(8)
                continue
            lbl = QLabel(text)
            lbl.setStyleSheet(style)
            vl.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        about_card = SettingsCard("About This Build")
        about_text = QLabel(
            "Gravity Nexus is a modular real-time log parser and overlay system "
            "for EverQuest. This release contains the UI foundation and theming "
            "system only. Parser logic, WebSocket services, and plugin overlays "
            "will be added in future releases."
        )
        about_text.setWordWrap(True)
        about_text.setProperty("secondary", "true")
        about_card.add_widget(about_text)
        vl.addWidget(about_card)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

