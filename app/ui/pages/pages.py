"""Parsing, Notifications, Appearance, Advanced, and About pages."""
from __future__ import annotations

import logging
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

from core.registry import registry
from services.protocols import ISettingsService, ILogParserService
from theme.spec import ColorRole, FontRole, FontSize
from theme.theme_manager import FONT_SIZE_OPTIONS, ThemeManager
from ui.cards.settings_card import SettingsCard
from ui.widgets.themed_button import ThemedButton
from ui.widgets.themed_label import ThemedLabel
from ui.widgets.themed_widgets import ThemedComboBox
from ui.widgets.toggle_switch import ToggleSwitch
from _version import __version__


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
    """Log parser configuration page.

    Toggles are generated automatically from the built-in matcher list exposed
    by ``ILogParserService.builtin_matchers``.  To add a new matcher to this
    page, set ``DISPLAY_NAME``, ``DESCRIPTION``, and ``MATCHER_KEY`` on the
    matcher class and register it in ``LogParserService.__init__``.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        self._parser_svc = registry.get(ILogParserService)

        scroll, vl = _make_page_scroll()
        _page_header(vl, "Parsing", "Enable or disable individual log-event handlers.")

        # ── Card: active handlers ─────────────────────────────────────────────
        handlers_card = SettingsCard(
            "Active Handlers",
            "Each handler listens for a specific type of log event. "
            "Disabled handlers are skipped entirely — no CPU cost.",
        )
        vl.addWidget(handlers_card)

        # Track (matcher, toggle) pairs so Save can iterate them
        self._matcher_toggles: list[tuple] = []

        matchers = self._parser_svc.builtin_matchers
        if matchers:
            for matcher in matchers:
                # Look up persisted state; fall back to ENABLED_BY_DEFAULT
                saved = self._svc.settings.parsing.enabled_matchers.get(
                    matcher.MATCHER_KEY, matcher.ENABLED_BY_DEFAULT
                )
                row, tog = _toggle_row(matcher.DISPLAY_NAME, checked=saved)
                if matcher.DESCRIPTION:
                    # Wrap in a vertical block: toggle row + description label
                    block = QVBoxLayout()
                    block.setSpacing(2)
                    block.addLayout(row)
                    desc = ThemedLabel(
                        matcher.DESCRIPTION,
                        font_size=FontSize.SMALL,
                        color_role=ColorRole.TEXT_MUTED,
                        word_wrap=True,
                    )
                    block.addWidget(desc)
                    handlers_card.add_layout(block)
                else:
                    handlers_card.add_layout(row)

                # Apply the persisted enabled state immediately
                matcher.set_enabled(saved)
                self._matcher_toggles.append((matcher, tog))
        else:
            no_matchers = QLabel("No handlers are registered.")
            no_matchers.setProperty("secondary", "true")
            handlers_card.add_widget(no_matchers)

        # ── Save button ───────────────────────────────────────────────────────
        save_btn = ThemedButton("Save Changes", ThemedButton.VARIANT_PRIMARY)
        save_btn.clicked.connect(self._save)
        vl.addWidget(save_btn)
        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _save(self) -> None:
        enabled_map = self._svc.settings.parsing.enabled_matchers
        for matcher, tog in self._matcher_toggles:
            state = tog.is_checked()
            enabled_map[matcher.MATCHER_KEY] = state
            matcher.set_enabled(state)
        self._svc.save()


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


# ── Advanced Page ─────────────────────────────────────────────────────────────


class AdvancedPage(QWidget):
    """Advanced / developer settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageWrapper")
        self._svc = registry.get(ISettingsService)
        scroll, vl = _make_page_scroll()
        _page_header(vl, "Advanced", "Developer and power-user settings.")

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
        reduce_row, self._reduce_rate_toggle = _toggle_row("Reduce update rate in background", True)
        perf_card.add_layout(reduce_row)
        self._reduce_rate_toggle.toggled.connect(self._on_reduce_rate_toggled)
        vl.addWidget(perf_card)

        danger_card = SettingsCard("⚠ Danger Zone", "Irreversible operations.")
        reset_btn = ThemedButton("Reset All Settings", ThemedButton.VARIANT_DANGER)
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
        self._reduce_rate_toggle.set_checked(
            self._svc.settings.general.reduce_update_rate_in_background, animated=False
        )

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
            f"<li><a href='https://github.com/GravityGuild/gravity_nexus' style='color: {_link_color};'>Changelog</a></li>"
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
