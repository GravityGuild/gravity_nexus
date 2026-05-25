from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget

from core.registry import registry
from services.protocols import ILogParserService, ISettingsService
from theme import FontSize, ColorRole
from ui.cards import SettingsCard
from ui.pages.pages import _toggle_row, _make_page_scroll, _page_header
from ui.widgets import ThemedButton, ThemedLabel


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
            "Handlers",
            "Each handler listens for a specific type of log event. "
            "Disabled handlers are skipped entirely — no CPU cost.",
        )
        vl.addWidget(handlers_card)

        # Track (matcher, toggle) pairs so Save can iterate them
        self._matcher_toggles: list[tuple] = []

        matchers = self._parser_svc.builtin_matchers
        if matchers:
            for matcher in matchers:
                if matcher.MATCHER_KEY == "raid_log":
                    continue  # managed on the Raid Tools page
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
