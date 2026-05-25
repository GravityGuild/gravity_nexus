"""ToolCard — collapsible accordion card with tabbed content and a header enable toggle."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.toggle_switch import ToggleSwitch

_QWIDGETSIZE_MAX = 16_777_215


class ToolCard(QFrame):
    """Collapsible card with a header enable toggle and tabbed body content.

    Layout::

        ┌─ ToolCardHeader ─────────────────────────────────────────┐
        │  ▼  Title                          [enable ToggleSwitch] │
        │     Description                                          │
        ├──────────────────────────────────────────────────────────┤
        │  Overview │ Instructions │ [Settings]                    │
        │  ─────────────────────────────────────────────────────── │
        │  <tab content>                                           │
        └──────────────────────────────────────────────────────────┘

    Clicking the header chrome (anywhere except the toggle) expands or collapses the body.
    The enable toggle wires directly to ``enabled_changed`` without affecting the accordion.
    """

    enabled_changed = Signal(bool)

    def __init__(
        self,
        title: str,
        description: str = "",
        enabled: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ToolCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._expanded = True
        self._settings_container: Optional[QWidget] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_header(title, description, enabled)
        self._build_body()
        self._build_animation()

        root.addWidget(self._header)
        root.addWidget(self._body_container)

        self._header.installEventFilter(self)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)

    # ── Construction helpers ───────────────────────────────────────────────────

    def _build_header(self, title: str, description: str, enabled: bool) -> None:
        self._header = QWidget()
        self._header.setObjectName("ToolCardHeader")

        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(10)

        self._chevron = QLabel("▼")
        self._chevron.setObjectName("ToolCardChevron")
        self._chevron.setFixedWidth(14)
        self._chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        hl.addWidget(self._chevron, alignment=Qt.AlignmentFlag.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("ToolCardTitle")
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title_col.addWidget(self._title_label)

        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setObjectName("ToolCardDescription")
            self._desc_label.setWordWrap(True)
            self._desc_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            title_col.addWidget(self._desc_label)

        hl.addLayout(title_col, 1)

        self._toggle = ToggleSwitch(checked=enabled)
        self._toggle.toggled.connect(self.enabled_changed)
        hl.addWidget(self._toggle, alignment=Qt.AlignmentFlag.AlignVCenter)

    def _build_body(self) -> None:
        self._body_container = QWidget()
        self._body_container.setObjectName("ToolCardBody")
        self._body_container.setMinimumHeight(0)

        bl = QVBoxLayout(self._body_container)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("ToolCardTabs")
        self._tab_widget.setMinimumWidth(0)

        self._overview_container = QWidget()
        self._overview_layout = QVBoxLayout(self._overview_container)
        self._overview_layout.setContentsMargins(16, 14, 16, 14)
        self._overview_layout.setSpacing(8)
        self._overview_layout.addStretch()

        self._instructions_container = QWidget()
        self._instructions_layout = QVBoxLayout(self._instructions_container)
        self._instructions_layout.setContentsMargins(16, 14, 16, 14)
        self._instructions_layout.setSpacing(8)
        self._instructions_layout.addStretch()

        self._tab_widget.addTab(self._overview_container, "Overview")
        self._tab_widget.addTab(self._instructions_container, "Instructions")
        bl.addWidget(self._tab_widget)

    def _build_animation(self) -> None:
        self._anim = QPropertyAnimation(self._body_container, b"maximumHeight", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.finished.connect(self._on_anim_finished)

    # ── Content API ────────────────────────────────────────────────────────────

    def add_overview_widget(self, widget: QWidget) -> None:
        """Prepend a widget into the Overview tab (before the trailing stretch)."""
        self._overview_layout.insertWidget(self._overview_layout.count() - 1, widget)

    def add_overview_layout(self, layout: QLayout) -> None:
        """Prepend a sub-layout into the Overview tab (before the trailing stretch)."""
        self._overview_layout.insertLayout(self._overview_layout.count() - 1, layout)

    def add_instructions_widget(self, widget: QWidget) -> None:
        """Prepend a widget into the Instructions tab (before the trailing stretch)."""
        self._instructions_layout.insertWidget(self._instructions_layout.count() - 1, widget)

    def add_instructions_layout(self, layout: QLayout) -> None:
        """Prepend a sub-layout into the Instructions tab (before the trailing stretch)."""
        self._instructions_layout.insertLayout(self._instructions_layout.count() - 1, layout)

    def add_settings_tab(self) -> QVBoxLayout:
        """Create the optional Settings tab on demand and return its layout."""
        if self._settings_container is not None:
            return self._settings_layout  # type: ignore[return-value]
        self._settings_container = QWidget()
        self._settings_layout = QVBoxLayout(self._settings_container)
        self._settings_layout.setContentsMargins(16, 14, 16, 14)
        self._settings_layout.setSpacing(8)
        self._settings_layout.addStretch()
        self._tab_widget.addTab(self._settings_container, "Settings")
        return self._settings_layout

    # ── State API ──────────────────────────────────────────────────────────────

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool, animated: bool = True) -> None:
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._chevron.setText("▼" if expanded else "▶")
        self._anim.stop()

        if expanded:
            self._body_container.show()
            self._body_container.setMaximumHeight(_QWIDGETSIZE_MAX)
            target = self._body_container.sizeHint().height()
            if animated:
                self._anim.setStartValue(0)
                self._anim.setEndValue(max(target, 1))
                self._anim.start()
            else:
                self._body_container.setMaximumHeight(_QWIDGETSIZE_MAX)
        else:
            current = self._body_container.height()
            if animated:
                self._anim.setStartValue(current)
                self._anim.setEndValue(0)
                self._anim.start()
            else:
                self._body_container.setMaximumHeight(0)
                self._body_container.hide()

    def is_tool_enabled(self) -> bool:
        return self._toggle.is_checked()

    def set_enabled(self, enabled: bool, animated: bool = True) -> None:
        self._toggle.set_checked(enabled, animated=animated)

    # ── Event filter — accordion click without intercepting the toggle ─────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._header and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:  # type: ignore[union-attr]
                toggle_local = self._toggle.mapFrom(
                    self._header, event.position().toPoint()  # type: ignore[union-attr]
                )
                if self._toggle.rect().contains(toggle_local):
                    return False  # let the click reach the ToggleSwitch normally
                self._toggle_expand()
                return True  # consumed — do not propagate
        return super().eventFilter(obj, event)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _toggle_expand(self) -> None:
        self.set_expanded(not self._expanded)

    def _on_anim_finished(self) -> None:
        if not self._expanded:
            self._body_container.hide()
        else:
            self._body_container.setMaximumHeight(_QWIDGETSIZE_MAX)
