"""Parsing, Notifications, Appearance, Advanced, and About pages."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.registry import registry
from services.protocols import IAuthService, IGravityBotService, ISettingsService, ILogParserService
from theme.spec import ColorRole, FontRole, FontSize
from theme.theme_manager import FONT_SIZE_OPTIONS, ThemeManager
from ui.cards.settings_card import SettingsCard
from ui.sidebar import _StatusDot
from ui.widgets.status_widgets import StatusIndicator
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.themed_widgets import ThemedComboBox
from ui.widgets.toggle_switch import ToggleSwitch
from _version import __version__
from feature_flags import feature_enabled


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
        self._svc = registry.get(ISettingsService)
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
        self._preview_lbl = ThemedLabel(
            "The quick brown fox jumps over the lazy dog — 0123456789",
            color_role=ColorRole.TEXT_SECONDARY,
            word_wrap=True,
        )
        font_card.add_widget(self._preview_lbl)

        btn_row = QHBoxLayout()
        apply_font_btn = ThemedButton("Apply Font Scale", ThemedButton.VARIANT_PRIMARY)
        apply_font_btn.clicked.connect(self._apply_font_scale)
        btn_row.addWidget(apply_font_btn)
        btn_row.addStretch()
        font_card.add_layout(btn_row)

        # ── Theme card ────────────────────────────────────────────────────────
        if feature_enabled("theme_selector", self._svc.settings):
            theme_card = SettingsCard("Theme", "UI colour scheme (future releases).")
            combo = ThemedComboBox()
            for t in ["Cosmic (Default)", "Deep Space", "Amber Alert", "Frost"]:
                combo.addItem(t)
            combo.setEnabled(False)  # placeholder — themes not yet implemented
            theme_card.add_widget(combo)
            vl.addWidget(theme_card)

        # ── Typography card ───────────────────────────────────────────────────
        if feature_enabled("typography_options", self._svc.settings):
            typo_card = SettingsCard("Typography", "Additional font preferences.")
            orbitron_row, self._orbitron_toggle = _toggle_row(
                "Use Orbitron for headings",
                self._svc.settings.appearance.use_orbitron_headings,
            )
            typo_card.add_layout(orbitron_row)
            contrast_row, _ = _toggle_row("High-contrast mode", False)
            typo_card.add_layout(contrast_row)
            vl.addWidget(typo_card)
            self._orbitron_toggle.toggled.connect(self._on_orbitron_toggled)

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

    def _on_orbitron_toggled(self, enabled: bool) -> None:
        self._svc.settings.appearance.use_orbitron_headings = enabled
        self._svc.save()
        app = QApplication.instance()
        if app:
            ThemeManager.instance().apply_orbitron_headings(app, enabled)


# ── Advanced Page ─────────────────────────────────────────────────────────────


class AdvancedPage(QWidget):
    """Advanced / developer settings page."""

    start_parser_requested = Signal()
    stop_parser_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._parser_running = False
        self._svc = registry.get(ISettingsService)
        self._bot_svc = registry.get(IGravityBotService)
        self._auth = registry.get(IAuthService)
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Advanced", "Developer and power-user settings.")

        # ── Card: Bot Connection ──────────────────────────────────────────────
        conn_card = SettingsCard(
            "Bot Connection",
            "WebSocket connection to the Gravity Bot server.",
        )
        vl.addWidget(conn_card)

        account_row = QHBoxLayout()
        account_lbl = ThemedLabel("Signed in as:", color_role=ColorRole.TEXT_MUTED)
        account_lbl.setFixedWidth(96)
        self._account_display = ThemedLabel("", color_role=ColorRole.TEXT_PRIMARY)
        account_row.addWidget(account_lbl)
        account_row.addWidget(self._account_display)
        account_row.addStretch()
        conn_card.add_layout(account_row)

        status_row = QHBoxLayout()
        self._conn_status = StatusIndicator("Disconnected", "offline")
        status_row.addWidget(self._conn_status)
        status_row.addStretch()
        conn_card.add_layout(status_row)

        btn_row = QHBoxLayout()
        self._connect_btn = ThemedButton("Connect", ThemedButton.VARIANT_PRIMARY)
        self._disconnect_btn = ThemedButton("Disconnect", ThemedButton.VARIANT_DANGER)
        self._disconnect_btn.setEnabled(False)
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        btn_row.addWidget(self._connect_btn)
        btn_row.addWidget(self._disconnect_btn)
        btn_row.addStretch()
        conn_card.add_layout(btn_row)

        # ── Card: Parser status ───────────────────────────────────────────────
        parser_card = SettingsCard(
            "Parser",
            "View the current status of the parser and start or stop it.",
        )
        self._build_parser_status(parser_card)
        vl.addWidget(parser_card)

        perf_card = SettingsCard("Performance", "Tuning for long-session stability.")

        # Debug logging toggle — wired up to the Python root logger
        debug_row, self._debug_toggle = _toggle_row("Enable debug logging", False)
        perf_card.add_layout(debug_row)
        self._debug_toggle.toggled.connect(self._on_debug_logging_toggled)

        # Hardware-accelerated rendering toggle
        hw_row, self._hw_toggle = _toggle_row("Hardware-accelerated rendering", True)
        perf_card.add_layout(hw_row)
        self._hw_toggle.toggled.connect(self._on_hw_accel_toggled)

        self._hw_restart_lbl = ThemedLabel(
            "⚠  Rendering backend change takes effect after restart.",
            font_size=FontSize.SMALL,
            color_role=ColorRole.ACCENT_ALT,
        )
        self._hw_restart_lbl.setVisible(False)
        perf_card.add_widget(self._hw_restart_lbl)

        # Reduce update rate in background toggle
        self._reduce_rate_toggle: Optional[ToggleSwitch] = None
        if feature_enabled("reduce_update_rate_in_background", self._svc.settings):
            reduce_row, self._reduce_rate_toggle = _toggle_row("Reduce update rate in background", True)
            perf_card.add_layout(reduce_row)
            self._reduce_rate_toggle.toggled.connect(self._on_reduce_rate_toggled)
        vl.addWidget(perf_card)

        danger_card = SettingsCard("⚠ Danger Zone", "Irreversible operations.")
        reset_btn = ThemedButton("Reset All Settings", ThemedButton.VARIANT_DANGER)
        reset_btn.clicked.connect(self._on_reset_settings)
        danger_card.add_widget(reset_btn)
        vl.addWidget(danger_card)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Load persisted values (no animation on initial load)
        self._debug_toggle.set_checked(
            self._svc.settings.general.debug_logging, animated=False
        )
        self._hw_toggle.set_checked(
            self._svc.settings.general.hardware_accelerated, animated=False
        )
        if self._reduce_rate_toggle is not None:
            self._reduce_rate_toggle.set_checked(
                self._svc.settings.general.reduce_update_rate_in_background, animated=False
            )

        username = self._auth.username
        self._account_display.setText(username if username else "Not signed in")
        self._on_connected_changed(self._bot_svc.is_connected)
        self._bot_svc.connected_changed.connect(self._on_connected_changed)

    def _build_parser_status(self, card: SettingsCard) -> None:
        hl_status = QHBoxLayout()
        status_lbl = QLabel("Status")
        status_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hl_status.addWidget(status_lbl)
        self._parser_status_text = QLabel("Stopped")
        self._parser_status_text.setObjectName("StatusBarText")
        hl_status.addWidget(self._parser_status_text)
        self._parser_status_dot = _StatusDot("offline")
        hl_status.addWidget(self._parser_status_dot)
        card.add_layout(hl_status)

        hl_char = QHBoxLayout()
        char_lbl = QLabel("Character")
        char_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hl_char.addWidget(char_lbl)
        self._parser_character_text = QLabel("—")
        self._parser_character_text.setObjectName("StatusBarText")
        hl_char.addWidget(self._parser_character_text)
        card.add_layout(hl_char)

        self._parser_btn = ThemedButton("▶  Start Parser", ThemedButton.VARIANT_PRIMARY)
        self._parser_btn.clicked.connect(self._on_parser_btn_clicked)
        card.add_widget(self._parser_btn)

    def _on_parser_btn_clicked(self) -> None:
        if self._parser_running:
            self.stop_parser_requested.emit()
        else:
            self.start_parser_requested.emit()

    def set_parser_status(self, running: bool, log_name: str = "") -> None:
        self._parser_running = running
        if running:
            self._parser_status_dot.set_status("online")
            self._parser_status_text.setText("Running")
            self._parser_character_text.setText(log_name or "—")
            self._parser_btn.setText("■  Stop Parser")
            self._parser_btn.setProperty("variant", "danger")
        else:
            self._parser_status_dot.set_status("offline")
            self._parser_status_text.setText("Stopped")
            self._parser_character_text.setText("—")
            self._parser_btn.setText("▶  Start Parser")
            self._parser_btn.setProperty("variant", "primary")
        self._parser_btn.style().unpolish(self._parser_btn)
        self._parser_btn.style().polish(self._parser_btn)

    def _on_connect(self) -> None:
        self._conn_status.set_status("connecting", "Connecting…")
        self._connect_btn.setEnabled(False)
        self._bot_svc.connect_bot()

    def _on_disconnect(self) -> None:
        self._bot_svc.disconnect_bot()

    def _on_connected_changed(self, connected: bool) -> None:
        if connected:
            self._conn_status.set_status("online", "Connected")
            self._connect_btn.setEnabled(False)
            self._disconnect_btn.setEnabled(True)
        else:
            self._conn_status.set_status("offline", "Disconnected")
            self._connect_btn.setEnabled(True)
            self._disconnect_btn.setEnabled(False)

    def _on_debug_logging_toggled(self, enabled: bool) -> None:
        """Apply the new debug-logging level, persist the setting, and emit a log message."""
        root = logging.getLogger()
        if enabled:
            root.setLevel(logging.DEBUG)
            # Emit an info banner so the change is immediately visible in any log output
            root.info("Debug logging ENABLED — all logger messages will now be captured.")
            # Re-emit every existing logger's effective level so nothing is silently suppressed
            for name, logger in logging.Logger.manager.loggerDict.items():
                if isinstance(logger, logging.Logger):
                    logger.debug("Logger '%s' now at effective level DEBUG", name)
        else:
            root.setLevel(logging.INFO)
            root.info("Debug logging DISABLED — reverted to INFO level.")

        self._svc.settings.general.debug_logging = enabled
        self._svc.save()

    def _on_hw_accel_toggled(self, enabled: bool) -> None:
        """Persist the hardware-acceleration preference and show a restart notice."""
        self._svc.settings.general.hardware_accelerated = enabled
        self._svc.save()
        # Show the restart warning only when the value differs from what is currently active
        from PySide6.QtWidgets import QApplication as _QApp  # noqa: PLC0415
        currently_hw = not _QApp.testAttribute(
            Qt.ApplicationAttribute.AA_UseSoftwareOpenGL
        )
        self._hw_restart_lbl.setVisible(enabled != currently_hw)

    def _on_reduce_rate_toggled(self, enabled: bool) -> None:
        """Persist the reduce-update-rate-in-background preference."""
        self._svc.settings.general.reduce_update_rate_in_background = enabled
        self._svc.save()

    def _on_reset_settings(self) -> None:
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415
        from PySide6.QtCore import QSettings       # noqa: PLC0415
        reply = QMessageBox.question(
            self,
            "Reset All Settings",
            "All settings will be cleared and the app will close.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QSettings("GravityNexus", "GravityNexus").clear()
            QApplication.quit()


# ── About Page ────────────────────────────────────────────────────────────────


class AboutPage(QWidget):
    """About / version information page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        scroll, vl = _make_page_scroll()

        title = ThemedLabel(
            "GRAVITY NEXUS",
            font_size=FontSize.HEADING,
            color_role=ColorRole.ACCENT_ALT,
            font_role=FontRole.DISPLAY,
        )
        title.setObjectName("AboutTitle")
        vl.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        _link_color = ThemeManager.instance().get_color(ColorRole.TEXT_PRIMARY)
        about_card = SettingsCard("About")
        about_text = QLabel(
            "Gravity Nexus is a set of tools and overlays for interacting with Gravity's discord bot and raid website. "
            "<ul>"
            f"<li><a href='https://gravityp99.com/' style='color: {_link_color};'>Guild Website</a></li>"
            f"<li><a href='https://github.com/GravityGuild/gravity_nexus' style='color: {_link_color};'>Gravity Nexus Github</a></li>"
            f"<li><a href='https://github.com/GravityGuild/gravity_nexus/releases' style='color: {_link_color};'>Releases</a></li>"
            f"<li><a href='https://github.com/GravityGuild/gravity_nexus/releases' style='color: {_link_color};'>Changelog</a></li>"
            "</ul>"
        )
        about_text.setOpenExternalLinks(True)
        about_text.setWordWrap(True)
        about_text.setProperty("secondary", "true")
        about_card.add_widget(about_text)
        vl.addWidget(about_card)

        vl.addStretch()

        ver_lbl = ThemedLabel(
            f"Version {__version__}",
            font_size=FontSize.SMALL,
            color_role=ColorRole.TEXT_SECONDARY,
        )
        vl.addWidget(ver_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
